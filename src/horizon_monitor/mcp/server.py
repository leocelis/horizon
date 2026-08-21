"""Horizon MCP server — built on FastMCP (mcp.server.fastmcp).

Exposes the full Horizon API as MCP primitives following the three-layer
model recommended by the MCP specification and Anthropic's tool-writing guide:

  ┌─────────────────────────────────────────────────────────────────────┐
  │  Tools      (model-controlled, state-changing / live computation)   │
  │    new_conversation   process_turn   configure_session              │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Resources  (application-controlled, read-only, cacheable context)  │
  │    horizon://session/{id}/trajectory                                │
  │    horizon://session/{id}/events                                    │
  ├─────────────────────────────────────────────────────────────────────┤
  │  Prompts    (user-controlled, reusable workflow templates)          │
  │    monitor_conversation                                             │
  └─────────────────────────────────────────────────────────────────────┘

Transport support (all via FastMCP):
  stdio            — default; Cursor / Claude Desktop / any local client.
  sse              — legacy web transport; still widely supported.
  streamable-http  — production / multi-user / enterprise deployments.

Cursor integration (.cursor/mcp.json):
    {
      "mcpServers": {
        "horizon": {
          "command": "/path/to/venv/bin/python",
          "args": ["-m", "horizon_monitor.mcp.server"],
          "env": {}
        }
      }
    }

Claude Desktop (claude_desktop_config.json) — same shape, different file.

Privacy guarantee: the monitor stores embeddings and metrics only — raw text
is never persisted. All computation is fully local; adding this server adds
zero network calls beyond the MCP stdio/HTTP pipe itself.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import time
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from horizon_monitor import Config, FidelityMonitor, __version__
from horizon_monitor.mcp.auth import current_key_id, current_key_sha
from horizon_monitor.mcp.session_registry import SessionOwnershipError, SessionRegistry
from horizon_monitor.memento import engine as memento_engine
from horizon_monitor.memento import propose as memento_propose
from horizon_monitor.memento import signals as memento_signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.errors import MementoError, TenantResolutionError
from horizon_monitor.memento.models import EventKind, ItemKind, Provenance
from horizon_monitor.memento.store import MementoStore
from horizon_monitor.monitor import SessionNotFoundError

# Per-key session cap on the hosted multi-tenant server (see session_registry.py
# for why this lives at the server layer, not in FidelityMonitor itself).
_MAX_SESSIONS_PER_KEY = int(os.environ.get("HORIZON_MAX_SESSIONS_PER_KEY", "50"))
_registry = SessionRegistry(max_sessions_per_key=_MAX_SESSIONS_PER_KEY)

_NOT_FOUND_HINT = "Call new_conversation first."


def _resolve_eval_instant(timestamp: str | None) -> tuple[datetime, str]:
    """Resolve the evaluation instant and say where it came from.

    The engine itself is pure — ``t_eval`` is always a parameter
    (memento_engine_intent.yaml::pure_function_injected_time). Somebody at the
    boundary must still read a wall clock when the host does not inject one, so
    this is the ONE place that may, and every report it feeds carries
    ``eval_instant_source`` so an auditor can tell a host-injected instant from
    a boundary default. Two identical calls with no ``timestamp`` legitimately
    differ; the field is what makes that visible instead of silent.
    """
    if timestamp:
        return datetime.fromisoformat(timestamp), "injected"
    return datetime.now(timezone.utc), "host_clock"


def _session_not_found_response(session_id: str) -> dict:
    """Same error shape for 'unknown session' and 'not your session' —
    a caller must not be able to distinguish the two (see SessionOwnershipError)."""
    return {"error": f"Unknown session_id: {session_id!r}", "hint": _NOT_FOUND_HINT}


def _register_session(sid: str, monitor: FidelityMonitor) -> None:
    """Record ownership for a newly created session; end+evict the oldest
    session of the SAME key if the caller is now over their cap."""
    key_id = current_key_id.get()
    evicted = _registry.register(sid, key_id)
    if evicted is not None:
        monitor.end_conversation(evicted)
        _log.info("SESSION  evicted (per-key cap)  key=%s  session=%s", key_id, evicted[:8] + "…")


# ── Structured log — file for local Cursor use, stdout for DO/production ──────
_LOG_PATH = os.path.expanduser("~/.cursor/horizon_mcp.log")
_handlers: list[logging.Handler] = []
if os.environ.get("HORIZON_ENV") == "production":
    _handlers.append(logging.StreamHandler())
else:
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        _handlers.append(logging.FileHandler(_LOG_PATH, mode="a"))
    except OSError:
        _handlers.append(logging.StreamHandler())
logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", handlers=_handlers)
_log = logging.getLogger("horizon_monitor.mcp")

try:
    from mcp.server.fastmcp import FastMCP
    from mcp.server.sse import TransportSecuritySettings
except ImportError as exc:
    raise ImportError("MCP support requires: pip install 'horizon-monitor[mcp]'") from exc


def _transport_security() -> TransportSecuritySettings | None:
    """
    Build TransportSecuritySettings for production deployments.

    In production (HORIZON_ENV=production) DNS rebinding protection is
    configured with explicit allowed hosts. Bearer token auth (HorizonAuthMiddleware)
    is the primary access control layer. If HORIZON_ALLOWED_HOSTS is not set,
    DNS rebinding protection is disabled entirely — safe because every non-/health
    request still requires a valid Bearer token.
    """
    if os.environ.get("HORIZON_ENV") != "production":
        return None  # default FastMCP behaviour (localhost only) for local dev

    raw = os.environ.get("HORIZON_ALLOWED_HOSTS", "")
    hosts = [h.strip() for h in raw.split(",") if h.strip()]

    if hosts:
        return TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=hosts,
        )
    # No explicit list: disable DNS rebinding protection — auth middleware gates access
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


# ── Server-level instructions ─────────────────────────────────────────────────
#
# Cursor and Claude Desktop surface these instructions to the agent before the
# conversation starts, giving it a one-paragraph orientation without requiring
# a project-specific system prompt.

_INSTRUCTIONS = """
Horizon Fidelity Monitor — invisible 4D conversation health tracking.

