"""S-5 — entity namespace defaults to slot; person requires an explicit flag.

memento_store_intent.yaml::person_namespace_explicit.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento.errors import PersonNamespaceUnflaggedError
from horizon_monitor.memento.models import ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def _root(store: MementoStore) -> str:
    return store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )


def test_entity_default_namespace_is_slot(store: MementoStore) -> None:
    """S-5a: no namespace argument -> "slot"."""
    root_id = _root(store)
    item_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=root_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    assert store.get_item(item_id).namespace == "slot"


def test_person_namespace_requires_explicit_flag(store: MementoStore) -> None:
    """S-5b: namespace="person" without the flag -> PersonNamespaceUnflaggedError."""
    root_id = _root(store)
    with pytest.raises(PersonNamespaceUnflaggedError):
        store.register_item(
            kind=ItemKind.ENTITY,
            title="a named counterparty",
            parent_id=root_id,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
            namespace="person",
        )


def test_person_namespace_with_flag_is_accepted_and_stored(store: MementoStore) -> None:
    """S-5c: the explicit flag stores namespace="person" on the item."""
    root_id = _root(store)
    item_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="a named counterparty",
        parent_id=root_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        namespace="person",
        person_namespace_confirmed=True,
    )
    assert store.get_item(item_id).namespace == "person"
