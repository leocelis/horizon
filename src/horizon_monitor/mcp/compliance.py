"""ComplyEdge runtime checks on the conversation text process_turn receives.

Off unless the MCP server has COMPLYEDGE_API_KEY; the FidelityMonitor core
never calls out (horizon_intent.yaml: no_external_calls_default). When on,
each process_turn sends two POST /v1/check calls, in parallel:

  human_message   direction "prompt"
  agent_response  direction "output"

Horizon records a turn after it happened, so it cannot block the text. A
violation is returned to the agent as an active conversation event,
``alert.compliance``, naming the rule, so the next reply does not build on
the flagged content. If ComplyEdge cannot be reached the turn is recorded as
usual (fail-open).

Log IDs: ComplyEdge keeps a keyed fingerprint of each checked text, never the
text, and Horizon keeps no text either, so the two event_ids go back to the
caller in the tool result's _meta, outside the result text:
  {"complyedge": {"input_event_id": <human_message>, "output_event_id": <agent_response>}}

Attribution (the three fields ComplyEdge writes on the audit record):
  user_id    "hzkey:<first 12 hex of sha256(bearer key)>", never the key;
             "local:<login>" over stdio / auth disabled
  user_role  "mcp_client" (remote) or "maintainer" (local)
  session_id the Horizon session_id of the conversation

Env:
  COMPLYEDGE_API_KEY      turns the checks on (never commit it)
  COMPLYEDGE_API_URL      default https://api.complyedge.io
  COMPLYEDGE_AGENT_ID     default horizon-mcp
  COMPLYEDGE_JURISDICTION default EU
  COMPLYEDGE_TIMEOUT_S    default 5
"""

from __future__ import annotations

import getpass
import json
import logging
import os
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

MAX_TEXT = 50000  # /v1/check rejects text longer than this

_log = logging.getLogger("horizon_monitor.mcp.compliance")

META_KEY = "complyedge"

# One dict per MCP tool call, opened by the dispatch; process_turn fills it.
_call_log_ids: ContextVar[dict | None] = ContextVar("complyedge_log_ids", default=None)


@dataclass
class Verdict:
    """Outcome of one check. checked=False means ComplyEdge was not consulted."""

    direction: str
    allowed: bool = True
    checked: bool = False
    violations: list = field(default_factory=list)
    event_id: str | None = None
    error: str | None = None


def enabled() -> bool:
    return bool(os.environ.get("COMPLYEDGE_API_KEY", "").strip())


def attribution(key_sha: str, session_id: str) -> dict:
    """user_id / user_role / session_id for the audit record. Never a credential."""
    if key_sha:
        ctx = {"user_id": f"hzkey:{key_sha[:12]}", "user_role": "mcp_client"}
    else:
        try:
            login = os.environ.get("USER") or getpass.getuser()
        except Exception:
            login = "unknown"
        ctx = {"user_id": f"local:{login}", "user_role": "maintainer"}
    ctx["session_id"] = session_id
    return ctx


def check(text: str, direction: str, context: dict) -> Verdict:
    """One /v1/check call. Fail-open: any transport or server error allows."""
    key = os.environ.get("COMPLYEDGE_API_KEY", "").strip()
    if not key:
        return Verdict(direction)
    url = os.environ.get("COMPLYEDGE_API_URL", "https://api.complyedge.io").rstrip("/")
    body = json.dumps(
        {
            "text": text[:MAX_TEXT],
            "agent_id": os.environ.get("COMPLYEDGE_AGENT_ID", "horizon-mcp"),
            "jurisdiction": os.environ.get("COMPLYEDGE_JURISDICTION", "EU"),
            "direction": direction,
            "context": context,
        }
    ).encode()
    req = urllib.request.Request(
        f"{url}/v1/check",
        data=body,
        method="POST",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        timeout = float(os.environ.get("COMPLYEDGE_TIMEOUT_S", "5"))
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https host
            data = json.loads(resp.read())
        return Verdict(
            direction,
            allowed=bool(data.get("allowed", True)),
            checked=True,
            violations=data.get("violations") or [],
            event_id=data.get("event_id"),
        )
    except urllib.error.HTTPError as exc:
        return Verdict(direction, error=f"HTTP {exc.code}")
    except Exception as exc:  # network, timeout, bad JSON
        return Verdict(direction, error=type(exc).__name__)


def check_turn(human_message: str, agent_response: str, context: dict) -> list[Verdict]:
    """Both checks in parallel; skips are logged, never raised."""
    with ThreadPoolExecutor(max_workers=2) as pool:
        verdicts = list(
            pool.map(
                lambda args: check(*args, context),
                [(human_message, "prompt"), (agent_response, "output")],
            )
        )
    for v in verdicts:
        if v.error:
            _log.warning("ComplyEdge %s check skipped (%s); turn recorded", v.direction, v.error)
    return verdicts


def compliance_event(verdicts: list[Verdict]) -> dict | None:
    """The alert.compliance active event for any blocked verdict, else None."""
    flagged = [v for v in verdicts if not v.allowed]
    if not flagged:
        return None
    rule_ids = [x.get("rule_id", "rule") for v in flagged for x in v.violations] or ["unspecified"]
    parts = {"prompt": "the user's message", "output": "your reply"}
    where = " and ".join(parts[v.direction] for v in flagged)
    return {
        "type": "alert.compliance",
        "plane": "conversation",
        "suggested_behavior": (
            f"ComplyEdge flagged {where} in the previous turn under "
            f"{', '.join(rule_ids)} (EU AI Act). Do not repeat, expand on or act on "
            "that content; if the user needs it, explain it cannot be provided."
        ),
        "rule_ids": rule_ids,
        "event_ids": [v.event_id for v in flagged if v.event_id],
    }


def note_log_ids(verdicts: list[Verdict]) -> None:
    """Record the Log IDs of one turn on the current tool call, if one is open."""
    holder = _call_log_ids.get()
    if holder is None:
        return
    by_dir = {v.direction: v.event_id for v in verdicts}
    holder.update(input_event_id=by_dir.get("prompt"), output_event_id=by_dir.get("output"))


def open_call() -> tuple[dict, Any]:
    """Start collecting Log IDs for one tool call; returns (holder, reset token)."""
    holder: dict = {}
    return holder, _call_log_ids.set(holder)


def close_call(token: Any) -> None:
    _call_log_ids.reset(token)


def with_log_ids(result: Any, ids: dict) -> Any:
    """The tool result as the CallToolResult the client receives, plus _meta.

    Mirrors the conversion the MCP server applies to a plain result, so the
    result text is unchanged; the Log IDs sit outside it.
    """
    from mcp.types import CallToolResult, TextContent

    if isinstance(result, CallToolResult):
        meta = {**(result.meta or {}), META_KEY: ids}
        return result.model_copy(update={"meta": meta})
    structured = None
    if isinstance(result, tuple):  # (content blocks, structured)
        result, structured = result
    elif isinstance(result, dict):
        structured = result
        result = [TextContent(type="text", text=json.dumps(result, indent=2))]
    return CallToolResult(content=list(result or []), structuredContent=structured, _meta={META_KEY: ids})
