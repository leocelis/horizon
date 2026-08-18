"""Success-metric instrumentation (PRD §9) — the plane judging itself.

Pure arithmetic over caller-supplied fires and recorded externally-visible
events; no prediction, no ambient clock, no LLM. These functions are
deliberately NOT auto-embedded into ``engine.evaluate()`` /
``signals.evaluate_signals()`` — like ``propose.breakeven_proposal()``,
they are explicit, separately-callable reads over records the caller
already has (a sequence of past ``SignalReport``s, a store's events),
mirroring money.py's automatic-vs-explicit split (money.py module
docstring). Callers wire the result into clock_status's payload
themselves; this module supplies the arithmetic only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from horizon_monitor.memento.models import ClockEvent, EventKind

_EXTERNALLY_VISIBLE_KINDS = (EventKind.PROGRESS, EventKind.ARTIFACT)


@dataclass(frozen=True)
class TimeToNextAction:
    """One fired signal's distance to the next recorded externally-visible
    event on the same item — the primary success metric (PRD §9): "the
    interval between a clock event ... and the next recorded externally
    visible action on that mission"."""

    item_id: str
    signal_type: str
    fired_at: datetime
    next_action_at: datetime | None
    interval_days: int | None
    """None when no externally-visible event has been recorded yet since
    the fire — never estimated, never a placeholder duration
    (facts_are_caller_provided)."""

    derivation: str

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "signal_type": self.signal_type,
            "fired_at": self.fired_at.isoformat(),
            "next_action_at": self.next_action_at.isoformat() if self.next_action_at else None,
            "interval_days": self.interval_days,
            "derivation": self.derivation,
        }


def time_to_next_action(
    fired_signals: tuple[tuple[str, str, datetime], ...],
    events_by_item: dict[str, tuple[ClockEvent, ...]],
) -> tuple[TimeToNextAction, ...]:
    """``fired_signals`` is a caller-supplied sequence of
    ``(item_id, signal_type, fired_at)`` — the caller's own record of past
    ``Signal`` fires (from ``SignalReport.fired`` across turns, persisted
    by the caller; this module reads no store). For each, finds the
    earliest recorded PROGRESS/ARTIFACT event on that item at-or-after
    ``fired_at``. This is the queryable metric test plan R-3 requires;
    its *evaluation* against a baseline (did the plane actually shorten
    this interval) is the operational exercise the PRD names, not
    something a unit test can assert.
    """
    results: list[TimeToNextAction] = []
    for item_id, signal_type, fired_at in fired_signals:
        events = events_by_item.get(item_id, ())
        candidates = sorted(
            e.valid_time
            for e in events
            if e.kind in _EXTERNALLY_VISIBLE_KINDS and e.valid_time >= fired_at
        )
        next_action_at = candidates[0] if candidates else None
        interval_days = (next_action_at.date() - fired_at.date()).days if next_action_at else None
        derivation = (
            f"earliest PROGRESS/ARTIFACT event on {item_id!r} at-or-after fired_at"
            f"({fired_at.date()}) = "
            f"{next_action_at.date().isoformat() if next_action_at else 'none recorded yet'}"
        )
        results.append(
            TimeToNextAction(
                item_id=item_id,
                signal_type=signal_type,
                fired_at=fired_at,
                next_action_at=next_action_at,
                interval_days=interval_days,
                derivation=derivation,
            )
        )
    return tuple(results)


@dataclass(frozen=True)
class AlarmKPIs:
    """PRD §9 secondary metric: "fires per associated-turn-hour; % of
    turns with more than one new fire; stale-ack count" — the alarm
    philosophy's own budget, computed over caller-supplied per-turn
    history."""

    turns_evaluated: int
    fires_per_turn: float
    pct_turns_with_multiple_new_fires: float
    """Structurally 0.0 whenever every turn respected
    config.per_turn_fire_cap == 1 (memento_signals_intent.yaml::ack_and_cap,
    test plan G-5) — a nonzero value here means the cap was raised above 1
    or violated, never a tuning target on its own."""

    stale_ack_count: int
    derivation: str

    def to_dict(self) -> dict:
        return {
            "turns_evaluated": self.turns_evaluated,
            "fires_per_turn": self.fires_per_turn,
            "pct_turns_with_multiple_new_fires": self.pct_turns_with_multiple_new_fires,
            "stale_ack_count": self.stale_ack_count,
            "derivation": self.derivation,
        }


def alarm_kpis(fired_counts_per_turn: tuple[int, ...], stale_ack_count: int) -> AlarmKPIs:
    """``fired_counts_per_turn`` is a caller-supplied sequence of
    ``len(SignalReport.fired)`` values, one per associated turn already
    evaluated. ``stale_ack_count`` is the caller's own count of STALE
    fires observed over the same window. Pure arithmetic; an empty
    sequence returns zeros rather than an invented rate."""
    turns = len(fired_counts_per_turn)
    if turns == 0:
        return AlarmKPIs(
            turns_evaluated=0,
            fires_per_turn=0.0,
            pct_turns_with_multiple_new_fires=0.0,
            stale_ack_count=stale_ack_count,
            derivation="no turns evaluated yet",
        )
    total_fires = sum(fired_counts_per_turn)
    multi_fire_turns = sum(1 for c in fired_counts_per_turn if c > 1)
    fires_per_turn = total_fires / turns
    pct_multi = multi_fire_turns / turns
    derivation = (
        f"fires_per_turn = total_fires({total_fires}) / turns({turns}) = {round(fires_per_turn, 6)}; "
        f"pct_turns_with_multiple_new_fires = multi_fire_turns({multi_fire_turns}) / turns({turns}) "
        f"= {round(pct_multi, 6)}"
    )
    return AlarmKPIs(
        turns_evaluated=turns,
        fires_per_turn=fires_per_turn,
        pct_turns_with_multiple_new_fires=pct_multi,
        stale_ack_count=stale_ack_count,
        derivation=derivation,
    )
