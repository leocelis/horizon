"""Tests for the temporal gap and retention functions."""

from __future__ import annotations

from horizon.spacetime.temporal import (
    classify_gap,
    compute_resumption_cost,
    compute_retention,
    compute_temporal_asymmetry_penalty,
    compute_temporal_gap,
)


def test_temporal_gap_zero_on_first_turn() -> None:
    """First turn has no prior timestamp → gap = 0."""
    gap, gap_class = compute_temporal_gap("2026-04-22T10:00:00+00:00", None)
    assert gap == 0.0
    assert gap_class == "realtime"


def test_temporal_gap_ninety_seconds() -> None:
    gap, gap_class = compute_temporal_gap(
        "2026-04-22T10:01:30+00:00",
        "2026-04-22T10:00:00+00:00",
    )
    assert abs(gap - 90.0) < 0.001
    # 90 seconds is >= 60 seconds → classified as "minutes"
    assert gap_class == "minutes"


def test_classify_gap_all_classes() -> None:
    assert classify_gap(0) == "realtime"
    assert classify_gap(0.5) == "realtime"
    assert classify_gap(30) == "seconds"
    assert classify_gap(600) == "minutes"
    assert classify_gap(7200) == "hours"
    assert classify_gap(86400) == "days"
    assert classify_gap(3 * 86400) == "days"


def test_retention_full_on_zero_gap() -> None:
    assert compute_retention(0, 24.0, 1.0) == 1.0


def test_retention_half_at_half_life() -> None:
    """After 24 hours (h_c=24), retention should be approximately 0.5."""
    h_c = 24.0
    gap = h_c * 3600  # exactly one half-life
    R = compute_retention(gap, h_c, kappa=1.0)
    assert abs(R - 0.5) < 0.01


def test_retention_with_low_kappa() -> None:
    """Low circadian factor reduces retention."""
    R_high = compute_retention(3600, 24.0, kappa=1.0)
    R_low = compute_retention(3600, 24.0, kappa=0.3)
    assert R_low < R_high


def test_retention_clamped() -> None:
    """Retention is always in [0, 1]."""
    assert 0.0 <= compute_retention(1e9, 24.0, 0.3) <= 1.0


def test_resumption_cost_none_for_short_gap() -> None:
    assert compute_resumption_cost(0, 1.0) == "none"
    assert compute_resumption_cost(30, 1.0) == "none"


def test_resumption_cost_extreme_for_long_gap() -> None:
    assert compute_resumption_cost(4 * 86400, 0.01) == "extreme"


def test_temporal_asymmetry_penalty_zero_realtime() -> None:
    """Penalty is 0 for sub-minute gaps."""
    assert compute_temporal_asymmetry_penalty(30, 24.0, 1.0) == 0.0


def test_temporal_asymmetry_penalty_positive_for_large_gap() -> None:
    """Penalty is positive for gaps larger than a minute."""
    delta_tau = compute_temporal_asymmetry_penalty(3600, 24.0, 1.0)
    assert delta_tau > 0.0
    assert delta_tau <= 1.0


def test_no_timestamp_no_temporal_signals() -> None:
    """Constraint: temporal_signals_optional.

    All 4D temporal signals are None when no timestamp is provided.
    Referenced by horizon_intent.yaml::constraints[temporal_signals_optional].test.
    """
    from horizon import FidelityMonitor

    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    result = monitor.process_turn(sid, "hello", "hi there", timestamp=None)

    assert result.gap_seconds is None
    assert result.gap_class is None
    assert result.estimated_retention is None
    assert result.circadian_factor is None
    assert result.temporal_references is None
    assert result.conversation_velocity is None
    assert result.spacetime_interval is None
    assert result.interval_class is None
    assert result.reachable_turns is None
    assert result.reachable_fraction is None

    assert 0.0 <= result.fidelity_score <= 1.0
    temporal_event_types = {
        "signal.temporal_desync",
        "signal.broken_reference",
        "signal.pace_shift",
        "signal.light_cone_collapse",
    }
    for e in result.events:
        assert e.type not in temporal_event_types, (
            f"Temporal event {e.type} fired without timestamp"
        )


def test_retention_monotonic() -> None:
    """Retention is monotonically decreasing as gap_seconds increases.

    Property referenced by horizon_intent.yaml::property_tests.temporal_monotonicity.
    """
    gaps = [0, 60, 600, 3600, 86_400, 3 * 86_400, 7 * 86_400]
    retentions = [compute_retention(g, 24.0, 1.0) for g in gaps]
    for prev, curr in zip(retentions, retentions[1:]):  # noqa: B905 — intentionally different lengths
        assert curr <= prev + 1e-9, (
            f"Retention must be non-increasing: got {retentions}"
        )
    for g in [0, 3600, 86_400, 10 * 86_400]:
        assert compute_temporal_asymmetry_penalty(g, 24.0, 1.0) >= 0.0
