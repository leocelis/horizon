"""R — Replay & self-judgment (PRD §9).

MEMENTO_MORI_TEST_PLAN.md::R-1..R-4. R-1/R-2 are [GOLDEN] (hand-checked
fixture: tests/fixtures/memento_mori/replay_golden.json); R-3 is [HUMAN];
R-4 is untagged supporting coverage.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento import engine, metrics
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind

from .conftest import load_replay_golden

UTC = timezone.utc


def _build_replay_fixture(store, operator_side: bool):
    """A synthetic 90-day history (2026-01-01 -> 2026-04-01) with one
    entity's CLOSED sojourn deliberately made the longest of three
    recorded entities — the designed bottleneck. Every sojourn here is
    closed (E-4's open-sojourn-dominates shortcut never engages), so
    naming the bottleneck exercises the plain argmax(time_in_stage_days)
    arithmetic from stage timestamps alone. ``operator_side`` swaps the
    bottleneck's slot label to "operator" for R-2's comfortable-instrument
    check (PRD §9)."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="90-day replay mission",
        parent_id=root_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    for d in (date(2026, 1, 15), date(2026, 2, 15), date(2026, 3, 15)):
        store.record_event(
            item_id=mission_id,
            kind=EventKind.PROGRESS,
            valid_time=datetime(d.year, d.month, d.day, tzinfo=UTC),
        )

    bottleneck_title = "operator" if operator_side else "legal-review"
    bottleneck_id = store.register_item(
        kind=ItemKind.ENTITY,
        title=bottleneck_title,
        parent_id=mission_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    fast1_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=mission_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    fast2_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="design-review",
        parent_id=mission_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )

    store.record_event(
        item_id=bottleneck_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 1, 1, tzinfo=UTC),
        stage=bottleneck_title,
    )
    store.record_event(
        item_id=bottleneck_id,
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 3, 2, tzinfo=UTC),
        stage=bottleneck_title,
    )
    store.record_event(
        item_id=fast1_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 1, 1, tzinfo=UTC),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=fast1_id,
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 1, 11, tzinfo=UTC),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=fast2_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 1, 1, tzinfo=UTC),
        stage="design-review",
    )
    store.record_event(
        item_id=fast2_id,
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 1, 6, tzinfo=UTC),
        stage="design-review",
    )

    return mission_id, bottleneck_id


def test_r1_retrospective_replay_names_designed_bottleneck(store) -> None:
    """R-1 [GOLDEN]: a synthetic 90-day history with a designed bottleneck
    at one entity -> slowest-entity computation names it from stage
    timestamps alone, with the golden duration and slot label."""
    golden = load_replay_golden()
    mission_id, bottleneck_id = _build_replay_fixture(store, operator_side=False)
    eval_instant = datetime.fromisoformat(golden["eval_instant"])

    report = engine.evaluate(store.snapshot(), eval_instant, MementoConfig())
    slowest = next(s for s in report.slowest_entities if s.mission_id == mission_id)

    assert slowest.entity_item_id == bottleneck_id
    assert slowest.slot_label == golden["r1_bottleneck_slot_label"] == "legal-review"
    assert slowest.latency_days == golden["entity_bottleneck_time_in_stage_days"] == 60
    assert slowest.is_open == golden["slowest_entity_is_open"] is False


def test_r2_operator_side_bottleneck_is_named_not_exempted(store) -> None:
    """R-2 [GOLDEN]: the "comfortable instrument" test — when the designed
    bottleneck IS the operator slot, the computation names it exactly as
    it would name any other entity. No special-case exemption exists for
    the operator (intent risk: "comfortable instrument")."""
    golden = load_replay_golden()
    mission_id, bottleneck_id = _build_replay_fixture(store, operator_side=True)
    eval_instant = datetime.fromisoformat(golden["eval_instant"])

    report = engine.evaluate(store.snapshot(), eval_instant, MementoConfig())
    slowest = next(s for s in report.slowest_entities if s.mission_id == mission_id)

    assert slowest.entity_item_id == bottleneck_id
    assert slowest.slot_label == golden["r2_bottleneck_slot_label"] == "operator"
    assert slowest.latency_days == golden["entity_bottleneck_time_in_stage_days"] == 60


def test_r3_time_to_next_action_metric_exists_and_is_queryable(store) -> None:
    """R-3 [HUMAN]: the primary success metric — interval between a fired
    signal and the next recorded externally-visible event on that
    mission — is computed and queryable. Its *evaluation* against a
    baseline (whether the plane actually shortens this interval in real
    use) is an operational exercise the PRD names explicitly as outside
    unit-test scope; this test only asserts the arithmetic exists and is
    correct over caller-supplied records.

    REVIEWER NOTE [HUMAN]: confirm the design choice "next PROGRESS/
    ARTIFACT event at-or-after fired_at, on the SAME item_id" is the
    intended scope for this metric (PRD §9 says "on that mission" —
    metrics.time_to_next_action() takes item_id, not mission_id, as the
    caller passes each fired signal's own item; a caller wanting the
    mission-level metric passes the mission's own item_id alongside its
    children's, or aggregates several TimeToNextAction rows themselves).
    """
    mission_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="T1",
        parent_id=mission_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        ttl_start=date(2026, 1, 1),
        ttl_end=date(2026, 1, 10),
    )
    fired_at = datetime(2026, 1, 11, tzinfo=UTC)  # the day ttl_expired would have fired

    # No externally-visible event recorded yet -> None, never a guessed interval.
    (unresolved,) = metrics.time_to_next_action(
        fired_signals=((task_id, "ttl_expired", fired_at),),
        events_by_item={task_id: tuple(store.get_events(task_id))},
    )
    assert unresolved.next_action_at is None and unresolved.interval_days is None

    # The blocker gets investigated three days later -> interval computed.
    store.record_event(
        item_id=task_id, kind=EventKind.PROGRESS, valid_time=datetime(2026, 1, 14, tzinfo=UTC)
    )
    (resolved,) = metrics.time_to_next_action(
        fired_signals=((task_id, "ttl_expired", fired_at),),
        events_by_item={task_id: tuple(store.get_events(task_id))},
    )
    assert resolved.next_action_at == datetime(2026, 1, 14, tzinfo=UTC)
    assert resolved.interval_days == 3
    assert str(fired_at.date()) in resolved.derivation


def test_r4_alarm_kpis_are_present_and_queryable() -> None:
    """R-4: fires-per-turn, % turns with >1 new fire (structurally 0 when
    the per-turn cap is respected, per G-5), and a caller-supplied
    stale-ack count — present as a queryable arithmetic result."""
    kpis = metrics.alarm_kpis(fired_counts_per_turn=(1, 0, 1, 1, 0), stale_ack_count=2)
    assert kpis.turns_evaluated == 5
    assert kpis.fires_per_turn == 3 / 5
    assert kpis.pct_turns_with_multiple_new_fires == 0.0  # cap respected -> structurally 0
    assert kpis.stale_ack_count == 2
    assert "3" in kpis.derivation and "5" in kpis.derivation

    empty_kpis = metrics.alarm_kpis(fired_counts_per_turn=(), stale_ack_count=0)
    assert empty_kpis.turns_evaluated == 0
    assert empty_kpis.fires_per_turn == 0.0  # no turns yet -> zero, never an invented rate
