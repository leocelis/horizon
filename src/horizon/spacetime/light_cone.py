"""Causal Reachability Map J⁻(t_i) — conversation light cone.

A turn j is causally reachable from current turn i iff:
  R = in_context(j) × retention(j→i) × semantic_similarity(j, i) > θ_R

Based on DCGM (2026) proving causal structure > context window for memory.
"""

from __future__ import annotations

import numpy as np
from numpy import ndarray

from horizon.config import Config
from horizon.session import Session
from horizon.spacetime.temporal import compute_retention


def compute_reachability(
    session: Session,
    current_turn: int,
    current_embedding: ndarray,
    gap_seconds: float,
    kappa: float,
    config: Config,
) -> tuple[int, float]:
    """Compute |J⁻| and the reachable fraction of prior turns.

    Returns (reachable_count, reachable_fraction).
    """
    reachable = []

    for turn_state in session.turns:
        if turn_state.turn_number >= current_turn:
            continue

        # Factor 1: context window membership
        in_context = 1.0 if turn_state.in_context else 0.0

        # Factor 2: human retention of that turn
        if gap_seconds > 0:
            R_H = compute_retention(gap_seconds, config.context_half_life_hours, kappa)
        else:
            R_H = 1.0

        # Factor 3: semantic relevance to current turn
        S = float(np.dot(turn_state.combined_embedding, current_embedding))
        S = max(0.0, (S + 1.0) / 2.0)  # [-1,1] → [0,1]

        R = in_context * R_H * S

        if R > config.reachability_threshold:
            reachable.append(turn_state.turn_number)

    count = len(reachable)
    total_prior = current_turn - 1

    # Turn 1: no prior turns → fraction = 1.0 (nothing lost)
    if total_prior <= 0:
        return 0, 1.0

    fraction = count / total_prior
    return count, fraction
