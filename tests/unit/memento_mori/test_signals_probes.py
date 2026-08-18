"""G-8 [GOLDEN] — probe_ready and path_ahead: first completed sojourn fires
once; path_ahead payload carries both measured intervals plus n and
derivation, and no p-value/confidence-interval field exists anywhere on the
signal (memento_signals_intent.yaml parent goal; PRD §7 — no inferential
dominance test)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind

UTC = timezone.utc


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


def _evaluate(store, t_eval: datetime, config: MementoConfig):
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, t_eval, config)
    signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, config)
    for (item_id, signal_type), state in new_states.items():
        store.set_fire_state(item_id, signal_type, state)
    return signal_report


def test_probe_ready_and_path_ahead_fire_with_full_payload(store) -> None:
    mission_created = _dt(2026, 1, 1)
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2020, 1, 1),
        # deliberately far beyond any realistic eval window so
        # horizon_share never crosses even its first rung here — this
        # fixture isolates probe_ready/path_ahead from every other predicate.
        end_date=(mission_created + timedelta(days=100_000)).date(),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=mission_created,
        stall_days=3650,
    )
    probe_id = store.register_item(
        kind=ItemKind.PROBE,
        title="channel-b",
        parent_id=mission_id,
        created_valid=_dt(2026, 8, 1),
    )
    store.record_event(
        item_id=probe_id, kind=EventKind.STAGE_ENTER, valid_time=_dt(2026, 8, 2), stage="channel-b"
    )
    store.record_event(
        item_id=probe_id, kind=EventKind.STAGE_EXIT, valid_time=_dt(2026, 8, 6), stage="channel-b"
    )
    store.record_event(item_id=mission_id, kind=EventKind.PROGRESS, valid_time=_dt(2026, 8, 15))

    # cap=2 so both P3 predicates can be observed on the same turn; the
    # per-turn cap and priority ordering are G-5/G-6's concern, not this one.
    config = MementoConfig(per_turn_fire_cap=2)
    report = _evaluate(store, _dt(2026, 8, 18), config)

    fired_by_type = {s.signal_type: s for s in report.fired}
    assert set(fired_by_type) == {"probe_ready", "path_ahead"}

    probe_ready = fired_by_type["probe_ready"]
    assert probe_ready.item_id == mission_id
    assert probe_ready.n == 1

    path_ahead = fired_by_type["path_ahead"]
    assert path_ahead.item_id == mission_id
    assert path_ahead.n == 1
    assert path_ahead.derivation  # traceable, not a bare number
    assert path_ahead.payload["probe_sojourn_days"] == 4
    assert path_ahead.payload["incumbent_accrued_delay_days"] == 17

    for signal in (probe_ready, path_ahead):
        assert "p_value" not in signal.payload
        assert "confidence_interval" not in signal.payload
        assert "posterior" not in signal.payload
        for key in signal.to_dict():
            assert "p_value" not in key.lower()
            assert "confidence" not in key.lower()


def test_probe_ready_only_before_any_completed_sojourn(store) -> None:
    """A probe registered but never closed out ⇒ probe_ready is due but
    false (not yet true), and path_ahead is not even a tracked predicate
    yet — there is nothing completed to compare."""
    mission_created = _dt(2026, 1, 1)
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2020, 1, 1),
        end_date=(mission_created + timedelta(days=100_000)).date(),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=mission_created,
        stall_days=3650,
    )
    probe_id = store.register_item(
        kind=ItemKind.PROBE, title="channel-b", parent_id=mission_id, created_valid=_dt(2026, 8, 1)
    )
    store.record_event(
        item_id=probe_id, kind=EventKind.STAGE_ENTER, valid_time=_dt(2026, 8, 2), stage="channel-b"
    )
    store.record_event(item_id=mission_id, kind=EventKind.PROGRESS, valid_time=_dt(2026, 8, 15))

    config = MementoConfig(per_turn_fire_cap=2)
    report = _evaluate(store, _dt(2026, 8, 18), config)

    assert report.fired == ()
    assert all(s.signal_type != "path_ahead" for s in report.due)
