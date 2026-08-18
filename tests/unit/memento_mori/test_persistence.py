"""Parent constraint: mission_scope_persistence.

horizon_memento_mori_intent.yaml::constraints[mission_scope_persistence].
test: tests/unit/memento_mori/test_persistence.py::test_items_survive_session_lifecycle
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_items_survive_session_lifecycle(tmp_path: Path) -> None:
    """Clocked items persist across sessions/processes/agent restarts; a
    session's end, reset, or crash never deletes or ages-out an item; only
    explicit caller writes change the store."""
    db_path = tmp_path / "memento.db"

    session_1 = MementoStore(db_path)
    root_id = session_1.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = session_1.register_item(
        kind=ItemKind.MISSION,
        title="a mission spanning months",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    session_1.record_event(
        item_id=mission_id,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 6, 5, tzinfo=UTC),
    )
    # Simulate a crash: no close(), no explicit shutdown.
    del session_1

    # A brand-new session/process, months later, reopens the same store.
    session_2 = MementoStore(db_path)
    items = session_2.get_items()
    events = session_2.get_events(mission_id)
    session_2.close()

    assert len(items) == 2, "no item aged out or was deleted by the session ending"
    assert len(events) == 1, "no event was lost across the session boundary"
    assert any(i.item_id == mission_id for i in items)