CALL ORDER — deferred recording (eliminates response duplication)

  Turn 1 only:
    • Call new_conversation. Store session_id. Say nothing about it.
    • Do your work. Output your response.

  Every subsequent turn (turn 2, 3, …):
    • FIRST: call process_turn with the PREVIOUS turn's data from conversation history:
        session_id    — stored from new_conversation
        human_message — the user's message from the PREVIOUS turn
        agent_response — your response from the PREVIOUS turn
        timestamp     — ISO 8601 from your system context (do NOT run a shell command)
    • THEN: do your work for the current turn and output your response.

  This order guarantees the tool call fires before any text is generated,
  eliminating the duplication caused by calling it mid-stream or at the end.

PROCESS_TURN RESPONSE CONTRACT
  {"ok": true,  "turn": N}                         → ignore entirely, proceed normally
  {"ok": false, "health_status", "active_events"}  → route EACH event by its
    `plane` field:
      plane "conversation" → silently apply suggested_behavior to the current
        reply. Say nothing about it.
      plane "mission"      → SURFACE it: state the signal with its numbers and
        derivation, then propose ONE concrete next action. Never absorb a mission
        signal silently — a deadline nobody hears about is the failure that plane
        exists to prevent. Full rules: docs/integrations/MEMENTO_MORI_AGENTS.md.
    (The mission plane is inert unless a mission store is configured; with none,
    no mission events are ever emitted and its tools do not appear.)

INVISIBILITY CONTRACT (non-negotiable — CONVERSATION plane only)
  - Never mention Horizon, session_id, fidelity, monitoring, or turn number in any user-facing reply
  - session_id is for MCP tool/resource calls only — never surface it to the user
  - Never narrate Horizon calls in thinking steps or intermediate text
  - Never use confidence markers (✓/~/?) on Horizon state
  - Never read trajectory or events Resources proactively — only when an active event fires (ok: false)
  - Never call configure_session automatically — only on explicit user request
  - Treat the conversation plane like a background logger: silent, never surfaced.
    Mission-plane signals are the documented exception: they are surfaced, with
    their numbers, by design.

SAFE TO AUTO-RUN:
  new_conversation, process_turn

REQUIRE HUMAN APPROVAL:
  configure_session
""".strip()

# ── FastMCP app ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    "horizon-fidelity-monitor",
    instructions=_INSTRUCTIONS,
    transport_security=_transport_security(),
)


# ─────────────────────────────────────────────────────────────────────────────
# MEMENTO MORI — optional mission plane (docs/integrations/MEMENTO_MORI_AGENTS.md)
# ─────────────────────────────────────────────────────────────────────────────
#
# The mission plane is LOUD (unlike the conversation plane above, which stays
# invisible): its tool descriptions carry the surface-don't-absorb line so a
# schema-only client still inherits the behavioral contract (test plan M-5).

_LOUD_CONTRACT_LINE = (
    "This is the Memento Mori MISSION plane, not the conversation monitor: "
    "surface this to the operator with its numbers; never absorb it silently. "
    "See docs/integrations/MEMENTO_MORI_AGENTS.md §1-2."
)


def _memento_store_path_from_env() -> Path | None:
    """None => the mission plane is disabled entirely; no store is opened
    and its six tools never register (test plan M-1), mirroring
    memento_signals_intent.yaml::strict_additivity's "code path not
    entered" mechanism."""
    raw = os.environ.get("HORIZON_MEMENTO_STORE_PATH")
    return Path(raw) if raw else None


def _memento_store_dsn_from_env() -> str | None:
    """MySQL DSN for durable multi-tenant deployments (mysql://user:pass@host/db).
    Wins over HORIZON_MEMENTO_STORE_PATH when both are set. Requires the
    [mysql] extra and a CA certificate — see memento/backends/mysql.py."""
    return os.environ.get("HORIZON_MEMENTO_STORE_DSN") or None


def _jsonable(obj: Any) -> Any:
    """Round-trip through JSON so Decimal/date/datetime values in a memento
    report become JSON-native before crossing the MCP wire, the same way
    the trajectory/events Resources already do with `default=str`."""
    return json.loads(json.dumps(obj, default=str))


def _serialize_memento_error(exc: MementoError) -> dict:
    """{error_type, rule, fix} — never a stack trace, never a silent
    coercion (test plan M-2 [GOLDEN]). Every horizon_monitor.memento.errors
    exception sets `.rule` and `.fix` as first-class attributes (see
    memento/errors.py); reading them directly avoids regex-parsing the
    human-readable message, which broke on rule text containing its own
    sentence breaks (e.g. PersonRankingRefusedError) during the first pass
    at this function — see the M-2 section of the implementation report."""
    return {"error_type": type(exc).__name__, "rule": exc.rule, "fix": exc.fix}


