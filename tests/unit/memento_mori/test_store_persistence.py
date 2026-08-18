"""S-7 — the store survives process restart + session reset.

Backs both memento_store scope and the parent
horizon_memento_mori_intent.yaml::mission_scope_persistence constraint.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_store_survives_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "memento.db"

    store_a = MementoStore(db_path)
    root_id = store_a.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = store_a.register_item(
        kind=ItemKind.MISSION,
        title="M1",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store_a.record_event(
        item_id=mission_id,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
    )
    items_before = store_a.get_items()
    events_before = store_a.get_events()
    store_a.close()

    # Simulate a process restart / new session: reopen the same file.
    store_b = MementoStore(db_path)
    items_after = store_b.get_items()
    events_after = store_b.get_events()
    store_b.close()

    assert {i.item_id for i in items_before} == {i.item_id for i in items_after}
    assert {e.event_id for e in events_before} == {e.event_id for e in events_after}
    assert len(items_after) == 2
    assert len(events_after) == 1
