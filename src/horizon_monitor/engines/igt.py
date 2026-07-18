"""Information Gain per Turn (IGT) engine."""

from __future__ import annotations

import numpy as np
from numpy import ndarray

from horizon.session import Session


def compute_igt(
    combined_embedding: ndarray,
    history_embedding: ndarray | None,
    turn_number: int,
) -> float:
    """Compute how much new semantic content this turn adds beyond prior history.

    Returns a value in [0, 1]: 0 = fully redundant, 1 = fully novel.
    Turn 1 always returns 1.0 because no prior history exists.
    """
    if turn_number == 1 or history_embedding is None:
        return 1.0

    similarity = float(np.dot(combined_embedding, history_embedding))
    similarity = max(-1.0, min(1.0, similarity))

    # Orthogonal component = novelty
    igt = 1.0 - similarity
    return max(0.0, igt)


def compute_igt_trend(session: Session, window: int) -> float:
    """Linear regression slope of IGT values over the last `window` turns.

    Negative slope → information gain declining (conversation converging).
    """
    if session.turn_count < 2:
        return 0.0

    recent = [t.igt_value for t in session.turns[-window:]]
    if len(recent) < 2:
        return 0.0

    x = np.arange(len(recent), dtype=float)
    slope = float(np.polyfit(x, recent, 1)[0])
    return slope
