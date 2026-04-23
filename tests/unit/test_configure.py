"""Tests for monitor.configure() — per-session and global overrides."""

from __future__ import annotations

import pytest

from horizon import Config, ConfigResult, FidelityMonitor, SessionNotFoundError


def test_configure_global_applies_to_existing_sessions() -> None:
    """Global configure() propagates to already-created sessions."""
    monitor = FidelityMonitor()
    sid_a = monitor.new_conversation()
    sid_b = monitor.new_conversation()

    result = monitor.configure(clarification_threshold=0.42)

    assert isinstance(result, ConfigResult)
    assert result.applied.get("clarification_threshold") == 0.42

    assert monitor._sessions[sid_a].config.clarification_threshold == 0.42
    assert monitor._sessions[sid_b].config.clarification_threshold == 0.42


def test_configure_per_session_does_not_leak() -> None:
    """Per-session configure() must not affect other sessions."""
    monitor = FidelityMonitor()
    sid_a = monitor.new_conversation()
    sid_b = monitor.new_conversation()

    monitor.configure(session_id=sid_a, clarification_threshold=0.1)

    assert monitor._sessions[sid_a].config.clarification_threshold == 0.1
    assert (
        monitor._sessions[sid_b].config.clarification_threshold == Config().clarification_threshold
    )


def test_configure_unknown_parameter_returns_warning() -> None:
    """Unknown config parameters produce a ConfigWarning, not an error."""
    monitor = FidelityMonitor()
    result = monitor.configure(not_a_real_parameter=123)

    assert len(result.warnings) >= 1
    messages = [w.parameter for w in result.warnings]
    assert "not_a_real_parameter" in messages


def test_configure_invalid_temporal_threshold_warns() -> None:
    """Negative temporal_desync_threshold_seconds triggers a warning and is not applied."""
    monitor = FidelityMonitor()
    result = monitor.configure(temporal_desync_threshold_seconds=-5)

    assert any(w.parameter == "temporal_desync_threshold_seconds" for w in result.warnings)
    assert (
        monitor._config.temporal_desync_threshold_seconds
        == Config().temporal_desync_threshold_seconds
    )


def test_configure_event_modes_activates_event() -> None:
    """configure(event_modes=...) flips an event from observe to active."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    monitor.configure(
        session_id=sid,
        clarification_threshold=0.0,
        event_modes={"checkpoint.clarification": "active"},
    )
    result = monitor.process_turn(
        sid,
        "How do DNS lookups work?",
        "DNS maps domain names to IP addresses via recursive and iterative queries.",
    )
    clarification_events = [e for e in result.events if e.type == "checkpoint.clarification"]
    assert clarification_events, "clarification event expected with threshold=0.0"
    assert clarification_events[0].active is True


# Intent-pinned alias (see horizon_intent.yaml::interface.tools.configure.test).
test_event_mode_override = test_configure_event_modes_activates_event


def test_configure_returns_config_result_with_applied() -> None:
    """ConfigResult.applied reflects exactly what was passed (minus unknowns)."""
    monitor = FidelityMonitor()
    result = monitor.configure(
        clarification_threshold=0.3,
        verbosity_threshold=0.55,
        unknown_field="ignored",
    )
    assert result.applied["clarification_threshold"] == 0.3
    assert result.applied["verbosity_threshold"] == 0.55
    assert "unknown_field" not in result.applied


def test_configure_missing_session_raises() -> None:
    """configure() with a non-existent session_id raises SessionNotFoundError."""
    monitor = FidelityMonitor()
    with pytest.raises(SessionNotFoundError):
        monitor.configure(session_id="does-not-exist", clarification_threshold=0.1)


def test_configure_flattens_fidelity_weights() -> None:
    """Per HORIZON_TECH_SPEC §2.1, fidelity_weights={...} flattens onto Config fields."""
    monitor = FidelityMonitor()
    result = monitor.configure(
        fidelity_weights={"alpha": 0.42, "lambda_r": 0.21, "lambda_i": 0.33, "beta": 0.17}
    )
    assert monitor._config.alpha == 0.42
    assert monitor._config.lambda_r == 0.21
    assert monitor._config.lambda_i == 0.33
    assert monitor._config.beta == 0.17
    assert "fidelity_weights" not in [w.parameter for w in result.warnings]


def test_configure_flattens_temporal_weights() -> None:
    """temporal_weights={gamma, delta} flattens onto Config fields."""
    monitor = FidelityMonitor()
    monitor.configure(temporal_weights={"gamma": 0.07, "delta": 0.04})
    assert monitor._config.gamma == 0.07
    assert monitor._config.delta == 0.04


def test_configure_flattens_spacetime_coefficients() -> None:
    """spacetime_coefficients={alpha,beta,gamma,delta_st} maps to spacetime_* fields."""
    monitor = FidelityMonitor()
    monitor.configure(
        spacetime_coefficients={"alpha": 2.0, "beta": 1.5, "gamma": 0.8, "delta_st": 0.5}
    )
    assert monitor._config.spacetime_alpha == 2.0
    assert monitor._config.spacetime_beta == 1.5
    assert monitor._config.spacetime_gamma == 0.8
    assert monitor._config.spacetime_delta == 0.5


def test_configure_resolves_logical_embedding_model() -> None:
    """Logical embedding_model values (per intent) resolve to concrete slugs."""
    monitor = FidelityMonitor()
    monitor.configure(embedding_model="local-sentence-transformer")
    assert monitor._config.embedding_model == "all-MiniLM-L6-v2"


def test_configure_custom_embedding_requires_model_path() -> None:
    """embedding_model='custom' without model_path emits a warning."""
    monitor = FidelityMonitor()
    result = monitor.configure(embedding_model="custom")
    assert any(w.parameter == "embedding_model" for w in result.warnings)
