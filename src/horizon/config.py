"""Configuration dataclass for the Horizon Fidelity Monitor."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class Config:
    """Immutable configuration for a Horizon monitor instance or session override.

    All thresholds have defaults calibrated to a "general" conversation domain.
    Use configure() to tune per-domain or per-session.
    """

    # ── Core signal thresholds ──────────────────────────────────────────────
    clarification_threshold: float = 0.35
    """D_JS above this → checkpoint.clarification"""

    convergence_window: int = 3
    """Consecutive turns of low IGT required to detect convergence."""

    convergence_threshold: float = 0.1
    """IGT trend below this (and all recent IGT values) = converging."""

    drift_window: int = 4
    """Consecutive fidelity-declining turns before declaring degrading/critical."""

    verbosity_threshold: float = 0.5
    """TWR above this → alert.verbosity."""

    consistency_threshold: float = 0.6
    """Bipredictability below this → alert.contradiction."""

    consistency_method: Literal["fast", "nli"] = "fast"
    """fast = Tier 1 (bipredictability only); nli = adds Tier 3 cross-encoder."""

    # ── Fidelity dynamics weights ───────────────────────────────────────────
    alpha: float = 0.3
    """Semantic information absorption coefficient."""

    lambda_r: float = 0.1
    """Recoverable drift penalty coefficient."""

    lambda_i: float = 0.3
    """Irreversible loss penalty coefficient."""

    beta: float = 0.2
    """D_JS penalty coefficient."""

    gamma: float = 0.1
    """Temporal asymmetry penalty coefficient (Δτ)."""

    delta: float = 0.05
    """Circadian penalty coefficient (1 - κ)."""

    # ── Composite score weights ─────────────────────────────────────────────
    w_igt: float = 0.3
    w_djs: float = 0.3
    w_twr: float = 0.15
    w_consistency: float = 0.25

    # ── Temporal ────────────────────────────────────────────────────────────
    context_half_life_hours: float = 24.0
    """h_c for Half-Life Regression retention model (Ebbinghaus-inspired)."""

    temporal_desync_threshold_seconds: float = 3600.0
    """Gap >= this AND retention < 0.5 → signal.temporal_desync."""

    chronotype_offset: float = 0.0
    """Hours to shift κ(t) curve for individual chronotype. Positive = night owl."""

    # ── 4D Spacetime ────────────────────────────────────────────────────────
    pace_shift_threshold: float = 0.3
    """Acceleration magnitude above this → signal.pace_shift."""

    light_cone_ratio_threshold: float = 0.3
    """Reachable fraction below this → signal.light_cone_collapse."""

    light_cone_min_threshold: int = 3
    """Absolute reachable turns below this → signal.light_cone_collapse."""

    reachability_threshold: float = 0.1
    """Combined reachability score θ_R — turns above this are in J⁻."""

    broken_reference_threshold: float = 0.3
    """Reachable fraction below this → signal.broken_reference (if turn_count > 5)."""

    spacetime_alpha: float = 1.0
    """ds² time coefficient (sign: negative, timelike)."""

    spacetime_beta: float = 1.0
    """ds² D_JS coefficient."""

    spacetime_gamma: float = 1.0
    """ds² ε coefficient."""

    spacetime_delta: float = 1.0
    """ds² coherence coefficient."""

    # ── Conversation mode ───────────────────────────────────────────────────
    conversation_mode: Literal["auto", "execute", "explore", "refine", "learn"] = "auto"
    domain: str = "general"

    # ── Embedding ───────────────────────────────────────────────────────────
    embedding_model: str = "all-MiniLM-L6-v2"
    model_path: str | None = None
    """Local path to pre-downloaded model weights. Overrides embedding_model lookup."""

    # ── Event modes ─────────────────────────────────────────────────────────
    event_modes: dict[str, Literal["active", "observe"]] = field(default_factory=dict)
    """event_type → "active" | "observe". Unknown types default to "observe"."""

    def event_is_active(self, event_type: str) -> bool:
        """Return True if the event type is in active mode."""
        return self.event_modes.get(event_type, "observe") == "active"

    def merge(self, **overrides: object) -> Config:
        """Return a new Config with the given fields overridden."""
        import dataclasses

        current = dataclasses.asdict(self)
        current.update({k: v for k, v in overrides.items() if v is not None})
        return Config(**current)
