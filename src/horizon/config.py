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
    """IGT-trend threshold that must be undershot for convergence."""

    convergence_igt_ceiling: float = 0.35
    """Absolute IGT ceiling below which the conversation is considered
    'plateaued'. v0.1 reused convergence_threshold for both checks, which
    required IGT ≈ 0 — unrealistic for real conversations. v0.2 splits
    these so convergence fires on a real plateau, not a numerical zero."""
    """IGT trend below this (and all recent IGT values) = converging."""

    drift_window: int = 4
    """Consecutive fidelity-declining turns before declaring degrading/critical."""

    verbosity_threshold: float = 0.5
    """TWR above this → alert.verbosity."""

    consistency_threshold: float = 0.6

    # ── Event trigger thresholds (v0.2 tightening) ──────────────────────────
    comprehension_trend_threshold: float = -0.05
    """checkpoint.comprehension fires only when igt_trend drops below this.
    v0.1 used -0.05 which fired on every natural conversation rhythm change."""

    comprehension_igt_ceiling: float = 0.4
    """checkpoint.comprehension also requires absolute IGT to be in the
    bottom-third of the scale — genuine confusion, not a topic switch."""

    horizon_widening_ratio: float = 2.0
    """signal.horizon_widening requires ε to jump by at least this multiple
    of the prior turn's ε. v0.1 used 1.5 which fired on routine topic shifts."""

    horizon_widening_floor: float = 0.5
    """signal.horizon_widening requires ε to land above this absolute value
    after the jump. v0.1 used 0.3 — too low for "real ontological gap"."""

    optimal_length_decay: float = 0.4
    """signal.optimal_length fires when current IGT has dropped to at most
    this fraction of the running peak — i.e., the conversation has
    delivered most of its information already. v0.1 used a t-star
    projection that required impossible decay rates to fire."""
    """Bipredictability below this → alert.contradiction."""

    consistency_method: Literal["fast", "nli"] = "fast"
    """fast = Tier 1 (bipredictability only); nli = adds Tier 3 cross-encoder."""

    contradiction_method: Literal["coherence", "claim_tracker"] = "claim_tracker"
    """coherence = v0.1 behaviour (alert.contradiction fires only when
    bipredictability drops below ``consistency_threshold``); claim_tracker =
    v0.2 numeric/named-claim contradiction detector (catches "2x → 4x → no
    speedup" cases the embedding-only check misses). claim_tracker is the
    default in v0.2; set to "coherence" for backward compatibility."""

    contradiction_relative_tolerance: float = 0.10
    """For claim_tracker: two scale/percent/currency claims about the same
    topic are considered restatements (no contradiction) when their
    fractional difference is within this band."""

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

    eta: float = 0.40
    """Coherence-drop penalty coefficient — applied as a hinge loss against
    a coherence floor (see ``coherence_floor``) so clean turns pay nothing
    and only drift/hallucination turns are penalised. Added in v0.2 to
    close the loophole where a hallucinated/drifted turn could inflate
    fidelity through raw IGT."""

    coherence_floor: float = 0.6
    """Below this consistency value, the eta coherence penalty engages.
    Tuned to the empirical coherence of clean sentence-transformer output."""

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
    pace_shift_threshold: float = 0.1
    """Acceleration magnitude above this → signal.pace_shift.

    Units: semantic-displacement-per-second per turn. The v0.1 value (0.3)
    required pathologically large velocity swings to fire on real
    conversations; v0.2 calibrates against the synthetic V2 corpus where
    a meaningful pace inversion (∼8 minute gap → ∼5 second gap) lands
    around 0.12 — comfortably above the new threshold and well above the
    noise floor of routine turn-by-turn micro-shifts (~0.01)."""

    light_cone_ratio_threshold: float = 0.3
    """Reachable fraction below this → signal.light_cone_collapse."""

    light_cone_min_threshold: int = 3
    """Absolute reachable turns below this → signal.light_cone_collapse."""

    reachability_threshold: float = 0.1
    """Combined reachability score θ_R — turns above this are in J⁻."""

    broken_reference_threshold: float = 0.3
    """Reachable fraction below this → signal.broken_reference (if turn_count > 5)."""

    grounding_required_threshold: float = 0.5
    """Estimated grounding-need score above this → signal.grounding_required."""

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
