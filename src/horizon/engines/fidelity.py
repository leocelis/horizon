"""Fidelity computation and health status engine."""

from __future__ import annotations

from horizon.config import Config
from horizon.session import Session


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
        config.w_igt * min(igt, 1.0)
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
) -> float:
    """Trajectory-aware fidelity incorporating temporal and circadian penalties.

    Amended dynamics (Appendix C.5):
      F_t = F_{t-1} + α·IGT - λ_r·δ_recov - λ_i·δ_irrev - β·D_JS - γ·Δτ - δ·(1-κ)

    Returns [0, 1].
    """
    f = (
        prev_fidelity
        + config.alpha * min(igt, 1.0)
        - config.lambda_r * delta_recoverable
        - config.lambda_i * delta_irreversible
        - config.beta * djs
        - config.gamma * delta_tau
        - config.delta * (1.0 - kappa)
    )
    return max(0.0, min(1.0, f))


def compute_health(
    session: Session,
    fidelity: float,
    igt_trend: float,
    config: Config,
) -> str:
    """Classify conversation health from trajectory and current signals.

    Returns one of: healthy | degrading | critical | converged.
    """
    # Convergence: IGT trend negative and all recent IGT values are low
    if (
        igt_trend < config.convergence_threshold
        and session.turn_count >= config.convergence_window
    ):
        recent_igt = [t.igt_value for t in session.turns[-config.convergence_window :]]
        if all(v < config.convergence_threshold for v in recent_igt):
            return "converged"

    # Drift: fidelity declining every turn for drift_window turns
    trajectory = session.fidelity_trajectory
    if len(trajectory) >= config.drift_window:
        recent = trajectory[-config.drift_window :]
        monotone_decline = all(
            recent[i] > recent[i + 1] for i in range(len(recent) - 1)
        )
        if monotone_decline:
            return "critical" if fidelity < 0.3 else "degrading"

    return "healthy"
