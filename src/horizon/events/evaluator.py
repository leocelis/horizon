"""Event evaluation engine — all 15 signal conditions.

Events are emitted in observe mode by default. Each event carries:
- type: the signal name (e.g. 'checkpoint.clarification')
- active: True only when the event type is in active mode via configure()
- confidence: [0, 1] signal strength
- suggested_behavior: plain-English instruction for the agent controller
- metadata: signal-specific auxiliary data
"""

from __future__ import annotations

from horizon.config import Config
from horizon.engines.claim_consistency import (
    detect_contradictions,
    summarise_conflicts,
)
from horizon.models import Event, TurnResult
from horizon.session import Session, TurnState


def evaluate_events(
    session: Session,
    turn: TurnState,
    result: TurnResult,
    config: Config,
    *,
    agent_response: str = "",
) -> list[Event]:
    """Evaluate all event conditions and return the fired events.

    ``agent_response`` is the raw agent text for this turn — required by the
    v0.2 claim-tracker contradiction detector, defaulted to the empty string
    so older callers continue to work (they fall back to the v0.1
    coherence-only path).
    """
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

    # 2. checkpoint.comprehension — fires when the human's information
    # gain has clearly stalled (deep IGT drop AND low absolute IGT). The
    # v0.1 trigger (`igt_trend < -0.05`) fired on essentially every
    # natural conversation rhythm change, killing precision; v0.2
    # additionally requires the absolute IGT to be in the bottom-third
    # of the scale (genuine confusion, not just a topic switch).
    if (
        result.igt_trend < config.comprehension_trend_threshold
        and result.igt_value < config.comprehension_igt_ceiling
        and session.turn_count >= config.convergence_window
    ):
        emit(
            "checkpoint.comprehension",
            abs(result.igt_trend),
            "Summarise your current understanding and ask for confirmation",
            igt_trend=result.igt_trend,
            igt_value=result.igt_value,
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
    # claim_tracker (v0.2): only fires on explicit numeric/named-claim
    #   conflicts — no coherence fallback to keep precision high.
    # coherence (v0.1, opt-in via config): fires when bipredictability
    #   coherence drops below ``consistency_threshold``.
    if config.contradiction_method == "claim_tracker" and agent_response:
        conflicts = detect_contradictions(
            session.claim_tracker,
            agent_response,
            turn.turn_number,
            relative_tolerance=config.contradiction_relative_tolerance,
        )
        if conflicts:
            emit(
                "alert.contradiction",
                min(1.0, 0.6 + 0.1 * len(conflicts)),
                "Reconcile the conflicting claims before continuing: "
                + summarise_conflicts(conflicts),
                conflict_count=len(conflicts),
                method="claim_tracker",
            )
    elif (
        config.contradiction_method == "coherence"
        and result.consistency_score < config.consistency_threshold
    ):
        emit(
            "alert.contradiction",
            1.0 - result.consistency_score,
            "Flag the specific contradicting turns for resolution",
            consistency_score=result.consistency_score,
            method="coherence",
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

    # 7. signal.optimal_length — the conversation has clearly peaked. Fires
    # when (a) we have at least 5 turns, (b) IGT trend is negative, and
    # (c) current IGT has dropped to at most ``optimal_length_decay``
    # fraction of the running peak. v0.1 used a t-star projection that
    # required pathologically steep decay to ever fire.
    if session.turn_count >= 5 and result.igt_trend < 0:
        recent_igt = [t.igt_value for t in session.turns[-config.convergence_window :]]
        peak_igt = max(t.igt_value for t in session.turns) if session.turns else 0.0
        if peak_igt > 0 and (result.igt_value / peak_igt) <= config.optimal_length_decay:
            emit(
                "signal.optimal_length",
                0.7,
                "Proactively summarise and check if more turns are needed",
                igt_decay_ratio=result.igt_value / peak_igt,
                peak_igt=peak_igt,
            )

    # 8. signal.horizon_widening — fires when the ontological gap (ε)
    # both jumps significantly AND lands at a meaningfully high absolute
    # value. The v0.1 thresholds (ratio>1.5, eps>0.3) fired on routine
    # topic micro-shifts; v0.2 doubles both requirements.
    if session.turn_count >= 2:
        prev_eps = session.turns[-2].epsilon_t
        if (
            result.epsilon_t > prev_eps * config.horizon_widening_ratio
            and result.epsilon_t > config.horizon_widening_floor
        ):
            emit(
                "signal.horizon_widening",
                result.epsilon_t,
                "Increase epistemic humility; ask for more context",
                epsilon_t=result.epsilon_t,
                prev_epsilon_t=prev_eps,
            )

    # 9. signal.session_reset — fires whenever the context window has just
    # evicted at least one turn (degradation includes any irreversible
    # component). v0.1 only matched the pure ``irreversible_loss`` label
    # which never fired when recoverable drift co-occurred with eviction.
    if result.degradation_type in ("irreversible_loss", "both"):
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
            "Summarise key context before it becomes unreachable; " "do not reference lost turns",
            reachable_turns=result.reachable_turns,
            reachable_fraction=result.reachable_fraction,
        )

    # 15. signal.grounding_required
    # Fires when the heuristic grounding-need score crosses threshold. The
    # agent should hedge unsupported specifics OR cite evidence returned by
    # the registered grounding hook (if one is wired).
    if result.grounding_need >= config.grounding_required_threshold:
        if result.grounding_confidence > 0 and result.grounding_evidence:
            behavior = (
                "Cite the attached grounding evidence verbatim before making "
                "any specific numeric or named claim; never present an "
                "unsupported specific as fact."
            )
        else:
            behavior = (
                "Lead every concrete claim with a hedge marker "
                "('rough estimate', 'approximately', 'from memory') or ask the "
                "user for the figure — no grounding evidence is available."
            )
        emit(
            "signal.grounding_required",
            result.grounding_need,
            behavior,
            grounding_need=result.grounding_need,
            grounding_confidence=result.grounding_confidence,
            evidence_count=len(result.grounding_evidence),
            source_count=len(result.grounding_sources),
        )

    # 16. signal.pace_premature_report
    # Fires when (a) the agent asked the user to do something deferred on the
    # previous turn, (b) the user replied faster than that action could
    # plausibly complete, and (c) the user did not say they completed it.
    # The agent should re-confirm completion before treating the reply as a
    # post-action result.
    if (
        session.turn_count >= 2
        and result.gap_seconds is not None
        and result.gap_seconds > 0
    ):
        prev_turn = session.turns[-2]
        prev_hint = prev_turn.agent_pacing_hint
        if (
            prev_hint is not None
            and prev_hint.has_deferred_action
            and result.gap_seconds < prev_hint.est_min_seconds
            and not turn.human_completion_marker
        ):
            ratio = result.gap_seconds / max(prev_hint.est_min_seconds, 1.0)
            confidence = max(0.0, min(1.0, 1.0 - ratio))
            emit(
                "signal.pace_premature_report",
                confidence,
                "User replied faster than the deferred action could plausibly "
                "complete and did not signal completion; treat their message as "
                "in-progress / current state, and confirm whether they finished "
                "the action before continuing.",
                gap_seconds=result.gap_seconds,
                expected_min_seconds=prev_hint.est_min_seconds,
                action_hint=prev_hint.action_hint,
                matched_pattern=prev_hint.matched_pattern,
            )

    return events
