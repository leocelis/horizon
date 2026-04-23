"""Intent–Response Divergence (D_JS proxy) engine."""

from __future__ import annotations

import numpy as np
from numpy import ndarray


def compute_divergence(human_embedding: ndarray, agent_embedding: ndarray) -> float:
    """Proxy for Jensen-Shannon divergence between human intent and agent response.

    Both vectors must be L2-normalised (cosine similarity == dot product).
    Returns [0, 1]: 0 = perfect alignment, 1 = maximally divergent.
    """
    similarity = float(np.dot(human_embedding, agent_embedding))
    similarity = max(-1.0, min(1.0, similarity))

    # Map cosine similarity [-1, 1] to divergence [0, 1]
    divergence = (1.0 - similarity) / 2.0
    return divergence
