"""E-1, E-2, E-10, E-11, E-19 — calendar-date arithmetic on the smallco
fixture.

memento_engine_intent.yaml::calendar_day_arithmetic.
test: tests/unit/memento_mori/test_engine_calendar.py::test_dst_and_future_dates
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import ItemKind

from .conftest import EVAL_INSTANT, build_smallco, load_golden

UTC = timezone.utc


def _row(report, item_id: str):
    return next(r for r in report.items if r.item_id == item_id)


def test_smallco_ages_and_remaining_match_golden(store) -> None:
    """E-1 [GOLDEN]: M1 age 78d; D1 remaining 43d; H remaining 1232d; F1
    expired by 8d; T1 ttl_state expired (29d past)."""
    golden = load_golden()
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    m1 = _row(report, ids["M1"])
    assert m1.age_days == golden["mission_age_days"] == 78

    d1 = _row(report, ids["D1"])
    assert d1.days_remaining == golden["deadline_d1_days_remaining"] == 43

    h = _row(report, ids["H"])
    assert h.days_remaining == golden["horizon_days_remaining"] == 1232

    f1 = _row(report, ids["F1"])
    assert f1.days_remaining == -golden["deferral_f1_expired_by_days"] == -8

    t1 = _row(report, ids["T1"])
    assert t1.ttl_state == golden["task_t1_ttl_state"] == "expired"
    days_past = (EVAL_INSTANT.date() - date(2026, 7, 20)).days
    assert days_past == golden["task_t1_days_past_ttl_end"] == 29


def test_days_since_progress_stalled(store) -> None:
    """E-2 [GOLDEN]: M1 days_since_progress = 47d (since 2026-07-02) -> stalled."""
    golden = load_golden()
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    m1 = _row(report, ids["M1"])
    assert m1.days_since_progress == golden["mission_days_since_progress"] == 47
    assert (m1.days_since_progress > 14) == golden["mission_stalled"] is True


def test_future_dated_item_clamps_to_age_zero(store) -> None:
    """E-10: a task created after t_eval gets age 0, flagged future_dated,
    never negative."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    future_task_id = store.register_item(
        kind=ItemKind.TASK,
        title="future task",
        parent_id=root_id,
        created_valid=datetime(2026, 9, 1, tzinfo=UTC),  # after eval instant
    )
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    row = _row(report, future_task_id)
    assert row.age_days == 0
    assert row.future_dated is True


def test_dst_offset_does_not_change_day_count(store) -> None:
    """E-11 [GOLDEN]: day counts are computed on calendar dates in UTC; a
    +13h-offset caller timestamp changes no day count."""
    ids = build_smallco(store)

    # Same calendar date as EVAL_INSTANT, offset by +13h from a caller's
    # local perspective, normalized to the same UTC date.
    dst_shifted_instant = datetime(2026, 8, 18, 23, 59, tzinfo=UTC) - timedelta(
        hours=11, minutes=59
    )
    assert dst_shifted_instant.date() == EVAL_INSTANT.date()

    report_a = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    report_b = engine.evaluate(store.snapshot(), dst_shifted_instant, MementoConfig())

    m1_a = _row(report_a, ids["M1"])
    m1_b = _row(report_b, ids["M1"])
    assert m1_a.age_days == m1_b.age_days == 78


def test_horizon_share_crosses_rung(store) -> None:
    """E-19 [GOLDEN]: M1 elapsed 78d vs H remaining-at-creation 1310d ->
    share ~= 0.0595 (78/1310), crossing the 0.05 rung."""
    golden = load_golden()
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    m1 = _row(report, ids["M1"])
    assert m1.horizon_share is not None
    assert round(m1.horizon_share, 4) == golden["horizon_share_m1"] == 0.0595
    assert m1.horizon_share > golden["horizon_share_m1_crosses_rung"] == 0.05
    assert "1310" in m1.derivation
