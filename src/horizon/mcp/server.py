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
          "args": ["-m", "horizon.mcp.server"],
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
from datetime import datetime, timezone
from typing import Any

from horizon import __version__

from horizon import Config, FidelityMonitor
from horizon.monitor import SessionNotFoundError

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
_log = logging.getLogger("horizon.mcp")

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    raise ImportError(
        "MCP support requires: pip install 'horizon-monitor[mcp]'"
    ) from exc

# ── Server-level instructions ─────────────────────────────────────────────────
#
# Cursor and Claude Desktop surface these instructions to the agent before the
# conversation starts, giving it a one-paragraph orientation without requiring
# a project-specific system prompt.

_INSTRUCTIONS = """
Horizon Fidelity Monitor — 4D conversation dynamics for AI agents.

RECOMMENDED AGENT LOOP
  1. Call new_conversation once per distinct task or chat thread. Store the
     returned session_id for the entire thread.
  2. Call process_turn after EVERY human-agent round-trip. Pass the ISO 8601
     wall-clock timestamp to enable all temporal and spacetime signals. This
     is a fast, local call (≈90 ms p50) and safe to auto-run.
  3. Before composing a long or complex response, read the Resources:
       horizon://session/{session_id}/trajectory  — fidelity arc + health
       horizon://session/{session_id}/events      — all fired events
     These are read-only and token-efficient. No tool-call slot needed.
  4. When health_status == 'degrading' or 'critical', surface the issue to the
     user and offer to re-anchor the conversation.
  5. When active alert/signal events fire (e.g. alert.drift, alert.contradiction,
     signal.pace_premature_report), act on the suggested_behavior field.
  6. Use configure_session only when the user explicitly requests a threshold
     change. This is the only tool that modifies session state beyond tracking.

SAFE TO AUTO-RUN (read-only or append-only):
  new_conversation, process_turn

REQUIRE HUMAN APPROVAL (mutates config):
  configure_session
""".strip()

# ── Singleton monitor ─────────────────────────────────────────────────────────
#
# One monitor per server process. Stateless between MCP connections for stdio
# (each Cursor session spawns a fresh process), stateful for SSE/HTTP (the
# process persists across connections).

_monitor: FidelityMonitor | None = None


def _get_monitor() -> FidelityMonitor:
    global _monitor
    if _monitor is None:
        _monitor = FidelityMonitor()
    return _monitor


# ── FastMCP app ───────────────────────────────────────────────────────────────

mcp = FastMCP(
    "horizon-fidelity-monitor",
    instructions=_INSTRUCTIONS,
)


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
    _log.info("TOOL  new_conversation  session=%s  metadata=%s", sid[:8] + "…", metadata)
    return {"session_id": sid}


