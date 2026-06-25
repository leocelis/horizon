"""Unit tests for horizon.analysis.leading_indicator.

These use hand-constructed trajectories with a *known* ground truth so the
classifier's leading / lagging / no-signal verdicts are checkable exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from horizon.analysis import (
    analyze_leading_indicator,
    analyze_session_leading_indicator,
)

# A 26-turn trajectory with three degradation steps at turns 6, 14, 22 (each a
# 0.20 single-step drop). Drops are spaced 8 turns apart — wider than 2*horizon_k
# — so an event firing 2 turns before a drop is unambiguously *not* trailing the
# previous one. Index 0 == turn 1.
SCORES = (
    [0.95] * 5  # turns 1-5
    + [0.75]  # turn 6  ← drop
    + [0.75] * 7  # turns 7-13
    + [0.55]  # turn 14 ← drop
    + [0.55] * 7  # turns 15-21
    + [0.35]  # turn 22 ← drop
    + [0.35] * 4  # turns 23-26
)

# lead.x fires 2 turns before each drop; lag.y fires 1 turn after each drop;
# insuff.w fires only twice (below the min-samples gate).
EVENTS = [
    (4, "lead.x"),
    (12, "lead.x"),
    (20, "lead.x"),
    (7, "lag.y"),
    (15, "lag.y"),
    (23, "lag.y"),
    (3, "insuff.w"),
    (5, "insuff.w"),
]


def _report():
    return analyze_leading_indicator(
        SCORES, EVENTS, horizon_k=3, drop_threshold=0.05, min_samples=3
    )


def test_degradation_steps_detected() -> None:
    report = _report()
    assert report.n_degradation_steps == 3
    assert report.n_turns_total == 26
    assert report.n_trajectories == 1


def test_leading_event_classified_leading() -> None:
    stats = _report().per_event["lead.x"]
    assert stats.classification == "leading"
    assert stats.n_fired == 3
    assert stats.conditional_rate == 1.0  # every firing precedes a drop
    assert stats.lagging_fraction == 0.0
    assert stats.mean_lead_turns == 2.0  # always exactly 2 turns ahead
    assert stats.lift > 1.0
    assert 0.0 < stats.base_rate < 1.0


def test_lagging_event_classified_lagging() -> None:
    stats = _report().per_event["lag.y"]
    assert stats.classification == "coincident/lagging"
    assert stats.conditional_rate == 0.0  # never precedes a drop
    assert stats.lagging_fraction == 1.0  # always trails one
    assert stats.mean_lead_turns is None
    assert stats.lift == 0.0


def test_insufficient_samples_gated() -> None:
    stats = _report().per_event["insuff.w"]
    assert stats.classification == "insufficient-data"
    assert stats.n_fired == 2


def test_leading_events_helper() -> None:
    report = _report()
    assert report.leading_events() == ["lead.x"]


def test_predictive_recall_for_leading_event() -> None:
    # All three degradation steps are preceded by a lead.x firing within k turns.
    stats = _report().per_event["lead.x"]
    assert stats.predictive_recall == 1.0


def test_input_formats_are_equivalent() -> None:
    """(turn, type) tuples, a {turn: [types]} mapping, and Event-like objects
    must produce identical statistics."""

    @dataclass
    class FakeEvent:
        turn: int
        type: str

    mapping = {
        4: ["lead.x"],
        12: ["lead.x"],
        20: ["lead.x"],
        7: ["lag.y"],
        15: ["lag.y"],
        23: ["lag.y"],
        3: ["insuff.w"],
        5: ["insuff.w"],
    }
    objects = [FakeEvent(t, e) for t, e in EVENTS]

    base = analyze_leading_indicator(SCORES, EVENTS, horizon_k=3).to_dict()
    from_map = analyze_leading_indicator(SCORES, mapping, horizon_k=3).to_dict()
    from_obj = analyze_leading_indicator(SCORES, objects, horizon_k=3).to_dict()

    assert base == from_map == from_obj


def test_multi_trajectory_pooling() -> None:
    report = analyze_leading_indicator(
        [SCORES, SCORES], [EVENTS, EVENTS], horizon_k=3, min_samples=3
    )
    assert report.n_trajectories == 2
    assert report.n_turns_total == 52
    assert report.n_degradation_steps == 6
    # Firings pool across both trajectories.
    assert report.per_event["lead.x"].n_fired == 6
    assert report.per_event["lead.x"].classification == "leading"


def test_empty_and_single_turn_are_safe() -> None:
    empty = analyze_leading_indicator([], [], horizon_k=3)
    assert empty.n_degradation_steps == 0
    assert empty.per_event == {}

    single = analyze_leading_indicator([0.9], [(1, "x")], horizon_k=3)
    assert single.n_degradation_steps == 0


def test_invalid_params_raise() -> None:
    with pytest.raises(ValueError):
        analyze_leading_indicator(SCORES, EVENTS, horizon_k=0)
    with pytest.raises(ValueError):
        analyze_leading_indicator(SCORES, EVENTS, drop_threshold=-0.1)


def test_mismatched_multi_lengths_raise() -> None:
    with pytest.raises(ValueError):
        analyze_leading_indicator([SCORES, SCORES], [EVENTS], horizon_k=3)


def test_to_dict_shape() -> None:
    d = _report().to_dict()
    assert d["horizon_k"] == 3
    assert d["n_degradation_steps"] == 3
    assert set(d["per_event"]) == {"lead.x", "lag.y", "insuff.w"}
    assert d["per_event"]["lead.x"]["classification"] == "leading"


def test_session_wrapper_with_duck_typed_monitor() -> None:
    """analyze_session_leading_indicator should work against any object exposing
    get_trajectory().scores and get_events()."""

    @dataclass
    class FakeEvent:
        turn: int
        type: str

    @dataclass
    class FakeTrajectory:
        scores: list

    class FakeMonitor:
        def get_trajectory(self, session_id: str) -> FakeTrajectory:
            return FakeTrajectory(scores=list(SCORES))

        def get_events(self, session_id: str) -> list:
            return [FakeEvent(t, e) for t, e in EVENTS]

    report = analyze_session_leading_indicator(FakeMonitor(), "sid", horizon_k=3, min_samples=3)
    assert report.per_event["lead.x"].classification == "leading"