def _parse_item_kwargs(item: dict) -> dict[str, Any]:
    """Map the `item` dict from `clock_register` onto
    `MementoStore.register_item`'s keyword arguments. Every value is either
    caller-supplied verbatim or a straightforward type parse — no default is
    invented for a field the caller omitted (facts_are_caller_provided)."""
    kwargs: dict[str, Any] = {
        "kind": ItemKind(item["kind"]),
        "title": item["title"],
        "created_valid": datetime.fromisoformat(item["created_valid"]),
    }
    if item.get("parent_id") is not None:
        kwargs["parent_id"] = item["parent_id"]
    for date_field in ("end_date", "revisit_date", "ttl_start", "ttl_end", "deadline_date"):
        if item.get(date_field) is not None:
            kwargs[date_field] = date.fromisoformat(item[date_field])
    for passthrough in (
        "deadline_kind",
        "gates_item_id",
        "age_budget_days",
        "stall_days",
        "namespace",
    ):
        if item.get(passthrough) is not None:
            kwargs[passthrough] = item[passthrough]
    if item.get("person_namespace_confirmed") is not None:
        kwargs["person_namespace_confirmed"] = bool(item["person_namespace_confirmed"])
    if item.get("amount") is not None:
        kwargs["amount"] = Decimal(str(item["amount"]))
    return kwargs


def _parse_event_kwargs(event: dict) -> dict[str, Any]:
    """Map the `event` dict from `clock_progress` onto
    `MementoStore.record_event`'s keyword arguments."""
    kwargs: dict[str, Any] = {
        "kind": EventKind(event["kind"]),
        "valid_time": datetime.fromisoformat(event["valid_time"]),
    }
    if event.get("tx_time") is not None:
        kwargs["tx_time"] = datetime.fromisoformat(event["tx_time"])
    for passthrough in ("stage", "wait_or_touch", "correction_of"):
        if event.get(passthrough) is not None:
            kwargs[passthrough] = event[passthrough]
    if event.get("payload") is not None:
        kwargs["payload"] = event["payload"]
    provenance = event.get("provenance")
    if provenance is not None:
        kwargs["provenance"] = Provenance(
            source_system=provenance.get("source_system"),
            native_id=provenance.get("native_id"),
            raw_timestamp=(
                datetime.fromisoformat(provenance["raw_timestamp"])
                if provenance.get("raw_timestamp")
                else None
            ),
        )
    return kwargs