@mcp.tool(
    name="process_turn",
    title="Record a conversation turn",
    description=(
        "Record one human-agent turn and return the full Horizon fidelity "
        "snapshot for that turn. Call after EVERY round-trip in the "
        "conversation. Requires an active session_id from new_conversation. "
        "\n\nKey outputs:\n"
        "  • fidelity_score [0,1]    — composite conversation health\n"
        "  • health_status           — 'healthy'|'degrading'|'critical'|'converged'\n"
        "  • events                  — list of fired signals and alerts\n"
        "  • gap_class               — 'realtime'|'seconds'|'minutes'|'hours'|'days'\n"
        "  • estimated_retention     — fraction of prior context still accessible\n"
        "  • interval_class          — 'timelike'|'spacelike'|'lightlike' (ds²)\n"
        "\n"
        "Pass timestamp (ISO 8601) to enable all 4D temporal and spacetime "
        "signals; without it, only semantic signals fire. "
        "Pass client_context with device_type and timezone to enable spatial "
        "and circadian signals. "
        "To read the fidelity arc without updating it, use the Resource "
        "horizon://session/{session_id}/trajectory instead."
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
    Record one turn. Returns TurnResult as a dict.

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
        result = monitor.process_turn(
            session_id=session_id,
            human_message=human_message,
            agent_response=agent_response,
            timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
            client_context=client_context,
        )
        d = dataclasses.asdict(result)
        active_evs = [e["type"] for e in d.get("events", []) if e.get("active")]
        _log.info(
            "TOOL  process_turn  session=%s  turn=%s  fidelity=%.3f  health=%s  "
            "gap=%s  retention=%s  active_events=%s",
            session_id[:8] + "…",
            d["turn_number"],
            d["fidelity_score"],
            d["health_status"],
            d.get("gap_class", "n/a"),
            f"{d['estimated_retention']:.0%}" if d.get("estimated_retention") is not None else "n/a",
            active_evs if active_evs else "none",
        )
        return d
    except SessionNotFoundError as exc:
        _log.warning("TOOL  process_turn  ERROR: %s", exc)
        return {"error": str(exc), "hint": "Call new_conversation first."}


@mcp.tool(
    name="configure_session",
    title="Override thresholds or event modes",
    description=(
        "Override Horizon thresholds and event modes for a specific session "
        "or globally (when session_id is omitted). "
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

    Omit session_id to apply to all sessions (global override).
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

    try:
        result = monitor.configure(session_id=session_id, **kwargs)
        d = dataclasses.asdict(result)
        _log.info("TOOL  configure_session  session=%s  applied=%s", str(session_id)[:8], d["applied"])
        return d
    except SessionNotFoundError as exc:
        _log.warning("TOOL  configure_session  ERROR: %s", exc)
        return {"error": str(exc), "hint": "Call new_conversation first."}


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
        traj = monitor.get_trajectory(session_id)
        d = dataclasses.asdict(traj)
        _log.info(
            "RESOURCE  trajectory  session=%s  turns=%s  health=%s  fidelity=%.3f",
            session_id[:8] + "…", d["turn_count"], d["health_status"], d["current_fidelity"],
        )
        return json.dumps(d, indent=2, default=str)
    except SessionNotFoundError as exc:
        _log.warning("RESOURCE  trajectory  ERROR: %s", exc)
        return json.dumps({"error": str(exc), "hint": "Call new_conversation first."})


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
        events = monitor.get_events(session_id)
        active = [dataclasses.asdict(e) for e in events if e.active]
        all_events = [dataclasses.asdict(e) for e in events]
        _log.info(
            "RESOURCE  events  session=%s  total=%s  active=%s  active_types=%s",
            session_id[:8] + "…", len(all_events), len(active),
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
        _log.warning("RESOURCE  events  ERROR: %s", exc)
        return json.dumps({"error": str(exc), "hint": "Call new_conversation first."})


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
    sid = monitor.new_conversation(
        metadata={"domain": domain, "agent_name": agent_name}
    )
    ts = datetime.now(timezone.utc).isoformat()
    _log.info("PROMPT  monitor_conversation  session=%s  domain=%s  agent=%s", sid[:8] + "…", domain, agent_name)

    return f"""You are now being monitored by the Horizon Fidelity Monitor.

SESSION DETAILS
  session_id : {sid}
  domain     : {domain}
  agent_name : {agent_name}
  started_at : {ts}

YOUR MONITORING LOOP
  1. After every human-agent turn, call the process_turn tool with:
       session_id = {sid}
       human_message = <the user's message>
       agent_response = <your response>
       timestamp = <current ISO 8601 time>

  2. Before composing any complex or long response, read:
       Resource: horizon://session/{sid}/trajectory
       Resource: horizon://session/{sid}/events

  3. Act on health signals:
       health_status 'degrading'  → warn the user; offer to re-anchor.
       health_status 'critical'   → pause; summarise current understanding.
       health_status 'converged'  → the conversation has reached natural closure.

  4. Act on active events:
       alert.drift           → topic has drifted; ask a clarifying question.
       alert.contradiction   → a factual claim contradicts an earlier statement.
       alert.verbosity       → response is excessively long; trim the next one.
       signal.temporal_desync→ long gap detected; briefly recap context.
       signal.pace_premature_report → the user replied before a deferred task
                                      could complete; check assumptions.
       signal.convergence    → wrap up; the conversation is naturally ending.
       checkpoint.clarification → something is ambiguous; ask before proceeding.

  5. Privacy: Horizon stores embeddings + metrics only — raw text is never
     persisted off-device. Zero network calls beyond this MCP pipe.

Begin monitoring now. Call process_turn with the first turn of this conversation.
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
    return JSONResponse({
        "status": "healthy",
        "server": "horizon-monitor",
        "version": __version__,
        "sessions_active": session_count,
        "transports": ["streamable-http", "sse"],
    })


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
# Entry point — allows `python -m horizon.mcp.server` for Cursor mcp.json
# ─────────────────────────────────────────────────────────────────────────────


def create_app(config: Config | None = None) -> FastMCP:
    """Return the FastMCP app (used by cli.py and tests)."""
    if config is not None:
        global _monitor
        _monitor = FidelityMonitor(config)
    return mcp


if __name__ == "__main__":
    _log.info("=" * 60)
    _log.info("Horizon MCP server started  (stdio transport)")
    _log.info("Log: %s", _LOG_PATH)
    _log.info("=" * 60)
    mcp.run(transport="stdio")
