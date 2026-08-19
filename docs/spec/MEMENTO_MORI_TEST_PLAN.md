# Memento Mori — Acceptance Test Plan

**Status:** normative before implementation. Every case maps to a PRD section and an
intent constraint. Implementation is not done until all MUST cases pass and the joint
case J-1 passes.

**Oracle provenance rules (IVD):** an AI-generated test alone cannot mark a constraint
PASS. Cases tagged **[GOLDEN]** require a hand-checked expected output committed as a
fixture (`tests/fixtures/memento_mori/`); cases tagged **[PROPERTY]** are
property-based assertions; cases tagged **[HUMAN]** need a human-authored assertion at
review. Untagged cases are supporting coverage.

**Shared fixture "smallco"** (used by most cases; all data synthetic):
- Root horizon `H`: end date **2030-01-01**
- Mission `M1` "ship-widget" (created 2026-06-01, stall_days=14)
  - Task `T1` TTL ratified [2026-07-01 → 2026-07-20]
  - Deadline `D1` 2026-09-30, kind=hard_cutoff, gates `T1`
  - Deadline `D2` 2026-12-31, kind=one_shot_window, gates **nothing**
  - Gate `G1` age_budget_days=30 (created 2026-07-01)
  - Entity `E1` slot "vendor-queue"; Entity `E2` slot "operator"
  - Deferral `F1` revisit 2026-08-10
  - Probe `P1` (alt path "channel-b", registered 2026-08-01) TTL [2026-08-01 → 2026-08-15]
- Progress events on M1: 2026-06-05, 2026-06-20, 2026-07-02 (none after)
- Stage events: E1 enter 2026-07-03 / exit 2026-07-28 (25d); E2 enter 2026-07-28, still open
- P1 stage: enter 2026-08-02 / exit 2026-08-06 (4d sojourn, completed)
- Evaluation instant everywhere below: **2026-08-18T12:00:00Z**

---

## S — Store (memento_store_intent)

| ID | Case | Expected | PRD § | Tag |
|----|------|----------|-------|-----|
| S-1 | Register deferral without `revisit_date` | `UndatedDeferralError`; store unchanged | §1 rule 3 | [HUMAN] |
| S-2 | Register second `horizon` root | `DuplicateRootError` | §4.1 | |
| S-3 | Register item with no parent path to root | `RootlessItemError` | §4.1 | |
| S-4 | Root with `end_date=None` | schema error; a horizon must be finite | §4.1 | |
| S-5 | Entity default namespace | `slot`; `person` requires explicit flag, else `PersonNamespaceUnflaggedError` | §8 | [HUMAN] |
| S-6 | Correcting an event | new event referencing old `event_id`; both rows retained with both time axes (bitemporal) | §4.2 | [GOLDEN] |
| S-7 | Store survives process restart + session reset | all items/events identical after reopen; nothing aged out | §3.3 persistence | |
| S-8 | ARTIFACT event without provenance | schema error (source_system, native_id, raw_timestamp required) | §4.3 | |
| S-9 | Fifty concurrent single-statement writes from two connections | no lost writes; tx_time ordering total | §3 store | [PROPERTY] |

## E — Engine (memento_engine_intent)

