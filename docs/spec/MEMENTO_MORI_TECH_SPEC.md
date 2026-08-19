# Horizon Memento Mori — Technical Specification

**Status:** design — implementation not started. Derived from
[`horizon_memento_mori_intent.yaml`](horizon_memento_mori_intent.yaml) (v0.8) and
[`../product/MEMENTO_MORI_PRD.md`](../product/MEMENTO_MORI_PRD.md).
Sub-module intents: [`intents/memento_store_intent.yaml`](intents/memento_store_intent.yaml) ·
[`intents/memento_engine_intent.yaml`](intents/memento_engine_intent.yaml) ·
[`intents/memento_signals_intent.yaml`](intents/memento_signals_intent.yaml).
Acceptance tests: [`MEMENTO_MORI_TEST_PLAN.md`](MEMENTO_MORI_TEST_PLAN.md).

---

## 1. Overview

Memento Mori is an **optional second plane** in the `horizon_monitor` package. It has
three parts, mapped one-to-one to the sub-module intents:

| Part | Owns | Sub-intent |
|------|------|-----------|
| **Store** | Persistent rooted tree of clocked items; bitemporal event log; schema validation | `memento_store_intent.yaml` |
| **Engine** | The clock surface: pure arithmetic over (store, evaluation instant); proposals; monetary weighting; path comparison | `memento_engine_intent.yaml` |
| **Signals** | Edge/ack state machine; per-turn cap; `process_turn` integration; backward compat; artifact adapters | `memento_signals_intent.yaml` |

Hard invariants inherited from the parent intent (all seven constraints apply to every
part): facts are caller-provided; zero LLM / zero network on the clock path;
byte-identical reports for identical (store, evaluation instant); signals never
control; persistence across sessions; exactly one finite root; no invented dates,
durations, or amounts.

## 2. Data Models

### 2.1 Configuration

```python
@dataclass(frozen=True)
class MementoConfig:
    store_path: Path | None = None      # None => plane disabled entirely
    time_value_rate: Decimal | None = None   # currency per hour; optional
    rate_currency: str | None = None    # ISO 4217 label only; no conversion
    stall_default_days: int = 14        # per-mission override allowed
    deadline_warn_days: int = 14        # per-deadline override allowed
    horizon_share_rungs: tuple = (0.01, 0.05, 0.10, 0.25)
    per_turn_fire_cap: int = 1
    stale_ack_days: int = 30
    cost_of_delay_threshold: Decimal | None = None   # gates signal.cost_of_delay
```

`MementoConfig` hangs off the existing `Config`; `store_path is None` must make every
existing API byte-identical to the pre-plane release (backward-compat constraint).

### 2.2 Item schema (store)

```python
class ItemKind(StrEnum):
    HORIZON = "horizon"; MISSION = "mission"; TASK = "task"
    DEADLINE = "deadline"; GATE = "gate"; ENTITY = "entity"
    DEFERRAL = "deferral"; PROBE = "probe"

@dataclass(frozen=True)
class Item:
    item_id: str            # uuid4
    kind: ItemKind
    parent_id: str | None   # None ONLY for the single HORIZON root
    title: str
    created_valid: datetime     # when true (caller)
    created_tx: datetime        # when recorded (host clock at write)
    # kind-specific, all caller-written:
    end_date: date | None       # HORIZON: required finite
    revisit_date: date | None   # DEFERRAL: required (schema-enforced)
    ttl_start: date | None      # TASK/PROBE: ratified window
    ttl_end: date | None
    deadline_date: date | None  # DEADLINE: required
    deadline_kind: str | None   # recurring_pacer|one_shot_window|decaying_window|hard_cutoff
    gates_item_id: str | None   # DEADLINE: link to internal state (else unpaired)
    age_budget_days: int | None # GATE
    stall_days: int | None      # MISSION override
    namespace: str | None       # ENTITY: "slot" (default) | "person" (flagged)
    amount: Decimal | None      # cost / value_at_stake (caller)
    status: str                 # open | done | superseded
    superseded_by: str | None
```