def register_memento_tools(
    app: FastMCP, store_path: Path | None, dsn: str | None = None
) -> tuple[MementoStore, MementoConfig] | None:
    """Register the six mission-plane tools on `app` iff `store_path` is
    not None. With `store_path=None`, this function returns None and
    registers NOTHING — the six tools are absent from `app`'s tool
    discovery entirely, not merely disabled when called (test plan M-1),
    the same "code path not entered" mechanism `store_path=None` already
    guarantees for the library API (G-10).

    Returns the constructed `(MementoStore, MementoConfig)` so the caller
    can hand the same store to the `FidelityMonitor` singleton that backs
    `process_turn` — one store, one config, shared by the tools and the
    turn pipeline.
    """
    if store_path is None and dsn is None:
        return None

    # Tenant used by callers that carry NO authenticated key — stdio sessions
    # and the library path. Defaults to "local". Set HORIZON_MEMENTO_TENANT_ID
    # to run a local server against a shared (e.g. hosted) store and see the
    # SAME tenant the hosted server would resolve for your API key; or point it
    # at a scratch tenant to try things without touching real missions.
    # It never overrides an authenticated caller: when a bearer key is present
    # the key's mapping in horizon_api_keys wins, so this cannot be used to
    # reach another tenant's data over an authenticated transport.
    default_tenant = os.environ.get("HORIZON_MEMENTO_TENANT_ID", "local").strip() or "local"
    memento_store = MementoStore(store_path, dsn=dsn, tenant_id=default_tenant)
    memento_config = MementoConfig(store_path=store_path)

    # ── Per-request tenant scoping ────────────────────────────────────────
    # The store binds once per process (one backend connection); the TENANT
    # is resolved per call from the authenticated key's full sha256 and
    # bound as a lightweight scope over the same connection. Unknown or
    # revoked keys FAIL CLOSED with a typed error — the mission plane never
    # auto-provisions a tenant (see MementoStore.resolve_tenant_for_key_sha).
    # stdio / auth-disabled callers carry no key sha and use the default
    # tenant above (HORIZON_MEMENTO_TENANT_ID, else 'local').
    _tenant_cache: dict[str, tuple[str, float]] = {}
    _TENANT_CACHE_TTL_S = 60.0  # revocation bites within a minute

    def _scoped_store() -> MementoStore:
        key_sha = current_key_sha.get()
        if not key_sha:
            return memento_store  # default tenant — the stdio / library path
        now = time.monotonic()
        hit = _tenant_cache.get(key_sha)
        if hit is not None and now - hit[1] < _TENANT_CACHE_TTL_S:
            return memento_store.scoped(hit[0])
        tenant_id = memento_store.resolve_tenant_for_key_sha(key_sha)
        if tenant_id is None:
            _tenant_cache.pop(key_sha, None)
            raise TenantResolutionError()
        _tenant_cache[key_sha] = (tenant_id, now)
        return memento_store.scoped(tenant_id)

    def _scoped_store_or_none() -> MementoStore | None:
        """Same resolution, but returns None instead of raising.

        process_turn's mission-signal path must never raise, so an unmapped or
        revoked key becomes "no mission events" rather than an exception.
        """
        try:
            return _scoped_store()
        except TenantResolutionError:
            return None

    global _MEMENTO_SCOPE_RESOLVER
    _MEMENTO_SCOPE_RESOLVER = _scoped_store_or_none

    @app.tool(
        name="clock_register",
        title="Register or update a clocked mission item",
        description=(
            "Create a rooted-tree item (kind: horizon | mission | task | deadline | "
            "gate | entity | deferral | probe) in the mission store. `item` carries "
            "kind, title, created_valid (ISO 8601), and kind-specific fields "
            "(end_date, revisit_date, ttl_start/ttl_end, deadline_date, "
            "deadline_kind, gates_item_id, age_budget_days, stall_days, namespace, "
            "amount, parent_id). Schema violations (undated deferral, root-less "
            "item, unflagged person namespace, duplicate/non-finite root, ...) "
            "return a typed {error_type, rule, fix} — relay it to the operator "
            "verbatim, never route around it; e.g. an undated deferral means ask "
            "the operator for a revisit_date, never invent one. " + _LOUD_CONTRACT_LINE
        ),
    )
    def clock_register(item: dict) -> dict:
        try:
            item_id = _scoped_store().register_item(**_parse_item_kwargs(item))
            return {"item_id": item_id}
        except MementoError as exc:
            return {"error": _serialize_memento_error(exc)}

    @app.tool(
        name="clock_progress",
        title="Record a mission progress/stage/artifact event",
        description=(
            "Append one event (kind: progress | stage_enter | stage_exit | "
            "artifact | ratify | ack) to an item's bitemporal log. `event` carries "
            "kind, valid_time (ISO 8601, when the fact happened), and optionally "
            "stage, wait_or_touch, payload, correction_of, and provenance "
            "(required for kind=artifact: source_system, native_id, "
            "raw_timestamp). Record this as a side effect of real work in the "
            "SAME turn — never a separate logging session, never a fabricated or "
            "assumed event. " + _LOUD_CONTRACT_LINE
        ),
    )
    def clock_progress(item_id: str, event: dict) -> dict:
        try:
            event_id = _scoped_store().record_event(item_id=item_id, **_parse_event_kwargs(event))
            return {"event_id": event_id}
        except MementoError as exc:
            return {"error": _serialize_memento_error(exc)}

    @app.tool(
        name="clock_status",
        title="Full mission clock surface",
        description=(
            "Return the ClockReport for `timestamp` (the host-injected evaluation "
            "instant; ISO 8601 — omit only when you genuinely have no clock): ages, "
            "TTL states, latencies, horizon shares, path comparisons, and money "
            "(only when a rate is declared). Optional `scope` (a mission_id) "
            "filters the report to that mission's subtree. Open your first "
            "substantive reply for an associated mission with any red state here, "
            "numbers included. " + _LOUD_CONTRACT_LINE
        ),
    )
    def clock_status(scope: str | None = None, timestamp: str | None = None) -> dict:
        try:
            t_eval, instant_source = _resolve_eval_instant(timestamp)
            snapshot = _scoped_store().snapshot()
            report = memento_engine.evaluate(snapshot, t_eval, memento_config)
            d = report.to_dict()
            d["eval_instant_source"] = instant_source
            if scope:
                items_by_id = {i.item_id: i for i in snapshot.items}

                def _in_scope(iid: str) -> bool:
                    return (
                        iid == scope
                        or memento_signals.mission_scope_for_item(iid, items_by_id) == scope
                    )

                d["items"] = [row for row in d["items"] if _in_scope(row["item_id"])]
                d["slowest_entities"] = [
                    s for s in d["slowest_entities"] if s["mission_id"] == scope
                ]
                d["money"] = [m for m in d["money"] if _in_scope(m["item_id"])]
                d["path_comparisons"] = [
                    p for p in d["path_comparisons"] if p["mission_id"] == scope
                ]
            return _jsonable(d)
        except MementoError as exc:
            return {"error": _serialize_memento_error(exc)}

    @app.tool(
        name="clock_propose",
        title="Inert TTL or break-even proposal from recorded history",
        description=(
            "kind='ttl': nearest-rank `percentile` (default P80) over the "
            "caller-supplied `completed_durations_days` — an empty list returns "
            "proposal=null, never an invented default. kind='breakeven': "
            "cost_setup, rate, setup_hours, delta_t_hours, lam_per_day (all "
            "caller-measured) at `timestamp`. Either way the return is "
            "{item_id, kind, value, sample_size, derivation} and is INERT: "
            "nothing is applied until an explicit clock_progress(kind=ratify) "
            "write. Present the derivation and sample size; the operator "
            "ratifies. " + _LOUD_CONTRACT_LINE
        ),
    )
    def clock_propose(
        item_id: str,
        kind: str,
        completed_durations_days: list[int] | None = None,
        percentile: float | None = None,
        cost_setup: str | None = None,
        rate: str | None = None,
        setup_hours: str | None = None,
        delta_t_hours: str | None = None,
        lam_per_day: float | None = None,
        timestamp: str | None = None,
    ) -> dict:
        try:
            if kind == "ttl":
                proposal = memento_propose.ttl_proposal(
                    item_id=item_id,
                    completed_durations_days=completed_durations_days or [],
                    percentile=(
                        percentile
                        if percentile is not None
                        else memento_config.ttl_proposal_percentile
                    ),
                )
            elif kind == "breakeven":
                t_eval = _resolve_eval_instant(timestamp)[0]
                proposal = memento_propose.breakeven_proposal(
                    item_id=item_id,
                    t_eval=t_eval.date(),
                    cost_setup=Decimal(str(cost_setup)),
                    rate=Decimal(str(rate)),
                    setup_hours=Decimal(str(setup_hours)),
                    delta_t_hours=Decimal(str(delta_t_hours)),
                    lam_per_day=lam_per_day,
                )
            else:
                return {
                    "error": {
                        "error_type": "ValueError",
                        "rule": "clock_propose.kind",
                        "fix": "kind must be 'ttl' or 'breakeven'",
                    }
                }
            if proposal is None:
                return {"proposal": None}
            return {"proposal": _jsonable(dataclasses.asdict(proposal))}
        except MementoError as exc:
            return {"error": _serialize_memento_error(exc)}

    @app.tool(
        name="clock_ack",
        title="Acknowledge a fired mission signal",
        description=(
            "Move the (item_id, signal_type) alarm state machine to ACKED, "
            "recording `actor`. Call this ONLY on the operator's explicit "
            "acknowledgement of that exact signal — never self-ack to quiet a "
            "signal you find repetitive; the engine already caps and "
            "edge-triggers, and silence belongs to the operator, not the agent. "
            "Authorization is enforced by host rules, not by this tool. " + _LOUD_CONTRACT_LINE
        ),
    )
    def clock_ack(item_id: str, signal_type: str, actor: str, timestamp: str | None = None) -> dict:
        try:
            t_eval, _ = _resolve_eval_instant(timestamp)
            _store = _scoped_store()
            prior = _store.get_fire_state(item_id, signal_type) or {}
            current_rung = prior.get("rung", 0)
            new_state = memento_signals.ack(
                item_id=item_id,
                signal_type=signal_type,
                valid_time=t_eval,
                actor=actor,
                current_rung=current_rung if isinstance(current_rung, int) else 0,
            )
            _store.set_fire_state(item_id, signal_type, new_state)
            event_id = _store.record_event(
                item_id=item_id,
                kind=EventKind.ACK,
                valid_time=t_eval,
                payload={"signal_type": signal_type, "actor": actor},
            )
            return {"acked": True, "event_id": event_id}
        except MementoError as exc:
            return {"error": _serialize_memento_error(exc)}

    @app.tool(
        name="associate_mission",
        title="Bind this session to a mission",
        description=(
            "Bind `session_id` to `mission_id` so that mission's due signals "
            "(post-cap, at most one new per turn) start arriving in "
            'process_turn\'s active_events, tagged plane="mission". Without '
            "this call, a configured mission store still emits ZERO events into "
            "this session. Call at the start of any conversation that concerns a "
            "known mission, before the first clock_status. " + _LOUD_CONTRACT_LINE
        ),
    )
    def associate_mission(session_id: str, mission_id: str) -> dict:
        monitor = _get_monitor()
        monitor.associate_mission(session_id, mission_id)
        return {"associated": True, "session_id": session_id, "mission_id": mission_id}

    return memento_store, memento_config


