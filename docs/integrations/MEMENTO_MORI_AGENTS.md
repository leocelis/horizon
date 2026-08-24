# Memento Mori for Agents — MCP Tools and Host Instructions

**Status:** design (implementation pending). This document is the **canonical source**
for the agent-rules block below, the same way `CLAUDE_DESKTOP.md` is canonical for the
fidelity plane. Host configuration (Claude Desktop, Claude Code, Cursor, Copilot) is
identical to the existing plane — same server, same registration; the mission tools
appear alongside the conversation tools once the plane is configured with a store.

---

## 1. The contract difference: this plane is LOUD

The fidelity plane's instructions are built on invisibility — never mention the
monitor, apply `suggested_behavior` silently. **Memento Mori inverts that.** Its
signals exist to change what the operator does next, so they must be **surfaced,
attributed, and numbered**:

> ❌ silently reprioritizing because a deferral expired
> ✅ "Clock: `deferral_expired` — *renew-hosting-decision* passed its revisit date
> (2026-08-10, 8 days ago). Handle it now, re-defer with a new date, or close it?"

An agent must never quietly absorb a mission signal. The whole failure mode the plane
exists to fix is silence.

## 2. MCP tool surface (mission plane)

| Tool | Purpose | Key params | Returns |
|------|---------|-----------|---------|
| `clock_register` | create/update a clocked item (8 kinds); ratify proposals | `item` (kind, dates, parent_id, …), `ratify_proposal_id?` | `item_id` or typed schema error |
| `clock_progress` | record a progress/stage event (caller fact, or derived artifact w/ provenance) | `item_id`, `event` | ack or typed error |
| `clock_status` | full clock surface: ages, TTL states, latencies, shares, paths, money | `scope?`, `timestamp` (host-injected) | `ClockReport` dict |
| `clock_propose` | TTL window or break-even date from recorded history; inert | `item_id`, `kind: ttl\|breakeven` | `{value, sample_size, derivation}` |
| `clock_ack` | acknowledge a fired signal (operator-authorized) | `item_id`, `signal_type`, `actor` | ack |
| `associate_mission` | bind this session to a mission so its events reach `process_turn` | `session_id`, `mission_id` | ack |

Errors are **typed and instructive** (`UndatedDeferralError`, `RefusedComputation`, …):
the message states the violated rule and the fix. Agents relay them verbatim rather
than working around them.

Delivery: for associated sessions, due mission events (post-cap, max one new per turn)
arrive in the same `process_turn → active_events[]` the host already consumes. The
`suggested_behavior` on mission events is **meant to be surfaced**, unlike the
conversation plane's.

## 3. Canonical agent-rules block

Paste into the host's rules file (`CLAUDE.md`, `.cursor/rules/`, Copilot instructions).
This block is versioned here; reload from this file to refresh.

```text
# ============================================================
# Horizon Memento Mori — mission clock (agent rules v1)
# Source: horizon/docs/integrations/MEMENTO_MORI_AGENTS.md
# ============================================================
# The mission plane is LOUD (unlike the conversation monitor, which stays
# invisible). Surface every mission signal; never absorb one silently.

SESSION START (when the conversation concerns a known mission):
  1. Call associate_mission(session_id, mission_id).
  2. Call clock_status for that scope and OPEN your first substantive reply
     with any red state, numbers included: expired TTLs/deferrals, stall
     days, deadline windows, horizon share, and BOTH entity readings when
     present — slowest entity (longest recorded sojourn; say "still
     accruing" when it is flagged censored) and blocking entity (who the
     mission is waiting on right now). They are different questions and may
     name different slots; never merge them into one claim.

WHEN A MISSION EVENT ARRIVES in active_events:
  - State it to the operator with its numbers and derivation, then propose
    ONE concrete next action (investigate / re-date / record progress /
    close). Do not proceed with unrelated work before surfacing it.

NEW ITEMS — register, don't narrate:
  - When work reveals a new task, deadline, gate, entity, or deferral under
    an associated mission, call clock_register for it — do not just mention
    it in prose. A deferral without a revisit_date is rejected by the store
    (see PARKS AND DATES below); every other kind needs only its required
    fields.

WRITES — the side-effect rule (capture dies otherwise):
  - When you complete real work tied to a mission IN THIS TURN, record it:
    clock_progress with the fact and its date. One write, same turn, as a
    side-effect of the work — never a separate "logging session", and NEVER
    a fabricated or assumed event.
  - Meaning is explicit: linking artifacts to missions, stage labels,
    wait-vs-touch — only via explicit tool calls, never inferred silently.

PARKS AND DATES:
  - Any deferral ("park it", "later", "revisit when…") MUST be registered
    with a concrete revisit_date. The store rejects undated deferrals; do
    not route around the rejection — ask the operator for the date.
  - NEVER invent durations, deadlines, or amounts. If the operator wants a
    task window, call clock_propose(kind=ttl) and present the derivation
    and sample size; the operator ratifies. Empty history => say so; do not
    substitute a guess.

ACK DISCIPLINE:
  - clock_ack only on the operator's explicit acknowledgement of that
    signal. Never self-ack to quiet a signal you find repetitive — the
    engine already caps and edge-triggers; silence belongs to the operator.

PROHIBITIONS (mirror the engine's refusals):
  - No person-ranked lists anywhere in your replies (slowest entity is a
    SLOT label). No counterfactuals ("would have taken"). No NPV/forecast
    math on mission money. No inferential "path A beats path B" — report
    the two recorded intervals (path_ahead) as exactly that.
  - Do not present the root horizon with mortality framing; it is a date
    the operator chose.
```

