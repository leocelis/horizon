"""G-9 [HUMAN] — mechanical linter: no person-ordered lists anywhere in
suggested_behavior templates or generated payloads; slowest_entity uses slot
labels only, even when the winning entity is a confirmed person namespace.

memento_signals_intent.yaml::no_person_ranking_in_output: "a template linter
enforces this in CI" — this file IS that linter, run as a normal test.

REVIEWER NOTE [HUMAN]: an ai_generated test cannot certify this constraint
alone (IVD Rule 3); a human reviewer should read SUGGESTED_BEHAVIOR verbatim
before sign-off, since a banned phrase this linter does not anticipate would
otherwise slip through silently.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind

UTC = timezone.utc

# Deliberately mechanical: any of these substrings in a template or a
# generated payload value fails the linter. Ordinal / ranking words are the
# shape a person-ranking regression would take ("fastest team member",
# "top performer", "slowest: alice, bob, carol").
_BANNED_SUBSTRINGS = (
    "fastest",
    "slowest performer",
    "top performer",
    "ranked",
    "ranking",
    "leaderboard",
    "compared to their peers",
    "vs. other",
)


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


def test_suggested_behavior_templates_carry_no_ranking_language() -> None:
    for signal_type, text in signals.SUGGESTED_BEHAVIOR.items():
        lowered = text.lower()
        for banned in _BANNED_SUBSTRINGS:
            assert (
                banned not in lowered
            ), f"{signal_type!r} template contains banned phrase {banned!r}"


def test_slowest_entity_payload_redacts_person_namespace_winner(store) -> None:
    """A confirmed person-namespace entity may still win the argmax
    (engine.py does not exclude it from computation) but its title must
    never reach the signal payload or derivation text — only the generic
    "person" slot label may."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=_dt(2020, 1, 1),
        end_date=date(2030, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root_id,
        created_valid=_dt(2026, 1, 1),
        stall_days=3650,
    )
    person_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="a-real-persons-actual-name",
        parent_id=mission_id,
        created_valid=_dt(2026, 1, 1),
        namespace="person",
        person_namespace_confirmed=True,
    )
    slot_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=mission_id,
        created_valid=_dt(2026, 1, 1),
    )
    store.record_event(
        item_id=person_id, kind=EventKind.STAGE_ENTER, valid_time=_dt(2026, 7, 1), stage="review"
    )
    store.record_event(
        item_id=person_id, kind=EventKind.STAGE_EXIT, valid_time=_dt(2026, 7, 30), stage="review"
    )
    store.record_event(
        item_id=slot_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=_dt(2026, 7, 1),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=slot_id, kind=EventKind.STAGE_EXIT, valid_time=_dt(2026, 7, 5), stage="vendor-queue"
    )
    store.record_event(item_id=mission_id, kind=EventKind.PROGRESS, valid_time=_dt(2026, 8, 15))

    config = MementoConfig()
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, _dt(2026, 8, 18), config)
    signal_report, _ = signals.evaluate_signals(snapshot, report, _dt(2026, 8, 18), config)

    all_signals = signal_report.fired + signal_report.due + signal_report.acked
    slowest_entity_signals = [s for s in all_signals if s.signal_type == "slowest_entity"]
    assert slowest_entity_signals, "expected a slowest_entity predicate to be tracked"

    for signal in slowest_entity_signals:
        assert "a-real-persons-actual-name" not in str(signal.payload)
        assert "a-real-persons-actual-name" not in signal.derivation
        if signal.payload.get("entity_item_id") == person_id:
            assert signal.payload["slot_label"] == "person"

    # The engine report itself carries the same redaction independently of
    # signals.py (belt-and-suspenders against a person name reaching either
    # surface).
    assert all("a-real-persons-actual-name" not in se.slot_label for se in report.slowest_entities)
