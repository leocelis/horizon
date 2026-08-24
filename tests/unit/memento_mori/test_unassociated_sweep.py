"""The unassociated status sweep — closing the association circularity.

Signals reached the operator only in a session they had already told the system
was about that mission. So the plane reminded them of what they had already
remembered, which is precisely the failure it exists to prevent. The sweep
surfaces LEVELS in an unassociated session — and, critically, does not fire the
alert, because RAISED fires once (C2 F5) and burning that edge in a conversation
where the operator cannot act would leave it silent where they could.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor import FidelityMonitor
from horizon_monitor.memento import EventKind, ItemKind, MementoConfig, MementoStore

UTC = timezone.utc
T_EVAL = "2026-08-18T12:00:00+00:00"


@pytest.fixture()
def stalled(tmp_path):
    """A mission well past its stall threshold — something genuinely due."""
    store = MementoStore(tmp_path / "missions.db")
    root = store.register_item(
        kind=ItemKind.HORIZON,
        title="h",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="forgotten mission",
        parent_id=root,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        stall_days=14,
    )
    store.record_event(
        item_id=mission, kind=EventKind.PROGRESS, valid_time=datetime(2026, 6, 1, tzinfo=UTC)
    )
    monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
    yield store, mission, monitor
    store.close()


def _sweep(monitor, session="s1", turn=1):
    return monitor._mission_events_for_turn(session, turn, T_EVAL)


def test_an_unassociated_session_is_told_something_is_due(stalled):
    """The whole point: no association, and the operator still hears about it."""
    _store, _mission, monitor = stalled
    events = _sweep(monitor)
    assert events, "an unassociated session heard nothing about an overdue mission"
    e = events[0]
    assert e.plane == "mission"
    assert e.type.startswith("status."), f"a level must not masquerade as an alert: {e.type}"
    assert e.metadata["surface"] == "level"
    assert e.metadata["unassociated_sweep"] is True
    assert e.metadata["derivation"], "surfaced without its derivation"


def test_the_sweep_does_not_burn_the_alert_edge(stalled):
    """C2 F5: RAISED fires once. If the sweep consumed it, the associated
    session — where the operator can actually act — would hear nothing."""
    store, mission, monitor = stalled

    _sweep(monitor)
    assert store.get_all_fire_states() == [], (
        "the status sweep wrote fire state; the alert edge has been consumed in a "
        "session where the operator was not working on this mission"
    )

    # now associate: the real alert must still be available to fire
    monitor.associate_mission("s2", mission)
    alerts = monitor._mission_events_for_turn("s2", 1, T_EVAL)
    assert any(
        a.type.startswith("signal.") for a in alerts
    ), "the associated session got no alert — the edge was lost"
    assert store.get_all_fire_states(), "the associated fire DID transition state"


def test_the_sweep_happens_once_per_session_not_every_turn(stalled):
    """A level repeated every turn is the flood F4 warns about."""
    _store, _mission, monitor = stalled
    first = _sweep(monitor, "s1", 1)
    second = _sweep(monitor, "s1", 2)
    third = _sweep(monitor, "s1", 3)
    assert len(first) == 1
    assert second == [] and third == []


def test_a_different_session_gets_its_own_sweep(stalled):
    _store, _mission, monitor = stalled
    assert _sweep(monitor, "s1", 1)
    assert _sweep(monitor, "s2", 1), "a new session was not swept"


def test_nothing_due_means_nothing_said(tmp_path):
    """Silence when there is genuinely nothing to report."""
    store = MementoStore(tmp_path / "m.db")
    try:
        root = store.register_item(
            kind=ItemKind.HORIZON,
            title="h",
            created_valid=datetime(2026, 8, 17, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        mission = store.register_item(
            kind=ItemKind.MISSION,
            title="fresh",
            parent_id=root,
            created_valid=datetime(2026, 8, 17, tzinfo=UTC),
            stall_days=90,
        )
        store.record_event(
            item_id=mission, kind=EventKind.PROGRESS, valid_time=datetime(2026, 8, 18, tzinfo=UTC)
        )
        monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
        assert monitor._mission_events_for_turn("s1", 1, T_EVAL) == []
    finally:
        store.close()


def test_an_empty_store_sweeps_nothing(tmp_path):
    store = MementoStore(tmp_path / "m.db")
    try:
        monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
        assert monitor._mission_events_for_turn("s1", 1, T_EVAL) == []
    finally:
        store.close()


def test_no_timestamp_means_no_sweep(stalled):
    """The evaluation instant is never guessed."""
    _store, _mission, monitor = stalled
    assert monitor._mission_events_for_turn("s1", 1, None) == []
