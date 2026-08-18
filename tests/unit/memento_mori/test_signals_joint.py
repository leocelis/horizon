"""Joint satisfaction test for memento_signals_intent.yaml.

constraint_satisfiability.joint_satisfaction_test: one flow that exercises
edge_not_level, ack_and_cap, no_person_ranking_in_output, and
strict_additivity together on the SAME sequence of evaluations, not as four
isolated unit tests (IVD Rule 2: individual-pass does not imply joint-pass).
"""

from __future__ import annotations

from datetime import datetime, timezone

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind, SignalState
from horizon_monitor.memento.signals import AssociationRegistry

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


def _evaluate(store, t_eval: datetime, config: MementoConfig):
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, t_eval, config)
    signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, config)
    for (item_id, signal_type), state in new_states.items():
        store.set_fire_state(item_id, signal_type, state)
    return signal_report


def test_state_machine_cap_ranking_additivity_one_flow(store) -> None:
    ids = build_smallco(store)
    config = MementoConfig()

    # A confirmed person-namespace entity, given the longest closed sojourn
    # on M1 so it wins slowest_entity's argmax outright — this is the
    # no_person_ranking_in_output half of the flow: the plane must still
    # compute a winner, just never leak the name anywhere.
    person_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="a-real-persons-actual-name",
        parent_id=ids["M1"],
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        namespace="person",
        person_namespace_confirmed=True,
    )
    store.record_event(
        item_id=person_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        stage="counsel",
    )
    store.record_event(
        item_id=person_id,
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 8, 10, tzinfo=UTC),
        stage="counsel",
    )

    # ── ack_and_cap + edge_not_level, turn 1 ──────────────────────────────
    turn1 = _evaluate(store, EVAL_INSTANT, config)
    assert len(turn1.fired) == 1, "ack_and_cap: at most per_turn_fire_cap new events per turn"
    winner = turn1.fired[0]
    assert winner.signal_type == "ttl_expired" and winner.tier == "P1"
    due_after_turn1 = {(s.item_id, s.signal_type) for s in turn1.due}
    assert (
        winner.item_id,
        winner.signal_type,
    ) not in due_after_turn1  # the winner is not also "due"
    assert len(due_after_turn1) >= 3  # everything else the cap held back

    # ── edge_not_level, turn 2 (same day, nothing new recorded) ──────────
    turn2 = _evaluate(store, EVAL_INSTANT, config)
    turn2_keys = {(s.item_id, s.signal_type) for s in turn2.fired}
    assert (winner.item_id, winner.signal_type) not in turn2_keys, (
        "edge_not_level: turn 1's winner is already RAISED and unacked — that exact "
        "(item, signal_type) pair must never re-fire on a subsequent turn with no new fact"
    )
    assert (
        len(turn2.fired) == 1
    )  # cap still holds; a different predicate wins this turn (e.g. P1's own ttl_expired)

    # ── ack_and_cap: acknowledge turn 2's winner, confirm it silences ────
    turn2_winner = turn2.fired[0]
    store.set_fire_state(
        turn2_winner.item_id,
        turn2_winner.signal_type,
        signals.ack(turn2_winner.item_id, turn2_winner.signal_type, EVAL_INSTANT, actor="operator"),
    )
    turn3 = _evaluate(store, EVAL_INSTANT, config)
    acked_keys = {(s.item_id, s.signal_type) for s in turn3.acked}
    assert (turn2_winner.item_id, turn2_winner.signal_type) in acked_keys

    # ── no_person_ranking_in_output, verified over every signal produced
    #    across all three turns ───────────────────────────────────────────
    every_signal = (
        turn1.fired + turn1.due + turn2.fired + turn2.due + turn3.fired + turn3.due + turn3.acked
    )
    for s in every_signal:
        assert "a-real-persons-actual-name" not in str(s.payload)
        assert "a-real-persons-actual-name" not in s.derivation
        assert "a-real-persons-actual-name" not in s.suggested_behavior
    slowest_entity_signals = [s for s in every_signal if s.signal_type == "slowest_entity"]
    assert slowest_entity_signals, "expected slowest_entity to be a tracked predicate on M1"
    for s in slowest_entity_signals:
        if s.payload.get("entity_item_id") == person_id:
            assert s.payload["slot_label"] == "person"

    # ── strict_additivity, same store instance, same flow ────────────────
    registry = AssociationRegistry()
    assert registry.is_associated("some-other-session") is False
    registry.associate("some-other-session", ids["M1"])
    assert registry.missions_for("some-other-session") == (ids["M1"],)

    # SignalState stays a closed 5-member enum throughout this flow — no
    # state produced above is a turn-count/elapsed-turns member (G-4,
    # re-asserted here so the joint flow, not just an isolated unit test,
    # touches every constraint).
    observed_states = {s.state for s in every_signal}
    assert observed_states <= {member.value for member in SignalState}