Validation (all schema errors, no override flags): exactly one `HORIZON` per store with
a finite `end_date`; every non-root item's `parent_id` chain terminates at the root;
`DEFERRAL` without `revisit_date` rejected; `ENTITY` defaults `namespace="slot"`;
`namespace="person"` requires an explicit flag argument at write time.

### 2.3 Event log (append-only, bitemporal)

```python
class EventKind(StrEnum):
    PROGRESS = "progress"; STAGE_ENTER = "stage_enter"; STAGE_EXIT = "stage_exit"
    ARTIFACT = "artifact"          # derived from external append-only sources
    RATIFY = "ratify"              # TTL / breakeven proposal accepted
    ACK = "ack"                    # acknowledgement of a fired signal

@dataclass(frozen=True)
class ClockEvent:
    event_id: str
    item_id: str
    kind: EventKind
    valid_time: datetime        # when the fact happened (caller / artifact)
    tx_time: datetime           # when the store learned it
    stage: str | None           # for stage events; caller-labelled
    wait_or_touch: str | None   # caller-labelled; never inferred
    provenance: Provenance | None   # REQUIRED when kind == ARTIFACT
    payload: dict               # amounts, notes; no engine interpretation

@dataclass(frozen=True)
class Provenance:
    source_system: str      # e.g. "git", "issue-tracker", "mail"
    native_id: str
    raw_timestamp: datetime
```

Corrections **supersede**, never overwrite: a correcting event references the corrected
`event_id`; both valid and tx times of both records are kept.

### 2.4 Report types (engine output; plain dataclasses → dicts)

`ClockReport` (per evaluation): list of `ItemClock` rows sorted by urgency, plus
`PathComparison` blocks and `Proposal`s. Every row carries `derivation: str` — the
arithmetic spelled out ("2026-08-18 − 2026-08-04 = 14d") — and `n` wherever a summary
statistic appears. Monetary fields are present **only** when a rate is declared and are
each traceable to `(amount, rate, measured duration)` in the derivation string.

## 3. Store

- **Backend:** SQLite in WAL mode at `store_path` (same `storage/` conventions as the
  existing plane). Tables: `mm_items`, `mm_events`, `mm_fires` (signal state), plus
  `mm_meta` (schema version). All migrations forward-only and reversible by backup.
- **Append-only discipline:** `mm_items` rows mutate only `status/superseded_by`;
  everything else is new rows. `mm_events` is insert-only.
- **Concurrency:** many agent sessions may write. Writes are single-statement
  transactions; ordering across sessions is by `tx_time` (host clock) — vector-clock
  precision is explicitly not required because arithmetic uses valid time and
  same-store tx ordering only.
- **Isolation from conversation storage:** separate file; the conversation plane never
  reads it; the mission plane never reads conversation content.

## 4. Evaluation Pipeline (`clock_status`)

Pure function `evaluate(store_snapshot, t_eval) -> ClockReport`. Steps, in order:

1. **Load + validate** the tree (root present, finite; orphans are store corruption →
   explicit error, never silent skip).
2. **Per-item arithmetic** (all subtraction/comparison on dates normalized to UTC;
   date-only fields compare at UTC midnight; DST never affects day counts because day
   arithmetic is calendar-date based, not epoch-seconds based):
   - `age_days = (t_eval.date() - created_valid.date()).days`
   - `days_remaining` for deadline/horizon; `ttl_state ∈ {pending, open, expired}`
   - `days_since_progress` = min over PROGRESS/ARTIFACT events; `None` if no events →
     recording-path check distinguishes "no capture" (zero events ever) from "no work"
     (events exist, none recent)
   - mission `rate λ = completions / window_days` **only** on a conserved window
     (arrivals == departures accounted); otherwise `λ = None` and downstream outputs
     degrade to counts
   - entity `time_in_stage`, `wait_vs_touch` (only over caller-labelled events),
     summarized as declared quantiles with `n`
   - `slowest_entity` per mission = argmax of recorded entity latencies over
     **all** sojourns, open and closed (operator entity included); slot label in
     output; an open winner carries `censored: true` because its recorded value
     is a lower bound (research A2 F6). Equal latencies break toward the open
     sojourn, whose true value is strictly greater.
   - `blocking_entity` per mission = argmax of **open** sojourn age — the
     constraint-aged open item (research B1), answering "who is blocking now"
     rather than "who was slowest". The two are computed and reported
     separately and may name different entities.
   - `horizon_share = age_days / max(1, root_days_remaining_at_item_creation)` and
     current share vs remaining
