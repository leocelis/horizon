"""Tests for the process_turn happy path and core signal correctness."""

from __future__ import annotations

from horizon import FidelityMonitor, TurnResult
from tests.conftest import (
    TIMESTAMP_1,
    TIMESTAMP_2,
    TURN_1_AGENT,
    TURN_1_HUMAN,
    TURN_2_AGENT,
    TURN_2_HUMAN,
)


def test_happy_path(monitor: FidelityMonitor, session_id: str) -> None:
    """process_turn returns a TurnResult with all required fields."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)

    assert isinstance(result, TurnResult)
    assert result.turn_number == 1
    assert 0.0 <= result.fidelity_score <= 1.0
    assert 0.0 <= result.igt_value <= 1.0
    assert 0.0 <= result.divergence_score <= 1.0
    assert 0.0 <= result.twr_value <= 1.0
    assert 0.0 <= result.consistency_score <= 1.0
    assert result.health_status in {"healthy", "degrading", "critical", "converged"}
    assert result.degradation_type in {"none", "recoverable_drift", "irreversible_loss", "both"}
    assert isinstance(result.events, list)
    assert result.conversation_mode in {"execute", "explore", "refine", "learn"}


def test_fidelity_bounds(monitor: FidelityMonitor, session_id: str) -> None:
    """Fidelity score must stay in [0, 1] across multiple turns."""
    from tests.conftest import TURN_3_AGENT, TURN_3_HUMAN

    for human, agent in [
        (TURN_1_HUMAN, TURN_1_AGENT),
        (TURN_2_HUMAN, TURN_2_AGENT),
        (TURN_3_HUMAN, TURN_3_AGENT),
    ]:
        result = monitor.process_turn(session_id, human, agent)
        assert 0.0 <= result.fidelity_score <= 1.0


def test_temporal_signals_with_timestamp(monitor: FidelityMonitor, session_id: str) -> None:
    """Temporal signals are populated when timestamp is provided."""
    r1 = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    # Turn 1: gap_seconds = 0 (no prior turn)
    assert r1.gap_seconds is not None
    assert r1.circadian_factor is not None
    assert 0.0 <= r1.circadian_factor <= 1.0

    r2 = monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_2)
    assert r2.gap_seconds is not None
    assert r2.gap_seconds > 0  # 90 seconds
    assert r2.estimated_retention is not None
    assert 0.0 <= r2.estimated_retention <= 1.0
    assert r2.resumption_cost is not None


def test_temporal_signals_absent_without_timestamp(monitor: FidelityMonitor, session_id: str) -> None:
    """Temporal signals must be None when no timestamp is provided."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    assert result.gap_seconds is None
    assert result.circadian_factor is None
    assert result.estimated_retention is None


def test_causal_reachability_opt_in_with_timestamp(monitor: FidelityMonitor, session_id: str) -> None:
    """Causal reachability (J⁻) is computed only when a timestamp is provided.

    Matches horizon_intent.yaml::constraints[temporal_signals_optional], which
    lists reachable_turns/reachable_fraction among the timestamp-gated signals.
    """
    result_no_ts = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    assert result_no_ts.reachable_turns is None
    assert result_no_ts.reachable_fraction is None

    sid2 = monitor.new_conversation()
    result_ts = monitor.process_turn(
        sid2,
        TURN_1_HUMAN,
        TURN_1_AGENT,
        timestamp="2026-04-22T10:00:00+00:00",
    )
    assert isinstance(result_ts.reachable_turns, int)
    assert isinstance(result_ts.reachable_fraction, float)
    assert 0.0 <= result_ts.reachable_fraction <= 1.0


def test_spatial_signals_with_client_context(monitor: FidelityMonitor, session_id: str) -> None:
    """Spatial signals are populated when client_context is provided."""
    ctx = {"device_type": "mobile", "location_class": "transit", "timezone": "America/New_York"}
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, client_context=ctx)

    assert result.spatial_constraint is not None
    assert result.spatial_constraint.attention_budget == "low"
    assert result.spatial_constraint.max_response_length == 400


def test_first_turn_igt_is_one(monitor: FidelityMonitor, session_id: str) -> None:
    """IGT for the first turn is always 1.0 (all information is new)."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    assert result.igt_value == 1.0


def test_degradation_type_field(monitor: FidelityMonitor, session_id: str) -> None:
    """degradation_type must be one of the four valid literals."""
    valid = {"none", "recoverable_drift", "irreversible_loss", "both"}
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    assert result.degradation_type in valid
