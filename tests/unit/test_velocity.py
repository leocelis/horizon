"""Tests for conversation velocity and acceleration."""

from __future__ import annotations

import numpy as np
import pytest

from horizon.spacetime.velocity import compute_acceleration, compute_velocity


@pytest.fixture
def unit_vector_a() -> np.ndarray:
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def unit_vector_b() -> np.ndarray:
    v = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    return v / np.linalg.norm(v)


@pytest.fixture
def unit_vector_a_copy() -> np.ndarray:
    v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    return v / np.linalg.norm(v)


def test_velocity_none_on_zero_gap(unit_vector_a, unit_vector_b) -> None:
    """No elapsed time → no velocity."""
    assert compute_velocity(unit_vector_b, unit_vector_a, 0.0) is None


def test_velocity_positive_for_displacement(unit_vector_a, unit_vector_b) -> None:
    """Orthogonal vectors produce positive velocity."""
    v = compute_velocity(unit_vector_b, unit_vector_a, 90.0)
    assert v is not None
    assert v > 0.0


def test_velocity_zero_for_identical_vectors(unit_vector_a, unit_vector_a_copy) -> None:
    """Identical embeddings → displacement = 0 → velocity = 0."""
    v = compute_velocity(unit_vector_a_copy, unit_vector_a, 90.0)
    assert v is not None
    assert abs(v) < 1e-6


def test_acceleration_none_when_prev_velocity_none(unit_vector_a, unit_vector_b) -> None:
    v = compute_velocity(unit_vector_b, unit_vector_a, 60.0)
    acc = compute_acceleration(v, None)
    assert acc is None


def test_acceleration_positive_when_speeding_up() -> None:
    acc = compute_acceleration(0.01, 0.005)
    assert acc is not None
    assert acc > 0.0


def test_acceleration_negative_when_slowing_down() -> None:
    acc = compute_acceleration(0.002, 0.01)
    assert acc is not None
    assert acc < 0.0


def test_velocity_consistency(unit_vector_a, unit_vector_b) -> None:
    """Velocity doubles when gap halves for same displacement."""
    v1 = compute_velocity(unit_vector_b, unit_vector_a, 60.0)
    v2 = compute_velocity(unit_vector_b, unit_vector_a, 30.0)
    assert v1 is not None and v2 is not None
    assert abs(v2 / v1 - 2.0) < 0.01


def test_velocity_derivation(unit_vector_a, unit_vector_b) -> None:
    """Property referenced by horizon_intent.yaml::property_tests.velocity_consistency.

    conversation_velocity == semantic_displacement / proper_time_delta
    (where semantic_displacement = 1 - cos_sim)
    acceleration == (v_t - v_{t-1})
    """
    cos_sim = float(np.dot(unit_vector_b, unit_vector_a))
    displacement = max(0.0, 1.0 - cos_sim)
    gap = 60.0
    v_expected = displacement / gap
    v_actual = compute_velocity(unit_vector_b, unit_vector_a, gap)
    assert v_actual is not None
    assert abs(v_actual - v_expected) < 1e-6

    prev_v = 0.005
    acc = compute_acceleration(v_actual, prev_v)
    assert acc is not None
    assert abs(acc - (v_actual - prev_v)) < 1e-9
