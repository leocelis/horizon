"""``evaluate()``: the pure clock surface for the Memento Mori mission plane.

Per MEMENTO_MORI_TECH_SPEC.md §4 and memento_engine_intent.yaml. This module
reads no ambient clock (the evaluation instant is always a parameter), makes
no network or subprocess call, and returns a byte-identical serialized
``ClockReport`` for identical ``(snapshot, t_eval, config)`` inputs
(memento_engine_intent.yaml::pure_function_injected_time).

All examples in this module's docstrings use the shared synthetic "smallco"
fixture from docs/spec/MEMENTO_MORI_TEST_PLAN.md — no private project,
person, or workspace data.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from horizon_monitor.memento import money, paths
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.errors import StoreCorruptionError
from horizon_monitor.memento.models import (
    ClockEvent,
    ClockReport,
    EventKind,
    Item,
    ItemClock,
    ItemKind,
    MoneyBlock,
    PathComparison,
    SlowestEntity,
    StoreSnapshot,
)


def evaluate(snapshot: StoreSnapshot, t_eval: datetime, config: MementoConfig) -> ClockReport:
    """The pure clock surface: ages, TTL states, latencies, shares, money,
    and path comparisons for one point-in-time snapshot. See module
    docstring for the purity/determinism guarantee."""
    eval_date = t_eval.date()

    items_by_id = {item.item_id: item for item in snapshot.items}
    _check_no_orphans(snapshot.items, items_by_id)

    events_by_item = _group_events_by_item(snapshot.events)
    root = next((i for i in snapshot.items if i.kind == ItemKind.HORIZON), None)

    rows: list[ItemClock] = []
    stage_by_item: dict[str, tuple[int | None, bool | None]] = {}
    for item in sorted(snapshot.items, key=lambda i: i.item_id):
        row, stage_days, stage_open = _evaluate_item(
            item, events_by_item.get(item.item_id, ()), root, eval_date
        )
        rows.append(row)
        stage_by_item[item.item_id] = (stage_days, stage_open)

    rows_by_id = {row.item_id: row for row in rows}

    slowest_entities = _compute_slowest_entities(snapshot.items, rows_by_id)
    blocking = _compute_blocking_entities(snapshot.items, rows_by_id)
    money_blocks = _compute_money_blocks(snapshot.items, rows_by_id, config)
    path_comparisons = _compute_path_comparisons(snapshot.items, stage_by_item, eval_date)

    return ClockReport(
        evaluated_at=t_eval,
        items=tuple(rows),
        slowest_entities=tuple(slowest_entities),
        blocking_entities=tuple(blocking),
        money=tuple(money_blocks),
        path_comparisons=tuple(path_comparisons),
        proposals=(),
        zero_network=True,
        zero_llm=True,
    )


def _check_no_orphans(items: tuple[Item, ...], items_by_id: dict[str, Item]) -> None:
    """Store corruption (a parent_id that resolves to nothing) fails
    evaluation loudly — never a silent skip (intent v0.7 clarification #3)."""
    for item in items:
        if item.parent_id is not None and item.parent_id not in items_by_id:
            raise StoreCorruptionError(item.item_id, item.parent_id)


def _group_events_by_item(events: tuple[ClockEvent, ...]) -> dict[str, tuple[ClockEvent, ...]]:
    grouped: dict[str, list[ClockEvent]] = {}
    for event in events:
        grouped.setdefault(event.item_id, []).append(event)
    return {item_id: tuple(evs) for item_id, evs in grouped.items()}


def _age_days(created_valid: datetime, eval_date: date) -> tuple[int, bool]:
    """Calendar-date subtraction, never epoch-seconds — DST-insensitive.
    Future-dated items clamp to age 0, flagged, never negative."""
    delta = (eval_date - created_valid.date()).days
    if delta < 0:
        return 0, True
    return delta, False


def _stage_sojourn(
    events: tuple[ClockEvent, ...], eval_date: date
) -> tuple[int | None, bool | None, float | None, str | None]:
    """Walk an item's STAGE_ENTER/STAGE_EXIT events and return
    ``(time_in_stage_days, is_open, wait_vs_touch_ratio, omitted)`` for its
    most recent sojourn. The ratio is computed ONLY from segments whose
    closing event carries a caller ``wait_or_touch`` label — never inferred
    from unlabelled timestamps (memento_engine_intent.yaml::degrade_by_omission).
    """
    stage_events = sorted(
        (e for e in events if e.kind in (EventKind.STAGE_ENTER, EventKind.STAGE_EXIT)),
        key=lambda e: (e.valid_time, e.tx_seq),
    )
    if not stage_events:
        return None, None, None, None

    time_in_stage_days: int | None = None
    is_open: bool | None = None
    wait_total = 0
    touch_total = 0
    has_any_label = False
    open_enter: datetime | None = None

    for ev in stage_events:
        if ev.kind == EventKind.STAGE_ENTER:
            open_enter = ev.valid_time
        elif ev.kind == EventKind.STAGE_EXIT and open_enter is not None:
            duration_days = (ev.valid_time.date() - open_enter.date()).days
            time_in_stage_days = duration_days
            is_open = False
            if ev.wait_or_touch == "wait":
                wait_total += duration_days
                has_any_label = True
            elif ev.wait_or_touch == "touch":
                touch_total += duration_days
                has_any_label = True
            open_enter = None

    if open_enter is not None:
        time_in_stage_days = (eval_date - open_enter.date()).days
        is_open = True

    if has_any_label and (wait_total + touch_total) > 0:
        ratio: float | None = wait_total / (wait_total + touch_total)
        omitted: str | None = None
    else:
        ratio = None
        omitted = (
            "omitted: wait_vs_touch_ratio requires a caller-labelled wait_or_touch on the "
            "closing stage event; none was labelled here — no inference from unlabelled "
            "timestamps."
        )

    return time_in_stage_days, is_open, ratio, omitted


def _progress_derived_at(events: tuple[ClockEvent, ...]) -> datetime | None:
    """The most recent PROGRESS/ARTIFACT event's valid_time, or None if no
    such event was ever recorded on this item."""
    times = [e.valid_time for e in events if e.kind in (EventKind.PROGRESS, EventKind.ARTIFACT)]
    return max(times) if times else None


def _evaluate_item(
    item: Item,
    events: tuple[ClockEvent, ...],
    root: Item | None,
    eval_date: date,
) -> tuple[ItemClock, int | None, bool | None]:
    """Per-item arithmetic (MEMENTO_MORI_TECH_SPEC.md §4 step 2). Returns
    the ItemClock row plus (stage_days, stage_open) so callers building
    path comparisons/slowest-entity don't have to re-walk events."""
    age_days, future_dated = _age_days(item.created_valid, eval_date)
    stage_days, stage_open, wait_ratio, stage_omitted = _stage_sojourn(events, eval_date)

    days_remaining: int | None = None
    ttl_state: str | None = None
    days_since_progress: int | None = None
    recording_path: str | None = None
    horizon_share: float | None = None
    omitted = stage_omitted
    n: int | None = 1 if stage_days is not None else None

    derivation_parts = [
        f"age_days = t_eval({eval_date}) - created_valid({item.created_valid.date()}) "
        f"= {age_days}d" + (" (future_dated, clamped)" if future_dated else "")
    ]

    if item.kind == ItemKind.HORIZON and item.end_date is not None:
        days_remaining = (item.end_date - eval_date).days
        derivation_parts.append(
            f"days_remaining = end_date({item.end_date}) - t_eval({eval_date}) = {days_remaining}d"
        )

    elif item.kind == ItemKind.DEADLINE and item.deadline_date is not None:
        days_remaining = (item.deadline_date - eval_date).days
        derivation_parts.append(
            f"days_remaining = deadline_date({item.deadline_date}) - t_eval({eval_date}) "
            f"= {days_remaining}d"
        )

    elif item.kind == ItemKind.DEFERRAL and item.revisit_date is not None:
        days_remaining = (item.revisit_date - eval_date).days
        derivation_parts.append(
            f"days_remaining = revisit_date({item.revisit_date}) - t_eval({eval_date}) "
            f"= {days_remaining}d"
        )

    if item.ttl_start is not None or item.ttl_end is not None:
        ttl_state = _ttl_state(item.ttl_start, item.ttl_end, eval_date)
        derivation_parts.append(
            f"ttl_state({item.ttl_start}..{item.ttl_end} vs t_eval={eval_date}) = {ttl_state!r}"
        )

    if item.kind == ItemKind.MISSION:
        latest_progress = _progress_derived_at(events)
        if latest_progress is None:
            recording_path = "no capture"
            derivation_parts.append(
                "recording_path='no capture': zero progress/artifact events ever recorded"
            )
        else:
            days_since_progress = (eval_date - latest_progress.date()).days
            recording_path = "no recent work" if days_since_progress > 0 else None
            derivation_parts.append(
                f"days_since_progress = t_eval({eval_date}) - latest_progress"
                f"({latest_progress.date()}) = {days_since_progress}d"
            )

        if root is not None and root.end_date is not None:
            root_days_remaining_at_creation = max(
                1, (root.end_date - item.created_valid.date()).days
            )
            horizon_share = age_days / root_days_remaining_at_creation
            derivation_parts.append(
                f"horizon_share = age_days({age_days}) / root_days_remaining_at_creation"
                f"({root_days_remaining_at_creation}) = {round(horizon_share, 6)}"
            )

    if stage_days is not None:
        derivation_parts.append(f"time_in_stage_days = {stage_days}d (is_open_stage={stage_open})")
    if wait_ratio is not None:
        derivation_parts.append(f"wait_vs_touch_ratio = {round(wait_ratio, 4)}")

    row = ItemClock(
        item_id=item.item_id,
        kind=item.kind.value,
        title=item.title,
        age_days=age_days,
        days_remaining=days_remaining,
        ttl_state=ttl_state,
        days_since_progress=days_since_progress,
        recording_path=recording_path,
        horizon_share=horizon_share,
        time_in_stage_days=stage_days,
        is_open_stage=stage_open,
        wait_vs_touch_ratio=wait_ratio,
        future_dated=future_dated,
        derivation="; ".join(derivation_parts),
        n=n,
        omitted=omitted,
    )
    return row, stage_days, stage_open


def _ttl_state(ttl_start: date | None, ttl_end: date | None, eval_date: date) -> str:
    if ttl_start is not None and eval_date < ttl_start:
        return "pending"
    if ttl_end is not None and eval_date > ttl_end:
        return "expired"
    return "open"


def _compute_slowest_entities(
    items: tuple[Item, ...], rows_by_id: dict[str, ItemClock]
) -> list[SlowestEntity]:
    """One row per mission with ≥1 ENTITY child: the slowest recorded
    entity on that mission's critical path. An entity with a currently OPEN
    sojourn dominates any closed one regardless of duration — it is the
    presently-accruing blocker (PRD §6; test plan E-4). Slot label only —
    never a person name (memento_signals_intent.yaml::no_person_ranking_in_output)."""
    entities_by_mission: dict[str, list[Item]] = {}
    for item in items:
        if item.kind == ItemKind.ENTITY and item.parent_id is not None:
            entities_by_mission.setdefault(item.parent_id, []).append(item)

    result: list[SlowestEntity] = []
    for mission_id in sorted(entities_by_mission):
        entities = entities_by_mission[mission_id]
        measured = [
            (e, rows_by_id[e.item_id])
            for e in entities
            if rows_by_id[e.item_id].time_in_stage_days is not None
        ]
        if not measured:
            continue

        # argmax over EVERY recorded sojourn, open and closed alike. An open
        # sojourn is a right-censored lower bound (research A2 F6), so it does
        # NOT automatically outrank a longer closed one — that shortcut would
        # report a 1-day open entity as "slower" than a 400-day closed one.
        # Equal latencies break toward the open sojourn, whose true value is
        # strictly greater because it is still accruing.
        winner_item, winner_row = max(
            measured,
            key=lambda pair: (pair[1].time_in_stage_days, pair[1].is_open_stage),
        )

        is_person = winner_item.namespace == "person"
        slot_label = "person" if is_person else winner_item.title
        censored = bool(winner_row.is_open_stage)
        derivation = (
            f"slowest_entity = argmax(time_in_stage_days) over {len(measured)} recorded "
            f"entities (open and closed alike); winner {slot_label!r} "
            f"time_in_stage_days={winner_row.time_in_stage_days}d, "
            f"is_open={winner_row.is_open_stage}"
            + (
                " — still accruing, so this is a censored lower bound"
                if censored
                else " — closed sojourn, final value"
            )
        )
        result.append(
            SlowestEntity(
                mission_id=mission_id,
                # A person-namespace winner is measured but never identified:
                # emitting its stable item_id would let any reader resolve the
                # title through the store, defeating the slot-label redaction
                # (memento_signals_intent.yaml::no_person_ranking_in_output).
                entity_item_id=None if is_person else winner_item.item_id,
                slot_label=slot_label,
                latency_days=winner_row.time_in_stage_days,
                is_open=bool(winner_row.is_open_stage),
                censored=censored,
                derivation=derivation,
                # n is the size of the population the argmax summarised, not a
                # constant (memento_engine_intent.yaml::derivation_on_every_row
                # — "n for any summary statistic").
                n=len(measured),
            )
        )
    return result


def _compute_blocking_entities(items, rows_by_id) -> list:
    """The oldest currently-OPEN entity per mission — "who is blocking now".

    Research B1 keeps this as its own primitive (the constraint-aged open
    item) precisely because it answers a different question from
    slowest_entity: a closed sojourn can be the longest ever recorded while
    nothing is waiting on it today. Same slot-label redaction rule.
    """
    from horizon_monitor.memento.models import BlockingEntity

    entities_by_mission: dict[str, list] = {}
    for item in items:
        if item.kind == ItemKind.ENTITY and item.parent_id is not None:
            entities_by_mission.setdefault(item.parent_id, []).append(item)

    out: list = []
    for mission_id in sorted(entities_by_mission):
        open_rows = [
            (e, rows_by_id[e.item_id])
            for e in entities_by_mission[mission_id]
            if rows_by_id[e.item_id].time_in_stage_days is not None
            and rows_by_id[e.item_id].is_open_stage
        ]
        if not open_rows:
            continue
        winner_item, winner_row = max(open_rows, key=lambda p: p[1].time_in_stage_days)
        is_person = winner_item.namespace == "person"
        slot_label = "person" if is_person else winner_item.title
        out.append(
            BlockingEntity(
                mission_id=mission_id,
                entity_item_id=None if is_person else winner_item.item_id,
                slot_label=slot_label,
                open_age_days=winner_row.time_in_stage_days,
                derivation=(
                    f"blocking_entity = argmax(open sojourn age) over {len(open_rows)} "
                    f"OPEN entities; winner {slot_label!r} open_age_days="
                    f"{winner_row.time_in_stage_days}d (still accruing)"
                ),
                n=len(open_rows),
            )
        )
    return out


def _compute_money_blocks(
    items: tuple[Item, ...], rows_by_id: dict[str, ItemClock], config: MementoConfig
) -> list[MoneyBlock]:
    """Cost-of-delay per item that carries a caller ``amount`` — skipped
    entirely when ``time_value_rate`` is None. Break-even dates are not
    produced automatically here: the Item schema has no per-item
    cost_setup/Δt/λ fields, so break-even is only available via the
    explicit ``propose.breakeven_proposal()`` call (see IMPLEMENTATION NOTE
    in the segment report — this narrows TECH_SPEC §4 step 3's automatic
    money-block wording to what the schema can actually support without
    inventing fields)."""
    if config.time_value_rate is None:
        return []

    blocks: list[MoneyBlock] = []
    for item in items:
        if item.amount is None:
            continue
        row = rows_by_id[item.item_id]
        age_days = row.age_days or 0
        elapsed_hours = Decimal(age_days) * Decimal(24)
        cost = money.cost_of_delay(item.amount, config.time_value_rate, elapsed_hours)
        derivation = (
            f"cost_of_delay = amount({item.amount}) * rate({config.time_value_rate}) * "
            f"elapsed_hours({elapsed_hours}) = {cost}"
        )
        blocks.append(
            MoneyBlock(
                item_id=item.item_id,
                cost_of_delay=cost,
                breakeven_date=None,
                breakeven_cycle_count=None,
                derivation=derivation,
            )
        )
    return blocks


def _compute_path_comparisons(
    items: tuple[Item, ...],
    stage_by_item: dict[str, tuple[int | None, bool | None]],
    eval_date: date,
) -> list[PathComparison]:
    """One comparison per mission with ≥1 registered PROBE child
    (MEMENTO_MORI_TECH_SPEC.md §4 step 4; PRD §7)."""
    probes_by_mission: dict[str, list[Item]] = {}
    for item in items:
        if item.kind == ItemKind.PROBE and item.parent_id is not None:
            probes_by_mission.setdefault(item.parent_id, []).append(item)

    comparisons: list[PathComparison] = []
    for mission_id in sorted(probes_by_mission):
        probe_triples = tuple(
            (
                probe,
                stage_by_item.get(probe.item_id, (None, None))[0],
                stage_by_item.get(probe.item_id, (None, None))[1] or False,
            )
            for probe in probes_by_mission[mission_id]
        )
        comparison = paths.build_comparison(mission_id, probe_triples, eval_date)
        if comparison is not None:
            comparisons.append(comparison)
    return comparisons