_MEMENTO_SCOPE_RESOLVER = None  # set by register_memento_tools when a store exists
_MEMENTO_STORE_PATH = _memento_store_path_from_env()
_MEMENTO_STORE_DSN = _memento_store_dsn_from_env()
_memento_registration = register_memento_tools(mcp, _MEMENTO_STORE_PATH, _MEMENTO_STORE_DSN)
_memento_store: MementoStore | None
_memento_config: MementoConfig
if _memento_registration is not None:
    _memento_store, _memento_config = _memento_registration
else:
    _memento_store, _memento_config = None, MementoConfig()


# ── Singleton monitor ─────────────────────────────────────────────────────────
#
# One monitor per server process. Stateless between MCP connections for stdio
# (each Cursor session spawns a fresh process), stateful for SSE/HTTP (the
# process persists across connections).

_monitor: FidelityMonitor | None = None


def _get_monitor() -> FidelityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = FidelityMonitor(memento_store=_memento_store, memento_config=_memento_config)
    # Mission signals must come from the CALLER's tenant, not the process
    # default. The six mission tools scope themselves; this path is a separate
    # consumer and needs the same resolver installed.
    _monitor._memento_store_resolver = _MEMENTO_SCOPE_RESOLVER
    return _monitor


# ─────────────────────────────────────────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────────────────────────────────────────


@mcp.tool(
    name="new_conversation",
    title="Start a new Horizon session",
    description=(
        "Initialise a new Horizon conversation session. "
        "Call ONCE per distinct task or chat thread and store the returned "
        "session_id — it is required by every other tool and resource. "
        "Optionally pass metadata to set domain, user_id, or agent_name; "
        "these are embedded in trajectory reports but never sent off-device. "
        "Do NOT call for each turn — one session tracks the whole thread. "
        "To reset tracking mid-conversation, call new_conversation again and "
        "discard the old session_id."
    ),
)
def new_conversation(
    metadata: dict | None = None,
) -> dict:
    """Create a new Horizon session. Returns {session_id: str}."""
    monitor = _get_monitor()
    sid = monitor.new_conversation(metadata=metadata)
    _register_session(sid, monitor)
    _log.info(
        "TOOL  new_conversation  key=%s  session=%s  metadata=%s",
        current_key_id.get(),
        sid[:8] + "…",
        metadata,
    )
    return {"session_id": sid}


