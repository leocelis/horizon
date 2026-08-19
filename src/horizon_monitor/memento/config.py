"""Configuration dataclass for the Memento Mori mission plane.

Per MEMENTO_MORI_TECH_SPEC.md §2.1. ``store_path is None`` disables the
plane entirely — every existing Horizon API must then behave byte-
identically to the pre-plane release
(horizon_memento_mori_intent.yaml::optional_plane_backward_compat).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


@dataclass(frozen=True)
class MementoConfig:
    """Immutable configuration for a Memento Mori store + evaluation pipeline."""

    store_path: Path | None = None
    """Local SQLite file path. None => the plane is disabled entirely; no
    memento code path is entered anywhere in Horizon."""

    time_value_rate: Decimal | None = None
    """Currency per hour, operator-declared. None => every monetary field is
    omitted and every non-monetary output is byte-identical to the
    rate-declared report."""

    rate_currency: str | None = None
    """ISO 4217 label only (e.g. "USD"). Never used for conversion."""

    stall_default_days: int = 14
    """Default mission stall threshold; per-mission override allowed via
    Item.stall_days."""

    deadline_warn_days: int = 14
    """Default deadline warning-window width; per-deadline override allowed."""

    horizon_share_rungs: tuple[float, ...] = (0.01, 0.05, 0.10, 0.25)
    """Ascending thresholds signal.horizon_share escalates across."""

    per_turn_fire_cap: int = 1
    """Max new RAISED/ESCALATED signal events per associated turn."""

    stale_ack_days: int = 30
    """Days an ACKED item may sit with no progress before one low-tier
    STALE event fires."""

    ttl_proposal_percentile: float = 0.80

    cost_of_delay_threshold: Decimal | None = None
    """Operator-set threshold above which accrued cost-of-delay fires
    ``signal.cost_of_delay`` (PRD §5.2). The signal is only ever computable
    when a rate, an item amount, AND this threshold are all caller-declared
    — money never enters by default (parent intent: money is a weight on
    time, never a subsystem)."""
    """Default percentile (nearest-rank) for clock_propose(kind="ttl")."""

    def __post_init__(self) -> None:
        if isinstance(self.store_path, str):
            object.__setattr__(self, "store_path", Path(self.store_path))
