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
