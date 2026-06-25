"""Ontological gap width estimator (ε_t tracker)."""

from __future__ import annotations

import numpy as np
from numpy import ndarray

from horizon.session import Session


def estimate_epsilon(
    session: Session,
    current_embedding: ndarray,
    divergence_score: float,
) -> float:
    """Estimate the current ontological gap width ε_t.

    ε_t measures how hard the current topic/domain is for human-AI communication.
    High ε → more structural loss, increase humility.

    Algorithm:
    - Bootstrap (< 3 turns): use D_JS as initial estimate
    - Running average of recent D_JS as baseline
    - Spike ε when topic shifts into unfamiliar territory

    Returns [0, 1].
    """
    if session.turn_count < 3:
        return divergence_score

    # Topic shift magnitude from previous combined embedding
    if session.turn_count >= 2:
        prev = session.turns[-2].combined_embedding
        topic_shift = 1.0 - float(np.dot(current_embedding, prev))
        topic_shift = max(0.0, topic_shift)
    else:
        topic_shift = 0.0

    # Running D_JS baseline
    recent_djs = [t.divergence_score for t in session.turns[-5:]]
    baseline_eps = sum(recent_djs) / len(recent_djs)

    epsilon = baseline_eps + 0.5 * topic_shift
    return min(1.0, epsilon)
