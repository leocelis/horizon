"""Conversation mode detector — classifies current session context."""

from __future__ import annotations

import numpy as np
from numpy import ndarray

from horizon.session import Session


def detect_conversation_mode(
    session: Session,
    human_embedding: ndarray,
    turn_number: int,
) -> str:
    """Classify the current conversation mode from recent signal patterns.

    Modes:
    - execute: specific task in progress, high specificity
    - explore: broad discovery, high information gain, diverse topics
    - refine: iterative improvement, converging on target
    - learn: teaching pattern, high coherence with repetition
    """
    if turn_number <= 2:
        return "explore"

    recent = session.turns[-3:]
    avg_igt = sum(t.igt_value for t in recent) / len(recent)
    avg_djs = sum(t.divergence_score for t in recent) / len(recent)
    avg_twr = sum(t.twr_value for t in recent) / len(recent)
    avg_consistency = sum(t.consistency_score for t in recent) / len(recent)

    # High specificity (low D_JS) + low information gain (converging) = execute
    if avg_djs < 0.2 and avg_igt < 0.3:
        return "execute"

    # High redundancy + high coherence = learn/teach pattern
    if avg_twr > 0.4 and avg_consistency > 0.7:
        return "learn"

    # Low information gain + low divergence + moderate consistency = refine
    if avg_igt < 0.3 and avg_djs < 0.35 and avg_consistency > 0.5:
        return "refine"

    # High information gain + higher divergence = explore
    return "explore"
