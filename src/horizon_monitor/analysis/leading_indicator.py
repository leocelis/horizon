"""Leading-indicator analysis for Horizon events.

A monitor that only *confirms* damage after it happens (a lagging indicator) is
worth far less than one that *predicts* it (a leading indicator). This module
answers, for each event type, the question the red-team review (Fix 3) asked:

    When an event fires at turn *t*, does conversation fidelity degrade in the
    look-ahead window (t, t+k] — and how far ahead (lead time)? Or does the event
    only co-occur with / trail a drop that already happened (lagging)?

It is a pure, offline computation over data Horizon already records: the per-turn
fidelity trajectory and the event log. No model calls, no embeddings, no runtime
cost. It does **not** prove the value of *acting* on events (that needs the
interventional A/B in ``scripts/run_interventional_ab.py``); it characterises
whether the signal *anticipates* degradation at all.

Definitions (all turn indices are 1-based, matching ``Event.turn``):

  * ``fidelity_scores[i]`` is the fidelity at turn ``i+1`` (index 0 = turn 1).
  * A **degradation step** occurs at turn ``t`` (t >= 2) when
    ``fidelity[t] <= fidelity[t-1] - drop_threshold``.
  * An event firing at turn ``t`` **precedes** a drop if a degradation step
    occurs in ``(t, t+k]``; its **lead time** is the distance to the first such
    step. It **lags** a drop if a degradation step occurred in ``[t-k, t]``.

The classification per event type:

  * ``insufficient-data`` — fewer than ``min_samples`` firings.
  * ``leading``           — fires before drops more than chance, and anticipates
                            more than it trails.
  * ``coincident/lagging``— predicts no better than (or trails) drops it follows.
  * ``no-signal``         — firing tells you nothing about future drops.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

# Default look-ahead window (turns) and minimum single-step fidelity drop that
# counts as degradation. These are deliberately conservative; callers tune them.
DEFAULT_HORIZON_K = 3
DEFAULT_DROP_THRESHOLD = 0.05
DEFAULT_MIN_SAMPLES = 3
# A firing predicts "better than chance" when its hit-rate beats the base rate by
# this relative margin.
DEFAULT_LEADING_LIFT = 1.1


@runtime_checkable
class _EventLike(Protocol):
    """Anything with a 1-based ``turn`` and a string ``type`` (e.g. horizon.Event)."""

    turn: int
    type: str


# An event input may be Horizon Event objects, (turn, type) tuples, or a
# {turn: [type, ...]} mapping.
EventInput = Iterable["_EventLike"] | Iterable[tuple[int, str]] | Mapping[int, Sequence[str]]


@dataclass(frozen=True)
class EventLeadStats:
    """Leading-indicator statistics for a single event type."""

    event_type: str
    n_fired: int
    """Number of eligible firings (a firing is eligible when it has a full
    look-ahead window, i.e. turn <= n_turns - 1)."""

    base_rate: float
    """P(a degradation step occurs in the next k turns) over all eligible turns."""

    conditional_rate: float
    """P(degradation step in next k turns | event fired) — predictive precision."""

    lift: float
    """conditional_rate / base_rate. > 1 means the event anticipates drops."""

    predictive_recall: float
    """Fraction of degradation steps that were preceded by this event within k turns."""

    lagging_fraction: float
    """Fraction of firings that *follow* a drop within the prior k turns."""

    mean_lead_turns: float | None
    """Mean turns between a firing and the future drop it precedes (None if never)."""

    classification: str
    """One of: leading | coincident/lagging | no-signal | insufficient-data."""


@dataclass(frozen=True)
class LeadingIndicatorReport:
    """Per-event-type leading-indicator analysis over one or more trajectories."""

    horizon_k: int
    drop_threshold: float
    n_turns_total: int
    n_trajectories: int
    n_degradation_steps: int
    per_event: dict[str, EventLeadStats] = field(default_factory=dict)

    def leading_events(self) -> list[str]:
        """Event types classified as leading indicators, sorted by lift desc."""
        leading = [s for s in self.per_event.values() if s.classification == "leading"]
        leading.sort(key=lambda s: s.lift, reverse=True)
        return [s.event_type for s in leading]

    def to_dict(self) -> dict:
        return {
            "horizon_k": self.horizon_k,
            "drop_threshold": self.drop_threshold,
            "n_turns_total": self.n_turns_total,
            "n_trajectories": self.n_trajectories,
            "n_degradation_steps": self.n_degradation_steps,
            "per_event": {
                etype: {
                    "n_fired": s.n_fired,
                    "base_rate": round(s.base_rate, 4),
                    "conditional_rate": round(s.conditional_rate, 4),
                    "lift": round(s.lift, 4),
                    "predictive_recall": round(s.predictive_recall, 4),
                    "lagging_fraction": round(s.lagging_fraction, 4),
                    "mean_lead_turns": (
                        None if s.mean_lead_turns is None else round(s.mean_lead_turns, 3)
                    ),
                    "classification": s.classification,
                }
                for etype, s in self.per_event.items()
            },
        }


def _normalize_events(events: EventInput, n_turns: int) -> dict[int, set[str]]:
    """Collapse any supported event input into {turn: {event_type, ...}}.

    Turns outside ``[1, n_turns]`` are dropped (defensive)."""
    by_turn: dict[int, set[str]] = {}

    def add(turn: int, etype: str) -> None:
        if 1 <= turn <= n_turns:
            by_turn.setdefault(int(turn), set()).add(str(etype))

    if isinstance(events, Mapping):
        for turn, etypes in events.items():
            for etype in etypes:
                add(int(turn), etype)
        return by_turn

    for item in events:
        if isinstance(item, tuple):
            turn, etype = item
            add(int(turn), etype)
        else:  # _EventLike (duck-typed)
            add(int(item.turn), item.type)
    return by_turn


def _degradation_steps(scores: Sequence[float], drop_threshold: float) -> set[int]:
    """Return the set of 1-based turns t (t >= 2) where a degradation step starts."""
    steps: set[int] = set()
    for i in range(1, len(scores)):
        if scores[i] <= scores[i - 1] - drop_threshold:
            steps.add(i + 1)  # 1-based turn number
    return steps


def _analyze_one(
    scores: Sequence[float],
    by_turn: Mapping[int, set[str]],
    event_types: Sequence[str],
    k: int,
    drop_threshold: float,
) -> tuple[dict[str, dict], int, int, int]:
    """Accumulate raw counts for a single trajectory.

    Returns (acc, n_eligible_turns, n_eligible_drop_turns, n_degradation_steps).
    """
    n = len(scores)
    steps = _degradation_steps(scores, drop_threshold)

    # A turn is eligible (for base-rate / firing prediction) when it has at least
    # one future turn to look at.
    eligible_turns = [t for t in range(1, n + 1) if t <= n - 1]

    def future_drop(t: int) -> int | None:
        """First degradation-step turn in (t, t+k], or None."""
        for j in range(t + 1, min(n, t + k) + 1):
            if j in steps:
                return j
        return None

    def past_drop(t: int) -> bool:
        """Any degradation step in [t-k, t]."""
        return any(j in steps for j in range(max(2, t - k), t + 1))

    n_eligible = len(eligible_turns)
    n_eligible_with_future_drop = sum(1 for t in eligible_turns if future_drop(t) is not None)

    acc: dict[str, dict] = {
        etype: {
            "n_fired": 0,
            "precedes": 0,
            "lags": 0,
            "lead_sum": 0,
            "lead_n": 0,
        }
        for etype in event_types
    }

    for etype in event_types:
        a = acc[etype]
        for t in eligible_turns:
            if etype not in by_turn.get(t, ()):  # event did not fire this turn
                continue
            a["n_fired"] += 1
            fd = future_drop(t)
            if fd is not None:
                a["precedes"] += 1
                a["lead_sum"] += fd - t
                a["lead_n"] += 1
            if past_drop(t):
                a["lags"] += 1

    # Predictive recall needs, per degradation step, whether an event of this type
    # fired in the preceding window [step-k, step-1]. Compute per event type.
    for etype in event_types:
        covered = 0
        for step_turn in steps:
            window = range(max(1, step_turn - k), step_turn)
            if any(etype in by_turn.get(w, ()) for w in window):
                covered += 1
        acc[etype]["recall_covered"] = covered

    return acc, n_eligible, n_eligible_with_future_drop, len(steps)


def analyze_leading_indicator(
    trajectories: Sequence[float] | Sequence[Sequence[float]],
    events: EventInput | Sequence[EventInput],
    *,
    event_types: Sequence[str] | None = None,
    horizon_k: int = DEFAULT_HORIZON_K,
    drop_threshold: float = DEFAULT_DROP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    leading_lift: float = DEFAULT_LEADING_LIFT,
) -> LeadingIndicatorReport:
    """Compute leading-indicator statistics per event type.

    Args:
        trajectories: a single fidelity-score list, or a list of such lists when
            pooling several conversations.
        events: matching event input. When ``trajectories`` is a list-of-lists,
            ``events`` must be a parallel sequence of event inputs (one per
            trajectory). Otherwise a single event input.
        event_types: restrict to these event types; defaults to every type seen.
        horizon_k: look-ahead window in turns.
        drop_threshold: minimum single-step fidelity drop counted as degradation.
        min_samples: minimum firings before a type is classified (else
            ``insufficient-data``).
        leading_lift: relative margin over base rate to count as "better than chance".

    Returns:
        A :class:`LeadingIndicatorReport`.
    """
    if horizon_k < 1:
        raise ValueError("horizon_k must be >= 1")
    if drop_threshold < 0:
        raise ValueError("drop_threshold must be >= 0")

    # Normalize to parallel lists of (scores, events).
    multi = bool(trajectories) and isinstance(trajectories[0], (list, tuple))
    if multi:
        traj_list: list[Sequence[float]] = list(trajectories)  # type: ignore[arg-type]
        if not isinstance(events, Sequence) or len(events) != len(traj_list):
            raise ValueError(
                "When passing multiple trajectories, `events` must be a parallel "
                "sequence of the same length."
            )
        events_list = list(events)
    else:
        traj_list = [trajectories]  # type: ignore[list-item]
        events_list = [events]

    normalized = [
        _normalize_events(ev, len(sc)) for sc, ev in zip(traj_list, events_list, strict=False)
    ]

    # Discover event types if not given.
    if event_types is None:
        discovered: set[str] = set()
        for by_turn in normalized:
            for etypes in by_turn.values():
                discovered.update(etypes)
        event_types = sorted(discovered)

    totals: dict[str, dict] = {
        etype: {
            "n_fired": 0,
            "precedes": 0,
            "lags": 0,
            "lead_sum": 0,
            "lead_n": 0,
            "recall_covered": 0,
        }
        for etype in event_types
    }
    n_eligible_total = 0
    n_eligible_drop_total = 0
    n_steps_total = 0
    n_turns_total = 0

    for sc, by_turn in zip(traj_list, normalized, strict=False):
        n_turns_total += len(sc)
        acc, n_elig, n_elig_drop, n_steps = _analyze_one(
            sc, by_turn, event_types, horizon_k, drop_threshold
        )
        n_eligible_total += n_elig
        n_eligible_drop_total += n_elig_drop
        n_steps_total += n_steps
        for etype in event_types:
            for key, val in acc[etype].items():
                totals[etype][key] += val

    base_rate = (n_eligible_drop_total / n_eligible_total) if n_eligible_total else 0.0

    per_event: dict[str, EventLeadStats] = {}
    for etype in event_types:
        t = totals[etype]
        n_fired = t["n_fired"]
        conditional = (t["precedes"] / n_fired) if n_fired else 0.0
        lift = (
            (conditional / base_rate)
            if base_rate > 0
            else (0.0 if conditional == 0 else float("inf"))
        )
        recall = (t["recall_covered"] / n_steps_total) if n_steps_total else 0.0
        lagging_fraction = (t["lags"] / n_fired) if n_fired else 0.0
        mean_lead = (t["lead_sum"] / t["lead_n"]) if t["lead_n"] else None

        classification = _classify(
            n_fired=n_fired,
            conditional=conditional,
            base_rate=base_rate,
            lagging_fraction=lagging_fraction,
            min_samples=min_samples,
            leading_lift=leading_lift,
        )

        per_event[etype] = EventLeadStats(
            event_type=etype,
            n_fired=n_fired,
            base_rate=base_rate,
            conditional_rate=conditional,
            lift=lift,
            predictive_recall=recall,
            lagging_fraction=lagging_fraction,
            mean_lead_turns=mean_lead,
            classification=classification,
        )

    return LeadingIndicatorReport(
        horizon_k=horizon_k,
        drop_threshold=drop_threshold,
        n_turns_total=n_turns_total,
        n_trajectories=len(traj_list),
        n_degradation_steps=n_steps_total,
        per_event=per_event,
    )


def _classify(
    *,
    n_fired: int,
    conditional: float,
    base_rate: float,
    lagging_fraction: float,
    min_samples: int,
    leading_lift: float,
) -> str:
    if n_fired < min_samples:
        return "insufficient-data"
    # Does the firing predict future drops better than chance?
    beats_chance = conditional > 0 and (
        base_rate == 0.0 and conditional > 0 or conditional >= base_rate * leading_lift
    )
    if not beats_chance:
        # No predictive edge. If it mostly trails drops, call it lagging.
        return "coincident/lagging" if lagging_fraction > max(base_rate, 0.5) else "no-signal"
    # Predicts future drops. Leading only if it anticipates more than it trails.
    if lagging_fraction > conditional:
        return "coincident/lagging"
    return "leading"


def analyze_session_leading_indicator(
    monitor: object,
    session_id: str,
    *,
    horizon_k: int = DEFAULT_HORIZON_K,
    drop_threshold: float = DEFAULT_DROP_THRESHOLD,
    min_samples: int = DEFAULT_MIN_SAMPLES,
) -> LeadingIndicatorReport:
    """Convenience wrapper: pull a session's trajectory + events from a monitor.

    ``monitor`` must expose ``get_trajectory(session_id).scores`` and
    ``get_events(session_id)`` returning objects with ``.turn`` and ``.type``
    (the public Horizon ``FidelityMonitor`` API). Kept duck-typed so this module
    has no hard import dependency on the monitor.
    """
    trajectory = monitor.get_trajectory(session_id)  # type: ignore[attr-defined]
    events = monitor.get_events(session_id)  # type: ignore[attr-defined]
    return analyze_leading_indicator(
        list(trajectory.scores),
        events,
        horizon_k=horizon_k,
        drop_threshold=drop_threshold,
        min_samples=min_samples,
    )
