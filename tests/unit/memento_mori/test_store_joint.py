"""Store joint satisfaction — all four memento_store constraints on one flow.

memento_store_intent.yaml::constraint_satisfiability.joint_satisfaction_test.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento.errors import (
    ArtifactProvenanceRequiredError,
    PersonNamespaceUnflaggedError,
    UndatedDeferralError,
)
from horizon_monitor.memento.models import EventKind, ItemKind, Provenance
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_all_store_constraints_one_flow(store: MementoStore) -> None:
    # 1. finite rooted tree
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="M1",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )

    # 2. schema_rejections_total: undated deferral rejected atomically
    before = store.get_items()
    with pytest.raises(UndatedDeferralError):
        store.register_item(
            kind=ItemKind.DEFERRAL,
            title="undated",
            parent_id=mission_id,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        )
    assert store.get_items() == before

    # 3. person_namespace_explicit
    with pytest.raises(PersonNamespaceUnflaggedError):
        store.register_item(
            kind=ItemKind.ENTITY,
            title="named counterparty",
            parent_id=mission_id,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
            namespace="person",
        )
    person_entity_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="named counterparty",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        namespace="person",
        person_namespace_confirmed=True,
    )
    assert store.get_item(person_entity_id).namespace == "person"

    # 4. artifact_provenance_required
    with pytest.raises(ArtifactProvenanceRequiredError):
        store.record_event(
            item_id=mission_id,
            kind=EventKind.ARTIFACT,
            valid_time=datetime(2026, 7, 2, tzinfo=UTC),
        )
    artifact_event_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.ARTIFACT,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
        provenance=Provenance(
            source_system="git", native_id="abc123", raw_timestamp=datetime(2026, 7, 2, tzinfo=UTC)
        ),
    )

    # 5. append_only_bitemporal: correction supersedes, both retained
    correction_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.ARTIFACT,
        valid_time=datetime(2026, 7, 3, tzinfo=UTC),
        provenance=Provenance(
            source_system="git", native_id="abc123", raw_timestamp=datetime(2026, 7, 2, tzinfo=UTC)
        ),
        correction_of=artifact_event_id,
    )

    events = {e.event_id: e for e in store.get_events(mission_id)}
    assert artifact_event_id in events and correction_id in events
    assert events[correction_id].correction_of == artifact_event_id