@mcp.tool(
    name="process_turn",
    title="Record a conversation turn",
    description=(
        "Record one human-agent turn and return a minimal action signal. "
        "Use deferred recording: on turn 2+, call at the START of the turn with the "
        "PREVIOUS turn's human_message and agent_response (not the current turn). "
        "Turn 1: call new_conversation only — no process_turn yet. "
        "Requires an active session_id from new_conversation.\n\n"
        "Return shape:\n"
        "  • {ok: true,  turn: N}                          — session healthy, nothing to do\n"
        "  • {ok: false, health_status, active_events: []} — action required\n\n"
        "When ok is false, each active_event contains:\n"
        "  • type              — e.g. 'alert.drift', 'alert.contradiction'\n"
        "  • suggested_behavior — exact text to follow\n\n"
        "Full fidelity metrics are available via the Resources:\n"
        "  horizon://session/{session_id}/trajectory\n"
        "  horizon://session/{session_id}/events\n\n"
        "Pass timestamp (ISO 8601) to enable temporal and spacetime signals. "
        "Pass client_context with device_type and timezone for spatial signals."
    ),
)
def process_turn(
    session_id: str,
    human_message: str,
    agent_response: str,
    timestamp: str | None = None,
    client_context: dict | None = None,
) -> dict:
    """
    Record one turn. Returns a minimal action signal.

    When the session is healthy and no events are active, returns:
        {"ok": True, "turn": N}

    When action is needed, returns:
        {"ok": False, "health_status": ..., "active_events": [{type, suggested_behavior}, ...]}

    Full TurnResult metrics are accessible via the trajectory/events Resources.

    Args:
        session_id: UUID from new_conversation().
        human_message: The user's message text.
        agent_response: The agent's reply text.
        timestamp: ISO 8601 wall-clock time, e.g. '2026-05-06T15:30:00+00:00'.
                   Omit only when you genuinely have no clock (rare).
        client_context: Optional dict. Recognised keys:
            device_type  — 'mobile'|'tablet'|'laptop'|'desktop'|'tv'
            timezone     — IANA tz name, e.g. 'America/Sao_Paulo'
            location_class — 'inferred'|'explicit'|'unknown' (override GeoIP)
            ip_address   — IPv4/IPv6 string (enables GeoIP lookup)
            geoip_db_path — path to MaxMind .mmdb file
    """
    monitor = _get_monitor()
    try:
        _registry.check(session_id, current_key_id.get())
        result = monitor.process_turn(
            session_id=session_id,
            human_message=human_message,
            agent_response=agent_response,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            client_context=client_context,
        )
        d = dataclasses.asdict(result)
        active_evs = [e for e in d.get("events", []) if e.get("active")]
        _log.info(
            "TOOL  process_turn  key=%s  session=%s  turn=%s  fidelity=%.3f  health=%s  "
            "gap=%s  retention=%s  active_events=%s",
            current_key_id.get(),
            session_id[:8] + "…",
            d["turn_number"],
            d["fidelity_score"],
            d["health_status"],
            d.get("gap_class", "n/a"),
            (
                f"{d['estimated_retention']:.0%}"
                if d.get("estimated_retention") is not None
                else "n/a"
            ),
            [e["type"] for e in active_evs] if active_evs else "none",
        )
        is_healthy = d["health_status"] == "healthy" and not active_evs
        if is_healthy:
            return {"ok": True, "turn": d["turn_number"]}
        return {
            "ok": False,
            "health_status": d["health_status"],
            "active_events": [
                {
                    "type": e["type"],
                    "suggested_behavior": e["suggested_behavior"],
                }
                for e in active_evs
            ],
        }
    except SessionNotFoundError as exc:
        _log.warning("TOOL  process_turn  key=%s  ERROR: %s", current_key_id.get(), exc)
        return {"error": str(exc), "hint": "Call new_conversation first."}
    except SessionOwnershipError:
        _log.warning(
            "TOOL  process_turn  key=%s  ERROR: not owner of session=%s",
            current_key_id.get(),
            session_id[:8] + "…",
        )
        return _session_not_found_response(session_id)


@mcp.tool(
    name="configure_session",
    title="Override thresholds or event modes",
    description=(
        "Override Horizon thresholds and event modes for a specific session "
        "or, when session_id is omitted, every session YOU own (on the hosted "
        "multi-tenant server, this never touches another API key's sessions — "
        "see the tool result's 'sessions_affected' count). "
        "REQUIRES HUMAN APPROVAL — this mutates session config. "
        "Do NOT auto-run this tool. "
        "\n\nCommon use cases:\n"
        "  • Tighten clarification threshold for a customer-support domain: "
        "    {session_id, clarification_threshold: 0.15}\n"
        "  • Flip an event to active mode: "
        "    {session_id, event_modes: {'alert.drift': 'active'}}\n"
        "  • Set half-life for a long-running thread: "
        "    {session_id, context_half_life_hours: 4}\n"
        "\n"
        "To read current fidelity without changing anything, "
        "use the Resources or process_turn instead."
    ),
)
def configure_session(
    session_id: str | None = None,
    clarification_threshold: float | None = None,
    convergence_window: int | None = None,
    event_modes: dict | None = None,
    domain: str | None = None,
    chronotype_offset: float | None = None,
    context_half_life_hours: float | None = None,
) -> dict:
    """
    Override session config. Returns {applied: dict, warnings: list}.

    Omit session_id to apply to every session the CALLING key owns (see
    session_registry.py). A local/stdio caller (no API key — single-tenant by
    construction) instead gets the original unrestricted behavior: apply to
    the shared default config and every existing session, since there is no
    other tenant it could affect.
    """
    monitor = _get_monitor()
    kwargs: dict[str, Any] = {}
    if clarification_threshold is not None:
        kwargs["clarification_threshold"] = clarification_threshold
    if convergence_window is not None:
        kwargs["convergence_window"] = convergence_window
    if event_modes is not None:
        kwargs["event_modes"] = event_modes
    if domain is not None:
        kwargs["domain"] = domain
    if chronotype_offset is not None:
        kwargs["chronotype_offset"] = chronotype_offset
    if context_half_life_hours is not None:
        kwargs["context_half_life_hours"] = context_half_life_hours

    key_id = current_key_id.get()
    try:
        if session_id is not None:
            _registry.check(session_id, key_id)
            result = monitor.configure(session_id=session_id, **kwargs)
            d = dataclasses.asdict(result)
            d["sessions_affected"] = 1
        elif key_id == "local":
            # No API key involved (stdio / direct library usage) — there is no
            # other tenant to protect, so the original global-default
            # semantics (mutate the shared config template + every existing
            # session) are safe and remain the useful behavior.
            result = monitor.configure(session_id=None, **kwargs)
            d = dataclasses.asdict(result)
            d["sessions_affected"] = monitor.session_count
        else:
            # Authenticated multi-tenant caller with no session_id: "global"
            # is reinterpreted as "every session I own" — never the shared
            # default template, never another key's sessions.
            owned = _registry.owned_sessions(key_id)
            applied: dict = {}
            warnings: list = []
            for sid in owned:
                result = monitor.configure(session_id=sid, **kwargs)
                applied = result.applied
                warnings.extend(result.warnings)
            d = {
                "applied": applied,
                "warnings": [dataclasses.asdict(w) for w in warnings],
                "sessions_affected": len(owned),
            }
        _log.info(
            "TOOL  configure_session  key=%s  session=%s  sessions_affected=%s  applied=%s",
            key_id,
            str(session_id)[:8],
            d["sessions_affected"],
            d["applied"],
        )
        return d
    except SessionNotFoundError as exc:
        _log.warning("TOOL  configure_session  key=%s  ERROR: %s", key_id, exc)
        return {"error": str(exc), "hint": "Call new_conversation first."}
    except SessionOwnershipError:
        _log.warning(
            "TOOL  configure_session  key=%s  ERROR: not owner of session=%s",
            key_id,
            str(session_id)[:8] + "…",
        )
        return _session_not_found_response(session_id)


