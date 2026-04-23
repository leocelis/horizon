"""Tests for get_trajectory() return shape and field correctness."""

from __future__ import annotations

import pytest

from horizon import FidelityMonitor, FidelityTrajectory
from tests.conftest import (
    TIMESTAMP_1, TIMESTAMP_2, TIMESTAMP_3,
    TURN_1_AGENT, TURN_1_HUMAN,
    TURN_2_AGENT, TURN_2_HUMAN,
    TURN_3_AGENT, TURN_3_HUMAN,
)


def test_full_trajectory(monitor: FidelityMonitor, session_id: str) -> None:
    """Trajectory returns correct shape after multiple turns."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_2)
    monitor.process_turn(session_id, TURN_3_HUMAN, TURN_3_AGENT, timestamp=TIMESTAMP_3)

    traj = monitor.get_trajectory(session_id)

    assert isinstance(traj, FidelityTrajectory)
    assert traj.session_id == session_id
    assert traj.turn_count == 3
    assert len(traj.scores) == 3
    assert len(traj.timestamps) == 3
    assert len(traj.gap_durations) == 3
    assert traj.gap_durations[0] is None  # no prior turn for turn 1


def test_trajectory_scores_in_bounds(monitor: FidelityMonitor, session_id: str) -> None:
    """All trajectory fidelity scores must be in [0, 1]."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT)

    traj = monitor.get_trajectory(session_id)
    for score in traj.scores:
        assert 0.0 <= score <= 1.0


def test_trajectory_peak_and_current(monitor: FidelityMonitor, session_id: str) -> None:
    """peak_fidelity >= current_fidelity in a declining conversation."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT)

    traj = monitor.get_trajectory(session_id)
    assert traj.peak_fidelity >= 0.0
    assert traj.current_fidelity >= 0.0
    assert traj.peak_fidelity >= traj.current_fidelity or traj.peak_fidelity == traj.current_fidelity


def test_trajectory_health_status_valid(monitor: FidelityMonitor, session_id: str) -> None:
    """health_status must be one of the four valid literals."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    traj = monitor.get_trajectory(session_id)
    assert traj.health_status in {"healthy", "degrading", "critical", "converged"}


def test_gap_durations_non_negative(monitor: FidelityMonitor, session_id: str) -> None:
    """Non-None gap durations must be non-negative."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_2)

    traj = monitor.get_trajectory(session_id)
    for gap in traj.gap_durations:
        if gap is not None:
            assert gap >= 0.0
