"""Signal state machine — edge-triggered, acknowledgeable, capped.

Per MEMENTO_MORI_TECH_SPEC.md §5, PRD §5, and memento/philosophy.md. This
module is pure: it reads a ``StoreSnapshot`` (which already carries the
prior fire-state rows) and an ``engine.ClockReport``, and returns the
signal surface for this evaluation plus the fire-state updates the caller
should persist. It performs no store writes itself, mirroring engine.py's
purity (memento_engine_intent.yaml::pure_function_injected_time — the same
discipline extended to signals).

Predicate table (MEMENTO_MORI_TECH_SPEC.md §5.1 / PRD §5.2). Each predicate
is evaluated against the item's ItemClock row; an event fires only on a
``false -> true`` edge or a strictly higher enumerated escalation rung —
never on "another turn happened"
(memento_signals_intent.yaml::edge_not_level).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import (
    ClockReport,
    EventKind,
    Item,
    ItemClock,
    ItemKind,
    Signal,
    SignalReport,
    SignalState,
    StoreSnapshot,
)

UTC = timezone.utc

TIER = {
    "ttl_expired": "P1",
    "deadline_window": "P1",
    "deferral_expired": "P2",
    "gate_aging": "P2",
    "mission_stalled": "P2",
    "slowest_entity": "P2",
    "clock_unpaired": "P2",
    "horizon_share": "P3",
    "cost_of_delay": "P3",
    "probe_ready": "P3",
    "path_ahead": "P3",
    "breakeven_passed": "P3",
}
_TIER_RANK = {"P1": 0, "P2": 1, "P3": 2}
# "cost_of_delay" and "breakeven_passed" are emitted by _due_predicates like
# every other type, but only from caller-declared money facts:
# cost_of_delay needs a rate + an item amount + config.cost_of_delay_threshold
# (engine.evaluate() already computes the per-item MoneyBlocks it reads);
# breakeven_passed needs a RATIFY event whose payload carries a breakeven
# date. With none of those declared the predicates are simply absent — the
# degrade-by-omission rule, not a special case. Tests: G-13, G-14.

SUGGESTED_BEHAVIOR = {
    "ttl_expired": "investigate the blocker — this task outlived its ratified lifespan",
    "deadline_window": "an external deadline has entered its warning window",
    "deferral_expired": "this deferral passed its revisit date — decide or re-defer it",
    "gate_aging": "this gate exceeded its age budget with no recorded progress",
    "mission_stalled": "record progress or investigate why this mission has stalled",
    "slowest_entity": "the mission's slowest recorded entity changed — review that sojourn",
    "clock_unpaired": "this deadline has no linked internal state — pair it or flag it intentionally unpaired",
    "horizon_share": "this item now consumes a larger share of the remaining horizon",
    "cost_of_delay": "the accrued cost of delay crossed the configured threshold",
    "probe_ready": "a probe sojourn completed — compare it against the incumbent's accrued delay",
    "path_ahead": "the probe's measured sojourn is currently shorter than the incumbent's accrued delay",
    "breakeven_passed": "the ratified break-even date passed without a measured improvement",
}


@dataclass(frozen=True)
class _Predicate:
    item_id: str
    signal_type: str
    tier: str
    is_true: bool
    rung: int
    derivation: str
    payload: dict
    tiebreak_days: int
    """days_remaining-ish value for the P1>P2>P3-then-fewest-days-remaining
    ordering (test plan G-6); a large sentinel when the signal has no
    natural days-remaining figure."""


_NO_TIEBREAK = 10**9


def _due_predicates(
    snapshot: StoreSnapshot,
    rows_by_id: dict[str, ItemClock],
    path_comparisons_by_mission: dict[str, object],
    eval_date: date,
    config: MementoConfig,
    money_blocks: tuple = (),
    slowest_entities: tuple = (),
) -> list[_Predicate]:
    """Every currently-true-or-tracked predicate over the snapshot, before
    any edge/ack/cap logic is applied."""
    items_by_id = {i.item_id: i for i in snapshot.items}
    predicates: list[_Predicate] = []

    entities_by_mission: dict[str, list[Item]] = {}
    for item in snapshot.items:
        if item.kind == ItemKind.ENTITY and item.parent_id is not None:
            entities_by_mission.setdefault(item.parent_id, []).append(item)

    for item in snapshot.items:
        row = rows_by_id.get(item.item_id)
        if row is None:
            continue

        if item.kind == ItemKind.TASK or item.kind == ItemKind.PROBE:
            if row.ttl_state == "expired":
                predicates.append(
                    _Predicate(
                        item.item_id,
                        "ttl_expired",
                        TIER["ttl_expired"],
                        True,
                        0,
                        f"ttl_state={row.ttl_state!r} (ttl_end={item.ttl_end})",
                        {},
                        0,
                    )
                )

        if item.kind == ItemKind.DEADLINE and row.days_remaining is not None:
            warn_days = config.deadline_warn_days
            in_window = row.days_remaining <= warn_days
            predicates.append(
                _Predicate(
                    item.item_id,
                    "deadline_window",
                    TIER["deadline_window"],
                    in_window,
                    0,
                    f"days_remaining({row.days_remaining}) <= warn_days({warn_days}) = {in_window}",
                    {},
                    row.days_remaining,
                )
            )
            if item.gates_item_id is None:
                predicates.append(
                    _Predicate(
                        item.item_id,
                        "clock_unpaired",
                        TIER["clock_unpaired"],
                        True,
                        0,
                        "gates_item_id is None: this deadline links to no internal state",
                        {},
                        row.days_remaining,
                    )
                )

        if item.kind == ItemKind.DEFERRAL and row.days_remaining is not None:
            expired = row.days_remaining < 0
            predicates.append(
                _Predicate(
                    item.item_id,
                    "deferral_expired",
                    TIER["deferral_expired"],
                    expired,
                    0,
                    f"days_remaining({row.days_remaining}) < 0 = {expired}",
                    {},
                    row.days_remaining,
                )
            )

        if item.kind == ItemKind.GATE and item.age_budget_days is not None:
            aging = row.age_days is not None and row.age_days > item.age_budget_days
            predicates.append(
                _Predicate(
                    item.item_id,
                    "gate_aging",
                    TIER["gate_aging"],
                    aging,
                    0,
                    f"age_days({row.age_days}) > age_budget_days({item.age_budget_days}) = {aging}",
                    {},
                    _NO_TIEBREAK,
                )
            )

        if item.kind == ItemKind.MISSION:
            stall_days = (
                item.stall_days if item.stall_days is not None else config.stall_default_days
            )
            stalled = row.days_since_progress is not None and row.days_since_progress > stall_days
            predicates.append(
                _Predicate(
                    item.item_id,
                    "mission_stalled",
                    TIER["mission_stalled"],
                    stalled,
                    0,
                    f"days_since_progress({row.days_since_progress}) > stall_days({stall_days}) "
                    f"= {stalled} (recording_path={row.recording_path!r})",
                    {},
                    _NO_TIEBREAK,
                )
            )
            if row.horizon_share is not None:
                rung = _rung_index(row.horizon_share, config.horizon_share_rungs)
                predicates.append(
                    _Predicate(
                        item.item_id,
                        "horizon_share",
                        TIER["horizon_share"],
                        rung >= 0,
                        rung,
                        f"horizon_share({round(row.horizon_share, 6)}) crosses rung index {rung} "
                        f"of {config.horizon_share_rungs}",
                        {"horizon_share": row.horizon_share},
                        _NO_TIEBREAK,
                    )
                )

    for mission_id, comparison in path_comparisons_by_mission.items():
        rows = comparison.rows
        probe_rows = [r for r in rows if r.is_probe]
        completed_probe_rows = [r for r in probe_rows if r.completed]
        if probe_rows:
            predicates.append(
                _Predicate(
                    mission_id,
                    "probe_ready",
                    TIER["probe_ready"],
                    bool(completed_probe_rows),
                    0,
                    f"{len(completed_probe_rows)} of {len(probe_rows)} registered probe(s) have "
                    "a completed sojourn (caller-written stage_exit, never a timer)",
                    {},
                    _NO_TIEBREAK,
                )
            )
        if completed_probe_rows:
            first_completed = completed_probe_rows[0]
            incumbent_accrued = next((r.accrued_delay_days for r in rows if not r.is_probe), None)
            predicates.append(
                _Predicate(
                    mission_id,
                    "path_ahead",
                    TIER["path_ahead"],
                    comparison.path_ahead,
                    0,
                    comparison.derivation,
                    {
                        "probe_sojourn_days": first_completed.sojourn_days,
                        "incumbent_accrued_delay_days": incumbent_accrued,
                        "n": 1,
                    },
                    _NO_TIEBREAK,
                )
            )

    # slowest_entity — consume the engine's already-computed rows rather than
    # recomputing the argmax here. Two copies of one decision is how the two
    # modules drift apart; the engine owns the semantics (argmax over ALL
    # recorded sojourns, open sojourns flagged as censored lower bounds) and
    # this module only turns them into predicates.
    for slowest in slowest_entities:
        # rung encodes WHICH entity won, so a change of winner is a genuine
        # edge rather than a level: position in a stable sort of all item ids
        # (deterministic, no ambient state). A withheld person id sorts last.
        rung = (
            sorted(items_by_id).index(slowest.entity_item_id)
            if slowest.entity_item_id in items_by_id
            else len(items_by_id)
        )
        predicates.append(
            _Predicate(
                slowest.mission_id,
                "slowest_entity",
                TIER["slowest_entity"],
                True,
                rung,
                slowest.derivation,
                {
                    # Person-namespace winners arrive from the engine already
                    # redacted (slot label only, id withheld) — this module
                    # never re-derives identity (no_person_ranking_in_output).
                    "entity_item_id": slowest.entity_item_id,
                    "slot_label": slowest.slot_label,
                    "n": slowest.n,
                    "censored": slowest.censored,
                },
                _NO_TIEBREAK,
            )
        )

    # --- cost_of_delay (P3) ---------------------------------------------
    # Fires only when a rate, an item amount, and an operator threshold are
    # ALL caller-declared; engine.evaluate() has already produced the
    # per-item MoneyBlock this reads. Absent any of the three there is no
    # predicate at all (degrade by omission, never substitution).
    if config.cost_of_delay_threshold is not None:
        for block in money_blocks:
            if block.cost_of_delay is None:
                continue
            crossed = block.cost_of_delay >= config.cost_of_delay_threshold
            predicates.append(
                _Predicate(
                    block.item_id,
                    "cost_of_delay",
                    TIER["cost_of_delay"],
                    crossed,
                    0,
                    f"cost_of_delay={block.cost_of_delay} >= threshold="
                    f"{config.cost_of_delay_threshold} -> {crossed}",
                    {
                        "cost_of_delay": str(block.cost_of_delay),
                        "threshold": str(config.cost_of_delay_threshold),
                    },
                    _NO_TIEBREAK,
                )
            )

    # --- breakeven_passed (P3) -------------------------------------------
    # A caller-ratified break-even date (a RATIFY event carrying
    # kind="breakeven") that the evaluation date has passed with no measured
    # improvement recorded. The date is always a ratified fact, never minted.
    for event in snapshot.events:
        if event.kind != EventKind.RATIFY:
            continue
        payload = event.payload or {}
        if payload.get("kind") != "breakeven":
            continue
        raw = payload.get("breakeven_date")
        if not raw:
            continue
        be_date = date.fromisoformat(str(raw)[:10])
        improved = bool(payload.get("measured_improvement"))
        predicates.append(
            _Predicate(
                event.item_id,
                "breakeven_passed",
                TIER["breakeven_passed"],
                eval_date > be_date and not improved,
                0,
                f"ratified breakeven_date={be_date.isoformat()} vs eval_date="
                f"{eval_date.isoformat()}; measured_improvement={improved}",
                {
                    "breakeven_date": be_date.isoformat(),
                    "measured_improvement": improved,
                },
                (eval_date - be_date).days,
            )
        )

    return predicates


def _rung_index(value: float, rungs: tuple[float, ...]) -> int:
    idx = -1
    for i, rung in enumerate(rungs):
        if value >= rung:
            idx = i
    return idx


def _transition(
    prev: dict, is_true: bool, rung: int, eval_date: date, config: MementoConfig
) -> tuple[dict | None, str | None]:
    """The (item, signal_type) state machine
    (memento_signals_intent.yaml::edge_not_level, ack_and_cap). Returns
    ``(new_state_or_None, event_kind_or_None)``; ``event_kind`` is one of
    "raised" / "escalated" / "stale" / None."""
    state = prev.get("state", SignalState.CLEAR.value)
    prev_rung = prev.get("rung", -1)

    if state == SignalState.CLEAR.value:
        if not is_true:
            return None, None
        return {"state": SignalState.RAISED.value, "rung": rung}, "raised"

    if state == SignalState.RAISED.value:
        if not is_true:
            return {"state": SignalState.CLEAR.value, "rung": -1}, None
        return None, None  # persisting level — never re-fires

    if state == SignalState.ACKED.value:
        if is_true and rung > prev_rung:
            return {"state": SignalState.ESCALATED.value, "rung": rung}, "escalated"
        ack_time = prev.get("ack_time")
        if ack_time is not None and config.stale_ack_days > 0:
            days_since_ack = (eval_date - date.fromisoformat(ack_time[:10])).days
            has_new_progress = prev.get("progress_since_ack", False)
            if days_since_ack >= config.stale_ack_days and not has_new_progress:
                return {**prev, "state": SignalState.STALE.value}, "stale"
        return None, None  # silent while acked

    if state in (SignalState.ESCALATED.value, SignalState.STALE.value):
        if is_true and rung > prev_rung:
            return {"state": SignalState.ESCALATED.value, "rung": rung}, "escalated"
        return None, None

    return None, None


def evaluate_signals(
    snapshot: StoreSnapshot,
    report: ClockReport,
    t_eval: datetime,
    config: MementoConfig,
) -> tuple[SignalReport, dict[tuple[str, str], dict]]:
    """Compute the full signal surface from an already-computed
    ``engine.evaluate()`` report. Returns ``(SignalReport,
    new_fire_states)``; ``new_fire_states`` maps ``(item_id, signal_type)``
    to the fire-state dict the caller should persist via
    ``MementoStore.set_fire_state`` for every entry (this function itself
    writes nothing — memento_engine_intent.yaml::pure_function_injected_time
    discipline extended to signals)."""
    eval_date = t_eval.date()
    rows_by_id = {row.item_id: row for row in report.items}
    comparisons_by_mission = {c.mission_id: c for c in report.path_comparisons}
    predicates = _due_predicates(
        snapshot,
        rows_by_id,
        comparisons_by_mission,
        eval_date,
        config,
        money_blocks=report.money,
        slowest_entities=report.slowest_entities,
    )

    fired: list[Signal] = []
    due: list[Signal] = []
    acked: list[Signal] = []
    new_states: dict[tuple[str, str], dict] = {}
    raise_candidates: list[tuple[_Predicate, dict]] = []

    for pred in predicates:
        key = (pred.item_id, pred.signal_type)
        prev = snapshot.fire_state_for(*key) or {"state": SignalState.CLEAR.value, "rung": -1}
        new_state, event_kind = _transition(prev, pred.is_true, pred.rung, eval_date, config)

        if event_kind in ("raised", "escalated") and new_state is not None:
            raise_candidates.append((pred, new_state))
            continue

        if new_state is not None:
            new_states[key] = new_state

        if event_kind == "stale":
            new_states[key] = new_state
            fired.append(_make_signal(pred, SignalState.STALE.value, fired=True))
        elif prev.get("state") in (SignalState.ACKED.value, SignalState.STALE.value):
            # both states are "silent, visible on clock_status" (PRD §5.1
            # rule 2) — STALE having already fired once does not remove it
            # from the operator's view, it just stops re-firing.
            acked.append(_make_signal(pred, prev["state"], fired=False))
        elif prev.get("state") == SignalState.RAISED.value and pred.is_true:
            due.append(_make_signal(pred, SignalState.RAISED.value, fired=False))

    raise_candidates.sort(
        key=lambda pair: (
            _TIER_RANK[pair[0].tier],
            pair[0].tiebreak_days,
            pair[0].item_id,
            pair[0].signal_type,
        )
    )
    cap = max(0, config.per_turn_fire_cap)
    for pred, new_state in raise_candidates[:cap]:
        key = (pred.item_id, pred.signal_type)
        new_states[key] = new_state
        state_label = new_state["state"]
        fired.append(_make_signal(pred, state_label, fired=True))
    for pred, _new_state in raise_candidates[cap:]:
        due.append(_make_signal(pred, SignalState.RAISED.value, fired=False))

    return SignalReport(fired=tuple(fired), due=tuple(due), acked=tuple(acked)), new_states


def _make_signal(pred: _Predicate, state: str, fired: bool) -> Signal:
    return Signal(
        item_id=pred.item_id,
        signal_type=pred.signal_type,
        tier=pred.tier,
        state=state,
        fired=fired,
        suggested_behavior=SUGGESTED_BEHAVIOR[pred.signal_type],
        n=1,
        derivation=pred.derivation,
        payload=pred.payload,
    )


def ack(
    item_id: str,
    signal_type: str,
    valid_time: datetime,
    actor: str,
    current_rung: int = 0,
    progress_since_ack: bool = False,
) -> dict:
    """Build the fire-state dict for an operator acknowledgement. The
    caller persists it via ``MementoStore.set_fire_state`` and SHOULD also
    record an ``EventKind.ACK`` event for audit
    (interface.tools.clock_ack: "operator-authorized ... never to
    self-quiet a signal")."""
    return {
        "state": SignalState.ACKED.value,
        "rung": current_rung,
        "ack_time": valid_time.isoformat(),
        "acked_by": actor,
        "progress_since_ack": progress_since_ack,
    }


def mission_scope_for_item(item_id: str, items_by_id: dict[str, Item]) -> str | None:
    """Walk ``item_id``'s parent chain to the nearest ancestor of
    kind=MISSION (or ``item_id`` itself, when it already is one) — the
    binding unit ``associate_mission`` operates on
    (memento_signals_intent.yaml::strict_additivity; test plan M-3, G-11).
    Returns ``None`` when the item has no MISSION ancestor (e.g. it hangs
    directly off the root), meaning no association can ever scope it in."""
    seen: set[str] = set()
    current = items_by_id.get(item_id)
    while current is not None and current.item_id not in seen:
        if current.kind == ItemKind.MISSION:
            return current.item_id
        seen.add(current.item_id)
        current = items_by_id.get(current.parent_id) if current.parent_id else None
    return None


class AssociationRegistry:
    """In-memory session -> mission binding
    (interface.tools.associate_mission). Without an explicit association a
    configured store still emits zero events into that session
    (memento_signals_intent.yaml::strict_additivity, test plan G-11)."""

    def __init__(self) -> None:
        self._by_session: dict[str, set[str]] = {}

    def associate(self, session_id: str, mission_id: str) -> None:
        self._by_session.setdefault(session_id, set()).add(mission_id)

    def missions_for(self, session_id: str) -> tuple[str, ...]:
        return tuple(sorted(self._by_session.get(session_id, ())))

    def is_associated(self, session_id: str) -> bool:
        return bool(self._by_session.get(session_id))
