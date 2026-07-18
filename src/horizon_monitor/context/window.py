"""Context window token estimation and eviction tracking."""

from __future__ import annotations

from horizon_monitor.session import Session


def estimate_tokens(text: str) -> int:
    """Rough token estimate: ~4 characters per token for English text."""
    return max(1, len(text) // 4)


def update_context_window(session: Session, human_msg: str, agent_resp: str) -> int:
    """Add this turn's token estimate to the session's running total.

    Evicts oldest in-context turns when the estimate exceeds max_context_tokens.
    Returns the number of TOKENS evicted from context this call (not the number
    of turns) — this is unit-consistent with config.min_eviction_threshold,
    which is itself a token-count floor for delta_irreversible.
    """
    new_tokens = estimate_tokens(human_msg) + estimate_tokens(agent_resp)
    session.context_window_tokens += new_tokens

    evicted_tokens = 0
    in_context_turns = [t for t in session.turns if t.in_context]
    while session.context_window_tokens > session.max_context_tokens and in_context_turns:
        oldest = in_context_turns.pop(0)
        # Estimate that turn's token contribution as average share
        turn_tokens = session.context_window_tokens // max(1, len(in_context_turns) + 1)
        oldest.in_context = False
        session.context_window_tokens = max(0, session.context_window_tokens - turn_tokens)
        evicted_tokens += turn_tokens

    return evicted_tokens
