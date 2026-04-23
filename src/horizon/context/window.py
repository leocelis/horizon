"""Context window token estimation and eviction tracking."""

from __future__ import annotations

from horizon.session import Session


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return max(1, len(text) // 4)


def update_context_window(session: Session, human_msg: str, agent_resp: str) -> int:
    """Add this turn's token estimate to the session's running total.

    Evicts oldest in-context turns when the estimate exceeds max_context_tokens.
    Returns the number of newly-evicted turns (used to compute delta_irreversible).
    """
    new_tokens = estimate_tokens(human_msg) + estimate_tokens(agent_resp)
    session.context_window_tokens += new_tokens

    evicted = 0
    in_context_turns = [t for t in session.turns if t.in_context]
    while session.context_window_tokens > session.max_context_tokens and in_context_turns:
        oldest = in_context_turns.pop(0)
        # Estimate that turn's token contribution as average share
        turn_tokens = session.context_window_tokens // max(1, len(in_context_turns) + 1)
        oldest.in_context = False
        session.context_window_tokens = max(0, session.context_window_tokens - turn_tokens)
        evicted += 1

    return evicted
