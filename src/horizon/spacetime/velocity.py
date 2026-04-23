"""Conversation velocity and acceleration — semantic pace signals."""

from __future__ import annotations

from typing import Optional

import numpy as np
from numpy import ndarray


def compute_velocity(
    current_embedding: ndarray,
    prev_embedding: ndarray,
    gap_seconds: float,
) -> Optional[float]:
    """Semantic displacement per second of proper time.

    High velocity: rapid topic changes (engagement surge or frustration).
    Near-zero velocity: conversation slowing or stalling.

    Returns None when no proper time elapsed (realtime turn).
    """
    if gap_seconds <= 0:
        return None

    semantic_displacement = 1.0 - float(np.dot(current_embedding, prev_embedding))
    semantic_displacement = max(0.0, semantic_displacement)

    return semantic_displacement / gap_seconds


def compute_acceleration(
    current_velocity: Optional[float],
    prev_velocity: Optional[float],
) -> Optional[float]:
    """Change in velocity between consecutive turns.

    Positive acceleration = conversation speeding up.
    Negative acceleration = conversation slowing down.

    Returns None when either velocity is unavailable.
    """
    if current_velocity is None or prev_velocity is None:
        return None
    return current_velocity - prev_velocity
