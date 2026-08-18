"""E-4, E-5 — entity latency and wait/touch-only-from-caller-labels.

memento_engine_intent.yaml::derivation_on_every_row (E-4 slowest_entity);
memento_engine_intent.yaml::degrade_by_omission (E-5 no inference).
"""

from __future__ import annotations

from datetime import timezone

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind

from .conftest import EVAL_INSTANT, build_smallco, load_golden

UTC = timezone.utc


def _row(report, item_id: str):
    return next(r for r in report.items if r.item_id == item_id)


def test_entity_time_in_stage_and_slowest_entity(store) -> None:
    """E-4 [GOLDEN]: E1 time-in-stage 25d (closed); E2 open 21d;
    slowest_entity = E2 "operator" — the OPEN sojourn dominates a longer
    closed one, because it is the currently-accruing blocker."""
    golden = load_golden()
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    e1 = _row(report, ids["E1"])
    assert e1.time_in_stage_days == golden["entity_e1_time_in_stage_days"] == 25
    assert e1.is_open_stage is golden["entity_e1_is_open"] is False

    e2 = _row(report, ids["E2"])
    assert e2.time_in_stage_days == golden["entity_e2_time_in_stage_days"] == 21
    assert e2.is_open_stage is golden["entity_e2_is_open"] is True

    slowest = next(s for s in report.slowest_entities if s.mission_id == ids["M1"])
    assert slowest.entity_item_id == ids["E2"]
    assert slowest.slot_label == golden["slowest_entity_slot_label"] == "operator"
    assert slowest.is_open is True
    assert "open" in slowest.derivation.lower()


def test_wait_touch_ratio_only_from_caller_labels(store) -> None:
    """E-5: stage events without a caller wait_or_touch label contribute to
    NO wait/touch ratio — never inferred."""
    ids = build_smallco(store)
    # smallco's E1/E2 stage events carry no wait_or_touch label.
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    e1 = _row(report, ids["E1"])
    assert e1.wait_vs_touch_ratio is None
    assert e1.omitted is not None and "wait" in e1.omitted.lower()


def test_wait_touch_ratio_computed_when_labelled(store) -> None:
    """When the caller DOES label stage segments, a ratio is computed —
    proving the omission above is a real degrade path, not a bug."""
    ids = build_smallco(store)
    store.record_event(
        item_id=ids["E2"],
        kind=EventKind.STAGE_EXIT,
        valid_time=EVAL_INSTANT,
        stage="operator",
        wait_or_touch="wait",
    )
    # Re-label E1's segment retroactively via a fresh, fully-labelled entity
    # instead of mutating history — corrections supersede, they do not
    # rewrite (append_only_bitemporal); labelling both existing E1 events
    # would require two correction events, so this test uses E2's freshly
    # closed, single-labelled segment as the positive case.
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    e2 = _row(report, ids["E2"])
    assert e2.wait_vs_touch_ratio == 1.0
    assert e2.omitted is None
