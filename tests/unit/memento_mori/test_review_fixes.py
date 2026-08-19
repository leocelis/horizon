"""Regression tests for defects found in the post-implementation review.

Each test asserts the *property the defect violated*, not the symptom, and
fails against the unfixed code:

* G-13 / G-14 — ``cost_of_delay`` and ``breakeven_passed`` were registered in
  the tier table but never emitted by ``_due_predicates``, so two of the twelve
  documented signals could not fire (PRD §5.2). The stated reason — "the engine
  does not compute a MoneyBlock per item" — was contradicted by
  ``engine.evaluate()``, which does.
* E-20 — ``SlowestEntity.n`` was hardcoded to ``1`` while its own derivation
  read "over N recorded entities", so the audit trail misreported the size of
  the population the argmax summarised
  (memento_engine_intent.yaml::derivation_on_every_row: "n for any summary
  statistic").
* E-21 — a person-namespace winner had its title redacted to ``"person"`` but
  its stable ``item_id`` still emitted, and an id is resolvable to the title
  through the store — so the redaction did not survive contact with a reader
  who has store access (memento_signals_intent.yaml::no_person_ranking_in_output).
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind, Provenance

from .conftest import build_smallco

UTC = timezone.utc
T_EVAL = datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)


def _root(store):
    return store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        parent_id=None,
        end_date=date(2030, 1, 1),
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )


# --------------------------------------------------------------------------
# G-13 — cost_of_delay fires from caller-declared money facts
# --------------------------------------------------------------------------
def test_g13_cost_of_delay_fires_when_rate_amount_and_threshold_are_declared(store):
    root = _root(store)
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        amount=Decimal("10"),
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )

    config = MementoConfig(
        store_path=None,
        time_value_rate=Decimal("50"),
        cost_of_delay_threshold=Decimal("1"),
    )
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    assert report.money, "engine must produce MoneyBlocks when rate + amount are declared"

    signal_report, _ = signals.evaluate_signals(store.snapshot(), report, T_EVAL, config)
    fired = {s.signal_type for s in signal_report.fired}
    assert "cost_of_delay" in fired, (
        "cost_of_delay is a documented signal (PRD §5.2) and must fire once its "
        "three caller-declared facts exist — rate, amount, threshold"
    )
    cod = next(s for s in signal_report.fired if s.signal_type == "cost_of_delay")
    assert "threshold=" in cod.derivation and str(mission)[:0] == ""


def test_g13_no_threshold_means_no_predicate_not_a_default(store):
    """Degrade by omission: without a declared threshold the signal is absent
    entirely — the engine never substitutes a default cutoff."""
    root = _root(store)
    store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        amount=Decimal("10"),
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    config = MementoConfig(store_path=None, time_value_rate=Decimal("50"))
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    signal_report, _ = signals.evaluate_signals(store.snapshot(), report, T_EVAL, config)
    all_types = {
        s.signal_type for s in (*signal_report.fired, *signal_report.due, *signal_report.acked)
    }
    assert "cost_of_delay" not in all_types


# --------------------------------------------------------------------------
# G-14 — breakeven_passed fires from a ratified break-even date
# --------------------------------------------------------------------------
def test_g14_breakeven_passed_fires_on_a_ratified_date_that_elapsed(store):
    root = _root(store)
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission,
        kind=EventKind.RATIFY,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        payload={"kind": "breakeven", "breakeven_date": "2026-08-01"},
    )

    config = MementoConfig(store_path=None)
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    signal_report, _ = signals.evaluate_signals(store.snapshot(), report, T_EVAL, config)

    fired = {s.signal_type for s in signal_report.fired}
    assert "breakeven_passed" in fired, (
        "a ratified break-even date that elapsed without a measured improvement "
        "must fire — it is the plane's only check that a purchase paid back"
    )


def test_g14_measured_improvement_suppresses_the_signal(store):
    root = _root(store)
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission,
        kind=EventKind.RATIFY,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        payload={
            "kind": "breakeven",
            "breakeven_date": "2026-08-01",
            "measured_improvement": True,
        },
    )
    config = MementoConfig(store_path=None)
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    signal_report, _ = signals.evaluate_signals(store.snapshot(), report, T_EVAL, config)
    assert "breakeven_passed" not in {s.signal_type for s in signal_report.fired}


# --------------------------------------------------------------------------
# E-20 — n is the summarised population, not a constant
# --------------------------------------------------------------------------
def test_e20_slowest_entity_n_matches_the_population_it_summarised(store):
    build_smallco(store)
    config = MementoConfig(store_path=None)
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    assert report.slowest_entities

    for se in report.slowest_entities:
        # the derivation states the population size; n must agree with it
        stated = int(se.derivation.split("over ")[1].split(" recorded")[0])
        assert se.n == stated, (
            f"n={se.n} contradicts the derivation's own population size {stated}; "
            "a summary statistic must report the n it summarised"
        )
        assert se.n >= 2 or stated == 1


# --------------------------------------------------------------------------
# E-21 — a person winner's identifier is withheld, not just its title
# --------------------------------------------------------------------------
def test_e21_person_namespace_winner_withholds_the_resolvable_identifier(store):
    root = _root(store)
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    person = store.register_item(
        kind=ItemKind.ENTITY,
        title="a-real-persons-actual-name",
        parent_id=mission,
        namespace="person",
        person_namespace_confirmed=True,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=person,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        stage="review",
    )

    config = MementoConfig(store_path=None)
    report = engine.evaluate(store.snapshot(), T_EVAL, config)
    winners = [se for se in report.slowest_entities if se.mission_id == mission]
    assert winners, "the person entity is still measured — only its identity is withheld"
    winner = winners[0]

    assert winner.slot_label == "person"
    assert winner.latency_days is not None, "redaction must not distort the measurement"
    assert winner.entity_item_id is None, (
        "the item_id resolves to the title through the store, so emitting it "
        "defeats the slot-label redaction for any reader with store access"
    )

    signal_report, _ = signals.evaluate_signals(store.snapshot(), report, T_EVAL, config)
    for sig in (*signal_report.fired, *signal_report.due, *signal_report.acked):
        if sig.signal_type != "slowest_entity":
            continue
        assert person not in str(sig.payload)
        assert person not in sig.derivation
        assert "a-real-persons-actual-name" not in str(sig.payload)
        assert "a-real-persons-actual-name" not in sig.derivation


# --------------------------------------------------------------------------
# E-22 — artifact provenance still required (guards the capture doctrine)
# --------------------------------------------------------------------------
def test_e22_artifact_event_still_requires_full_provenance(store):
    root = _root(store)
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission,
        kind=EventKind.ARTIFACT,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        provenance=Provenance(
            source_system="git",
            native_id="abc123",
            raw_timestamp=datetime(2026, 7, 1, tzinfo=UTC),
        ),
    )
    snapshot = store.snapshot()
    artifacts = [e for e in snapshot.events if e.kind == EventKind.ARTIFACT]
    assert artifacts and artifacts[0].provenance is not None
