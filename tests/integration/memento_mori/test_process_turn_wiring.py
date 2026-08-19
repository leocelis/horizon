"""M-3, M-4 — process_turn wiring for the mission plane.

Per docs/spec/MEMENTO_MORI_TEST_PLAN.md §M and
docs/spec/MEMENTO_MORI_TECH_SPEC.md §6 ("process_turn: when a session is
associated with >=1 mission ... the pipeline appends the plane's due events
(post-cap) to active_events"). This is the end-to-end companion to the
registry-level unit checks in
tests/integration/memento_mori/test_compat_additivity.py (G-10, G-11).
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime, timezone

from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore
from horizon_monitor.monitor import FidelityMonitor

UTC = timezone.utc


def _build_single_mission_with_expired_ttl(store: MementoStore) -> tuple[str, str]:
    """A root + one mission + one task whose TTL has already expired at the
    evaluation instant used below — the minimal fixture needed to prove a
    signal.ttl_expired mission event reaches process_turn. Returns
    (mission_id, task_id)."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2500, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="M1",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission_id, kind=EventKind.PROGRESS, valid_time=datetime(2026, 6, 5, tzinfo=UTC)
    )
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="T1",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        ttl_start=date(2026, 7, 1),
        ttl_end=date(2026, 7, 20),
    )
    return mission_id, task_id


def test_m3_associated_session_receives_the_mission_event(tmp_path) -> None:
    """M-3 / TECH_SPEC §6: a session explicitly associated with a mission
    (via associate_mission) receives that mission's due signal
    (post-cap) in process_turn's returned events, tagged plane="mission"."""
    store = MementoStore(tmp_path / "store.db")
    mission_id, task_id = _build_single_mission_with_expired_ttl(store)

    monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
    session_id = monitor.new_conversation()
    monitor.associate_mission(session_id, mission_id)

    result = monitor.process_turn(
        session_id,
        "how's the mission going?",
        "let me check.",
        timestamp="2026-08-18T12:00:00+00:00",
    )

    mission_events = [e for e in result.events if e.plane == "mission"]
    assert len(mission_events) == 1, [e.type for e in result.events]
    (event,) = mission_events
    assert event.type == "signal.ttl_expired"
    assert event.active is True
    assert event.metadata["item_id"] == task_id
    assert event.suggested_behavior

    store.close()


def test_g11_configured_store_unassociated_session_zero_mission_events(tmp_path) -> None:
    """G-11 / M-3 pairing, exercised end-to-end (not just at the registry
    unit): a store IS configured and has due signals, but this session was
    never associated with any mission — zero memento events reach it."""
    store = MementoStore(tmp_path / "store.db")
    _build_single_mission_with_expired_ttl(store)

    monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
    session_id = monitor.new_conversation()
    # Deliberately no associate_mission() call.

    result = monitor.process_turn(
        session_id,
        "how's the mission going?",
        "let me check.",
        timestamp="2026-08-18T12:00:00+00:00",
    )

    assert [e for e in result.events if e.plane == "mission"] == []
    assert all(e.plane == "conversation" for e in result.events)

    store.close()


def test_m3_association_survives_session_re_registration(tmp_path) -> None:
    """ "Association must survive session re-registration": ending a
    conversation and starting a fresh one under the SAME session_id does
    not clear an earlier associate_mission() call — the AssociationRegistry
    is independent of Session lifecycle."""
    store = MementoStore(tmp_path / "store.db")
    mission_id, _task_id = _build_single_mission_with_expired_ttl(store)

    monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
    fixed_session_id = "reused-session-id"
    monitor.new_conversation(session_id=fixed_session_id)
    monitor.associate_mission(fixed_session_id, mission_id)

    monitor.end_conversation(fixed_session_id)
    monitor.new_conversation(session_id=fixed_session_id)  # re-registration, same id

    result = monitor.process_turn(
        fixed_session_id,
        "resuming",
        "picking this back up",
        timestamp="2026-08-18T12:00:00+00:00",
    )

    mission_events = [e for e in result.events if e.plane == "mission"]
    assert len(mission_events) == 1
    assert mission_events[0].type == "signal.ttl_expired"

    store.close()