3. **Monetary block** (skipped entirely when `time_value_rate is None`; every
   non-monetary field must be identical either way):
   - `cost_of_delay = amount × rate × elapsed_hours` (caller amount = value at stake/day
     semantics documented in schema; formula fixed in the engine intent)
   - `breakeven_date = t_eval + (C_s + rate×T_s) / (rate × Δt × λ)` — components all
     measured/caller; if `λ is None` → cycle count `N = ceil(T_s/Δt)` only, no date
4. **Path comparison:** for each mission with ≥1 registered alternative: list recorded
   probe/incumbent sojourns side by side + incumbent delay accrued since alternative
   registration; base-rate fields (if caller attached literature values) rendered in a
   separate, provenance-labelled column, never merged; no synthetic latency anywhere.
5. **Proposals** (`clock_propose`): TTL = declared percentile (default P80) over the
   caller-keyed comparable class of completed durations, Kaplan–Meier when censored
   records exist; **empty class → no proposal**; breakeven per step 3. Returned with
   `{value, sample_size, derivation}`; never applied — a `RATIFY` event applies it.
6. **Determinism guard:** the report serializer sorts all collections by stable keys
   and formats numbers with fixed precision so identical inputs are byte-identical.

## 5. Signal State Machine (`signals` part)

Per `(item_id, signal_type)` a row in `mm_fires`:
`state ∈ {CLEAR, RAISED, ACKED, ESCALATED, STALE}`, `last_edge_tx`, `ack_event_id`,
`escalation_rung`.

- **Edge detection:** predicate evaluated against the previous stored state; fires only
  on `false→true` or on a **higher enumerated rung** (horizon-share rung index, tighter
  deadline window index, TTL-expired-after-ack, ack-timer-elapsed-without-progress).
  The rung enum is closed; "another turn happened" is unrepresentable as an edge.
- **Cap:** at most `per_turn_fire_cap` new RAISED/ESCALATED per associated turn;
  priority order P1 > P2 > P3, ties by days-remaining ascending; the suppressed
  remainder appears in the report, not as events.
- **Ack:** an ACK event moves state to ACKED; ACKED items render in `clock_status`
  under an `acked` section and never fire until an escalation rung or STALE.
- **Signal payload:** `{type, item_id, suggested_behavior, n, derivation}`.
  `suggested_behavior` templates live in config; they must not contain person-ranking
  language and are lintable (test-plan case S-9).

### 5.1 Signal predicates (normative table)

| Type | Predicate (edge) | Tier |
|------|------------------|------|
| deadline_window | `days_remaining <= warn_days` first time / tighter rung | P1 |
| ttl_expired | `t_eval.date() > ttl_end` | P1 |
| deferral_expired | `t_eval.date() > revisit_date` | P2 |
| gate_aging | `age_days > age_budget_days` and no PROGRESS since budget start | P2 |
| mission_stalled | `days_since_progress > stall_days` (recording-path check attached) | P2 |
| slowest_entity | identity of the argmax winner changes (payload carries n, censored, derivation) | P2 |
| clock_unpaired | DEADLINE with `gates_item_id is None` at first evaluation | P2 |
| horizon_share | share crosses next configured rung | P3 |
| cost_of_delay | accrued CoD crosses caller threshold (rate+amount+threshold all declared) | P3 |
| probe_ready | first completed probe sojourn (or caller-written count reached) | P3 |
| path_ahead | completed probe sojourn < incumbent accrued delay (or < each sojourn in frozen set) | P3 |
| breakeven_passed | `t_eval.date() > ratified breakeven` and measured post-switch Δlatency absent/≤0 | P3 |

## 6. Integration