## 4. Why each rule exists (for maintainers)

| Rule | Grounding |
|------|-----------|
| Loud, numbers-first surfacing | The plane's thesis: silence is the failure mode; PRD §1, §5 |
| Side-effect writes, never a logging ritual | Capture-burden research: manual logging habits die; artifact/side-effect capture survives (PRD §4.3) |
| Ask-for-a-date on parks | Undated deferral is a schema error; the agent is the UX in front of that rejection |
| Propose-then-ratify for windows | Accounting/estimation boundary; agent-invented durations are the banned failure |
| Operator-only ack | Alarm philosophy: shelving authority is explicit; self-ack recreates silent death |
| No person ranking in replies | Ethics rules — the agent's reply is the plane's most-read output surface (PRD §8) |
| One surfaced action per event | Per-turn cap exists to protect attention; the reply should match it |

## 5. Coexistence with the fidelity plane

Both planes ride the same `process_turn`. The host applies **both** contracts at once:
conversation events (`alert.*`, conversation `signal.*`) stay silent per the existing
instructions; mission events (the twelve `signal.*` types of this plane) are surfaced
per §3. Events carry their plane in the payload (`plane: "mission" | "conversation"`)
so hosts and rules can route without name-matching.

## 5a. Status levels vs alerts (`status.*` vs `signal.*`)

A session with no associated mission still receives a **once-per-session status
sweep** of what is due across the store, tagged `plane: "mission"` with a
`status.*` type and `metadata.surface == "level"`.

Treat it as information, not as an alarm:

- **State it with its numbers**, as with any mission surface, and offer to
  associate the mission so its real signals reach the session.
- **Do not `clock_ack` it.** There is nothing to acknowledge — no signal fired.
  The alert is still pending for the associated turn, deliberately: firing it
  here would spend its single RAISED edge in a conversation where the operator
  cannot act on it.
- It appears **once per session**. A level repeated every turn is the flood the
  alarm research warns about.

`signal.*` events are the alerts: edge-triggered, capped, acknowledgeable.

## 5b. Discoverability (when the rules block has not been pasted yet)

Two affordances carry the essentials on the tool surface itself, so a host that
has installed the MCP but not yet completed the checklist is not stranded:

- **Every tool description** ends with the loud-contract line, so an agent that
  calls a mission tool is told to surface the result rather than absorb it.
- **`clock_status` returns `setup_guidance`** while the store cannot answer
  anything useful — naming the next concrete call when there is no root horizon,
  or no mission under it. It goes quiet once a mission exists: this is a setup
  affordance, not a running commentary. It never proposes a horizon date; that
  is the operator's, and inventing one would cross the accounting/estimation
  boundary the plane exists to hold.
- **Resource `horizon://memento/agent-rules`** serves the §3 block below from the
  installed package, so a host can read the rules instead of copying them from
  GitHub. A drift test asserts the shipped copy matches §3.

## 6. Adoption checklist (per host)

1. Configure `store_path` (plane off otherwise — zero behavior change).
2. Register the root horizon and first mission (`clock_register`).
3. Paste the §3 block into the host's rules file.
4. Associate sessions that concern missions; verify a `clock_status` round-trip.
5. Confirm the loud contract: park something without a date in a test session — the
   agent should ask for the date, not silently accept.
```