# ─────────────────────────────────────────────────────────────────────────────
# RESOURCES
# ─────────────────────────────────────────────────────────────────────────────
#
# Resources are passive, read-only, and cacheable. They should be used as
# context injected before a response, not via a tool-call slot. Cursor can
# attach them directly to the conversation context.


@mcp.resource(
    uri="horizon://session/{session_id}/trajectory",
    name="session_trajectory",
    title="Fidelity trajectory for a session",
    description=(
        "Read-only fidelity arc for the given session. Use this as conversation "
        "context before composing a long response. Contains: per-turn fidelity "
        "scores, gap durations, IGT trend (negative = converging), health_status, "
        "estimated optimal conversation length (t_star), and current_fidelity. "
        "Does NOT modify any session state — safe to read at any time."
    ),
    mime_type="application/json",
)
def get_trajectory(session_id: str) -> str:
    """Return the fidelity trajectory for a session as JSON."""
    monitor = _get_monitor()
    try:
        _registry.check(session_id, current_key_id.get())
        traj = monitor.get_trajectory(session_id)
        d = dataclasses.asdict(traj)
        _log.info(
            "RESOURCE  trajectory  key=%s  session=%s  turns=%s  health=%s  fidelity=%.3f",
            current_key_id.get(),
            session_id[:8] + "…",
            d["turn_count"],
            d["health_status"],
            d["current_fidelity"],
        )
        return json.dumps(d, indent=2, default=str)
    except SessionNotFoundError as exc:
        _log.warning("RESOURCE  trajectory  key=%s  ERROR: %s", current_key_id.get(), exc)
        return json.dumps({"error": str(exc), "hint": "Call new_conversation first."})
    except SessionOwnershipError:
        _log.warning(
            "RESOURCE  trajectory  key=%s  ERROR: not owner of session=%s",
            current_key_id.get(),
            session_id[:8] + "…",
        )
        return json.dumps(_session_not_found_response(session_id))


@mcp.resource(
    uri="horizon://session/{session_id}/events",
    name="session_events",
    title="Event log for a session",
    description=(
        "Read-only list of all Horizon events fired in the session. Each event "
        "has: type, active (bool), confidence, turn, suggested_behavior, metadata. "
        "Active events are the actionable ones — check these before composing a "
        "response in a long-running conversation. "
        "Does NOT modify any session state — safe to read at any time."
    ),
    mime_type="application/json",
)
def get_events(session_id: str) -> str:
    """Return all events for a session as JSON."""
    monitor = _get_monitor()
    try:
        _registry.check(session_id, current_key_id.get())
        events = monitor.get_events(session_id)
        active = [dataclasses.asdict(e) for e in events if e.active]
        all_events = [dataclasses.asdict(e) for e in events]
        _log.info(
            "RESOURCE  events  key=%s  session=%s  total=%s  active=%s  active_types=%s",
            current_key_id.get(),
            session_id[:8] + "…",
            len(all_events),
            len(active),
            [e["type"] for e in active] if active else "none",
        )
        return json.dumps(
            {
                "active_events": active,
                "all_events": all_events,
                "active_count": len(active),
                "total_count": len(all_events),
            },
            indent=2,
            default=str,
        )
    except SessionNotFoundError as exc:
        _log.warning("RESOURCE  events  key=%s  ERROR: %s", current_key_id.get(), exc)
        return json.dumps({"error": str(exc), "hint": "Call new_conversation first."})
    except SessionOwnershipError:
        _log.warning(
            "RESOURCE  events  key=%s  ERROR: not owner of session=%s",
            current_key_id.get(),
            session_id[:8] + "…",
        )
        return json.dumps(_session_not_found_response(session_id))


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS
# ─────────────────────────────────────────────────────────────────────────────


