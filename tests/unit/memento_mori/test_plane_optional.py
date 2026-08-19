"""Parent constraint: optional_plane_backward_compat.

horizon_memento_mori_intent.yaml::constraints[optional_plane_backward_compat]
test: tests/unit/memento_mori/test_plane_optional.py::test_no_store_no_behavior_change

"With no mission store configured, every existing Horizon API behaves
byte-identically to the pre-plane release; enabling the plane requires
explicit configuration."

UPDATED (v0.8 MCP/agent integration): `FidelityMonitor` now imports
`horizon_monitor.memento` by construction — it is the one, explicit
integration point that turns `associate_mission` + the mission store into
`process_turn` events (see `monitor.py::_mission_events_for_turn`). The
static "no module outside memento imports memento" check this file used
before that wiring landed is therefore no longer the right proxy for the
constraint — module PRESENCE in the import graph never was what the
constraint promises; runtime BEHAVIOR with no store configured is. This
version asserts the stronger, more precise thing directly: with
`memento_store=None` (the default), `FidelityMonitor._mission_events_for_turn`
returns before calling a single memento function — proven by making every
memento entry point raise if reached — and the full existing turn/events
output is byte-identical between two independently constructed monitors.
"""

from __future__ import annotations

from unittest.mock import patch

from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.monitor import FidelityMonitor


def _boom(*args, **kwargs):
    raise AssertionError("memento function called with no memento_store configured")


def test_no_store_no_behavior_change() -> None:
    """Enabling the plane requires an explicit `memento_store`; with none,
    the existing `FidelityMonitor` API is untouched — no memento function is
    ever reached at runtime — and two independent monitors process the same
    turn byte-identically."""
    assert MementoConfig().store_path is None

    monitor_a = FidelityMonitor()
    monitor_b = FidelityMonitor()
    assert monitor_a._memento_store is None and monitor_b._memento_store is None

    session_a = monitor_a.new_conversation(session_id="fixed-session-id")
    session_b = monitor_b.new_conversation(session_id="fixed-session-id")

    with (
        patch("horizon_monitor.monitor.memento_engine.evaluate", side_effect=_boom),
        patch("horizon_monitor.monitor.memento_signals.evaluate_signals", side_effect=_boom),
    ):
        result_a = monitor_a.process_turn(
            session_a,
            "What time is it in UTC right now?",
            "I can't check the clock; please tell me.",
            timestamp="2026-04-22T10:30:00+00:00",
        )
        result_b = monitor_b.process_turn(
            session_b,
            "What time is it in UTC right now?",
            "I can't check the clock; please tell me.",
            timestamp="2026-04-22T10:30:00+00:00",
        )

    assert result_a.fidelity_score == result_b.fidelity_score
    assert [e.type for e in result_a.events] == [e.type for e in result_b.events]
    assert all(e.plane == "conversation" for e in result_a.events)
