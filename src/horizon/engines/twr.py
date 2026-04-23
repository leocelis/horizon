"""Token Waste Ratio (TWR) engine — semantic redundancy detector."""

from __future__ import annotations

import re
from collections.abc import Callable

import numpy as np
from numpy import ndarray

from horizon.session import Session


def split_sentences(text: str) -> list[str]:
    """Split text into sentences, filtering out trivial fragments."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s for s in sentences if len(s.split()) >= 3]


def compute_twr(
    agent_response: str,
    session: Session,
    embed_fn: Callable[[str], ndarray],
    threshold: float = 0.85,
) -> float:
    """Fraction of agent response sentences semantically redundant with prior turns.

    A sentence is redundant if its cosine similarity to any prior turn's agent
    embedding exceeds `threshold`. Returns [0, 1].
    """
    if session.turn_count == 0:
        return 0.0

    sentences = split_sentences(agent_response)
    if not sentences:
        return 0.0

    sent_embeddings = [embed_fn(s) for s in sentences]

    waste_count = 0
    for sent_emb in sent_embeddings:
        for prior_turn in session.turns:
            sim = float(np.dot(sent_emb, prior_turn.agent_embedding))
            if sim > threshold:
                waste_count += 1
                break

    return waste_count / len(sentences)