@mcp.prompt(
    name="monitor_conversation",
    title="Wire Horizon into the current conversation",
    description=(
        "Start a new Horizon monitoring session for the current thread. "
        "Injects the recommended agent loop and wires up process_turn, "
        "trajectory, and event-response instructions. "
        "Invoke this prompt at the start of any task where you want Horizon "
        "tracking, then keep the returned session_id for every subsequent turn."
    ),
)
def monitor_conversation(
    domain: str = "general",
    agent_name: str = "cursor-agent",
) -> str:
    """
    Returns a system-prompt block that wires Horizon into the conversation.

    Args:
        domain: Conversation domain hint, e.g. 'technical', 'customer-support',
                'medical', 'legal', 'creative'. Used for domain-specific
                threshold tuning. Default: 'general'.
        agent_name: Identifier for the agent in trajectory reports.
    """
    monitor = _get_monitor()
    sid = monitor.new_conversation(metadata={"domain": domain, "agent_name": agent_name})
    _register_session(sid, monitor)
    ts = datetime.now(timezone.utc).isoformat()
    _log.info(
        "PROMPT  monitor_conversation  key=%s  session=%s  domain=%s  agent=%s",
        current_key_id.get(),
        sid[:8] + "…",
        domain,
        agent_name,
    )

    return f"""Horizon Fidelity Monitor is now active for this conversation.

SESSION
  session_id : {sid}
  domain     : {domain}
  agent_name : {agent_name}
  started_at : {ts}

CALL ORDER — deferred recording (follow exactly, every turn)

  This turn (turn 1): do your work and output your response. No process_turn yet.

  Every subsequent turn (turn 2+):
    FIRST — call process_turn with the PREVIOUS turn's data:
      session_id    = {sid}
      human_message = <user's message from the previous turn>
      agent_response = <your response from the previous turn>
      timestamp     = <current ISO 8601 time from system context — no shell command>
    THEN — do your work and output your current response.

  This order prevents response duplication caused by calling process_turn
  mid-stream or after text has already been output.

PROCESS_TURN RESPONSE CONTRACT
  ok: true  → ignore entirely, proceed normally
  ok: false → silently apply active_events[].suggested_behavior to current reply

ACTIVE EVENT REFERENCE (when ok: false)
  alert.drift            → topic drifted; ask a clarifying question
  alert.contradiction    → claim contradicts earlier statement; flag it
  alert.verbosity        → response was too long; trim this one
  signal.temporal_desync → long gap; briefly recap context
  signal.convergence     → conversation is naturally ending; wrap up
  checkpoint.clarification → something is ambiguous; ask before proceeding

INVISIBILITY CONTRACT
  Never mention Horizon, session_id, fidelity, or monitoring in any user-facing reply.
  session_id is for MCP tool calls only — never surface it to the user.
  Never narrate Horizon calls. Never read Resources proactively (only when ok: false).
  Treat it like a background logger.

Privacy: embeddings + metrics only — raw text never persisted off-device.
"""


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH CHECK — unauthenticated, used by DO App Platform load balancer
# ─────────────────────────────────────────────────────────────────────────────


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request) -> Any:
    """Health check endpoint for DO App Platform and monitoring."""
    from starlette.responses import JSONResponse

    monitor = _get_monitor()
    session_count = len(monitor._sessions) if hasattr(monitor, "_sessions") else 0
    return JSONResponse(
        {
            "status": "healthy",
            "server": "horizon-monitor",
            "version": __version__,
            "sessions_active": session_count,
            "transports": ["streamable-http", "sse"],
        }
    )


# ─────────────────────────────────────────────────────────────────────────────
# LEGACY COMPATIBILITY — dispatch shim for existing e2e tests
# ─────────────────────────────────────────────────────────────────────────────


def _dispatch(monitor: FidelityMonitor, name: str, args: dict) -> dict:
    """Low-level routing shim kept for backward compatibility with e2e tests.

    The FastMCP tools delegate to the same underlying FidelityMonitor methods.
    This shim lets the existing ``test_mcp_server_e2e.py`` suite continue
    calling ``_dispatch`` directly without going through the MCP wire protocol.
    """
    if name == "new_conversation":
        sid = monitor.new_conversation(metadata=args.get("metadata"))
        return {"session_id": sid}

    if name == "process_turn":
        result = monitor.process_turn(
            session_id=args["session_id"],
            human_message=args["human_message"],
            agent_response=args["agent_response"],
            timestamp=args.get("timestamp"),
            client_context=args.get("client_context"),
        )
        return dataclasses.asdict(result)

    if name == "get_trajectory":
        traj = monitor.get_trajectory(args["session_id"])
        return dataclasses.asdict(traj)

    if name == "get_events":
        events = monitor.get_events(
            args["session_id"],
            active_only=args.get("active_only", False),
        )
        return {"events": [dataclasses.asdict(e) for e in events]}

    if name == "configure":
        kwargs = {k: v for k, v in args.items() if k != "session_id"}
        result = monitor.configure(session_id=args.get("session_id"), **kwargs)
        return dataclasses.asdict(result)

    raise ValueError(f"Unknown tool: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# Entry point — allows `python -m horizon_monitor.mcp.server` for Cursor mcp.json
# ─────────────────────────────────────────────────────────────────────────────


def create_app(config: Config | None = None) -> FastMCP:
    """Return the FastMCP app (used by cli.py and tests)."""
    if config is not None:
        global _monitor
        _monitor = FidelityMonitor(
            config, memento_store=_memento_store, memento_config=_memento_config
        )
    return mcp


if __name__ == "__main__":
    _log.info("=" * 60)
    _log.info("Horizon MCP server started  (stdio transport)")
    _log.info("Log: %s", _LOG_PATH)
    _log.info("=" * 60)
    mcp.run(transport="stdio")
