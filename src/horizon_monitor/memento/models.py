"""Data models for the Memento Mori mission plane.

Per MEMENTO_MORI_TECH_SPEC.md §2. All dataclasses are frozen — mutation
happens only by writing a new row through the store (append-only /
supersede discipline; see memento_store_intent.yaml::append_only_bitemporal).

All synthetic examples in this module's docstrings use the shared "smallco"
fixture from docs/spec/MEMENTO_MORI_TEST_PLAN.md — no private project, person,
or workspace data.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum


class ItemKind(StrEnum):
    """The eight clocked-item kinds. Exactly one HORIZON exists per store."""

    HORIZON = "horizon"
    MISSION = "mission"
    TASK = "task"
    DEADLINE = "deadline"
    GATE = "gate"
    ENTITY = "entity"
    DEFERRAL = "deferral"
    PROBE = "probe"


class EventKind(StrEnum):
    """The kinds of rows recorded in the append-only mm_events log."""

    PROGRESS = "progress"
    STAGE_ENTER = "stage_enter"
    STAGE_EXIT = "stage_exit"
    ARTIFACT = "artifact"
    RATIFY = "ratify"
    ACK = "ack"


class SignalState(StrEnum):
    """The five states of the per-(item, signal_type) alarm state machine
    (memento_signals_intent.yaml::edge_not_level). This enum is closed and
    deliberately has no turn-count / elapsed-turns member — "another turn
    happened" is structurally unrepresentable as a state (test plan G-4)."""

    CLEAR = "clear"
    RAISED = "raised"
    ACKED = "acked"
    ESCALATED = "escalated"
    STALE = "stale"


@dataclass(frozen=True)
class Provenance:
    """Required on every EventKind.ARTIFACT event; forbidden on no other kind."""

    source_system: str
    """e.g. "git", "issue-tracker", "mail"."""

    native_id: str
    """The identifier in the source system (commit sha, ticket key, ...)."""

    raw_timestamp: datetime
    """The timestamp as reported by the source system, before any
    interpretation. Bitemporal: this is distinct from tx_time (when THIS
    store learned it)."""


@dataclass(frozen=True)
class Item:
    """A node in the rooted horizon tree. Kind-specific fields are optional
    and validated by the store per kind at write time."""

    item_id: str
    kind: ItemKind
    parent_id: str | None
    title: str
    created_valid: datetime
    created_tx: datetime

    end_date: date | None = None
    revisit_date: date | None = None
    ttl_start: date | None = None
    ttl_end: date | None = None
    deadline_date: date | None = None
    deadline_kind: str | None = None
    gates_item_id: str | None = None
    age_budget_days: int | None = None
    stall_days: int | None = None
    namespace: str | None = None
    amount: Decimal | None = None
    status: str = "open"
    superseded_by: str | None = None

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass(frozen=True)
class ClockEvent:
    """An append-only row in mm_events. Corrections supersede — they never
    overwrite; both records are retained (memento_store_intent.yaml::
    append_only_bitemporal)."""

    event_id: str
    item_id: str
    kind: EventKind
    valid_time: datetime
    tx_time: datetime
    stage: str | None = None
    wait_or_touch: str | None = None
    provenance: Provenance | None = None
    payload: dict = field(default_factory=dict)
    correction_of: str | None = None
    """event_id of the event this one corrects, or None for an original
    record. Both rows are kept; neither is deleted or mutated."""

    tx_seq: int = 0
    """Monotonic total-order tie-breaker across all events in the store —
    the store assigns this from an autoincrement key, so tx ordering is
    total even when two writes share the same tx_time at wall-clock
    resolution (memento_store_intent.yaml test S-9)."""

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        d["kind"] = self.kind.value
        return d


@dataclass(frozen=True)
class StoreSnapshot:
    """Immutable point-in-time view of a store's items + events + fire
    state, fed into the pure ``engine.evaluate()`` function.

    Capturing a snapshot (rather than handing the engine a live store
    handle) is what makes evaluate() a pure function of (snapshot, t_eval):
    no ambient clock, no re-querying a mutable store mid-computation.
    """

    items: tuple[Item, ...]
    events: tuple[ClockEvent, ...]
    fire_states: tuple[tuple[tuple[str, str], dict], ...] = ()
    """((item_id, signal_type), fire_state_dict) pairs — a tuple of pairs
    rather than a dict so the snapshot itself stays a hashable, frozen
    dataclass."""

    def fire_state_for(self, item_id: str, signal_type: str) -> dict | None:
        for (iid, stype), state in self.fire_states:
            if iid == item_id and stype == signal_type:
                return state
        return None


# ── Report types (engine output; plain dataclasses -> dicts) ───────────────


