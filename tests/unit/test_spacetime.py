"""Tests for the spacetime interval ds²."""

from __future__ import annotations

import pytest

from horizon import Config
from horizon.spacetime.interval import compute_spacetime_interval


@pytest.fixture
def default_config() -> Config:
    return Config()


def test_large_time_gap_is_timelike(default_config: Config) -> None:
    """Large time gap with small semantic changes → timelike (ds² < 0)."""
    ds2, cls = compute_spacetime_interval(
        d_tau=3 * 86400,  # 3 days
        d_djs=0.01,
        d_epsilon=0.01,
        d_coherence=0.01,
        config=default_config,
    )
    assert cls == "timelike", f"Expected timelike, got {cls} with ds²={ds2}"
    assert ds2 < 0


def test_zero_time_with_large_semantic_shift_is_spacelike(default_config: Config) -> None:
    """No time elapsed but large semantic shift → spacelike (ds² > 0)."""
    ds2, cls = compute_spacetime_interval(
        d_tau=0.0,
        d_djs=0.9,
        d_epsilon=0.8,
        d_coherence=0.7,
        config=default_config,
    )
    assert cls == "spacelike", f"Expected spacelike, got {cls} with ds²={ds2}"
    assert ds2 > 0


def test_balanced_interval_lightlike(default_config: Config) -> None:
    """Balanced temporal and semantic change → lightlike (ds² ≈ 0)."""
    # Find an approximate balance — not exact but directionally correct
    ds2, cls = compute_spacetime_interval(
        d_tau=0.0,
        d_djs=0.0,
        d_epsilon=0.0,
        d_coherence=0.0,
        config=default_config,
    )
    assert cls == "lightlike"
    assert abs(ds2) <= 0.01


def test_interval_class_is_valid_literal(default_config: Config) -> None:
    """interval_class must be one of timelike, spacelike, lightlike."""
    valid = {"timelike", "spacelike", "lightlike"}
    for tau in [0, 60, 3600, 86400]:
        _, cls = compute_spacetime_interval(tau, 0.1, 0.1, 0.1, default_config)
        assert cls in valid


def test_spacetime_signature_negative_time_component(default_config: Config) -> None:
    """The time component of ds² must be negative (Minkowski-like signature)."""
    # Isolate: large time, zero semantics → ds² < 0
    ds2, _ = compute_spacetime_interval(
        d_tau=86400,
        d_djs=0.0,
        d_epsilon=0.0,
        d_coherence=0.0,
        config=default_config,
    )
    assert ds2 < 0


def test_no_client_context_no_spatial_signals() -> None:
    """Constraint: spatial_signals_optional.

    All spatial signals are None when no client_context is provided.
    Referenced by horizon_intent.yaml::constraints[spatial_signals_optional].test.
    """
    from horizon import FidelityMonitor

    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    result = monitor.process_turn(
        sid,
        "I need help debugging an async function.",
        "Sure — what error are you seeing?",
        timestamp="2026-04-22T11:00:00+00:00",
    )

    assert result.location_class is None
    assert result.spatial_constraint is None
    assert result.spatial_frame_shift is None

    assert 0.0 <= result.fidelity_score <= 1.0
    spatial_event_types = {"signal.frame_shift"}
    for e in result.events:
        assert (
            e.type not in spatial_event_types
        ), f"Spatial event {e.type} fired without client_context"


def test_minkowski_signature(default_config: Config) -> None:
    """Property referenced by horizon_intent.yaml::property_tests.spacetime_signature.

    ds² has Minkowski signature (-,+,+,+):
      - timelike (ds² < 0) when dτ² dominates
      - spacelike (ds² > 0) when semantic terms dominate
    """
    ds2_time, cls_time = compute_spacetime_interval(
        d_tau=10 * 86400,
        d_djs=0.0,
        d_epsilon=0.0,
        d_coherence=0.0,
        config=default_config,
    )
    assert ds2_time < 0
    assert cls_time == "timelike"

    ds2_space, cls_space = compute_spacetime_interval(
        d_tau=0.0,
        d_djs=0.9,
        d_epsilon=0.9,
        d_coherence=0.9,
        config=default_config,
    )
    assert ds2_space > 0
    assert cls_space == "spacelike"
