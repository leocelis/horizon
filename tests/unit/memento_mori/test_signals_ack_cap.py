"""G-2, G-5, G-6, G-7 — ack silences, per-turn cap, priority order, STALE.

memento_signals_intent.yaml::ack_and_cap.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind, SignalState

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


def _evaluate(store, t_eval: datetime, config: MementoConfig | None = None):
    cfg = config or MementoConfig()
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, t_eval, cfg)
    signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, cfg)
    for (item_id, signal_type), state in new_states.items():
        store.set_fire_state(item_id, signal_type, state)
    return signal_report


def _build_single_mission(store, stall_days: int = 14) -> str:
    """Root far beyond any date used in these tests (root_days_remaining_at_
    creation is fixed at mission creation — see engine.py) so horizon_share
    never crosses even its first rung and cannot compete for the cap here;
    one early progress event so the stall predicate is a real
    "no recent work" edge rather than the distinct "no capture" case."""
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
        stall_days=stall_days,
    )
    store.record_event(item_id=mission_id, kind=EventKind.PROGRESS, valid_time=_dt(2026, 1, 2))
    return mission_id


def test_ack_silences_mission_stalled(store) -> None:
    """G-2 [HUMAN]: ACK on mission_stalled stops further fires; the item is
    listed under `acked` on subsequent turns.

    REVIEWER NOTE: this test asserts the "listed under acked" behavior an
    ai_generated test cannot certify alone (IVD Rule 3) — a human reviewer
    should confirm this is the intended clock_status surface shape."""
    mission_id = _build_single_mission(store)

    raised = _evaluate(store, _dt(2026, 1, 20))  # 19d since progress > 14
    assert len(raised.fired) == 1
    assert raised.fired[0].signal_type == "mission_stalled"

    store.set_fire_state(
        mission_id,
        "mission_stalled",
        signals.ack(mission_id, "mission_stalled", _dt(2026, 1, 20), actor="operator"),
    )

    silenced = _evaluate(store, _dt(2026, 1, 25))
    assert silenced.fired == ()
    assert len(silenced.acked) == 1
    assert silenced.acked[0].item_id == mission_id
    assert silenced.acked[0].signal_type == "mission_stalled"


def test_stale_fires_once_after_ack_timeout_with_no_progress(store) -> None:
    """G-7: ACKED 30+ days with no progress ⇒ one low-tier STALE event; a
    further turn after that does not re-fire it."""
    mission_id = _build_single_mission(store)
    _evaluate(store, _dt(2026, 1, 20))
    store.set_fire_state(
        mission_id,
        "mission_stalled",
        signals.ack(mission_id, "mission_stalled", _dt(2026, 1, 20), actor="operator"),
    )

    still_fresh = _evaluate(store, _dt(2026, 1, 25))  # 5d since ack
    assert still_fresh.fired == ()

    stale = _evaluate(store, _dt(2026, 2, 25))  # 36d since ack, still no progress
    assert len(stale.fired) == 1
    assert stale.fired[0].signal_type == "mission_stalled"
    assert stale.fired[0].state == SignalState.STALE.value

    after_stale = _evaluate(store, _dt(2026, 3, 5))
    assert after_stale.fired == ()
    assert any(s.item_id == mission_id for s in after_stale.acked)


def test_per_turn_cap_holds_over_smallco(store) -> None:
    """G-5: over the smallco fixture at 2026-08-18, at least four predicates
    are simultaneously true for the first time (T1 ttl_expired, D2
    clock_unpaired, F1 deferral_expired, M1 mission_stalled, plus the
    P3-tier horizon_share/probe_ready/path_ahead predicates) — the default
    cap of 1 delivers exactly one event, and it is the P1
    (`ttl_expired` on T1), never a P2/P3 predicate."""
    build_smallco(store)
    report = _evaluate(store, EVAL_INSTANT)

    assert len(report.fired) == 1
    assert report.fired[0].signal_type == "ttl_expired"
    assert report.fired[0].tier == "P1"

    due_true_predicates = [s for s in report.due if s.fired is False]
    assert len(due_true_predicates) >= 4


def test_priority_order_p1_before_p2_then_fewest_days_remaining(store) -> None:
    """G-6: with cap=1 and both a P1 and a P2 predicate due on the same
    turn, the P1 wins; a custom fixture with two P1-tier deadlines proves
    the "fewest days-remaining" tiebreak inside the same tier."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2026, 1, 1),
        end_date=date(2030, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=_dt(2026, 1, 1),
        stall_days=3650,
    )
    # P2 predicate: a deferral already expired.
    store.register_item(
        kind=ItemKind.DEFERRAL,
        title="F1",
        parent_id=mission_id,
        created_valid=_dt(2026, 1, 1),
        revisit_date=date(2026, 1, 1),
    )
    # Two P1 predicates: deadlines entering their warning window, with
    # different days_remaining — the fewer-days one must win the tiebreak.
    near_id = store.register_item(
        kind=ItemKind.DEADLINE,
        title="D-near",
        parent_id=mission_id,
        created_valid=_dt(2026, 1, 1),
        deadline_date=date(2026, 8, 20),
        deadline_kind="hard_cutoff",
        gates_item_id=mission_id,
    )
    store.register_item(
        kind=ItemKind.DEADLINE,
        title="D-far",
        parent_id=mission_id,
        created_valid=_dt(2026, 1, 1),
        deadline_date=date(2026, 8, 30),
        deadline_kind="hard_cutoff",
        gates_item_id=mission_id,
    )

    report = _evaluate(store, _dt(2026, 8, 18))  # both deadlines inside the 14d warn window

    assert len(report.fired) == 1
    fired = report.fired[0]
    assert fired.tier == "P1"
    assert fired.item_id == near_id
    assert fired.signal_type == "deadline_window"

    due_item_ids = {s.item_id for s in report.due}
    assert near_id not in due_item_ids  # the winner never also appears in `due`
    assert len(report.due) >= 2  # the far deadline and the P2 deferral both lost the cap
