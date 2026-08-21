# Horizon Memento Mori — Product Requirements (Public)

*Leo Celis · August 2026 · maintained in open source for contributors and integrators*

**Codename:** Memento Mori (the mission plane)

> **Scope:** This is the **public PRD** shipped with the OSS repo. It is derived from the
> intent artifact [`docs/spec/horizon_memento_mori_intent.yaml`](../spec/horizon_memento_mori_intent.yaml)
> (v1.0) and a 17-topic source-audited research pack (private workspace; load-bearing
> citations are reproduced inline). Implementation follows the intent's constraint
> segments; nothing in this document overrides the intent's constraints.

**Design lineage:** the existing Horizon plane measures the health of a *conversation*
over turns. Memento Mori measures the health of a *mission* over calendar days. Same
philosophy, different object: external observer, deterministic, local by default,
signals-only.

---

## 1. Executive Summary

Memento Mori is a second measurement plane for Horizon whose unit of analysis is the
**mission** — a goal with a clock — persisted in a local store that outlives every
conversation, process, and agent. It performs **elapsed-time accounting**: ages,
days-remaining, days-since-progress, per-entity latency, and share-of-remaining-horizon,
computed as deterministic arithmetic over caller-supplied dates and recorded timestamps.
It emits **edge-triggered events** through Horizon's existing per-turn signal contract,
so elapsed calendar time becomes an input to agent planning instead of a retrospective
discovery.

**Core thesis:** goals do not usually die from lack of effort; they die politely — parked
without a revisit date, gated without an age, out-raced by external clocks nobody paired
to internal state, and bottlenecked by the slowest entity in their chain (which is
sometimes the operator). No conversation monitor can see this: a month of individually
healthy conversations that advance nothing is, to a conversation monitor, a month of
perfect health.

**The three boundary rules** (each one kills a known failure mode):

1. **Accounting, never estimation.** The engine never invents a duration, date, or
   amount. Every stored fact originates from a caller write; every output is arithmetic
   over stored facts and the evaluation instant.
2. **Alarm on age, on edges.** Events fire when the *passage of time* changes a
   predicate — a deferral expires, a gate crosses an age budget — and fire **once per
   state change**, never once per turn while a condition persists.
3. **An undated deferral is invalid.** "Revisit when things calm down" is rejected at
   the schema. A deferral carries a revisit date or it does not exist.

---

## 2. Problem Statement

### 2.1 Failure modes (mission-scale)

1. **Undated deferral** — work parked on a condition instead of a date becomes
   permanent by default; nothing is scheduled to re-trigger it.
2. **Silent gate ageing** — "0 of 2 complete" reads identically on day 1 and day 40;
   no instrument reports the 40.
3. **Unpaired external clocks** — regulatory dates, market windows, and contract
   deadlines are documented but never lined up against internal state; the deadline
   passes while the work sits parked, and the miss is discovered after the fact.
4. **Misattributed velocity** — a goal moves at the speed of the slowest entity in its
   serial chain, but effort flows to the entities that are pleasant to work on. The
   slowest entity — which may be the operator — is never named.
5. **Timeless collaboration** — the agent–operator relationship has no horizon, so a
   task done today and the same task done in three years are valued identically;
   deferral is free, forever.
6. **Session amnesia** — every new conversation resets the agent's clock to the
   session. A mission spanning months of sessions has no clock that survives any of
   them.

### 2.2 Why existing tools miss this

Surveyed against the combination under test (mission-scoped ∧ finite root ∧
agent-facing per-turn signals ∧ no estimation on the core path):

| Class | Measures | Structurally cannot see |
|-------|----------|-------------------------|
| Issue-tracker analytics (control charts, ageing WIP) | Cycle/lead time from status transitions | Non-ticket missions; personal root; agent turns; ships estimates elsewhere |
| Engineering analytics (git→deploy phase times) | Recorded delivery-pipeline sojourns | Non-repo work; entity waits; finite root; sells forecasts |
| OKR / goal software | Check-in % and KR counts on a cadence | Goal **age**; stall as missing *events*; % complete is an estimate |
| EVM / SPI | Earned vs planned value | Anything without a baseline plan — SPI *requires* estimates |
| Calendars / reminders | Point events at a due time | Age, progress, entities, horizon share |
| Personal time trackers | Hours (manual) or app usage (passive) | Mission stages, entity latency; wrong grain |
| Agent tool servers (task/calendar/goal CRUD) | Same objects as their hosts | Elapsed-mission arithmetic under a finite root |

