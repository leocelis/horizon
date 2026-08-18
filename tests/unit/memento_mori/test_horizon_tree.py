"""Parent constraint: finite_rooted_tree.

horizon_memento_mori_intent.yaml::constraints[finite_rooted_tree].
test: tests/unit/memento_mori/test_horizon_tree.py::test_single_finite_root_and_rooted_items
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento.errors import (
    DuplicateRootError,
    NonFiniteRootError,
    RootlessItemError,
)
from horizon_monitor.memento.models import ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_single_finite_root_and_rooted_items(store: MementoStore) -> None:
    """Exactly one finite-end-date HORIZON root per store; every other item
    must carry a parent path terminating at it; violations are rejected
    with a schema error."""
    with pytest.raises(NonFiniteRootError):
        store.register_item(
            kind=ItemKind.HORIZON,
            title="infinite",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=None,
        )

    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    assert store.get_root() is not None
    assert store.get_root().item_id == root_id

    with pytest.raises(DuplicateRootError):
        store.register_item(
            kind=ItemKind.HORIZON,
            title="second root",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2031, 1, 1),
        )

    with pytest.raises(RootlessItemError):
        store.register_item(
            kind=ItemKind.MISSION,
            title="orphan",
            parent_id=None,
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )

    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="rooted mission",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="grandchild task",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    assert store.get_item(task_id).parent_id == mission_id
