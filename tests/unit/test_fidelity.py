"""Tests for fidelity computation and health status."""

from __future__ import annotations

import pytest

from horizon import Config
from horizon.engines.fidelity import (
    compute_dynamic_fidelity,
    compute_health,
    compute_snapshot_fidelity,
)
from horizon.session import Session


@pytest.fixture
def config() -> Config:
    return Config()


def test_snapshot_fidelity_bounds(config: Config) -> None:
    """Snapshot fidelity must be in [0, 1]."""
    for igt in [0.0, 0.5, 1.0]:
        for djs in [0.0, 0.3, 0.9]:
            score = compute_snapshot_fidelity(igt, djs, 0.1, 0.8, config)
            assert 0.0 <= score <= 1.0


def test_snapshot_fidelity_higher_with_better_signals(config: Config) -> None:
    """Better signals (high IGT, low D_JS, low TWR, high consistency) → higher fidelity."""
    good = compute_snapshot_fidelity(1.0, 0.0, 0.0, 1.0, config)
    bad = compute_snapshot_fidelity(0.0, 1.0, 1.0, 0.0, config)
    assert good > bad


def test_dynamic_fidelity_increases_with_igt(config: Config) -> None:
    """High IGT should push fidelity up from the baseline."""
    f_high = compute_dynamic_fidelity(0.5, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0, config)
    f_low = compute_dynamic_fidelity(0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, config)
    assert f_high > f_low


def test_dynamic_fidelity_decreases_with_irreversible_loss(config: Config) -> None:
    """Context eviction (irreversible) should push fidelity down."""
    f_no_loss = compute_dynamic_fidelity(0.7, 0.5, 0.0, 0.0, 0.0, 0.0, 1.0, config)
    f_with_loss = compute_dynamic_fidelity(0.7, 0.5, 0.0, 0.0, 0.5, 0.0, 1.0, config)
    assert f_with_loss < f_no_loss


def test_health_healthy_initial(config: Config) -> None:
    """A fresh session with one turn should be healthy."""
    session = Session(session_id="test", config=config)
    session.fidelity_trajectory.append(0.8)
    health = compute_health(session, 0.8, 0.0, config)
    assert health == "healthy"


def test_health_critical_when_low_fidelity_declining(config: Config) -> None:
    """Critical when fidelity < 0.3 and monotonically declining."""
    session = Session(session_id="test", config=config)
    session.fidelity_trajectory = [0.5, 0.4, 0.3, 0.25]
    health = compute_health(session, 0.25, 0.0, config)
    assert health == "critical"