**Fragments are old; the combination is new.** Recorded-sojourn arithmetic already
exists in delivery analytics — this plane applies it to *missions*, adds a finite root
and a per-turn edge-triggered signal contract, and refuses the estimation layer those
tools wrap around their timestamps. Published agent frameworks do not ship
mission-scoped elapsed accounting; models do not track wall-clock time unless the host
injects it (METR's time-horizon work measures *capability* in human-time units, not
instance age).

### 2.3 Who has this problem

- AI agent builders whose agents plan multi-week or multi-month work
- Operators running long-horizon goals across many agent sessions
- Teams pairing external deadlines (regulatory, contractual, market) with agent-driven execution

---

## 3. Product Vision

### 3.1 What we are building

An extension to the Horizon library (same package, separate optional plane) that:

1. Maintains a **local, persistent, append-only store** of clocked items organized as a
   tree under exactly one finite root horizon
2. Computes the **clock surface** on demand (tool surface: `clock_register`,
   `clock_progress`, `clock_status`, `clock_propose` — final shapes in the intent): every item's age, TTL state,
   days-remaining, days-since-progress, per-entity latency, horizon share, and (when a
   rate is declared) cost-of-delay and break-even dates
3. Emits **edge-triggered, acknowledgeable events** through the existing
   `process_turn → active_events[]` contract for sessions associated with missions
4. Derives what it can from **artifacts that already exist** (commits, tracker
   transitions, message sends) and accepts caller writes for what artifacts cannot know
   (linking, stages, meaning)

### 3.2 What we are NOT building

- **Not an estimator.** No duration prediction, no completion forecasting, no invented
  dates or amounts, no counterfactuals ("what the untaken path would have cost").
- **Not a task manager or scheduler.** The plane clocks items that live wherever the
  operator manages work; it creates no todos and sends no human reminders.
- **Not a finance tool.** No NPV/IRR/DCF, no discount-rate selection, no currency, no
  tax. Money enters only as a caller-declared rate and caller-supplied amounts.
- **Not people analytics.** Entity latency is defensible as *operator wait accounting
  on functional slots*; it is never a responsiveness score on a human (§8).
- **Not a calendar or reminder integration.** No event creation, no human
  notifications; the delivery surface is the agent's turn context, by design.
- **Not purchase advice.** A latency-reducing purchase is validated
  retrospectively against measured before/after latency, never recommended from
  projected savings.
- **Not a collaboration surface.** The plane is single-operator by default: one local
  SQLite file, no dependencies, nothing shared. A self-hoster serving more than one
  operator may point it at MySQL instead, in which case each API key maps to an
  assigned tenant and every read, write and erasure is tenant-scoped — isolation, not
  collaboration. There are no shared missions, no cross-tenant views, no team rollups,
  and this licenses nothing about scoring third parties (§8). Sharing surfaces remain a
  later, separate decision.
- **Not a statistics engine.** No p-values, confidence intervals, sequential tests, or
  e-values on path latencies (§7). Error-controlled inference belongs, if anywhere, in
  an optional layer above the engine — never on the core path.

### 3.3 Design principles

- **Facts are caller-provided** — the engine's entire intelligence is arithmetic,
  ordering, and thresholds over caller-supplied records
- **Zero LLM calls, zero network on the clock path** — identical store + identical
  evaluation instant → byte-identical report
- **Signals, not control** — the engine measures and names; the agent layer proposes;
  the operator decides
- **Optional plane** — with no mission store configured, every existing Horizon API
  behaves identically to the pre-plane release
- **The clock clocks its own construction** — a deployment that builds or extends this
  plane registers that build as a mission in its own store, so
  instrumentation-as-deferral is measured by the instrument itself

---

## 4. Data Model

### 4.1 The tree

Every store contains **exactly one** root item of kind `horizon` carrying a finite end
date — operator-defined, or derived by arithmetic from operator-supplied inputs (e.g. an
operator-chosen life-table value; the engine embeds no demographic model). Every other
item carries a parent path terminating at the root. Root-less items and undated
deferrals are schema errors.

| Kind | Carries | Clock outputs |
|------|---------|---------------|
| `horizon` | finite end date (the root; exactly one) | days-remaining; denominator for every share |
| `mission` | progress events; stall threshold | age; days-since-progress; progress-per-day; slowest entity |
| `task` | TTL window (ratified) | TTL state; age |
| `deadline` | date; kind (recurring pacer · one-shot window · decaying window · hard cutoff); link to gated internal state | days-remaining; paired/unpaired |
| `gate` | age budget | age vs budget |
| `entity` | stage timestamps; namespace (slot vs person) | time-in-stage; wait-vs-touch |
| `deferral` | **mandatory** revisit date | expired / not |
| `probe` | TTL like a task; stage timestamps | recorded sojourn; feeds path comparison |

