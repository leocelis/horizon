"""E2E: Horizon MCP server exercised in-process.

Proves the MCP adapter used by Cursor + Claude Desktop + any MCP client:
    - ``new_conversation`` → returns a UUID
    - ``process_turn`` → returns all Horizon signals as a dict
    - ``get_trajectory`` → returns the full per-session trajectory
    - ``get_events`` → returns the event log
    - ``configure`` → persists per-session overrides

The full ``mcp`` package is only needed for transport (stdio / SSE). Here we
exercise the pure routing layer by calling ``_dispatch`` directly against a
live ``FidelityMonitor``, which is what the MCP ``call_tool`` handler invokes
for every incoming tool request.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from horizon import Config, FidelityMonitor
from horizon.mcp.server import _dispatch
from horizon.monitor import SessionNotFoundError


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor(Config())


def test_mcp_dispatch_new_conversation_returns_session_id(monitor: FidelityMonitor) -> None:
    result = _dispatch(monitor, "new_conversation", {})
    assert "session_id" in result
    assert isinstance(result["session_id"], str)
    assert len(result["session_id"]) > 10


def test_mcp_dispatch_full_flow(monitor: FidelityMonitor) -> None:
    """Full round-trip: new → process → trajectory → events → configure."""
    sid = _dispatch(monitor, "new_conversation", {"metadata": {"domain": "technical"}})["session_id"]

    clock = datetime(2026, 4, 22, 8, 30, tzinfo=timezone.utc)
    conversation = [
        ("What is a B-tree?", "A balanced tree optimised for block-oriented storage reads."),
        ("How does it differ from a B+ tree?", "B+ trees store values only in leaves and link leaves together."),
        ("When would I pick a LSM-tree instead?", "LSM-trees win for write-heavy workloads with bounded read amplification."),
    ]
    for human, agent in conversation:
        clock = clock + timedelta(seconds=60)
        turn = _dispatch(monitor, "process_turn", {
            "session_id": sid,
            "human_message": human,
            "agent_response": agent,
            "timestamp": clock.isoformat(),
        })
        assert "fidelity_score" in turn
        assert "igt_value" in turn
        assert "events" in turn
        assert isinstance(turn["events"], list)

    trajectory = _dispatch(monitor, "get_trajectory", {"session_id": sid})
    assert trajectory["turn_count"] == len(conversation)
    assert len(trajectory["scores"]) == len(conversation)

    events = _dispatch(monitor, "get_events", {"session_id": sid})
    assert "events" in events
    assert isinstance(events["events"], list)

    config_result = _dispatch(monitor, "configure", {
        "session_id": sid,
        "clarification_threshold": 0.25,
        "domain": "support",
    })
    assert "applied" in config_result
    assert config_result["applied"]["clarification_threshold"] == 0.25


def test_mcp_dispatch_unknown_session_returns_error(monitor: FidelityMonitor) -> None:
    with pytest.raises(SessionNotFoundError):
        _dispatch(monitor, "get_trajectory", {"session_id": "nope"})


def test_mcp_dispatch_unknown_tool_raises(monitor: FidelityMonitor) -> None:
    with pytest.raises(ValueError, match="Unknown tool"):
        _dispatch(monitor, "definitely_not_a_tool", {})


def test_mcp_dispatch_configure_active_mode_event_flow(monitor: FidelityMonitor) -> None:
    """Configure an event into active mode via MCP, then confirm the next turn
    emits it with active=True."""
    sid = _dispatch(monitor, "new_conversation", {})["session_id"]

    _dispatch(monitor, "configure", {
        "session_id": sid,
        "clarification_threshold": 0.0,
        "event_modes": {"checkpoint.clarification": "active"},
    })

    _dispatch(monitor, "process_turn", {
        "session_id": sid,
        "human_message": "What is the event horizon of a black hole?",
        "agent_response": "A recipe for chocolate cake: flour, sugar, cocoa, eggs.",
    })

    events = _dispatch(monitor, "get_events", {"session_id": sid, "active_only": True})
    active_types = {e["type"] for e in events["events"]}
    assert "checkpoint.clarification" in active_types
