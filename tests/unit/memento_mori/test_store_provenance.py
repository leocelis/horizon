"""S-8 — ARTIFACT events require complete provenance.

memento_store_intent.yaml::artifact_provenance_required.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento.errors import ArtifactProvenanceRequiredError
from horizon_monitor.memento.models import EventKind, ItemKind, Provenance
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def _mission(store: MementoStore) -> str:
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    return store.register_item(
        kind=ItemKind.MISSION,
        title="M1",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )


def test_artifact_event_without_provenance_rejected(store: MementoStore) -> None:
    mission_id = _mission(store)
    with pytest.raises(ArtifactProvenanceRequiredError):
        store.record_event(
            item_id=mission_id,
            kind=EventKind.ARTIFACT,
            valid_time=datetime(2026, 7, 2, tzinfo=UTC),
            provenance=None,
        )


def test_artifact_event_with_incomplete_provenance_rejected(store: MementoStore) -> None:
    mission_id = _mission(store)
    with pytest.raises(ArtifactProvenanceRequiredError):
        store.record_event(
            item_id=mission_id,
            kind=EventKind.ARTIFACT,
            valid_time=datetime(2026, 7, 2, tzinfo=UTC),
            provenance=Provenance(
                source_system="git", native_id="", raw_timestamp=datetime(2026, 7, 2, tzinfo=UTC)
            ),
        )


def test_artifact_event_with_full_provenance_accepted(store: MementoStore) -> None:
    mission_id = _mission(store)
    event_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.ARTIFACT,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
        provenance=Provenance(
            source_system="git",
            native_id="abc123",
            raw_timestamp=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
        ),
    )
    stored = {e.event_id: e for e in store.get_events(mission_id)}[event_id]
    assert stored.provenance is not None
    assert stored.provenance.source_system == "git"


def test_non_artifact_event_does_not_require_provenance(store: MementoStore) -> None:
    mission_id = _mission(store)
    event_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
    )
    assert event_id
