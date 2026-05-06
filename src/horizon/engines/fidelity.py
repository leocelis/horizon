"""Fidelity computation and health status engine."""

from __future__ import annotations

from horizon.config import Config
from horizon.session import Session


def _on_topic_igt(igt: float, consistency: float) -> float:
    """Effective IGT = novelty that stays on-topic.

    Raw IGT only measures semantic distance from prior turns; off-topic
    drift and hallucinated tangents both produce high IGT. Gating by
    consistency ensures that 'novelty' only counts when the agent's
    output is still coherent with the conversation's topic. This closes
    the v0.1 loophole where a hallucinated specific (high novelty + low
    coherence) artificially inflated fidelity.
    """
    return min(igt, 1.0) * max(0.0, min(1.0, consistency))


def _coherence_drop(consistency: float, floor: float = 0.6) -> float:
    """Hinge-loss style coherence penalty term.

    Returns 0 for consistency >= floor (clean turns have ~0.65-0.85 coherence
    as a side-effect of sentence-transformer cosine geometry, so penalising
    every turn would over-deflate clean conversations). For consistency
    below the floor, the penalty grows linearly to 1.0 at consistency=0.
    Calibrated so a single drift turn (consistency ~ 0.5) earns a penalty of
    ~0.17, while clean turns (consistency > 0.65) pay nothing.
    """
    c = max(0.0, min(1.0, consistency))
    if c >= floor:
        return 0.0
    return (floor - c) / floor


def compute_snapshot_fidelity(
    igt: float,
    djs: float,
    twr: float,
    consistency: float,
    config: Config,
) -> float:
    """Current-turn snapshot fidelity from four raw signals.

    Returns [0, 1].
    """
    score = (
        config.w_igt * _on_topic_igt(igt, consistency)
        + config.w_djs * (1.0 - djs)
        + config.w_twr * (1.0 - twr)
        + config.w_consistency * consistency
    )
    return max(0.0, min(1.0, score))


def compute_dynamic_fidelity(
    prev_fidelity: float,
    igt: float,
    djs: float,
    delta_recoverable: float,
    delta_irreversible: float,
    delta_tau: float,
    kappa: float,
    config: Config,
    consistency: float = 1.0,
) -> float:
    """Trajectory-aware fidelity incorporating temporal and circadian penalties.

    Amended dynamics (Appendix C.5, v0.2):
      F_t = F_{t-1} + α·IGT·C - λ_r·δ_recov - λ_i·δ_irrev - β·D_JS - γ·Δτ - δ·(1-κ)

    The α·IGT term is gated by C (consistency) so that off-topic novelty —
    the failure mode hallucinations and topic drift exhibit — no longer
    inflates the score. Default consistency=1.0 preserves backward
    compatibility for callers that don't pass it.

    Returns [0, 1].
    """
    f = (
        prev_fidelity
        + config.alpha * _on_topic_igt(igt, consistency)
        - config.lambda_r * delta_recoverable
        - config.lambda_i * delta_irreversible
        - config.beta * djs
        - config.gamma * delta_tau
        - config.delta * (1.0 - kappa)
        - config.eta * _coherence_drop(consistency, floor=config.coherence_floor)
    )
    return max(0.0, min(1.0, f))


def compute_health(
    session: Session,
    fidelity: float,
    igt_trend: float,
    config: Config,
    current_igt: float | None = None,
) -> str:
    """Classify conversation health from trajectory and current signals.

    Returns one of: healthy | degrading | critical | converged.

    Note: ``compute_health`` is called *before* the current turn is appended
    to ``session.turns``. Pass ``current_igt`` so the convergence-window
    check reflects the latest turn — otherwise a brand-new topic on the
    current turn would still be classified as "converged" because the
    window only sees the prior (low-IGT) turns.
    """
    # Convergence: IGT trend non-positive AND every IGT value in the
    # recent window — including the current turn — is below the absolute
    # IGT ceiling. The v0.1 trigger reused the trend threshold for both
    # checks, requiring IGT to be < 0.1 absolute, which almost never
    # fired on real conversations. v0.2 splits the thresholds *and*
    # includes the current turn so a sudden topic re-spark immediately
    # disqualifies convergence.
    if (
        igt_trend < config.convergence_threshold
        and session.turn_count + (1 if current_igt is not None else 0)
        >= config.convergence_window
    ):
        prior_igt = [t.igt_value for t in session.turns[-(config.convergence_window - 1) :]]
        recent_igt = (
            prior_igt + [current_igt] if current_igt is not None else prior_igt
        )
        recent_igt = recent_igt[-config.convergence_window :]
        if all(v < config.convergence_igt_ceiling for v in recent_igt):
            return "converged"

    # Drift: fidelity declining every turn for drift_window turns
    trajectory = session.fidelity_trajectory
    if len(trajectory) >= config.drift_window:
        recent = trajectory[-config.drift_window :]
        monotone_decline = all(recent[i] > recent[i + 1] for i in range(len(recent) - 1))
        if monotone_decline:
            return "critical" if fidelity < 0.3 else "degrading"

    return "healthy"
