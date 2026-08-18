"""S-1..S-4 — schema rejections are typed, atomic, and un-overridable.

memento_store_intent.yaml::schema_rejections_total.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento.errors import (
    DuplicateRootError,
    NonFiniteRootError,
    RootlessItemError,
    UndatedDeferralError,
)
from horizon_monitor.memento.models import ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_deferral_without_revisit_date_rejected(store: MementoStore) -> None:
    """S-1 [HUMAN]: UndatedDeferralError; store unchanged."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    before = store.get_items()

    with pytest.raises(UndatedDeferralError):
        store.register_item(
            kind=ItemKind.DEFERRAL,
            title="undated park",
            parent_id=root_id,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
            revisit_date=None,
        )

    after = store.get_items()
    assert before == after, "a rejected write must leave the store byte-identical"


def test_second_root_rejected(store: MementoStore) -> None:
    """S-2: DuplicateRootError."""
    store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    with pytest.raises(DuplicateRootError):
        store.register_item(
            kind=ItemKind.HORIZON,
            title="second root",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2031, 1, 1),
        )


def test_rootless_item_rejected(store: MementoStore) -> None:
    """S-3: an item with no parent path to root is rejected."""
    store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    with pytest.raises(RootlessItemError):
        store.register_item(
            kind=ItemKind.MISSION,
            title="orphan mission",
            parent_id="does-not-exist",
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )

    with pytest.raises(RootlessItemError):
        store.register_item(
            kind=ItemKind.MISSION,
            title="parentless mission",
            parent_id=None,
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        )


def test_root_with_no_end_date_rejected(store: MementoStore) -> None:
    """S-4: a horizon must be finite; end_date=None is a schema error."""
    with pytest.raises(NonFiniteRootError):
        store.register_item(
            kind=ItemKind.HORIZON,
            title="infinite root",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=None,
        )

    assert store.get_items() == []