### 4.2 Temporal semantics

- **Bitemporal records**: every event stores *valid time* (when the fact was true) and
  *transaction time* (when the clock learned it). Artifact timestamps routinely lag the
  real event; the lag is a recorded fact about the log, never a license to invent the
  "true" start. Corrections keep both times (supersede, not overwrite).
- **Closed-open intervals; endpoint arithmetic.** Sojourns are subtractions between
  recorded instants. Latencies are right-skewed, so summaries prefer **declared
  quantiles** over means, with **n always shown**.
- **One coordinate clock.** The evaluation instant is host-injected. The engine never
  reads ambient wall-clock mid-computation; a report is a pure function of
  (store, evaluation instant).
- **Conserved windows for rates.** A completion rate λ is computed only on windows
  where arrivals and departures are conserved (Little's-law discipline); with no honest
  λ, outputs that need one degrade to counts, never to a guessed date.

### 4.3 Capture: derive events, write meaning

The plane is usable **only if** most timestamps are side-effects of work that already
happened. Manual reconstruction dies: self-tracking abandons at the point of collection
cost (Epstein et al., CHI 2016), and professional timesheets are structurally biased —
55–89% of surveyed accountants self-report underreporting chargeable hours across three
classic surveys (via Akers & Eaton 2003).

**May be derived automatically** (with provenance: source system, native id, raw
timestamp): created / moved / touched events from git, issue trackers, sent messages,
calendar accepts, file writes.

**Must be a caller write** (human, or agent through the same validated path — never a
silent inference): the link from artifact to mission; wait-vs-touch labels; which entity
a stage belongs to; what counts as progress; TTLs, class keys, amounts, and the root
date.

Every stall signal pairs with a **recording-path check**: a mission with no derived
events *and* no caller writes is flagged "no capture," distinguishable from "no work."
Passive OS telemetry (app hours) is explicitly rejected as stage latency — right grain
for device usage, wrong object for missions.

---

## 5. Signals and the Alarm Philosophy

The plane's most likely death is not wrong arithmetic — it is **alert fatigue**. Alarm
science is unambiguous: nuisance volume causes desensitisation even when every alert is
true (ICU monitoring: PPV 27% at 97% sensitivity, Chambrin et al. 1999; 100–771 alarms
per monitored bed per day before rationalisation, Cvach 2013). Process-industry
standards (EEMUA 191, ISA-18.2) publish operator load targets on the order of **one
alarm per 10 minutes** and require a written **alarm philosophy**. Interruptions make
people faster and more stressed, not wiser (Mark, Gudith & Klocke, CHI 2008).

### 5.1 Firing rules (normative)

1. **Edges, not levels.** An event fires when its predicate *becomes* true — never
   again on subsequent turns while it stays true. Persisting conditions live on the
   `clock_status` surface.
2. **Acknowledgement gates firing.** State machine per (item, event type):
   `CLEAR → RAISED (fires once) → ACKED (silent, visible on status) → ESCALATED (fires
   once, on a new recorded fact only) → STALE (optional low-tier, once)`.
3. **Escalation requires a new fact** — a higher horizon-share rung crossed, a tighter
   deadline window entered, a TTL expiring after a stall was acked, an ack timer
   elapsing with no progress event. **"Another turn happened" is never an escalation
   fact.**
4. **Per-turn cap:** at most **one** new RAISED/ESCALATED event per associated turn,
   preempted only by a higher-priority class per the philosophy's ordering.
5. **A signal requires a possible action this turn** (investigate, ratify, pair a
   deadline, record progress). Anything else is status, not a signal.

### 5.2 Event types

| Signal | Fires when (edge) | Tier |
|--------|-------------------|------|
| `signal.deadline_window` | an external deadline enters its warning window | P1 |
| `signal.ttl_expired` | a task outlives its ratified lifespan → *investigate the blocker* (never "punish the estimate") | P1 |
| `signal.deferral_expired` | a deferral passes its revisit date | P2 |
| `signal.gate_aging` | a gate exceeds its age budget with no progress | P2 |
| `signal.mission_stalled` | zero progress events for the mission's threshold (paired with the recording-path check) | P2 |
| `signal.slowest_entity` | the identity of a mission's slowest entity changes — descriptive argmax over all recorded latencies (operator included), slot labels, with n, `censored`, and derivation attached; never a distributional claim | P2 |
| `signal.clock_unpaired` | a deadline exists with no linked internal state | P2 |
| `signal.horizon_share` | an item's elapsed time crosses a threshold share of the remaining root horizon | P3 |
| `signal.cost_of_delay` | accrued cost-of-delay crosses an operator threshold (only when rate and amount are declared) | P3 |
| `signal.probe_ready` | ≥ 1 completed probe sojourn (or caller-written count) — enough to *compare numbers*, never a powered test | P3 |
| `signal.path_ahead` | descriptive two-clock predicate on these records only (§7) | P3 |
| `signal.breakeven_passed` | a ratified break-even date passes without the measured latency improvement | P3 |

### 5.3 Alarm philosophy (shipped as a document, ISA-18.2's clause kinds without its plant numbers)

Definition of a signal · owner of the signal list (management of change) · priority
table · state machine · per-turn cap and flood definition · ack authority (operator;
agent-ack only if the philosophy allows, always visible) · enumerated escalation facts ·
KPIs (fires per associated-turn-hour, % turns with >1 new fire, stale count) · coupling
to the recording-path check · horizon signals never presented as mortality primes (§8).

---

## 6. Computation Model

Pure arithmetic; zero LLM calls; zero network. Semantic judgments (progress meaning,
latency classification as reducible/irreducible/self-imposed, blocker attribution)
enter the store only as caller-supplied metadata.

| Output | Method | Invented inputs? |
|--------|--------|------------------|
| Age / days-remaining / TTL state | Timestamp subtraction vs evaluation instant | None |
| Days-since-progress; stall predicate | Max progress-event time vs threshold | None |
| Progress-per-day / completion rate λ | Count ÷ conserved window | None (degrades to counts without a valid window) |
| Time-in-stage; wait-vs-touch | Stage-timestamp subtraction; declared quantiles with n | None |
| Slowest entity per mission | Argmax of recorded per-entity latencies over **all** sojourns, open and closed alike (operator included); an open sojourn is flagged `censored` — a right-censored lower bound, never an automatic winner | None |
| Blocking entity per mission | Argmax of **open** sojourn age — "who is blocking right now", a distinct question from "who was slowest" | None |
| Horizon share | Item elapsed ÷ root remaining | None |
| TTL proposal | Percentile over the operator's own completed comparables (empirical quantiles / Kaplan–Meier with censoring); derivation + sample size shown; **empty comparable class → no proposal**; **inert until ratified** | None — reference-class arithmetic, not prediction |
| Cost-of-delay | value_at_stake (caller) × elapsed × rate (caller) | None |
| Break-even date | (cost + rate × measured setup) ÷ (rate × measured Δlatency × measured λ) — cycles-only when λ is absent | None |
| Path comparison | Side-by-side recorded sojourns + incumbent delay accrued since the alternative was registered; n and derivation on every line | None — and no synthetic path may appear |

**Monetary rule:** the engine may **divide by money, never guess money.** One
operator-declared `time_value_rate` at the root plus caller `amount` fields make
cost-of-delay and break-even pure arithmetic. Refused: NPV/IRR/DCF, discount-rate
selection, currency conversion, tax, forecast savings, vendor "X% faster" figures as
Δlatency, and any money date minted without a declared rate. Every non-monetary output
is byte-identical with the rate removed.

---

## 7. Path Comparison: Measured, Never Simulated

When the clock names a slow block, the next question is "is there a faster path?" The
plane answers only with recorded numbers, in strength order: (1) the operator's own
history where both paths have been used; (2) **probes** — small, dated, instrumented
trials whose stage timestamps make the comparison measured-vs-measured; (3) published
base rates as provenance-labelled fields, never blended into measured columns.

**No inferential dominance.** At operator scale (n ≈ 5–20, skewed, serially dependent,
continuously observed) no "path A beats path B" distributional claim survives audit:

- Optional stopping voids fixed-n tests — checking at 20 then adding 10 observations
  yields a 7.7% false-positive rate at nominal 5%, and four common analytic freedoms
  combine to 60.7% (Simmons, Nelson & Simonsohn 2011, Table 1, verified against the
  publisher PDF).
- Continuous monitoring is worse: "even with 10,000 samples … Type I error can easily
  increase fivefold" (Johari, Pekelis & Walsh, arXiv:1512.04922, verbatim).
- The methods that legitimately fix peeking — mSPRT, always-valid p-values, e-values and
  confidence sequences (Ramdas, Grünwald, Vovk & Shafer, *Statistical Science* 2023) —
  do so by adding a likelihood or betting model. That is testing machinery, not
  timestamp accounting; it stays off the core path *by boundary*, not by ignorance.
- Pilot-study ns (12 per group, Julious 2005; 10–75 per arm, Whitehead et al. 2016) size
  a *later trial*; CONSORT's pilot extension states hypothesis-testing a pilot "is not
  recommended" (Eldridge et al., BMJ 2016). They can never arm a winner flag.

What fires instead is **`signal.path_ahead`**: a descriptive two-clock predicate — the
probe's recorded sojourn is shorter than the incumbent's accrued delay since the
alternative was registered (or than each incumbent sojourn in a frozen set) — labelled
as exactly those intervals, with n per path and the derivation. From the moment an
alternative is registered, the incumbent's accruing measured delay is the running
argument; that is the honest substitute for the counterfactual the plane refuses.

Switching cost enters as a **measured setup/learning sojourn** (switch-start →
caller-defined proficiency event) and optional caller money, folded into the break-even
arithmetic of §6. Learning-curve percentages (Wright's 80% is airplane labor vs doubled
quantity, 1936) and vendor time-to-proficiency tables are refused as inputs.

---

## 8. Ethics and Privacy (normative design rules)

Latency attributed to an identifiable human **is personal data** — behavioural metadata
included, not just content (GDPR Art. 4; WP29 Opinion 2/2017 on workplace data:
metadata analysis is explicitly in scope, and employee consent is "seldom" freely
given). The EPM meta-analysis (Ravid, Tomczak, White & Behrend, *Personnel Psychology*
2023; K=94, N=23,461) finds **no evidence electronic monitoring improves performance**
and a consistent association with **increased stress** — monitoring-shaped deployments
are a product failure mode, not just a legal one.

**May be recorded:** the operator's own timestamps; **functional slot** labels
("counsel," "vendor queue," "operator") with sojourns; a third party's display name
only for an open wait the operator must act on, with short retention after the wait
closes — implemented as an operator-declared retention window that flags an expired
name for redaction, plus an explicit redaction operation that removes the name and
leaves every recorded latency intact. The plane flags; it never purges silently,
because deleting operator data unasked is irreversible and is control rather than
measurement.

**Must stay aggregate or pseudonymous:** any view comparing people; cross-mission
responsiveness of a named other; exports and agent prompts (no person-rank tables —
agents must not rank people in `suggested_behavior`).

**Never computed:** person-level responsiveness scores or percentiles; solely automated
allocation or blame from latency (GDPR Art. 22 posture — banned by design, not
litigated); EPM-style always-on activity capture as a substitute for artifact events;
mortality primes. Terror-management "death salience" effects failed large-scale
replication (Many Labs 4: g = 0.07, n.s.), so the root horizon ships as **opt-in
arithmetic on an operator-typed date** — no skulls, no death-clock copy, no default
lifetime derivation.

`slowest_entity` therefore reports **slots by default**; a person namespace is explicit,
flagged, and excluded from shareable surfaces.

---

## 9. Success Metrics and Falsifiability

**Primary (the instrument judges itself):** monitored missions must show a bounded
interval between a clock event and the next recorded externally-visible action on that
mission. An instrument whose signals do not shorten time-to-next-irreversible-external-
action versus baseline **has failed its own thesis and must report so**. The named
failure mode is instrumentation-as-deferral: building and tuning the clock instead of
executing the highest-latency pending action.

**Secondary:**
- No expired TTL or deferral goes unsurfaced past its next associated session
- Zero undated deferrals and zero root-less items representable (schema-enforced)
- Every deadline paired to internal state or flagged `clock_unpaired` within one evaluation
- Reproducibility: identical store + evaluation instant → byte-identical report
- Retrospective replay: given historical stage timestamps, the slowest-entity
  computation re-discovers bottlenecks the operator independently names — including at
  least one operator-side bottleneck (the "comfortable instrument" test)
- Alarm KPIs stay inside the philosophy's budget (fires per associated-turn-hour; % of
  turns with more than one new fire; stale-ack count)