@dataclass(frozen=True)
class ItemClock:
    """One row of the clock report for a single item."""

    item_id: str
    kind: str
    title: str
    age_days: int | None = None
    days_remaining: int | None = None
    ttl_state: str | None = None
    days_since_progress: int | None = None
    recording_path: str | None = None
    """"no capture" | "no recent work" | None (has recent progress)."""

    horizon_share: float | None = None
    time_in_stage_days: int | None = None
    is_open_stage: bool | None = None
    wait_vs_touch_ratio: float | None = None
    future_dated: bool = False
    derivation: str = ""
    n: int | None = None
    omitted: str | None = None
    """Explanatory field for degrade-by-omission — states what was omitted
    and why. Never a substituted/guessed value
    (memento_engine_intent.yaml::degrade_by_omission)."""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SlowestEntity:
    """The slowest recorded entity on one mission's critical path.

    Slot label only — person-namespace entities are never surfaced here by
    name (memento_signals_intent.yaml::no_person_ranking_in_output).
    """

    mission_id: str
    entity_item_id: str | None
    """None when the winner is a person-namespace entity — the latency is
    still measured and reported, the identity is withheld."""
    slot_label: str
    latency_days: int
    is_open: bool
    derivation: str
    n: int = 1
    censored: bool = False
    """True when the winner's sojourn is still open: the recorded latency is a
    right-censored LOWER BOUND (A2 research F6 — an open sojourn's true
    duration is >= its current age), not a final value."""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class BlockingEntity:
    """The oldest currently-OPEN entity on a mission — "who is blocking right
    now", which is a different question from "who was slowest".

    Research B1 lists this as its own primitive ("constraint-aged open item":
    the open item on the tagged constraint entity with max age) and explicitly
    rejects collapsing constraint identification into "name the slowest
    person". Slot label only, same redaction rule as SlowestEntity.
    """

    mission_id: str
    entity_item_id: str | None
    slot_label: str
    open_age_days: int
    derivation: str
    n: int = 1

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class MoneyBlock:
    """Monetary fields for one item. Present only when time_value_rate is
    declared; every non-monetary ItemClock field is unaffected either way
    (memento_engine_intent.yaml::degrade_by_omission,
    horizon_memento_mori_intent.yaml::facts_are_caller_provided)."""

    item_id: str
    cost_of_delay: Decimal | None = None
    breakeven_date: date | None = None
    breakeven_cycle_count: int | None = None
    """Cycles-only fallback when λ is None — no date is minted."""

    derivation: str = ""

    def to_dict(self) -> dict:
        d = dataclasses.asdict(self)
        return d


@dataclass(frozen=True)
class PathComparisonRow:
    """One recorded latency in a path comparison — a really-run path only.

    No synthetic path latency may ever appear here
    (facts_are_caller_provided; PRD §7).
    """

    path_key: str
    """e.g. "incumbent" or the probe's registered alternative label
    ("channel-b")."""

    sojourn_days: int | None
    """Completed sojourn length, or None if this path's latest sojourn is
    still open (see accrued_delay_days for the open case)."""

    accrued_delay_days: int | None
    """For an open incumbent: days elapsed since the alternative was
    registered. None for a completed sojourn row."""

    n: int
    is_probe: bool
    completed: bool


@dataclass(frozen=True)
class BaseRateRow:
    """A published/literature base rate — provenance-labelled, never
    blended into measured columns (PRD §7)."""

    path_key: str
    value_days: float
    source: str


@dataclass(frozen=True)
class PathComparison:
    """Side-by-side recorded latencies for one mission's registered
    alternative(s), plus separate provenance-labelled base rates."""

    mission_id: str
    rows: tuple[PathComparisonRow, ...]
    base_rates: tuple[BaseRateRow, ...] = ()
    path_ahead: bool = False
    derivation: str = ""

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class Proposal:
    """Returned by clock_propose. Inert until an explicit RATIFY event
    (facts_are_caller_provided: 'never applied without an explicit
    ratifying write')."""

    item_id: str
    kind: str
    """"ttl" | "breakeven"."""

    value: object
    sample_size: int
    derivation: str


@dataclass(frozen=True)
class Signal:
    """One row of the per-evaluation signal surface: either an actual
    per-turn event (``fired=True``) or a currently-true predicate that the
    per-turn cap suppressed this turn (``fired=False`` — reported, not
    delivered; memento_signals_intent.yaml::ack_and_cap)."""

    item_id: str
    signal_type: str
    tier: str
    """"P1" | "P2" | "P3" — priority class used for the per-turn cap."""

    state: str
    """The SignalState this row reflects: "raised" | "escalated" | "acked"
    | "stale"."""

    fired: bool
    suggested_behavior: str
    n: int
    derivation: str
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class SignalReport:
    """The full per-evaluation signal surface for one or more missions.

    ``fired`` never exceeds ``config.per_turn_fire_cap`` in length
    (memento_signals_intent.yaml::ack_and_cap). ``due`` lists every other
    currently-true predicate that was NOT delivered this turn — visible in
    the report, never as an event. ``acked`` lists items currently silenced
    by an operator acknowledgement.
    """

    fired: tuple[Signal, ...] = ()
    due: tuple[Signal, ...] = ()
    acked: tuple[Signal, ...] = ()

    def to_dict(self) -> dict:
        return {
            "fired": [s.to_dict() for s in self.fired],
            "due": [s.to_dict() for s in self.due],
            "acked": [s.to_dict() for s in self.acked],
        }


@dataclass(frozen=True)
class ClockReport:
    """The full clock surface for one evaluation instant.

    Per memento_engine_intent.yaml::pure_function_injected_time: identical
    (snapshot, instant) inputs must yield a byte-identical serialized
    report. All collections here are sorted by stable keys before
    serialization; see engine.py::_stable_sort_key.
    """

    evaluated_at: datetime
    items: tuple[ItemClock, ...]
    slowest_entities: tuple[SlowestEntity, ...] = ()
    blocking_entities: tuple[BlockingEntity, ...] = ()
    money: tuple[MoneyBlock, ...] = ()
    path_comparisons: tuple[PathComparison, ...] = ()
    proposals: tuple[Proposal, ...] = ()
    zero_network: bool = True
    zero_llm: bool = True

    def to_dict(self) -> dict:
        return {
            "evaluated_at": self.evaluated_at.isoformat(),
            "items": [i.to_dict() for i in self.items],
            "slowest_entities": [s.to_dict() for s in self.slowest_entities],
            "blocking_entities": [b.to_dict() for b in self.blocking_entities],
            "money": [m.to_dict() for m in self.money],
            "path_comparisons": [p.to_dict() for p in self.path_comparisons],
            "proposals": [dataclasses.asdict(p) for p in self.proposals],
            "zero_network": self.zero_network,
            "zero_llm": self.zero_llm,
        }
