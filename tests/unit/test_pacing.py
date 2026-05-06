"""Tests for horizon.spacetime.pacing — deferred-action detection.

Covers:
  • detect_deferred_action — positive, negative, and false-positive (opinion) cases.
  • detect_completion_marker — recognising explicit completion signals.
  • signal.pace_premature_report — full pipeline integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from horizon import FidelityMonitor
from horizon.spacetime.pacing import detect_completion_marker, detect_deferred_action


# ── detect_deferred_action ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "agent_text, expected_action",
    [
        ("Try the migration on staging and let me know what happens.", "test_or_run"),
        ("Run the test suite and tell me which ones fail.", "test_or_run"),
        ("Read through the design doc and tell me which sections need clarifying.",
         "watch_or_review"),
        ("Once you're done with the install, ping me.", "report_back"),
        ("Wait 5 minutes for the cache to warm up, then come back.", "wait_or_observe"),
        ("Give it 10 minutes and check again.", "wait_or_observe"),
        ("Report back when the deploy finishes.", "report_back"),
        ("Let me know once the build is green.", "report_back"),
        ("After you read it, summarise what you got.", "report_back"),
    ],
)
def test_detects_deferred_actions(agent_text: str, expected_action: str) -> None:
    hint = detect_deferred_action(agent_text)
    assert hint.has_deferred_action is True, f"Should detect deferred action in: {agent_text!r}"
    assert hint.action_hint == expected_action
    assert hint.est_min_seconds > 0


@pytest.mark.parametrize(
    "agent_text",
    [
        "",
        "   ",
        "Here's the answer: Python uses reference counting.",
        "Let me know what you think of this design.",
        "Tell me what you think — does this feel right?",
        "Let me know if this makes sense.",
        "Does this make sense to you?",
        "Let me know your thoughts on the architecture.",
    ],
)
def test_does_not_fire_on_opinion_or_no_action(agent_text: str) -> None:
    """Opinion invitations and plain answers must NOT count as deferred actions."""
    hint = detect_deferred_action(agent_text)
    assert hint.has_deferred_action is False, (
        f"Should NOT detect deferred action in: {agent_text!r}"
    )


def test_deferred_action_not_suppressed_when_also_contains_opinion_language() -> None:
    """A message that says 'run X and tell me; let me know what you think of the results'
    must still detect the deferred action — the opinion language is secondary."""
    agent_text = (
        "Run `pytest -k test_user_signup --count=20` and tell me how many fail. "
        "Let me know what you think of the results once you've seen them."
    )
    hint = detect_deferred_action(agent_text)
    assert hint.has_deferred_action is True, (
        "Specific deferred action (test_or_run) should not be suppressed by co-occurring "
        "opinion language."
    )
    assert hint.action_hint == "test_or_run"


# ── detect_completion_marker ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "user_text",
    [
        "I ran it and got a 500 error.",
        "Done — the test passed.",
        "It worked!",
        "It failed with a connection refused error.",
        "After I deployed, the service crashed.",
        "Here's the result of the migration: success.",
        "Yes, finished the read-through.",
        "Ok, completed.",
    ],
)
def test_detects_completion_markers(user_text: str) -> None:
    assert detect_completion_marker(user_text) is True, (
        f"Should detect completion in: {user_text!r}"
    )


@pytest.mark.parametrize(
    "user_text",
    [
        "",
        "I'm not sure where to start.",
        "What does this error mean?",
        "I see a yellow squiggle in the editor.",
        "I'm still on the first paragraph.",
        # Present-tense "after I think / wonder" must NOT count as completion.
        "After I think about it, I still don't see the issue.",
        "Once I wonder what the problem is I'll let you know.",
    ],
)
def test_does_not_falsely_mark_in_progress_messages(user_text: str) -> None:
    """In-progress / question messages must NOT be flagged as completion."""
    assert detect_completion_marker(user_text) is False, (
        f"Should NOT detect completion in: {user_text!r}"
    )


# ── End-to-end: signal.pace_premature_report ───────────────────────────────────


def _ts(seconds_from: datetime, delta_seconds: float) -> str:
    return (seconds_from + timedelta(seconds=delta_seconds)).isoformat()


def test_pace_premature_report_fires_on_implausibly_fast_reply() -> None:
    """Agent says 'try X and tell me'; user replies 4s later with no completion marker."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)

    # Turn 1 — agent issues a deferred-action instruction.
    monitor.process_turn(
        sid,
        human_message="My migration is hanging on staging.",
        agent_response="Try restarting the migration with `--reset` and tell me what happens.",
        timestamp=_ts(base, 0),
    )
    # Turn 2 — user replies 4 seconds later, mid-action, with no completion marker.
    result = monitor.process_turn(
        sid,
        human_message="I'm seeing a yellow warning in the editor right now.",
        agent_response="That warning is unrelated.",
        timestamp=_ts(base, 4),
    )

    fired = [e.type for e in result.events]
    assert "signal.pace_premature_report" in fired, (
        f"Expected signal.pace_premature_report in {fired}"
    )

    pace = next(e for e in result.events if e.type == "signal.pace_premature_report")
    assert pace.metadata["gap_seconds"] == 4.0
    assert pace.metadata["expected_min_seconds"] >= 30.0
    assert pace.metadata["action_hint"] == "test_or_run"


def test_pace_premature_report_suppressed_by_completion_marker() -> None:
    """If user explicitly says they ran/finished it, the signal must NOT fire."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(
        sid,
        human_message="My migration is hanging on staging.",
        agent_response="Try restarting the migration with `--reset` and tell me what happens.",
        timestamp=_ts(base, 0),
    )
    result = monitor.process_turn(
        sid,
        # Even at 4s, "I ran it" is an explicit completion marker — trust the user.
        human_message="I ran it and got a 500 error immediately.",
        agent_response="A 500 right after restart usually means…",
        timestamp=_ts(base, 4),
    )

    fired = [e.type for e in result.events]
    assert "signal.pace_premature_report" not in fired, (
        f"Should suppress when user signals completion; got events: {fired}"
    )


def test_pace_premature_report_suppressed_when_gap_is_large() -> None:
    """If the user took longer than the implied action, no firing."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(
        sid,
        human_message="My migration is hanging on staging.",
        agent_response="Try restarting the migration with `--reset` and tell me what happens.",
        timestamp=_ts(base, 0),
    )
    # Reply after 10 minutes — well above the 30s threshold for test_or_run.
    result = monitor.process_turn(
        sid,
        human_message="Still trying — the connection just dropped again.",
        agent_response="Let's check the network layer.",
        timestamp=_ts(base, 600),
    )

    fired = [e.type for e in result.events]
    assert "signal.pace_premature_report" not in fired, (
        f"Should not fire on slow replies; got: {fired}"
    )


def test_pace_premature_report_suppressed_when_no_deferred_action() -> None:
    """If the agent didn't ask for deferred action, no firing — even on a fast reply."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 10, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(
        sid,
        human_message="What does TWR stand for in your monitor?",
        agent_response="TWR = Topic Weight Ratio. It measures how much of the response is "
        "off-topic relative to the user's last message.",
        timestamp=_ts(base, 0),
    )
    result = monitor.process_turn(
        sid,
        human_message="Got it — and what's the threshold?",
        agent_response="The default verbosity threshold is 0.5.",
        timestamp=_ts(base, 3),  # fast reply, no deferred action existed
    )

    fired = [e.type for e in result.events]
    assert "signal.pace_premature_report" not in fired, (
        f"Should not fire when no deferred action existed; got: {fired}"
    )
