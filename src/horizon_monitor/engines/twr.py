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
    sentence_embeddings_out: list[ndarray] | None = None,
    sentence_embeddings: list[ndarray] | None = None,
) -> float:
    """Fraction of agent response sentences semantically redundant with prior turns.

    A sentence is flagged as redundant when its cosine similarity exceeds
    ``threshold`` against EITHER:
      1. any prior turn's whole-agent embedding (catches "you're talking
         about the same topic"), OR
      2. any prior agent sentence's individual embedding (catches verbatim /
         near-verbatim sentence repeats — the v0.1 engine missed these
         because a single repeated sentence's cosine vs a 3-sentence prior
         turn embedding only reaches ~0.75).

    Returns [0, 1].
    """
    if session.turn_count == 0:
        return 0.0

    sentences = split_sentences(agent_response)
    if not sentences:
        return 0.0

    if sentence_embeddings is not None:
        if len(sentence_embeddings) != len(sentences):
            raise ValueError(
                "sentence_embeddings length must match split_sentences(agent_response)"
            )
        sent_embeddings = sentence_embeddings
    else:
        sent_embeddings = [embed_fn(s) for s in sentences]

    # Collect per-sentence anchors from prior turns when available.
    prior_sentence_anchors: list[ndarray] = []
    for prior_turn in session.turns:
        if prior_turn.agent_sentence_embeddings:
            prior_sentence_anchors.extend(prior_turn.agent_sentence_embeddings)

    waste_count = 0
    for sent_emb in sent_embeddings:
        is_redundant = False
        # Whole-turn check (unchanged from v0.1).
        for prior_turn in session.turns:
            sim = float(np.dot(sent_emb, prior_turn.agent_embedding))
            if sim > threshold:
                is_redundant = True
                break
        # Per-sentence check (v0.2) — catches verbatim sentence repeats
        # whose cosine vs a multi-sentence prior turn embedding falls just
        # short of the threshold.
        if not is_redundant:
            for anchor_emb in prior_sentence_anchors:
                sim = float(np.dot(sent_emb, anchor_emb))
                if sim > threshold:
                    is_redundant = True
                    break
        if is_redundant:
            waste_count += 1

    # If the caller provided an out-list, hand back this turn's per-sentence
    # embeddings so they can be stashed on the new TurnState — the next
    # turn's TWR call will then have sentence-grained anchors to match.
    if sentence_embeddings_out is not None:
        sentence_embeddings_out.extend(sent_embeddings)

    return waste_count / len(sentences)
