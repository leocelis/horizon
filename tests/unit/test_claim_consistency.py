"""Direct unit coverage for the v0.2 DEFAULT contradiction detector.

``Config.contradiction_method`` defaults to ``"claim_tracker"`` (see
``src/horizon_monitor/config.py``), which is implemented entirely in
``src/horizon_monitor/engines/claim_consistency.py``. Despite being the default
path, it previously had no direct unit tests — ``test_alert_signals.py``
only exercises the legacy ``"coherence"`` fallback.

This file tests the module's real public interface directly:
``ClaimTracker``, ``extract_claims``, ``detect_contradictions``, and
``summarise_conflicts``.
"""

from __future__ import annotations

from horizon_monitor.engines.claim_consistency import (
    ClaimTracker,
    detect_contradictions,
    extract_claims,
    summarise_conflicts,
)

# ── (a) no contradiction across turns ───────────────────────────────────────


def test_no_contradiction_for_unrelated_claims_across_turns() -> None:
    """Claims about different topics must never be compared against each
    other, even though both are numeric "scale"/"percent" claims."""
    tracker = ClaimTracker()

    first = detect_contradictions(tracker, "Revenue grew 20% year over year.", turn_number=1)
    assert first == []

    second = detect_contradictions(
        tracker, "User count grew to 500 users this month.", turn_number=2
    )
    assert (
        second == []
    ), f"unrelated claims across turns must not be flagged as contradictions, got: {second}"


def test_no_contradiction_when_restated_within_tolerance() -> None:
    """A restatement within the relative-tolerance band (default 10%) is a
    paraphrase, not a contradiction."""
    tracker = ClaimTracker()
    detect_contradictions(
        tracker,
        "The new caching layer delivered a 2x speedup in query latency.",
        turn_number=1,
    )
    # 2.1x is within 10% of 2x (5% relative delta) — should not fire.
    result = detect_contradictions(
        tracker,
        "To restate: roughly a 2.1x speedup in query latency.",
        turn_number=2,
    )
    assert result == [], f"restatement within tolerance must not contradict, got: {result}"


def test_no_contradiction_on_honest_retraction() -> None:
    """An explicit retraction marker suppresses the contradiction even
    though the values genuinely disagree."""
    tracker = ClaimTracker()
    detect_contradictions(
        tracker,
        "The new caching layer delivered a 2x speedup in query latency.",
        turn_number=1,
    )
    result = detect_contradictions(
        tracker,
        "Correction: it was actually a 4x speedup in query latency.",
        turn_number=2,
    )
    assert result == [], f"explicit retraction must suppress contradiction, got: {result}"


# ── (b) clear contradiction between an earlier and later turn ──────────────


def test_contradiction_fires_on_conflicting_numeric_claim() -> None:
    """A later turn asserting a materially different value for the same
    topic (no retraction language) must be flagged."""
    tracker = ClaimTracker()
    detect_contradictions(
        tracker,
        "The new caching layer delivered a 2x speedup in query latency.",
        turn_number=1,
    )
    conflicts = detect_contradictions(
        tracker,
        "The new caching layer delivered a 4x speedup in query latency.",
        turn_number=2,
    )

    assert len(conflicts) == 1, f"expected exactly one conflict, got: {conflicts}"
    prior, fresh = conflicts[0]
    assert prior.turn_number == 1
    assert fresh.turn_number == 2
    assert prior.topic_key == "speedup"
    assert fresh.topic_key == "speedup"
    assert prior.value == 2.0
    assert fresh.value == 4.0


def test_contradiction_fires_on_conflicting_year_claim() -> None:
    """Year claims use an absolute (not relative) tolerance: any non-zero
    integer delta is a contradiction, however small the ratio."""
    tracker = ClaimTracker()
    detect_contradictions(tracker, "The rollout is scheduled for release in 2025.", turn_number=1)
    conflicts = detect_contradictions(
        tracker, "The rollout is scheduled for release in 2027.", turn_number=2
    )
    assert len(conflicts) == 1, f"expected exactly one year conflict, got: {conflicts}"
    prior, fresh = conflicts[0]
    assert prior.value == 2025.0
    assert fresh.value == 2027.0


def test_summarise_conflicts_produces_readable_summary() -> None:
    tracker = ClaimTracker()
    detect_contradictions(
        tracker,
        "The new caching layer delivered a 2x speedup in query latency.",
        turn_number=1,
    )
    conflicts = detect_contradictions(
        tracker,
        "The new caching layer delivered a 4x speedup in query latency.",
        turn_number=2,
    )
    summary = summarise_conflicts(conflicts)
    assert "turn 1" in summary
    assert "turn 2" in summary
    assert "2x" in summary
    assert "4x" in summary
    assert "speedup" in summary


# ── (c) edge cases: empty input / single turn ───────────────────────────────


def test_empty_text_does_not_crash_and_yields_no_claims() -> None:
    assert extract_claims("", turn_number=1) == []

    tracker = ClaimTracker()
    result = detect_contradictions(tracker, "", turn_number=1)
    assert result == []
    assert tracker.records == []


def test_single_turn_with_claims_never_contradicts_itself() -> None:
    """With no prior turn to compare against, the very first turn can never
    produce a contradiction, however many claims it contains."""
    tracker = ClaimTracker()
    result = detect_contradictions(
        tracker,
        "We saw a 2x speedup, a 20% cost reduction, and a $500 saving in 2025.",
        turn_number=1,
    )
    assert result == []
    # Claims are still recorded for future-turn comparison.
    assert len(tracker.records) == 4


def test_whitespace_only_text_does_not_crash() -> None:
    tracker = ClaimTracker()
    result = detect_contradictions(tracker, "   \n\t  ", turn_number=1)
    assert result == []
