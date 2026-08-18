"""Shared fixtures for Memento Mori tests.

Builds the "smallco" synthetic fixture from
docs/spec/MEMENTO_MORI_TEST_PLAN.md verbatim. All data here is synthetic —
no private project, person, or workspace path.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc

# Evaluation instant used by nearly every test-plan case.
EVAL_INSTANT = datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)


def _dt(y: int, m: int, d: int) -> datetime:
    return datetime(y, m, d, tzinfo=UTC)


@pytest.fixture
def store(tmp_path: Path) -> MementoStore:
    s = MementoStore(tmp_path / "memento.db")
    yield s
    s.close()


def build_smallco(store: MementoStore) -> dict[str, str]:
    """Register the shared "smallco" fixture and return a name -> item_id map.

    Root horizon H: end date 2030-01-01
    Mission M1 "ship-widget" (created 2026-06-01, stall_days=14)
      Task T1 TTL ratified [2026-07-01 -> 2026-07-20]
      Deadline D1 2026-09-30, kind=hard_cutoff, gates T1
      Deadline D2 2026-12-31, kind=one_shot_window, gates nothing
      Gate G1 age_budget_days=30 (created 2026-07-01)
      Entity E1 slot "vendor-queue"; Entity E2 slot "operator"
      Deferral F1 revisit 2026-08-10
      Probe P1 (alt path "channel-b", registered 2026-08-01) TTL [2026-08-01 -> 2026-08-15]
    Progress events on M1: 2026-06-05, 2026-06-20, 2026-07-02 (none after)
    Stage events: E1 enter 2026-07-03 / exit 2026-07-28 (25d); E2 enter 2026-07-28, still open
    P1 stage: enter 2026-08-02 / exit 2026-08-06 (4d sojourn, completed)
    """
    ids: dict[str, str] = {}

    ids["H"] = store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        created_valid=_dt(2026, 1, 1),
        end_date=date(2030, 1, 1),
    )

    ids["M1"] = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=ids["H"],
        created_valid=_dt(2026, 6, 1),
        stall_days=14,
    )

    ids["T1"] = store.register_item(
        kind=ItemKind.TASK,
        title="T1",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
        ttl_start=date(2026, 7, 1),
        ttl_end=date(2026, 7, 20),
    )

    ids["D1"] = store.register_item(
        kind=ItemKind.DEADLINE,
        title="D1",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
        deadline_date=date(2026, 9, 30),
        deadline_kind="hard_cutoff",
        gates_item_id=ids["T1"],
    )

    ids["D2"] = store.register_item(
        kind=ItemKind.DEADLINE,
        title="D2",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
        deadline_date=date(2026, 12, 31),
        deadline_kind="one_shot_window",
        gates_item_id=None,
    )

    ids["G1"] = store.register_item(
        kind=ItemKind.GATE,
        title="G1",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
        age_budget_days=30,
    )

    ids["E1"] = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
    )

    ids["E2"] = store.register_item(
        kind=ItemKind.ENTITY,
        title="operator",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
    )

    ids["F1"] = store.register_item(
        kind=ItemKind.DEFERRAL,
        title="F1",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 7, 1),
        revisit_date=date(2026, 8, 10),
    )

    ids["P1"] = store.register_item(
        kind=ItemKind.PROBE,
        title="channel-b",
        parent_id=ids["M1"],
        created_valid=_dt(2026, 8, 1),
        ttl_start=date(2026, 8, 1),
        ttl_end=date(2026, 8, 15),
    )

    for d in (date(2026, 6, 5), date(2026, 6, 20), date(2026, 7, 2)):
        store.record_event(
            item_id=ids["M1"],
            kind=EventKind.PROGRESS,
            valid_time=datetime(d.year, d.month, d.day, tzinfo=UTC),
        )

    store.record_event(
        item_id=ids["E1"],
        kind=EventKind.STAGE_ENTER,
        valid_time=_dt(2026, 7, 3),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=ids["E1"],
        kind=EventKind.STAGE_EXIT,
        valid_time=_dt(2026, 7, 28),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=ids["E2"],
        kind=EventKind.STAGE_ENTER,
        valid_time=_dt(2026, 7, 28),
        stage="operator",
    )

    store.record_event(
        item_id=ids["P1"],
        kind=EventKind.STAGE_ENTER,
        valid_time=_dt(2026, 8, 2),
        stage="channel-b",
    )
    store.record_event(
        item_id=ids["P1"],
        kind=EventKind.STAGE_EXIT,
        valid_time=_dt(2026, 8, 6),
        stage="channel-b",
    )

    return ids
