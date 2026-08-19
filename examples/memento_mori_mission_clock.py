#!/usr/bin/env python3
"""Memento Mori — the mission plane, end to end in one file.

The conversation plane asks "is this dialogue degrading?". This plane asks a
different question: "is this goal still moving, and against what clock?"

Runs with no arguments, no network, no API key, no LLM call. It builds a small
synthetic mission in a temporary store, evaluates the clock at a fixed instant
so the output is reproducible, and prints what an operator would see.

    python examples/memento_mori_mission_clock.py
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from horizon_monitor.memento import (
    EventKind,
    ItemKind,
    MementoConfig,
    MementoStore,
    UndatedDeferralError,
    evaluate,
    evaluate_signals,
)

UTC = timezone.utc

# A fixed evaluation instant: the same store evaluated at the same instant
# always produces a byte-identical report, so this example's numbers are stable.
NOW = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)


def build_mission(store: MementoStore) -> dict[str, str]:
    """One mission: a deadline, a task whose lifespan ran out, a park nobody
    came back to, and two entities the work passed through."""
    ids: dict[str, str] = {}

    # The root. Exactly one per store, and it must be finite — that is what
    # makes elapsed time cost something instead of being free.
    ids["horizon"] = store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    ids["mission"] = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-the-thing",
        parent_id=ids["horizon"],
        stall_days=14,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    # A task with a ratified lifespan (a tripwire, not an estimate).
    ids["task"] = store.register_item(
        kind=ItemKind.TASK,
        title="draft-the-proposal",
        parent_id=ids["mission"],
        ttl_start=date(2026, 7, 1),
        ttl_end=date(2026, 7, 20),
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    # An external clock, paired to the internal state it gates.
    ids["deadline"] = store.register_item(
        kind=ItemKind.DEADLINE,
        title="regulator-cutoff",
        parent_id=ids["mission"],
        deadline_date=date(2026, 9, 30),
        deadline_kind="hard_cutoff",
        gates_item_id=ids["task"],
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    # A park. The revisit date is mandatory — see the rejection demo below.
    ids["deferral"] = store.register_item(
        kind=ItemKind.DEFERRAL,
        title="park-the-pricing-call",
        parent_id=ids["mission"],
        revisit_date=date(2026, 8, 10),
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    # Two entities the work passed through. Functional slot labels, not people.
    ids["vendor"] = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=ids["mission"],
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    ids["operator"] = store.register_item(
        kind=ItemKind.ENTITY,
        title="operator",
        parent_id=ids["mission"],
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )

    # Progress stopped on 2 July.
    for day in (date(2026, 6, 5), date(2026, 6, 20), date(2026, 7, 2)):
        store.record_event(
            item_id=ids["mission"],
            kind=EventKind.PROGRESS,
            valid_time=datetime(day.year, day.month, day.day, tzinfo=UTC),
        )

    # The vendor wait closed after 25 days; the operator's is still open.
    store.record_event(
        item_id=ids["vendor"],
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 7, 3, tzinfo=UTC),
        stage="waiting",
    )
    store.record_event(
        item_id=ids["vendor"],
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 7, 28, tzinfo=UTC),
        stage="waiting",
    )
    store.record_event(
        item_id=ids["operator"],
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 7, 28, tzinfo=UTC),
        stage="drafting",
    )
    return ids


def main() -> None:
    store = MementoStore(Path(tempfile.mkdtemp()) / "missions.db")
    ids = build_mission(store)
    report = evaluate(store.snapshot(), NOW, MementoConfig())
    by_id = {row.item_id: row for row in report.items}

    print(f"Mission clock at {NOW.date()}\n" + "=" * 62)

    mission = by_id[ids["mission"]]
    print(f"\n  mission '{mission.title}'")
    print(f"    age                 {mission.age_days} days")
    print(
        f"    since progress      {mission.days_since_progress} days  "
        f"({mission.recording_path})"
    )
    print(f"    horizon share       {mission.horizon_share:.4f} of what remained")

    task = by_id[ids["task"]]
    print(f"\n  task '{task.title}'")
    print(f"    lifespan            {task.ttl_state}  (window ended 2026-07-20)")

    deadline = by_id[ids["deadline"]]
    print(f"\n  deadline '{deadline.title}'")
    print(f"    days remaining      {deadline.days_remaining}")

    park = by_id[ids["deferral"]]
    print(f"\n  park '{park.title}'")
    print(
        f"    overdue by          {abs(park.days_remaining)} days "
        "(a park without a date cannot exist — see below)"
    )

    # Two different questions, answered separately.
    slowest = report.slowest_entities[0]
    blocking = report.blocking_entities[0]
    print("\n  who is slow, and who is blocking")
    print(
        f"    longest wait        {slowest.slot_label!r} — {slowest.latency_days} days"
        f" (n={slowest.n}, censored={slowest.censored})"
    )
    print(
        f"    blocking right now  {blocking.slot_label!r} — "
        f"{blocking.open_age_days} days and counting"
    )
    print(f"    derivation          {slowest.derivation}")

    # The write path refuses an undated park outright.
    print("\n  the store refuses an undated park")
    try:
        store.register_item(
            kind=ItemKind.DEFERRAL,
            title="revisit when things calm down",
            parent_id=ids["mission"],
            created_valid=NOW,
        )
        print("    !! accepted — this should never happen")
    except UndatedDeferralError as exc:
        print(f"    {exc.fix}")

    # Signals: edge-triggered, capped, and meant to be surfaced.
    signal_report, _ = evaluate_signals(store.snapshot(), report, NOW, MementoConfig())
    print("\n  signals raised this turn (cap = 1)")
    for sig in signal_report.fired:
        print(f"    {sig.signal_type}: {sig.derivation}")
    print(
        f"    ({len(signal_report.due)} more are due and visible on the status "
        "surface, held back by the per-turn cap)"
    )

    # Money is optional and only ever multiplies measured time.
    priced = evaluate(store.snapshot(), NOW, MementoConfig(time_value_rate=Decimal("50")))
    plain_no_money = {k: v for k, v in report.to_dict().items() if k != "money"}
    priced_no_money = {k: v for k, v in priced.to_dict().items() if k != "money"}
    print("\n  money is a weight, never a guess")
    print(
        f"    without a declared rate the report carries no money at all: " f"{report.money == ()}"
    )
    print(
        f"    every non-monetary field is identical either way: "
        f"{plain_no_money == priced_no_money}"
    )


if __name__ == "__main__":
    main()
