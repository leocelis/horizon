"""S-6 [GOLDEN] — correcting an event supersedes, never overwrites.

memento_store_intent.yaml::append_only_bitemporal.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_supersede_retains_both_records(store: MementoStore) -> None:
    """A correcting event references the corrected event_id; both rows are
    retained with both time axes (valid_time, tx_time)."""
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

    original_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
    )

    corrected_id = store.record_event(
        item_id=mission_id,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 3, tzinfo=UTC),  # the real date, learned later
        correction_of=original_id,
    )

    events = {e.event_id: e for e in store.get_events(mission_id)}

    assert original_id in events, "the corrected record must still exist"
    assert corrected_id in events, "the correcting record must exist"
    assert events[original_id].correction_of is None
    assert events[corrected_id].correction_of == original_id
    assert events[original_id].valid_time == datetime(2026, 7, 2, tzinfo=UTC)
    assert events[corrected_id].valid_time == datetime(2026, 7, 3, tzinfo=UTC)
    # Both rows carry their own tx_time (when THIS store learned each fact).
    assert events[original_id].tx_time is not None
    assert events[corrected_id].tx_time is not None
    assert len(events) == 2, "supersede never deletes or overwrites a row"
