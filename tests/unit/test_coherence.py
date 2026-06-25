"""Tests for bipredictability (Tier 1 coherence)."""

from __future__ import annotations

import numpy as np

from horizon.engines.coherence import compute_bipredictability


def make_unit(v: list[float]) -> np.ndarray:
    arr = np.array(v, dtype=np.float32)
    return arr / np.linalg.norm(arr)


def test_coherent_when_no_history() -> None:
    """First turn (no history) returns 1.0 by definition."""
    h = make_unit([1.0, 0.0])
    a = make_unit([0.9, 0.1])
    score = compute_bipredictability(h, a, None)
    assert score == 1.0


def test_high_coherence_for_aligned_triplet() -> None:
    """Three similar vectors should produce a score close to 1.0."""
    v = make_unit([1.0, 1.0, 0.0])
    score = compute_bipredictability(v, v, v)
    assert score > 0.9


def test_low_coherence_for_divergent_triplet() -> None:
    """Opposing vectors should produce a lower score."""
    h = make_unit([1.0, 0.0])
    a = make_unit([-1.0, 0.0])
    hist = make_unit([0.0, 1.0])
    score = compute_bipredictability(h, a, hist)
    assert score < 0.5


def test_score_in_bounds() -> None:
    """Score must always be in [0, 1]."""
    for _ in range(20):
        h = make_unit(np.random.randn(16).tolist())
        a = make_unit(np.random.randn(16).tolist())
        hist = make_unit(np.random.randn(16).tolist())
        score = compute_bipredictability(h, a, hist)
        assert 0.0 <= score <= 1.0