**When Memento Mori becomes unnecessary:**
1. Agent frameworks ship native mission-scoped elapsed accounting with per-turn
   delivery (would absorb the plane's role)
2. Models reliably track wall-clock age of their own long-horizon work across sessions
   without host injection
3. The primary metric fails: monitored missions show no improvement in
   time-to-next-external-action after honest capture (C1 conditions met) and honest
   alerting (§5) — the thesis, not the tuning, is then wrong

---

## 10. Delivery Shape

Sequenced by dependency (no dates; the plane will clock its own build):

1. **Store + tree + schema validation** — single finite root; rooted items; mandatory
   revisit dates; bitemporal events; append-only with supersede
2. **Evaluation engine** — the clock surface of §6, including latency accounting and
   the recording-path check
3. **Proposal path** — `clock_propose` (TTL from own-history percentiles; break-even
   from measured inputs), derivation shown, inert until ratified
4. **Monetary weighting** — rate + amounts; cost-of-delay; break-even; the
   with-rate/without-rate identity test
5. **Probes + path comparison** — recorded-only, two-clock predicate
6. **Signal integration** — event state machine, ack, cap, escalation facts, alarm
   philosophy document; wiring into `process_turn` for associated sessions;
   backward-compat guarantee (no store → no behavior change)
7. **Artifact adapters** — subscribe to append-only sources (git, trackers, mail
   metadata) with provenance; caller-write linking

Each segment lands against its constraint set per the intent's verification protocol
(ai-generated tests cannot self-certify; golden clock-report fixtures and
retrospective-replay fixtures are the external oracles).

---

## References (load-bearing, public)

- Chambrin, M.-C., et al. (1999). Multicentric study of monitoring alarms in the adult ICU. *Intensive Care Medicine, 25*, 1360–1366. doi:10.1007/s001340051082
- Cvach, M. (2013). Managing clinical alarms. *Nursing Management*.
- EEMUA 191 / ISA-18.2 (IEC 62682): alarm-system design guides and KPI targets.
- Mark, G., Gudith, D., & Klocke, U. (2008). The cost of interrupted work: more speed and stress. *CHI*.
- Epstein, D. A., et al. (2016). Beyond abandonment to next steps. *CHI*. doi:10.1145/2858036.2858045
- Akers, M. D., & Eaton, T. V. (2003). Underreporting of chargeable time. *Journal of Managerial Issues*.
- Simmons, J. P., Nelson, L. D., & Simonsohn, U. (2011). False-positive psychology. *Psychological Science*. doi:10.1177/0956797611417632
- Johari, R., Pekelis, L., & Walsh, D. Always valid inference. arXiv:1512.04922; KDD 2017 doi:10.1145/3097983.3097992; *Operations Research* 70(3) 2022.
- Ramdas, A., Grünwald, P., Vovk, V., & Shafer, G. (2023). Game-theoretic statistics and safe anytime-valid inference. *Statistical Science, 38*(4). doi:10.1214/23-STS894
- Julious, S. A. (2005). Sample size of 12 per group rule of thumb for a pilot study. *Pharmaceutical Statistics, 4*(4). doi:10.1002/pst.185
- Whitehead, A. L., et al. (2016). Estimating the sample size for a pilot randomised trial. *Stat. Methods Med. Res.* doi:10.1177/0962280215588241
- Eldridge, S. M., et al. (2016). CONSORT 2010 extension to pilot and feasibility trials. *BMJ, 355*, i5239.
- Ravid, D. M., Tomczak, D. L., White, J. C., & Behrend, T. S. (2023). A meta-analysis of the effects of electronic performance monitoring on work outcomes. *Personnel Psychology, 76*(1), 5–40. doi:10.1111/peps.12514
- Klein, R. A., et al. (2022). Many Labs 4 (mortality-salience replication). *Collabra: Psychology, 8*(1), 35271.
- Article 29 Working Party (2017). Opinion 2/2017 on data processing at work (WP249).
- Wright, T. P. (1936). Factors affecting the cost of airplanes. *J. Aeronautical Sciences, 3*.
- Goldratt, E. M. — Theory of Constraints lineage; Little, J. D. C. — L = λW; lean value-stream lead/touch decomposition (vocabulary and discipline; plant-specific constants deliberately not imported).
- METR (2025–2026). Measuring AI ability to complete long tasks (time-horizon methodology).

**Engineering reference:** [`docs/spec/horizon_memento_mori_intent.yaml`](../spec/horizon_memento_mori_intent.yaml) (v1.0, 7 constraints, joint-satisfaction test) ·
[`docs/spec/HORIZON_TECH_SPEC.md`](../spec/HORIZON_TECH_SPEC.md) (existing plane; the mission plane's tech spec and sub-module intents follow this PRD).
