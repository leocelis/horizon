"""Property tests referenced by horizon_intent.yaml.

Invariants that must hold regardless of input, conversation length,
domain, or configuration.
"""

from __future__ import annotations

import pytest

from horizon import FidelityMonitor, SessionNotFoundError


def _run_conversation(
    monitor: FidelityMonitor,
    session_id: str,
    turns: list[tuple[str, str]],
) -> list:
    results = []
    for human, agent in turns:
        results.append(monitor.process_turn(session_id, human_message=human, agent_response=agent))
    return results


def test_deterministic() -> None:
    """Same conversation processed twice in separate sessions produces
    identical metrics and events.

    Sentence-Transformer embeddings are deterministic in eval mode, so
    results are reproducible without an explicit seed.
    """
    monitor_a = FidelityMonitor()
    monitor_b = FidelityMonitor()

    sid_a = monitor_a.new_conversation()
    sid_b = monitor_b.new_conversation()

    turns = [
        (
            "What is the fastest sorting algorithm?",
            "Depends on input; quicksort has good average-case.",
        ),
        ("Why quicksort average-case?", "Because of randomized pivot and partitioning."),
        ("What about worst case?", "O(n^2) with poor pivot selection."),
    ]

    results_a = _run_conversation(monitor_a, sid_a, turns)
    results_b = _run_conversation(monitor_b, sid_b, turns)

    for a, b in zip(results_a, results_b, strict=True):
        assert abs(a.fidelity_score - b.fidelity_score) < 1e-6
        assert abs(a.igt_value - b.igt_value) < 1e-6
        assert abs(a.divergence_score - b.divergence_score) < 1e-6
        assert abs(a.twr_value - b.twr_value) < 1e-6
        assert abs(a.consistency_score - b.consistency_score) < 1e-6
        assert len(a.events) == len(b.events)
        for ea, eb in zip(a.events, b.events, strict=True):
            assert ea.type == eb.type
            assert ea.active == eb.active


def test_fidelity_bounds(monitor: FidelityMonitor, session_id: str) -> None:
    """Fidelity score always in [0, 1]; trajectory length == turns processed."""
    turns = [
        ("hello there", "hi"),
        ("tell me about black holes", "they are regions where gravity is strong"),
        ("what about event horizons?", "they are the boundary of no return"),
        ("so an AI has a similar state?", "in a metaphorical sense; its processing horizon"),
    ]

    for i, (h, a) in enumerate(turns, start=1):
        result = monitor.process_turn(session_id, human_message=h, agent_response=a)
        assert 0.0 <= result.fidelity_score <= 1.0

        trajectory = monitor.get_trajectory(session_id)
        assert len(trajectory.scores) == i
        for s in trajectory.scores:
            assert 0.0 <= s <= 1.0


def test_observe_mode_invariant(monitor: FidelityMonitor, session_id: str) -> None:
    """No event fires with active=True in default config, regardless of input."""
    scenarios = [
        ("hi", "hello"),
        ("x" * 2000, "y" * 2000),
        (
            "completely unrelated topic switch: tell me about cooking",
            "sure, cooking pasta involves boiling water",
        ),
        ("is that right?", "yes."),
    ]

    for h, a in scenarios:
        result = monitor.process_turn(session_id, human_message=h, agent_response=a)
        for event in result.events:
            assert (
                event.active is False
            ), f"Event {event.type} should be inactive in default (observe) mode"


def test_session_not_found_raises(monitor: FidelityMonitor) -> None:
    """process_turn with unknown session_id raises SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError):
        monitor.process_turn(
            "this-session-definitely-does-not-exist",
            human_message="hi",
            agent_response="hello",
        )

    with pytest.raises(SessionNotFoundError):
        monitor.get_trajectory("also-does-not-exist")
