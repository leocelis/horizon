"""G-1, G-3, G-4 [GOLDEN] — edge-triggered firing, escalation-on-new-fact-only,
and "another turn happened" is structurally unrepresentable.

memento_signals_intent.yaml::edge_not_level. Each case uses a small isolated
fixture (one predicate, no cap competition) so the edge/level distinction is
visible without cap interactions — see test_signals_ack_cap.py for cap and
priority behavior over the full smallco fixture.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind, SignalState

UTC = timezone.utc


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


def _evaluate(store, t_eval: datetime, config: MementoConfig | None = None):
    """One turn: snapshot -> engine.evaluate -> signals.evaluate_signals ->
    persist the returned fire states, exactly as an integrator is expected
    to drive it."""
    cfg = config or MementoConfig()
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, t_eval, cfg)
    signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, cfg)
    for (item_id, signal_type), state in new_states.items():
        store.set_fire_state(item_id, signal_type, state)
    return signal_report


def _build_single_deferral(store) -> str:
    """Root + mission + one DEFERRAL (F1, revisit 2026-08-10) — the only
    predicate in this store, so it always wins any per-turn cap trivially.

    The root horizon is deliberately far beyond any date used in this test
    (root_days_remaining_at_creation is fixed at mission creation — see
    engine.py) so horizon_share never crosses even its first rung here."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2026, 1, 1),
        end_date=date(2500, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=_dt(2026, 1, 1),
        stall_days=3650,
    )
    store.record_event(item_id=mission_id, kind=EventKind.PROGRESS, valid_time=_dt(2026, 7, 1))
    return store.register_item(
        kind=ItemKind.DEFERRAL,
        title="F1",
        parent_id=mission_id,
        created_valid=_dt(2026, 7, 1),
        revisit_date=date(2026, 8, 10),
    )


def test_fire_once_and_no_turn_rung(store) -> None:
    """G-1: no event before the revisit date; RAISED fires exactly once on
    the first evaluation after it passes; a second evaluation of the same
    (still-true, still-RAISED) state produces no event."""
    f1_id = _build_single_deferral(store)

    before = _evaluate(store, _dt(2026, 8, 9))
    assert before.fired == ()
    assert before.due == ()

    first_after = _evaluate(store, _dt(2026, 8, 11))
    assert len(first_after.fired) == 1
    fired_signal = first_after.fired[0]
    assert fired_signal.item_id == f1_id
    assert fired_signal.signal_type == "deferral_expired"
    assert fired_signal.state == SignalState.RAISED.value

    second_after = _evaluate(store, _dt(2026, 8, 12))
    assert second_after.fired == ()
    # still true, still RAISED, unacked — a level, reported once as a
    # standing due item, never re-delivered as an event.
    assert len(second_after.due) == 1
    assert second_after.due[0].fired is False


def _build_horizon_share_mission(store) -> tuple[str, datetime]:
    """Root + mission with a fixed, round root_days_remaining_at_creation of
    1000 days, so age_days/1000 crossings of the default rungs
    (0.01, 0.05, 0.10, 0.25) land on whole-day boundaries (10d, 50d, 100d)."""
    mission_created = _dt(2026, 1, 1)
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2020, 1, 1),
        end_date=(mission_created + timedelta(days=1000)).date(),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=mission_created,
        stall_days=3650,
    )
    return mission_id, mission_created


def test_escalation_only_on_new_rung_not_on_turns(store) -> None:
    """G-3: ACK silences horizon_share; further turns at the same rung stay
    silent; crossing the next configured rung fires a single ESCALATED
    event."""
    mission_id, created = _build_horizon_share_mission(store)
    config = MementoConfig()

    raised = _evaluate(store, created + timedelta(days=10), config)  # share=0.01, rung 0
    assert len(raised.fired) == 1
    assert raised.fired[0].signal_type == "horizon_share"
    assert raised.fired[0].state == SignalState.RAISED.value

    store.set_fire_state(
        mission_id,
        "horizon_share",
        signals.ack(
            mission_id,
            "horizon_share",
            created + timedelta(days=10),
            actor="operator",
            current_rung=0,
        ),
    )

    silent = _evaluate(store, created + timedelta(days=20), config)  # share=0.02, still rung 0
    assert silent.fired == ()
    assert any(s.item_id == mission_id and s.signal_type == "horizon_share" for s in silent.acked)

    escalated = _evaluate(store, created + timedelta(days=50), config)  # share=0.05, rung 1
    assert len(escalated.fired) == 1
    assert escalated.fired[0].signal_type == "horizon_share"
    assert escalated.fired[0].state == SignalState.ESCALATED.value

    silent_again = _evaluate(store, created + timedelta(days=51), config)  # still rung 1
    assert silent_again.fired == ()


def test_signal_state_enum_has_no_turn_count_member() -> None:
    """G-4: the escalation-rung enum is closed and API-level — no member
    represents "another turn happened"; only the five named lifecycle
    states exist."""
    member_names = {member.name for member in SignalState}
    assert member_names == {"CLEAR", "RAISED", "ACKED", "ESCALATED", "STALE"}
    for name in member_names:
        assert "TURN" not in name and "ELAPSED" not in name
