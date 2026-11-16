"""A write that names an item the tenant does not hold is refused, never stored.

Found by a two-tenant end-to-end run: tenant B's clock_progress on tenant A's
task id answered {event_id} and left an orphan row in B's log, while A's history
was untouched. The same path gave a false "recorded" for any mistyped id, and
clock_ack stored an alarm state the same way. register_item already refuses a
parent outside the tenant; events and alarm states now get the same check.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento import EventKind, ItemKind, MementoStore
from horizon_monitor.memento.errors import UnknownItemError

UTC = timezone.utc


@pytest.fixture()
def two_tenants(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    a, b = store.scoped("tenant-a"), store.scoped("tenant-b")
    root_a = a.register_item(kind=ItemKind.HORIZON, title="root-a",
                             created_valid=datetime(2026, 1, 1, tzinfo=UTC), end_date=date(2030, 1, 1))
    task_a = a.register_item(kind=ItemKind.TASK, title="task-a", parent_id=root_a,
                             created_valid=datetime(2026, 1, 2, tzinfo=UTC))
    b.register_item(kind=ItemKind.HORIZON, title="root-b",
                    created_valid=datetime(2026, 1, 1, tzinfo=UTC), end_date=date(2030, 1, 1))
    return a, b, task_a


def test_event_for_another_tenants_item_is_refused(two_tenants):
    a, b, task_a = two_tenants
    with pytest.raises(UnknownItemError):
        b.record_event(item_id=task_a, kind=EventKind.PROGRESS, valid_time=datetime(2026, 2, 1, tzinfo=UTC))
    assert b.get_events() == []
    assert a.get_events(task_a) == []


def test_event_for_a_mistyped_id_is_refused(two_tenants):
    a, _b, _task = two_tenants
    with pytest.raises(UnknownItemError):
        a.record_event(item_id="no-such-item", kind=EventKind.PROGRESS, valid_time=datetime(2026, 2, 1, tzinfo=UTC))
    assert a.get_events() == []


def test_fire_state_for_another_tenants_item_is_refused(two_tenants):
    _a, b, task_a = two_tenants
    with pytest.raises(UnknownItemError):
        b.set_fire_state(task_a, "deadline_window", {"state": "acked"})
    assert b.get_all_fire_states() == []


def test_own_item_still_records(two_tenants):
    a, _b, task_a = two_tenants
    a.record_event(item_id=task_a, kind=EventKind.PROGRESS, valid_time=datetime(2026, 2, 1, tzinfo=UTC))
    a.set_fire_state(task_a, "deadline_window", {"state": "acked"})
    assert len(a.get_events(task_a)) == 1
    assert len(a.get_all_fire_states()) == 1
