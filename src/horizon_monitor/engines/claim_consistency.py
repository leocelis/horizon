"""Numeric / named-claim contradiction detector.

Why this exists
---------------
Horizon's Tier-1 coherence engine compares embeddings — it cannot tell
that "2x speedup", "4x speedup", and "no speedup" are claims about the
same fact whose values disagree. The V3 structural-failure gate exposed
this as a v0.1 weakness: every case of agent self-contradiction passed
the bipredictability check because each turn was *individually* coherent
with history.

Approach
--------
Per session we keep a small dictionary mapping ``topic_key`` → list of
prior numeric/named claim strings. When the agent emits a new claim for
an already-seen topic and its normalised value differs from the prior
value, we report the conflict.

Topic keys are drawn from short noun-phrase windows around the matched
claim — robust enough for the validation corpus and for typical RAG /
support / coding chats without dragging in heavyweight NLP.

The detector is dependency-free, deterministic, ~1ms per call, and
opt-in via ``Config.contradiction_method = "claim_tracker"``. Turning it
off restores v0.1 behaviour exactly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

# Patterns that mark a fact-claim worth tracking. Each pattern captures
# (a) the value, (b) optional unit/scale, so we can normalise and compare.
_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("scale", re.compile(r"\b(\d+(?:\.\d+)?)\s*[x×]\b", re.IGNORECASE)),
    ("percent", re.compile(r"\b(\d+(?:\.\d+)?)\s*%")),
    ("currency", re.compile(r"\$\s*(\d+(?:[\.,]\d+)*)")),
    ("year", re.compile(r"\b(19|20)(\d{2})\b")),
    ("count", re.compile(r"\b(\d{2,})\s+(?:users|customers|requests|errors|seconds|ms|milliseconds|minutes|hours|days|months)\b", re.IGNORECASE)),
)

# Phrases whose presence indicates the claim is a *retraction* of a prior
# claim — emits no contradiction (the agent is honestly correcting).
_RETRACTION_MARKERS: tuple[str, ...] = (
    "actually",
    "on reflection",
    "correction",
    "i was wrong",
    "updating my prior",
    "scratch that",
    "to clarify",
    "actually it",
    "that was a mistake",
)

_TOPIC_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "for",
    "in", "on", "at", "by", "and", "or", "but", "with", "about", "as",
    "approximately", "approx", "around", "roughly", "actually",
    "reflection", "closer", "earlier", "previously", "now", "still",
    "really", "actually", "really", "very", "much", "more", "less",
    "wrong", "right", "correct", "number", "value", "count", "amount",
    "it", "its", "that", "this", "these", "those", "be", "been",
    "have", "has", "had", "from", "into", "than", "then", "so",
    "no", "not", "yes",
}

# Domain-specific anchor words pre-empt the "nearest content word" heuristic.
# When one of these appears in the surrounding window, it becomes the topic
# key — gives stable matching across rephrasings ("2x speedup" / "4x faster
# speedup" / "no speedup" all key to "speedup").
_TOPIC_ANCHORS: tuple[str, ...] = (
    "speedup", "speed", "latency", "throughput", "price", "cost", "fee",
    "revenue", "users", "customers", "errors", "version", "release",
    "rollout", "date", "deadline", "size", "memory", "storage",
    "accuracy", "precision", "recall", "f1", "score", "rating",
)


@dataclass
class ClaimRecord:
    """One agent-asserted value, paired with the topic key it referred to."""

    topic_key: str
    kind: str              # one of "scale", "percent", "currency", "year", "count"
    value: float
    raw_text: str          # the original matched claim, for diagnostics
    turn_number: int


@dataclass
class ClaimTracker:
    """Per-session memory of agent-asserted facts."""

    records: list[ClaimRecord] = field(default_factory=list)


def _topic_key(text: str, span: tuple[int, int], window: int = 50) -> str:
    """Return a normalised topic key from the words around a matched claim.

    Strategy:
      1. If a domain anchor word (``_TOPIC_ANCHORS``) appears in the window,
         use it — gives stable keys across rephrasings.
      2. Otherwise, pick the closest non-stopword content word adjacent to
         the claim.
      3. Fall back to "_unknown_" only when nothing usable is found.
    """
    start, end = span
    pre = text[max(0, start - window) : start]
    post = text[end : end + window]
    pre_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", pre.lower())
    post_words = re.findall(r"[A-Za-z][A-Za-z0-9_-]{2,}", post.lower())

    for w in reversed(pre_words):
        if w in _TOPIC_ANCHORS:
            return w
    for w in post_words:
        if w in _TOPIC_ANCHORS:
            return w

    for w in reversed(pre_words):
        if w not in _TOPIC_STOPWORDS:
            return w
    for w in post_words:
        if w not in _TOPIC_STOPWORDS:
            return w
    return "_unknown_"


def _is_retraction(text: str) -> bool:
    """Honest retraction → suppress contradiction firing.

    ONLY counts as a retraction when there is a clean acknowledgement of
    the prior mistake (not just the word "actually", which a hedger can
    use to introduce a contradicting claim without owning the change).
    """
    low = text.lower()
    explicit = (
        "i was wrong",
        "my earlier number was wrong",
        "my earlier claim was wrong",
        "correction:",
        "to correct myself",
        "scratch that",
        "updating my prior",
        "discarding what i just said",
        "that was a mistake",
    )
    return any(marker in low for marker in explicit)


def _normalise_value(kind: str, raw: re.Match) -> float:
    g1 = raw.group(1)
    if kind == "currency":
        return float(g1.replace(",", ""))
    if kind == "year":
        return float(g1 + raw.group(2))
    return float(g1)


def extract_claims(text: str, turn_number: int) -> list[ClaimRecord]:
    """Pull every numeric / named claim out of the agent text."""
    out: list[ClaimRecord] = []
    for kind, pattern in _CLAIM_PATTERNS:
        for m in pattern.finditer(text):
            value = _normalise_value(kind, m)
            topic = _topic_key(text, m.span())
            out.append(
                ClaimRecord(
                    topic_key=topic,
                    kind=kind,
                    value=value,
                    raw_text=m.group(0),
                    turn_number=turn_number,
                )
            )
    return out


def _is_contradiction(prior: "ClaimRecord", fresh: "ClaimRecord", relative_tolerance: float) -> bool:
    """Kind-aware contradiction test.

    * year claims: any non-zero integer difference is a contradiction
      (years aren't fuzzy — 2025 ≠ 2027 even though their ratio is ≈ 1).
    * everything else: relative-tolerance band around the prior value.
    """
    if prior.kind == "year":
        return abs(prior.value - fresh.value) >= 1.0
    denom = max(abs(prior.value), abs(fresh.value), 1e-6)
    delta = abs(prior.value - fresh.value) / denom
    return delta > relative_tolerance


def detect_contradictions(
    tracker: ClaimTracker,
    agent_text: str,
    turn_number: int,
    *,
    relative_tolerance: float = 0.10,
) -> list[tuple[ClaimRecord, ClaimRecord]]:
    """Update the tracker with new claims; return (prior, new) pairs that
    contradict. ``relative_tolerance`` is the fractional band within which
    two scale/percent/currency/count values are considered restatements
    rather than contradictions (10% by default). Year claims use absolute
    tolerance (any non-zero integer delta = contradiction)."""
    new_claims = extract_claims(agent_text, turn_number)
    conflicts: list[tuple[ClaimRecord, ClaimRecord]] = []

    is_retraction = _is_retraction(agent_text)

    for fresh in new_claims:
        for prior in tracker.records:
            if prior.kind != fresh.kind:
                continue
            if prior.topic_key != fresh.topic_key:
                continue
            if _is_contradiction(prior, fresh, relative_tolerance) and not is_retraction:
                conflicts.append((prior, fresh))

        tracker.records.append(fresh)

    return conflicts


def summarise_conflicts(
    conflicts: Iterable[tuple[ClaimRecord, ClaimRecord]],
) -> str:
    """Single-line natural-language summary of detected contradictions."""
    parts: list[str] = []
    for prior, fresh in conflicts:
        parts.append(
            f"turn {prior.turn_number} said '{prior.raw_text}' but turn "
            f"{fresh.turn_number} now says '{fresh.raw_text}' "
            f"(topic: {prior.topic_key or 'unknown'})"
        )
    return "; ".join(parts)