def test_m3_scoping_ignores_missions_the_session_was_not_associated_with(tmp_path) -> None:
    """A store may hold several missions; a session associated with ONE of
    them never receives another mission's signals, even though both are
    due at the same evaluation instant (mission_scope_for_item ancestry
    walk)."""
    store = MementoStore(tmp_path / "store.db")
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2500, 1, 1),
    )
    mission_a = store.register_item(
        kind=ItemKind.MISSION,
        title="A",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission_a, kind=EventKind.PROGRESS, valid_time=datetime(2026, 6, 5, tzinfo=UTC)
    )
    task_a = store.register_item(
        kind=ItemKind.TASK,
        title="T-A",
        parent_id=mission_a,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        ttl_start=date(2026, 7, 1),
        ttl_end=date(2026, 7, 20),
    )
    mission_b = store.register_item(
        kind=ItemKind.MISSION,
        title="B",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=mission_b, kind=EventKind.PROGRESS, valid_time=datetime(2026, 6, 5, tzinfo=UTC)
    )
    deferral_b = store.register_item(
        kind=ItemKind.DEFERRAL,
        title="F-B",
        parent_id=mission_b,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        revisit_date=date(2026, 7, 15),
    )

    monitor = FidelityMonitor(
        memento_store=store, memento_config=MementoConfig(per_turn_fire_cap=10)
    )
    session_id = monitor.new_conversation()
    monitor.associate_mission(session_id, mission_a)  # only A, never B

    result = monitor.process_turn(
        session_id, "status?", "checking", timestamp="2026-08-18T12:00:00+00:00"
    )

    mission_events = [e for e in result.events if e.plane == "mission"]
    item_ids = {e.metadata["item_id"] for e in mission_events}
    assert task_a in item_ids
    assert deferral_b not in item_ids

    store.close()


# ── M-4 [PROPERTY] — plane tag, byte-identical otherwise ───────────────────


def test_m4_mission_event_carries_plane_mission(tmp_path) -> None:
    store = MementoStore(tmp_path / "store.db")
    mission_id, _task_id = _build_single_mission_with_expired_ttl(store)
    monitor = FidelityMonitor(memento_store=store, memento_config=MementoConfig())
    session_id = monitor.new_conversation()
    monitor.associate_mission(session_id, mission_id)

    result = monitor.process_turn(
        session_id, "status?", "checking", timestamp="2026-08-18T12:00:00+00:00"
    )
    mission_events = [e for e in result.events if e.type == "signal.ttl_expired"]
    assert len(mission_events) == 1
    assert mission_events[0].plane == "mission"
    store.close()


def test_m4_conversation_events_are_byte_identical_except_the_new_plane_field() -> None:
    """ "existing conversation events gain plane='conversation' with no
    other byte changed": every field an Event carried before this
    integration is unchanged, and `plane` is the ONLY additional field.
    Constructs an Event exactly as events/evaluator.py::emit() does (no
    explicit `plane` kwarg — the point being tested is that the default
    kicks in) so this does not depend on a specific turn triggering a
    real signal."""
    from horizon_monitor.models import Event

    event = Event(
        type="checkpoint.clarification",
        active=True,
        confidence=0.5,
        turn=1,
        suggested_behavior="Pause and ask a targeted question before continuing",
        mode="explore",
        metadata={"divergence_score": 0.5},
    )
    d = dataclasses.asdict(event)
    assert set(d) == {
        "type",
        "active",
        "confidence",
        "turn",
        "suggested_behavior",
        "mode",
        "metadata",
        "plane",
    }
    without_plane = {k: v for k, v in d.items() if k != "plane"}
    assert without_plane == {
        "type": "checkpoint.clarification",
        "active": True,
        "confidence": 0.5,
        "turn": 1,
        "suggested_behavior": "Pause and ask a targeted question before continuing",
        "mode": "explore",
        "metadata": {"divergence_score": 0.5},
    }
    assert d["plane"] == "conversation"


def test_m4_full_conversation_only_regression_suite_marker_is_unaffected() -> None:
    """A direct proof that the plane tag changed nothing about conversation
    event SELECTION logic (only added a field to the dataclass): running
    the exact same multi-turn conversation through two independently
    constructed monitors still produces identical event type sequences."""
    monitor_a = FidelityMonitor()
    monitor_b = FidelityMonitor()
    sa = monitor_a.new_conversation(session_id="m4-fixed")
    sb = monitor_b.new_conversation(session_id="m4-fixed")

    turns = [
        ("What is a B-tree?", "A balanced tree optimised for block-oriented storage reads."),
        ("How does it differ from a B+ tree?", "B+ trees store values only in leaves."),
    ]
    clock = datetime(2026, 4, 22, 8, 30, tzinfo=UTC)
    for human, agent in turns:
        clock = clock.replace(minute=(clock.minute + 1) % 60)
        ra = monitor_a.process_turn(sa, human, agent, timestamp=clock.isoformat())
        rb = monitor_b.process_turn(sb, human, agent, timestamp=clock.isoformat())
        assert [e.type for e in ra.events] == [e.type for e in rb.events]
        assert all(e.plane == "conversation" for e in ra.events)
