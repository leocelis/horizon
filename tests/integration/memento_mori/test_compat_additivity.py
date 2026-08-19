"""G-10, G-11 [PROPERTY] — memento_signals_intent.yaml::strict_additivity.

"With store_path=None the memento code path is not entered and the full
existing test suite produces byte-identical results; with a store
configured, sessions not associated with a mission receive zero memento
events; association is an explicit registry call."

UPDATED (v0.8 MCP/agent integration): the `process_turn` wiring this file's
docstring used to flag as not-yet-implemented now exists —
`FidelityMonitor._mission_events_for_turn` (monitor.py), gated first on
`memento_store is not None` and then on `AssociationRegistry.missions_for`.
That means `horizon_monitor.monitor` now legitimately imports
`horizon_monitor.memento`, so the old "zero modules outside memento import
memento" structural check no longer holds — and was always a proxy, not the
constraint itself. `test_store_path_none_...` below is rewritten to assert
the actual constraint (no memento function is ever CALLED when no store is
configured) directly, by making every memento entry point raise if
reached. The end-to-end "process_turn appends zero events for an
unassociated session" check (G-11 in the running system, not just the
registry unit) is exercised in
`tests/integration/memento_mori/test_process_turn_wiring.py::test_g11_configured_store_unassociated_session_zero_mission_events`
— this file keeps the registry-level unit checks.
"""

from __future__ import annotations

from unittest.mock import patch

from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.signals import AssociationRegistry
from horizon_monitor.monitor import FidelityMonitor


def _boom(*args, **kwargs):
    raise AssertionError("memento function called with no memento_store configured")


def test_store_path_none_is_the_default_and_no_memento_function_is_called() -> None:
    """G-10: `store_path=None` is MementoConfig's default (an integrator who
    never opts in gets exactly that). With `memento_store` unset on
    `FidelityMonitor`, `process_turn` never calls a single memento function
    — proven by making `memento_engine.evaluate` and
    `memento_signals.evaluate_signals` raise if invoked — so no other code
    path in the existing test suite can be entered by, or diverge because
    of, memento's presence in the tree."""
    assert MementoConfig().store_path is None

    monitor = FidelityMonitor()
    assert monitor._memento_store is None
    session_id = monitor.new_conversation()

    with (
        patch("horizon_monitor.monitor.memento_engine.evaluate", side_effect=_boom),
        patch("horizon_monitor.monitor.memento_signals.evaluate_signals", side_effect=_boom),
    ):
        result = monitor.process_turn(
            session_id,
            "hello",
            "hi there",
            timestamp="2026-08-18T12:00:00+00:00",
        )
    assert all(e.plane == "conversation" for e in result.events)


def test_unassociated_session_has_zero_missions() -> None:
    """G-11: a session that never called `associate_mission` is not
    associated with anything — `is_associated` is False and `missions_for`
    is empty — which is the registry-level guarantee that feeds the
    process_turn integration's "zero events for unassociated sessions"
    behavior."""
    registry = AssociationRegistry()
    assert registry.is_associated("session-not-associated") is False
    assert registry.missions_for("session-not-associated") == ()


def test_association_is_explicit_and_survives_reregistration() -> None:
    """Association is a deliberate registry call, not inferred from any
    other state, and persists across repeated lookups for the same
    session_id (the registry survives "session re-registration" in the
    sense that calling associate() again does not clear a prior
    association)."""
    registry = AssociationRegistry()
    registry.associate("session-1", "mission-a")
    assert registry.is_associated("session-1") is True
    assert registry.missions_for("session-1") == ("mission-a",)

    registry.associate("session-1", "mission-b")
    assert registry.missions_for("session-1") == ("mission-a", "mission-b")

    # A different, never-associated session remains untouched.
    assert registry.is_associated("session-2") is False