| ID | Case | Expected (smallco @ 2026-08-18) | PRD § | Tag |
|----|------|--------------------------------|-------|-----|
| E-1 | Ages & remaining | M1 age **78d**; D1 remaining **43d**; H remaining **1232d**; F1 expired by **8d**; T1 ttl_state **expired** (29d past) | §6 | [GOLDEN] |
| E-2 | days_since_progress | M1 = **47d** (since 2026-07-02) → stalled (>14) | §6 | [GOLDEN] |
| E-3 | Recording-path check | M1 has events ⇒ "no recent work"; a mission with zero events ever ⇒ "no capture" — distinct flags | §4.3 | [HUMAN] |
| E-4 | Entity latency | E1 time-in-stage 25d (closed); E2 open 21d; slowest_entity = **E2 "operator"** (open sojourn dominates) | §6 | [GOLDEN] |
| E-5 | Wait/touch only from caller labels | events without labels contribute to no wait/touch ratio; no inference | §4.3 | |
| E-6 | λ on non-conserved window | window with arrivals≠departures ⇒ `λ=None`; break-even degrades to cycle count N, **no date** (covered in `test_engine_degradation.py` / `test_engine_joint.py`) | §6 | [HUMAN] |
| E-7 | Determinism | two `evaluate()` calls, same snapshot+instant ⇒ **byte-identical** serialized report | §3.3 | [PROPERTY] |
| E-8 | Evaluation instant injection | engine never reads system clock (monkeypatch `datetime.now` to raise; evaluate succeeds) | §4.2 | [PROPERTY] |
| E-9 | No-network / no-LLM | socket + subprocess guards active during evaluate; zero calls | intent c3 | [PROPERTY] |
| E-10 | Future-dated item | task created_valid > t_eval ⇒ age 0, flagged `future_dated`, never negative ages | stress test | |
| E-11 | DST / timezone | day counts computed on calendar dates in UTC; a +13h-offset caller timestamp changes no day count by more than documented normalization | stress test | [GOLDEN] |
| E-12 | TTL proposal | comparable class with completed durations {5,8,9,12,20}d ⇒ P80 = **12d** (nearest-rank), sample_size 5, derivation string; **empty class ⇒ no proposal** | §6 | [GOLDEN] |
| E-13 | Proposal inertness | proposal returned but TTL unchanged until a RATIFY event | §6 | [HUMAN] |
| E-14 | Money identity | full report with rate declared vs rate removed: **every non-monetary byte identical** | §6 rule | [PROPERTY] |
| E-15 | Break-even arithmetic | C_s=600, rate=50/h, T_s=4h, Δt=2h/cycle, λ=0.5 cycles/day ⇒ s=50·2·0.5=50/day; t_be = t_eval + (600+200)/50 = **+16 days** | §6 | [GOLDEN] |
| E-16 | Refusals | requests for NPV, currency conversion, forecast Δt, invented λ ⇒ typed refusal errors naming the rule, never a number | §6 | [HUMAN] |
| E-17 | Path comparison | P1 sojourn **4d** vs incumbent accrued **17d** (since 2026-08-01); base-rate column separate and provenance-labelled; no synthetic latency fields exist in the schema | §7 | [GOLDEN] |
| E-18 | Counterfactual refusal | API surface has no "would-have-taken" computation; requesting one is a typed refusal | §3.2 | |
| E-20 | `slowest_entity` n | `n` equals the population the argmax summarised (matches the derivation's own "over N recorded entities"), never a constant | §6 | [GOLDEN] |
| E-21 | Person-namespace redaction is complete | a person winner is still measured, but both its title AND its resolvable `entity_item_id` are withheld from report and payload — an id resolves to the name through the store | §8 | [HUMAN] |
| E-19 | Horizon share | M1 elapsed 78d vs H remaining ⇒ share **≈ 0.0595** (78/1310) crosses the 0.05 rung | §6 | [GOLDEN] |

## G — Signals (memento_signals_intent)

| ID | Case | Expected | PRD § | Tag |
|----|------|----------|-------|-----|
| G-1 | Edge fire once | F1 expired ⇒ `deferral_expired` RAISED on first evaluation after 2026-08-10; second evaluation same state ⇒ **no event** | §5.1 r1 | [GOLDEN] |
| G-2 | Ack silences | ACK on mission_stalled ⇒ no further fires; item listed under `acked` in status | §5.1 r2 | [HUMAN] |
| G-3 | Escalation only on new fact | after ack, more turns ⇒ silent; horizon-share crossing next rung ⇒ single ESCALATED event | §5.1 r3 | [GOLDEN] |
| G-4 | "Another turn" is unrepresentable | escalation-rung enum contains no turn-count member (API-level assertion) | §5.1 r3 | |
| G-5 | Per-turn cap | smallco @ 2026-08-18 has ≥4 due edges (F1, T1, M1 stall, D2 unpaired, share rung) ⇒ exactly **1** event emitted (P1 first: `ttl_expired` on T1); remainder in report | §5.1 r4 | [GOLDEN] |
| G-6 | Priority order | with cap 1 and both a P1 and P2 due, P1 wins; among P1s, fewer days-remaining wins | §5.2 | |
| G-7 | STALE | ACKED 30+ days with no progress ⇒ one low-tier STALE event | §5.1 | |
| G-8 | probe_ready & path_ahead | P1 completion ⇒ probe_ready once; path_ahead fires with payload carrying **both intervals, n=1, derivation** — and no p-value/CI field exists | §7 | [GOLDEN] |
| G-9 | No person ranking in behaviors | linter over `suggested_behavior` templates + generated payloads: no person-ordered lists; slowest_entity payload uses slot label | §8 | [HUMAN] |
| G-10 | Backward compat | `store_path=None` ⇒ full existing test suite byte-identical results; memento code path not entered (coverage assertion) | §3.3 | [PROPERTY] |
| G-11 | Association scoping | session not associated with any mission ⇒ zero memento events even with a store configured | §6 integration | |
| G-13 | `cost_of_delay` fires | with rate + item amount + `cost_of_delay_threshold` all declared, the signal fires; absent any of the three there is no predicate at all (omission, not a default cutoff) | §5.2 | [GOLDEN] |
| G-14 | `breakeven_passed` fires | a RATIFY event carrying `kind="breakeven"` whose date elapsed with no `measured_improvement` fires once; recorded improvement suppresses it | §5.2 | [GOLDEN] |
| G-12 | Adapter provenance | git_local adapter emits ARTIFACT events with full provenance; adapter cannot create links (API has no such parameter) | §4.3 | |

## M — MCP surface & agent contract

| ID | Case | Expected | Tag |
|----|------|----------|-----|
| M-1 | Tool discovery | with a store configured, the six mission tools (register/progress/status/propose/ack/associate) list alongside existing tools; with store_path=None they do not appear | [PROPERTY] |
| M-2 | Typed error serialization | UndatedDeferralError over MCP ⇒ {error_type, rule, fix}; no stack trace, no silent coercion | [GOLDEN] |
| M-3 | associate_mission scoping | events reach process_turn only for associated sessions (pairs with G-11); association survives session re-registration | |
| M-4 | Plane tag | every mission event payload carries plane="mission"; existing conversation events gain plane="conversation" with no other byte changed (compat) | [PROPERTY] |
| M-5 | Loud-contract text | each mission tool description contains the surface-don't-absorb line; suggested_behavior templates for mission events instruct surfacing with numbers | [HUMAN] |
| M-7 | Evaluation-instant provenance | `clock_status` output carries `eval_instant_source` ∈ {injected, host_clock}; the engine itself never reads a clock, and a boundary default is visible rather than silent | [PROPERTY] |
| M-6 | Instructions doc sync | the §3 rules block in docs/integrations/MEMENTO_MORI_AGENTS.md names every shipped tool and no unshipped one (doc-code consistency check) | [HUMAN] |

## R — Replay & self-judgment (PRD §9)

| ID | Case | Expected | Tag |
|----|------|----------|-----|
| R-1 | Retrospective replay | synthetic 90-day history with a designed bottleneck at entity X ⇒ slowest-entity computation names X from timestamps alone | [GOLDEN] |
| R-2 | Operator-side bottleneck | a replay variant where the designed bottleneck is the operator slot ⇒ named as such (comfortable-instrument test) | [GOLDEN] |
| R-3 | Time-to-next-action metric | interval between each fired event and the next recorded externally-visible event on that mission is computed and reported; the metric exists and is queryable (its *evaluation* against a baseline is an operational exercise, not a unit test) | [HUMAN] |
| R-4 | Alarm KPIs | fires per associated-turn, % turns >1 new fire (must be 0 by G-5), stale-ack count — present in status output | |

## J — Joint satisfaction (gates completion)

**J-1 [GOLDEN+HUMAN]** — single flow asserting all seven parent constraints on the same
output: configure store → register finite root → register mission+deadline+gate+entity
→ attempt root-less item (rejected) → attempt undated deferral (rejected) → request TTL
proposal (derivation shown, not applied) → ratify → declare rate + amount → assert
cost-of-delay and break-even derive only from stored facts → assert non-monetary bytes
identical with rate removed → register probe + second path → assert comparison contains
only measured latencies with base-rate fields separate → advance evaluation instant
past TTL and revisit dates → assert edge events fire once and ack silences → assert
report reproducible byte-identically → assert zero network/LLM → assert unconfigured
session unchanged.

---

## Out-of-scope for this suite (documented, not tested here)

- Human-rated usefulness of `suggested_behavior` text (operational evaluation)
- Legal adequacy of the privacy posture in any jurisdiction (documentation warnings
  ship; law is the deployer's obligation)
- Multi-tenant behavior (V1 non-goal)
