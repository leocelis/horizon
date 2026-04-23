"""Public frozen dataclasses returned by the Horizon Fidelity Monitor API."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass(frozen=True)
class TemporalReference:
    """A resolved deictic temporal expression found in conversation text."""

    expression: str
    """Original expression, e.g. 'yesterday', 'next Monday'."""

    resolved: Optional[str]
    """ISO 8601 datetime string, or None if unresolvable."""

    type: Literal["DATE", "TIME", "DURATION", "SET", "UNKNOWN"] = "UNKNOWN"


@dataclass(frozen=True)
class SpatialConstraint:
    """Inferred cognitive and screen constraints from the user's spatial context."""

    attention_budget: Literal["high", "medium", "low"]
    screen_capacity: Literal["large", "medium", "small"]
    max_response_length: int
    """Suggested maximum response length in tokens."""

    complexity_ceiling: Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Event:
    """A fidelity event emitted when a signal threshold is crossed."""

    type: str
    """e.g. 'checkpoint.clarification', 'signal.convergence'."""

    active: bool
    """True when the event is in active mode (has passed precision/recall gates)."""

    confidence: float
    """[0, 1] confidence score for this event."""

    turn: int
    suggested_behavior: str
    mode: Optional[str] = None
    """Conversation mode at time of emission."""

    metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class TurnResult:
    """Complete metrics, signals, and events for a single conversation turn."""

    # ── Core (always present) ────────────────────────────────────────────────
    turn_number: int
    igt_value: float
    """Information Gain per Turn — semantic novelty [0, ∞) effectively [0, 1]."""

    igt_trend: float
    """Slope of IGT over recent turns (negative = converging)."""

    divergence_score: float
    """D_JS proxy — intent/response divergence [0, 1]."""

    twr_value: float
    """Token Waste Ratio — semantic redundancy [0, 1]."""

    consistency_score: float
    """Bipredictability — structural coherence [0, 1]."""

    fidelity_score: float
    """Composite fidelity [0, 1]."""

    health_status: Literal["healthy", "degrading", "critical", "converged"]
    degradation_type: Literal["none", "recoverable_drift", "irreversible_loss", "both"]
    events: list[Event]
    epsilon_t: float
    """Estimated ontological gap width [0, 1]."""

    conversation_mode: str

    # ── Temporal (None when timestamp not provided) ──────────────────────────
    gap_seconds: Optional[float] = None
    gap_class: Optional[Literal["realtime", "seconds", "minutes", "hours", "days"]] = None
    estimated_retention: Optional[float] = None
    temporal_asymmetry: Optional[float] = None
    resumption_cost: Optional[Literal["none", "low", "medium", "high", "extreme"]] = None
    circadian_factor: Optional[float] = None
    temporal_references: Optional[list[TemporalReference]] = None

    # ── Pace (None when timestamp not provided or turn < 2) ──────────────────
    conversation_velocity: Optional[float] = None
    conversation_acceleration: Optional[float] = None

    # ── Spacetime (None when timestamp not provided or turn < 2) ─────────────
    spacetime_interval: Optional[float] = None
    interval_class: Optional[Literal["timelike", "spacelike", "lightlike"]] = None

    # ── Causal (None when timestamp not provided) ────────────────────────────
    reachable_turns: Optional[int] = None
    reachable_fraction: Optional[float] = None

    # ── Spatial (None when client_context not provided) ──────────────────────
    location_class: Optional[str] = None
    spatial_constraint: Optional[SpatialConstraint] = None
    spatial_frame_shift: Optional[float] = None

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class FidelityTrajectory:
    """Full per-session fidelity trajectory returned by get_trajectory()."""

    session_id: str
    turn_count: int
    scores: list[float]
    """Fidelity score per turn, index 0 = turn 1."""

    timestamps: list[Optional[str]]
    gap_durations: list[Optional[float]]
    """Seconds between consecutive turns, None for turn 1."""

    igt_trend: float
    """Slope over entire trajectory."""

    health_status: Literal["healthy", "degrading", "critical", "converged"]
    estimated_t_star: Optional[int]
    """Estimated optimal conversation length (None if not yet detectable)."""

    peak_fidelity: float
    current_fidelity: float

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class ConfigWarning:
    parameter: str
    message: str


@dataclass(frozen=True)
class ConfigResult:
    """Result of a configure() call."""

    applied: dict
    warnings: list[ConfigWarning]


@dataclass(frozen=True)
class ExportResult:
    """Result of an export_to() call."""

    status: Literal["success", "partial", "failed"]
    records_exported: int
    target: str
    target_url: Optional[str] = None
    errors: list[str] = field(default_factory=list)