- **`process_turn`:** when a session is associated with ≥1 mission
  (`associate_mission(session_id, mission_id)` on the registry), the pipeline appends
  the plane's due events (post-cap) to `active_events`. With no store configured, the
  code path is not entered at all (compat).
- **MCP tools:** `clock_register`, `clock_progress`, `clock_status`, `clock_propose`,
  `clock_ack` (thin wrapper writing an ACK event), and `associate_mission`
  (session→mission binding on the session registry) — same server, same auth, same
  local-only posture as existing tools. Tool descriptions embed the loud-contract
  one-liner ("surface this; never absorb silently") so schema-only clients still get
  the behavioral contract. Typed errors serialize as {error_type, rule, fix} and are
  meant to be relayed to the operator verbatim.
- **Event payload plane tag:** every emitted event carries `plane: "mission"`;
  existing conversation events carry `plane: "conversation"` (added as a
  backward-compatible field) so hosts and rules route the loud vs silent contracts
  without name-matching.
- **Agent instruction layer:** `docs/integrations/MEMENTO_MORI_AGENTS.md` is the
  canonical host-rules block (Claude/Cursor/Copilot). It is part of the product
  surface: capture (§4.3) depends on the side-effect write rule living in host rules,
  and the plane's loudness contract inverts the fidelity plane's invisibility.
- **Artifact adapters (`memento/adapters/`):** pull-based readers that translate an
  external append-only source into ARTIFACT events with mandatory provenance. V1 ships
  the interface plus a filesystem/git reference adapter; adapters never write links —
  linking an artifact stream to a mission is a caller `clock_register` association.
- **Evaluation instant:** the engine never calls `datetime.now()` — `t_eval` is
  always a parameter. The MCP boundary is the single place allowed to read a wall
  clock, and only when the host injects no `timestamp`; when it does, the response
  carries `eval_instant_source: "host_clock"` (vs `"injected"`) so a
  boundary-defaulted instant is auditable rather than silent. Two identical calls
  with no timestamp legitimately differ; that field is what makes the difference
  visible.

## 7. Package Structure

```
src/horizon_monitor/memento/
    __init__.py
    config.py          # MementoConfig
    models.py          # Item, ClockEvent, Provenance, report types
    store.py           # SQLite store, schema validation, migrations
    engine.py          # evaluate(): the pure clock surface
    money.py           # monetary block (guarded by rate presence)
    paths.py           # path comparison + probe arithmetic
    propose.py         # ttl / breakeven proposals
    signals.py         # state machine, cap, predicates
    philosophy.md      # the alarm philosophy document (shipped)
    adapters/
        base.py        # ArtifactAdapter interface
        git_local.py   # reference adapter
tests/unit/memento_mori/ ...        # per test plan
tests/integration/memento_mori/ ... # process_turn wiring, MCP tools
```

## 8. Error Handling

Schema violations raise typed exceptions (`UndatedDeferralError`, `RootlessItemError`,
`DuplicateRootError`, `PersonNamespaceUnflaggedError`) with messages that state the
rule and the fix — never silently coerced. Store corruption (orphaned parent) fails the
evaluation loudly. Missing optional inputs (no rate, no λ, empty comparable class)
degrade *by omission with an explanatory field*, never by substitution of a guessed
value.

## 9. Non-Goals (binding, from intent v0.7)

Duration estimation · task management · progress/latency semantic judgment · financial
modelling beyond rate×duration arithmetic · purchase advice · counterfactuals ·
people analytics or person ranking · calendar/reminder integration · conversation-plane
signals · multi-tenant coordination (V1).

## 10. Test Strategy

The acceptance suite is specified in [`MEMENTO_MORI_TEST_PLAN.md`](MEMENTO_MORI_TEST_PLAN.md):
PRD-mapped cases with concrete golden fixtures. Provenance rules apply — AI-generated
tests alone cannot mark a constraint PASS; the plan names which cases require
**golden-fixture oracles** (hand-checked expected reports committed to the repo) and
which require **property tests** (e.g., rate-removal identity). The joint-satisfaction
test drives all seven parent constraints on one flow and gates completion.
