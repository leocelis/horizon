"""Event evaluation engine — all 14 signal conditions.

Events are emitted in observe mode by default. Each event carries:
- type: the signal name (e.g. 'checkpoint.clarification')
- active: True only when the event type is in active mode via configure()
- confidence: [0, 1] signal strength
- suggested_behavior: plain-English instruction for the agent controller
- metadata: signal-specific auxiliary data
"""

from __future__ import annotations

from horizon.config import Config
from horizon.models import Event, TurnResult
from horizon.session import Session, TurnState


def evaluate_events(
    session: Session,
    turn: TurnState,
    result: TurnResult,
    config: Config,
) -> list[Event]:
    """Evaluate all 14 event conditions and return the fired events."""
    events: list[Event] = []

    def emit(event_type: str, confidence: float, behavior: str, **meta: object) -> None:
        events.append(
            Event(
                type=event_type,
                active=config.event_is_active(event_type),
                confidence=max(0.0, min(1.0, confidence)),
                turn=turn.turn_number,
                suggested_behavior=behavior,
                mode=result.conversation_mode,
                metadata=meta,
            )
        )

    # 1. checkpoint.clarification
    if result.divergence_score > config.clarification_threshold:
        emit(
            "checkpoint.clarification",
            result.divergence_score,
            "Pause and ask a targeted question before continuing",
            divergence_score=result.divergence_score,
        )

    # 2. checkpoint.comprehension
    if (
        result.igt_trend < -0.05
        and session.turn_count >= config.convergence_window
    ):
        emit(
            "checkpoint.comprehension",
            abs(result.igt_trend),
            "Summarise your current understanding and ask for confirmation",
            igt_trend=result.igt_trend,
        )

    # 3. alert.drift
    if result.health_status in ("degrading", "critical"):
        emit(
            "alert.drift",
            1.0 - result.fidelity_score,
            "Re-anchor to the original intent or reset context",
            health_status=result.health_status,
            fidelity_score=result.fidelity_score,
        )

    # 4. alert.contradiction
    if result.consistency_score < config.consistency_threshold:
        emit(
            "alert.contradiction",
            1.0 - result.consistency_score,
            "Flag the specific contradicting turns for resolution",
            consistency_score=result.consistency_score,
        )

    # 5. alert.verbosity
    if result.twr_value > config.verbosity_threshold:
        emit(
            "alert.verbosity",
            result.twr_value,
            "Reduce response length; maximise information density",
            twr_value=result.twr_value,
        )

    # 6. signal.convergence
    if result.health_status == "converged":
        emit(
            "signal.convergence",
            0.9,
            "Conversation reached its natural endpoint; summarise and close",
        )

    # 7. signal.optimal_length
    if session.turn_count >= 5 and result.igt_trend < 0:
        estimated_t_star = max(5, int(session.turn_count / max(0.01, -result.igt_trend)))
        if session.turn_count > estimated_t_star * 0.8:
            emit(
                "signal.optimal_length",
                0.7,
                "Proactively summarise and check if more turns are needed",
                estimated_t_star=estimated_t_star,
            )

    # 8. signal.horizon_widening
    if session.turn_count >= 2:
        prev_eps = session.turns[-2].epsilon_t
        if result.epsilon_t > prev_eps * 1.5 and result.epsilon_t > 0.3:
            emit(
                "signal.horizon_widening",
                result.epsilon_t,
                "Increase epistemic humility; ask for more context",
                epsilon_t=result.epsilon_t,
                prev_epsilon_t=prev_eps,
            )

    # 9. signal.session_reset
    if result.degradation_type == "irreversible_loss":
        emit(
            "signal.session_reset",
            0.9,
            "Start a fresh session with a structured handoff summary",
        )

    # 10. signal.temporal_desync
    if (
        result.gap_seconds is not None
        and result.gap_seconds > config.temporal_desync_threshold_seconds
        and result.estimated_retention is not None
        and result.estimated_retention < 0.5
    ):
        emit(
            "signal.temporal_desync",
            1.0 - result.estimated_retention,
            "Re-anchor: summarise where the conversation left off; check if intent changed",
            gap_seconds=result.gap_seconds,
            estimated_retention=result.estimated_retention,
        )

    # 11. signal.broken_reference
    if (
        result.reachable_fraction is not None
        and result.reachable_fraction < config.broken_reference_threshold
        and session.turn_count > 5
    ):
        emit(
            "signal.broken_reference",
            1.0 - result.reachable_fraction,
            "User may reference content the agent no longer has access to; ask for recap",
            reachable_fraction=result.reachable_fraction,
        )

    # 12. signal.frame_shift
    if (
        turn.client_context is not None
        and session.turn_count >= 2
        and session.turns[-2].client_context is not None
    ):
        prev_ctx = session.turns[-2].client_context
        curr_ctx = turn.client_context
        device_changed = prev_ctx.get("device_type") != curr_ctx.get("device_type")
        tz_changed = prev_ctx.get("timezone") != curr_ctx.get("timezone")
        if device_changed or tz_changed:
            emit(
                "signal.frame_shift",
                0.8,
                "Adjust assumptions about available attention and cognitive bandwidth",
                device_changed=device_changed,
                timezone_changed=tz_changed,
            )

    # 13. signal.pace_shift
    if (
        result.conversation_acceleration is not None
        and abs(result.conversation_acceleration) > config.pace_shift_threshold
    ):
        accel = result.conversation_acceleration
        if accel > 0 and result.divergence_score < config.clarification_threshold:
            behavior = "Engagement surge detected — match energy, maintain alignment"
        elif accel > 0:
            behavior = "Frustration detected — slow down and ask what is most important"
        else:
            behavior = "Disengagement detected — check if the user needs something different"
        emit(
            "signal.pace_shift",
            abs(accel),
            behavior,
            acceleration=accel,
        )

    # 14. signal.light_cone_collapse
    if (
        session.turn_count >= 3  # need enough history to have a meaningful light cone
        and result.reachable_turns is not None
        and result.reachable_fraction is not None
        and (
            result.reachable_turns < config.light_cone_min_threshold
            or result.reachable_fraction < config.light_cone_ratio_threshold
        )
    ):
        emit(
            "signal.light_cone_collapse",
            1.0 - result.reachable_fraction,
            "Summarise key context before it becomes unreachable; "
            "do not reference lost turns",
            reachable_turns=result.reachable_turns,
            reachable_fraction=result.reachable_fraction,
        )

    return events
