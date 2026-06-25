"""External grounding hook — opt-in tool callout for hallucination prevention.

Horizon's brief-only governance has an architectural ceiling: it can flag a
turn as ungrounded but cannot fetch evidence the model lacks. This module
provides a minimal, framework-agnostic interface for plugging an external
grounding source (RAG retrieval, web search, internal KB) into Horizon's
event pipeline.

When a ToolHook is registered, Horizon emits ``signal.grounding_required``
on turns where ungrounded specifics appear likely (high divergence between
human and agent embeddings combined with low consistency, or explicit
mention of hard-to-fabricate entity types like dollar amounts, dates, or
named citations). The hook is then invoked with the human message and the
agent's draft response. The result (a ``GroundingResult``) carries either
verified evidence the agent should cite, or an explicit "no grounding
available" signal that the brief can use to instruct the agent to hedge.

Privacy: hooks are *opt-in*. With no hook registered, Horizon makes zero
outbound calls (the privacy invariant from the intent is preserved).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Protocol


class GroundingHookError(RuntimeError):
    """Raised when the registered grounding hook fails irrecoverably."""


@dataclass(frozen=True)
class GroundingResult:
    """Evidence (or lack thereof) returned by a ToolHook.

    Fields:
        grounded: True if the hook found evidence supporting the agent's
                  draft. False if no supporting evidence was located.
        evidence: List of evidence strings (citations, retrieved snippets,
                  KB entries) that should be attached to the agent's
                  response. Empty when grounded=False.
        confidence: [0, 1] hook's confidence in the evidence. 0 = no
                    grounding; 1 = strong, verified evidence.
        sources: List of source identifiers (URLs, document IDs, KB rows)
                 the agent can cite alongside the evidence.
    """

    grounded: bool
    evidence: list[str] = field(default_factory=list)
    confidence: float = 0.0
    sources: list[str] = field(default_factory=list)


class ToolHook(Protocol):
    """Callable interface for an external grounding tool.

    Implementations receive (human_message, agent_draft) and return a
    GroundingResult. They must not raise on a "no evidence found" outcome
    — return ``GroundingResult(grounded=False)`` instead. They may raise
    GroundingHookError for unrecoverable infrastructure failures.
    """

    def __call__(
        self,
        *,
        human_message: str,
        agent_draft: str,
    ) -> GroundingResult: ...


# Patterns indicating fact-claims that benefit from grounding. Order
# matters only for readability — all patterns are evaluated.
_UNGROUNDED_CLAIM_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\$\s?\d[\d,\.]*\s?(million|billion|k|m|b)?", re.IGNORECASE),
    re.compile(r"\b\d{1,2}(\.\d+)?\s?%"),
    re.compile(r"\b(19|20)\d{2}\b"),
    re.compile(r"\bRFC\s?\d+\b", re.IGNORECASE),
    re.compile(r"\b(?:[A-Z][a-z]+\s+){1,3}et\s+al\.?", re.IGNORECASE),
    re.compile(r"\bhttps?://\S+"),
)


def estimate_grounding_need(
    human_message: str,
    agent_draft: str,
    divergence_score: float,
    consistency_score: float,
) -> float:
    """Return a [0, 1] estimate of how badly the turn needs external grounding.

    Heuristic: a draft contains specific numeric/cited claims (dollar amounts,
    percentages, dates, RFC numbers, "et al." citations, URLs) AND the
    consistency_score is low. We do NOT count claims the user already made
    in their message — those are verifiable against history.
    """
    user_claims = sum(1 for p in _UNGROUNDED_CLAIM_PATTERNS if p.search(human_message))
    draft_claims = sum(1 for p in _UNGROUNDED_CLAIM_PATTERNS if p.search(agent_draft))

    novel_claims = max(0, draft_claims - user_claims)
    if novel_claims == 0:
        return 0.0

    # Saturating function: 1 novel claim = 0.4, 3+ = 0.85+
    claim_signal = min(0.95, 0.4 + 0.2 * (novel_claims - 1))

    # Modulate by inverse consistency — agent disagreeing with priors is more
    # likely to have fabricated.
    consistency_modifier = 1.0 - max(0.0, min(1.0, consistency_score))
    divergence_modifier = max(0.0, min(1.0, divergence_score))

    score = claim_signal * (0.5 + 0.3 * consistency_modifier + 0.2 * divergence_modifier)
    return float(max(0.0, min(1.0, score)))


def call_hook(
    hook: ToolHook | Callable,
    *,
    human_message: str,
    agent_draft: str,
) -> GroundingResult:
    """Invoke a registered hook with consistent error handling.

    Returns a GroundingResult — never raises on "no evidence". Wraps
    infrastructure errors in GroundingHookError so the caller can decide
    whether to surface them or quietly degrade.
    """
    try:
        result = hook(human_message=human_message, agent_draft=agent_draft)
    except GroundingHookError:
        raise
    except Exception as exc:  # noqa: BLE001 — we re-raise as our typed error
        raise GroundingHookError(f"Grounding hook raised: {exc}") from exc

    if not isinstance(result, GroundingResult):
        raise GroundingHookError(
            f"Grounding hook returned {type(result).__name__}, expected GroundingResult"
        )
    return result
