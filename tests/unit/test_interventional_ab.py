"""Unit tests for horizon.analysis.interventional_ab."""

from __future__ import annotations

import pytest

from horizon.analysis.interventional_ab import (
    DEFAULT_ACTIONABLE,
    run_interventional_ab,
    sign_test,
)


def test_sign_test_all_wins() -> None:
    wins, losses, p = sign_test([0.1, 0.2, 0.3, 0.4, 0.5])
    assert (wins, losses) == (5, 0)
    assert p < 0.1


def test_sign_test_tied() -> None:
    wins, losses, p = sign_test([0.1, -0.1])
    assert (wins, losses) == (1, 1)
    assert p == pytest.approx(1.0)


def test_run_interventional_ab_structure() -> None:
    convo = [
        {
            "human": "How do I index this query?",
            "agent_raw": "Add a B-tree index on the filter column.",
            "agent_grounded": None,
            "reference": "Add a B-tree index on the filter column.",
            "timestamp": "2026-01-01T09:00:00+00:00",
        },
        {
            "human": "Still slow on the join.",
            "agent_raw": "Anyway, have you considered switching databases entirely?",
            "agent_grounded": "Index the join keys so the planner can use a hash join.",
            "reference": "Index the join keys so the planner can use a hash join.",
            "timestamp": "2026-01-01T09:03:00+00:00",
        },
    ]
    result = run_interventional_ab([convo], set(DEFAULT_ACTIONABLE))
    assert result["n_conversations"] == 1
    assert result["n_turns"] == 2
    assert -1.0 <= result["mean_control_outcome"] <= 1.0
    assert -1.0 <= result["mean_treatment_outcome"] <= 1.0
    assert set(result["sign_test"]) == {"wins", "losses", "p_value"}
