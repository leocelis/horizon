# The Memento Mori alarm philosophy

This document is the plane's written alarm philosophy, required by the same
discipline process-safety standards require of a plant control room (ISA-18.2,
EEMUA 191): a named owner, a closed state machine, an enumerated list of what
counts as new evidence, and a load budget. It borrows those clause *kinds*,
not their plant-specific numbers — this is mission tracking for one operator,
not a refinery.

The plane's most likely failure mode is not wrong arithmetic. It is alert
fatigue: ICU monitoring data shows desensitisation sets in even when every
alarm is individually true (positive predictive value of 27% at 97%
sensitivity — Chambrin et al. 1999; 100–771 alarms per monitored bed per day
before rationalisation — Cvach 2013). Interruptions measurably make people
faster and more stressed, not wiser (Mark, Gudith & Klocke, CHI 2008). Every
clause below exists to keep the fire rate low enough that a fire still means
something.

## 1. Definition of a signal

A signal is a named predicate over one item's clock row that, when it becomes
true, implies a possible action *this turn* — investigate a blocker, ratify a
proposal, pair a deadline to internal state, record progress. A condition
that persists without implying a new action is status, reported on
`clock_status`, and is never a signal (PRD §5.1 rule 5). The full predicate
table lives in `signals.py::TIER` / `SUGGESTED_BEHAVIOR` and is reproduced
below.

## 2. Owner of the signal list (management of change)

The predicate table, tier assignments, thresholds (`deadline_warn_days`,
`stall_default_days`, `horizon_share_rungs`, `stale_ack_days`,
`per_turn_fire_cap`) are all fields on `MementoConfig` — one file, one
dataclass, one place any change to what fires or how loudly is reviewed. No
predicate, tier, or threshold is hardcoded inside the state machine itself;
`signals.py` reads `MementoConfig` at every evaluation and never invents a
default the config does not declare.

## 3. Priority table

| Tier | Signals | Cap behavior |
|------|---------|---------------|
| P1 | `deadline_window`, `ttl_expired` | first to consume the per-turn cap |
| P2 | `deferral_expired`, `gate_aging`, `mission_stalled`, `slowest_entity`, `clock_unpaired` | second |
| P3 | `horizon_share`, `cost_of_delay`, `probe_ready`, `path_ahead`, `breakeven_passed` | last |

Within a tier, the predicate with the fewest days-remaining wins; predicates
with no natural days-remaining figure (stall, slowest-entity, share-rung
crossings) sort after every predicate that has one.

## 4. State machine

Closed, five states, per (item, signal type):

```
CLEAR -> RAISED (fires once) -> ACKED (silent, visible on clock_status)
      -> ESCALATED (fires once, only on a new recorded fact)
      -> STALE (optional, low-tier, once, after stale_ack_days with no progress)
```

The enum (`SignalState`) has no turn-count or elapsed-turns member. "Another
turn happened" is not representable as a state transition — it is structurally
absent from the type, not merely discouraged by convention (test plan G-4).

## 5. Per-turn cap and flood definition

At most `per_turn_fire_cap` (default 1) new RAISED or ESCALATED events are
delivered per associated turn. Every other currently-true predicate that lost
the cap is still visible in the report's `due` list — never silently dropped,
never delivered as an event. A "flood" is any turn where the number of newly
true predicates exceeds the cap; the philosophy's answer to a flood is
priority ordering, not raising the cap.

## 6. Ack authority

Acknowledgement is operator authority. `signals.ack()` builds the fire-state
row; the caller is expected to record it through the same validated write path
as any other event (an `EventKind.ACK` row), so an ack is never a side effect
an agent can perform invisibly. Once acked, a signal moves to silent-but-visible:
no further fires until a strictly higher escalation rung is reached, or the
stale timer elapses with no progress in between.

## 7. Enumerated escalation facts

An ACKED signal escalates only on one of these newly recorded facts — never on
elapsed turns alone:

- a higher horizon-share rung crossed
- a tighter deadline window entered
- a TTL expiring after the item was already acked for a different reason
- the stale-ack timer elapsing with zero progress events recorded since the ack

## 8. KPIs

The plane judges itself on: fires per associated-turn-hour, the percentage of
turns with more than one newly-true predicate (flood rate), and the STALE
count (acked items nobody returned to). These are operational health metrics
for the alarm system itself, not mission-progress metrics — a rising STALE
count means the ack discipline is failing, not that the missions are.

## 9. Coupling to the recording-path check

Every stall-class signal is paired with the recording-path distinction
computed in `engine.py`: "no capture" (the mission has zero recorded events,
ever) is a different fact from "no recent work" (events exist; none are
recent). A stalled mission with no capture is a measurement gap, not
necessarily an idle one, and the signal payload says which case applies.

## 10. Horizon signals are never presented as mortality primes

The root horizon is opt-in arithmetic on a date the operator typed in — never
a default lifetime derivation, never death-clock copy, no skulls. Terror-
management "death salience" effects failed large-scale replication (Many Labs
4: g = 0.07, not significant), and this plane does not lean on an effect that
was never there. `horizon_share` reports a ratio and a rung crossing; nothing
in its payload or `suggested_behavior` text references mortality.

## Related, binding elsewhere

`slowest_entity` payloads carry slot labels, never person names, and no
surface in this plane ever produces a person-ranked list — that constraint
(`no_person_ranking_in_output`) is enforced mechanically by a linter over the
`suggested_behavior` templates and generated payloads
(`memento_signals_intent.yaml`), not by convention.
