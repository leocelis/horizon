"""Pacing analysis — detect when an agent's deferred-action request is replied
to faster than the action could plausibly have completed.

Motivating failure mode
-----------------------
The agent says: "Try the migration on staging and tell me what happens."
The user replies 4 seconds later: "I'm seeing a yellow warning in the editor."

A naive agent treats the user's reply as a *post-action result* (the migration
was tried, the warning is the outcome) and proceeds to advise on yellow
warnings in migration output. The user, however, was reporting *current
in-progress state* — they hadn't run the migration yet.

The mismatch is detectable from three pieces of evidence Horizon already has:
1. The agent's prior text contained a deferred-state cue ("tell me when…",
   "let me know if…", "report back when…").
2. The inter-turn gap is shorter than the implied completion duration.
3. The user's reply lacks a completion marker ("ran it", "done", "tried it").

When all three line up, Horizon emits `signal.pace_premature_report` so the
agent (or a governance layer) can re-confirm completion before continuing.

Detection here is intentionally lightweight — regex + per-pattern duration
estimates — to keep the core library framework-agnostic, dependency-free, and
fast (sub-millisecond per turn). Apps that want richer detection (e.g. an LLM
classifier) can pre-compute a richer hint and configure a custom threshold.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PacingHint:
    """Lightweight result of scanning one agent message for deferred-action cues.

    Fields:
        has_deferred_action: True if the agent asked the user to do something
            and report back.
        est_min_seconds: Conservative estimate of the minimum time the implied
            action would take. Used as the floor for the gap-too-short test.
        matched_pattern: The regex that matched (for debugging / telemetry).
        action_hint: A short label describing the implied action class
            (e.g. "watch_or_review", "test_or_run", "wait_or_observe").
    """

    has_deferred_action: bool
    est_min_seconds: float
    matched_pattern: str | None
    action_hint: str | None


# Patterns are ordered most-specific → most-general. First match wins.
# Each entry: (regex_pattern, est_min_seconds, action_hint, opinion_safe).
#
# `opinion_safe=True` means this pattern is unambiguously a deferred action
# even if the message also contains opinion-invitation language ("let me know
# what you think of the result"). The negative-gate only applies to patterns
# marked `opinion_safe=False` (the generic last-resort "let me know / tell me"
# patterns that overlap with opinion invitations).
#
# Proximity constraint uses `[^!?\n]` (not `[^.?!]`) so periods inside file
# paths / code blocks (`test_db.py`, `app.config.X`) don't break the match.
_DEFERRED_PATTERNS: list[tuple[str, float, str, bool]] = [
    # "wait N minutes / give it N minutes" — explicit time delay.
    (r"\bwait\s+(\d+)\s*(min|minute|minutes|hour|hours)\b", 120.0, "wait_or_observe", True),
    (r"\bgive\s+it\s+(\d+)\s*(min|minute|minutes|hour|hours)\b", 120.0, "wait_or_observe", True),
    (r"\bcome\s+back\s+(in|after)\b", 300.0, "wait_or_observe", True),
    # "report back when X happens / once you Y" — state change.
    (r"\breport\s+back\b", 60.0, "report_back", True),
    (r"\bonce\s+you[\u2019']?(?:re|ve|d)?\s+(done|finished|ready|tried|tested)\b", 60.0,
     "report_back", True),
    (r"\bwhen\s+you[\u2019']?(?:re|ve|d)?\s+(done|finished|ready)\b", 60.0, "report_back", True),
    (r"\bafter\s+you\s+\w+", 60.0, "report_back", True),
    # "try X and tell me / run X and let me know" — execution.
    (r"\b(try|run|execute|test|deploy|launch|install)\b[^!?\n]{0,200}\b"
     r"(and|then)\s+(let|tell)\s+me\b", 30.0, "test_or_run", True),
    # Multi-step instruction trailing with "let me know".
    (r"\b(read|review|check|look\s+at|skim|go\s+through|study|watch)\b[^!?\n]{0,200}"
     r"\b(let|tell)\s+me\b", 60.0, "watch_or_review", True),
    # Generic deferred prompts — opinion_safe=False because these patterns
    # overlap with "let me know what you think" style invitations. The negative
    # gate is applied before testing these.
    (r"\blet\s+me\s+know\s+(when|once|how|what|whether|if\s+(it|that|you)\s+\w+)\b", 60.0,
     "report_back", False),
    (r"\btell\s+me\s+(when|once|how|what|whether|if\s+(it|that|you)\s+\w+)\b", 60.0,
     "report_back", False),
]


# Patterns that look like deferred-action cues but are NOT — they're invitations
# for opinion or clarification, expected immediately.
# Applied only against opinion_safe=False patterns (see above).
_OPINION_OR_CLARIFICATION_PATTERNS: list[str] = [
    r"\blet\s+me\s+know\s+what\s+you\s+think\b",
    r"\blet\s+me\s+know\s+your\s+thoughts\b",
    r"\btell\s+me\s+what\s+you\s+think\b",
    r"\bif\s+(this|that|it)\s+(makes\s+sense|works\s+for\s+you|sounds\s+(right|good))\b",
    r"\blet\s+me\s+know\s+if\s+(this|that)\s+(makes\s+sense|works|helps)\b",
    r"\bdoes\s+(this|that)\s+(make\s+sense|work|help)\b",
]


# Patterns in the user reply indicating they DID complete the prior action.
# Restricted to past-tense / explicit completion verbs so present-tense phrases
# like "after I think about it" don't falsely suppress the signal.
_COMPLETION_MARKERS: list[str] = [
    r"\b(done|finished|completed|all\s+set)\b",
    r"\bi\s+(ran|tried|tested|did|finished|completed|deployed|installed|read|watched)\b",
    r"\b(it|that|the\s+\w+)\s+(worked|works|failed|crashed|errored|finished|completed|"
    r"passed|ran)\b",
    r"\bhere[\u2019']?s\s+(the\s+)?(result|output|error|log|response|trace)\b",
    r"\b(success|passed|failed|error)\b[^.?!]{0,40}\b(after|when|while|during)\b",
    # "after I <past-tense verb>" — only past-tense completion verbs, not "think" / "wonder"
    r"\b(after|once)\s+i\s+(ran|tried|tested|did|finished|deployed|installed|read|watched|"
    r"restarted|rebooted|updated|upgraded|checked|ran|applied|pushed|merged)\b",
    r"^\s*(yes|yep|yeah|done|ok|okay)[\s,.!]",
]


def detect_deferred_action(agent_text: str) -> PacingHint:
    """Scan an agent message for "do X and report back" patterns.

    For specific, verb-driven patterns (test_or_run, watch_or_review, wait_or_observe,
    report_back) the result is returned immediately — even if the message also
    contains opinion-invitation language ("run the tests and tell me how many fail;
    let me know what you think of the results").

    The opinion negative-gate only applies to the generic low-specificity patterns
    ("let me know when…", "tell me how…") that genuinely overlap with immediate
    clarification asks.
    """
    if not agent_text or not agent_text.strip():
        return PacingHint(False, 0.0, None, None)

    text = agent_text.lower()

    # Pass 1: try all opinion-safe (high-specificity) patterns first, no gate.
    for pattern, est_seconds, action, opinion_safe in _DEFERRED_PATTERNS:
        if opinion_safe and re.search(pattern, text):
            return PacingHint(True, est_seconds, pattern, action)

    # Pass 2: before trying generic patterns, apply the opinion negative-gate.
    is_opinion = any(re.search(neg, text) for neg in _OPINION_OR_CLARIFICATION_PATTERNS)
    if is_opinion:
        return PacingHint(False, 0.0, None, None)

    for pattern, est_seconds, action, opinion_safe in _DEFERRED_PATTERNS:
        if not opinion_safe and re.search(pattern, text):
            return PacingHint(True, est_seconds, pattern, action)

    return PacingHint(False, 0.0, None, None)


def detect_completion_marker(user_text: str) -> bool:
    """Return True if the user's reply explicitly signals action completion.

    Used to suppress `signal.pace_premature_report` when the user clearly says
    they completed the action (even if their reply came back fast — they may
    just be a fast typist or the action was quicker than estimated).
    """
    if not user_text or not user_text.strip():
        return False

    text = user_text.lower()
    for pattern in _COMPLETION_MARKERS:
        if re.search(pattern, text):
            return True
    return False
