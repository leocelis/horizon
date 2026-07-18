"""Conversation coherence engine — Tier 1 bipredictability."""

from __future__ import annotations

import numpy as np
from numpy import ndarray


def compute_bipredictability(
    human_embedding: ndarray,
    agent_embedding: ndarray,
    history_embedding: ndarray | None,
) -> float:
    """Tier 1 coherence: structural consistency via bipredictability triangle.

    Measures whether the agent response bridges conversation history and the
    human's current message in a mutually consistent way. High when all three
    pair-wise similarities are positive; low when any pair diverges.

    Returns [0, 1] where 1 = fully coherent.
    """
    if history_embedding is None:
        return 1.0

    h_a = float(np.dot(history_embedding, agent_embedding))
    h_h = float(np.dot(history_embedding, human_embedding))
    a_h = float(np.dot(agent_embedding, human_embedding))

    # Mean of three cosine similarities, normalised from [-1,1] to [0,1]
    P = (h_a + h_h + a_h) / 3.0
    score = (P + 1.0) / 2.0
    return max(0.0, min(1.0, score))
