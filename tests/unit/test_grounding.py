"""Tests for the external grounding hook — opt-in tool callout API.

Covers v0.2.0 grounding interface. Two layers of behaviour:

1. The heuristic ``estimate_grounding_need`` — must rise on drafts with
   numeric/cited specifics that are NOT in the human message.
2. The integration with ``FidelityMonitor`` — registering a hook causes
   ``signal.grounding_required`` to fire and evidence to populate the
   ``TurnResult``.

Privacy invariant: with no hook registered, the monitor must make zero
outbound calls (verified by the existing ``test_privacy.py`` plus an
explicit assertion that a unmocked monitor never invokes a hook).
"""

from __future__ import annotations

from horizon import (
    Config,
    FidelityMonitor,
    GroundingHookError,
    GroundingResult,
)
from horizon.grounding import call_hook, estimate_grounding_need


def test_estimate_grounding_need_zero_for_empty_draft() -> None:
    score = estimate_grounding_need(
        human_message="hello",
        agent_draft="hi there",
        divergence_score=0.1,
        consistency_score=0.95,
    )
    assert score == 0.0


def test_estimate_grounding_need_ignores_user_supplied_numbers() -> None:
    """If the user already mentioned the number, the agent isn't fabricating it."""
    score = estimate_grounding_need(
        human_message="We raised $15M Series A at $60M pre.",
        agent_draft="Congrats on the $15M! Here's how to position the $60M valuation.",
        divergence_score=0.1,
        consistency_score=0.9,
    )
    assert score == 0.0


def test_estimate_grounding_need_rises_on_novel_specifics() -> None:
    """Novel dollar amounts, percentages, citations push the score up."""
    score = estimate_grounding_need(
        human_message="Tell me about PostgreSQL performance.",
        agent_draft="A study by Jones et al. (2023) found 47% throughput gains. RFC 9999 says ...",
        divergence_score=0.4,
        consistency_score=0.5,
    )
    assert score > 0.5


def test_register_grounding_hook_triggers_event_and_evidence() -> None:
    calls: list[tuple[str, str]] = []

    def fake_hook(*, human_message: str, agent_draft: str) -> GroundingResult:
        calls.append((human_message, agent_draft))
        return GroundingResult(
            grounded=True,
            evidence=["postgres docs §14.4: pg_prewarm warms the buffer cache"],
            confidence=0.85,
            sources=["https://www.postgresql.org/docs/current/pgprewarm.html"],
        )

    monitor = FidelityMonitor(grounding_hook=fake_hook)
    sid = monitor.new_conversation()
    result = monitor.process_turn(
        sid,
        "How do I warm the PostgreSQL buffer cache?",
        "Per a 2023 benchmark by Jones et al., pg_prewarm gives a 47% boost. RFC 7001 covers this.",
    )

    assert len(calls) == 1, "hook should be invoked when grounding-need crosses threshold"
    assert result.grounding_need >= 0.5
    assert result.grounding_evidence == [
        "postgres docs §14.4: pg_prewarm warms the buffer cache"
    ]
    assert result.grounding_sources == [
        "https://www.postgresql.org/docs/current/pgprewarm.html"
    ]
    assert any(e.type == "signal.grounding_required" for e in result.events)


def test_no_hook_means_no_outbound_callout() -> None:
    """Without a registered hook, grounding_evidence stays empty (privacy invariant)."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    result = monitor.process_turn(
        sid,
        "Tell me about PostgreSQL.",
        "Jones et al. (2023) reported 47% gains; see RFC 9999.",
    )
    assert result.grounding_evidence == []
    assert result.grounding_sources == []
    # The signal still fires — the agent is told to hedge.
    assert any(e.type == "signal.grounding_required" for e in result.events)


def test_hook_failure_does_not_crash_pipeline() -> None:
    def bad_hook(*, human_message: str, agent_draft: str) -> GroundingResult:
        raise RuntimeError("retrieval index offline")

    monitor = FidelityMonitor(grounding_hook=bad_hook)
    sid = monitor.new_conversation()
    result = monitor.process_turn(
        sid,
        "Tell me about Postgres.",
        "Jones et al. (2023) reported 47%; see RFC 9999.",
    )
    assert result.grounding_evidence == []
    assert any(e.type == "signal.grounding_required" for e in result.events)


def test_call_hook_wraps_unexpected_exceptions() -> None:
    def bad_hook(**_: object) -> GroundingResult:
        raise RuntimeError("kaboom")

    try:
        call_hook(bad_hook, human_message="x", agent_draft="y")
    except GroundingHookError as exc:
        assert "kaboom" in str(exc)
        return
    raise AssertionError("expected GroundingHookError")


def test_call_hook_rejects_wrong_return_type() -> None:
    def wrong_type_hook(**_: object):
        return "not a GroundingResult"

    try:
        call_hook(wrong_type_hook, human_message="x", agent_draft="y")
    except GroundingHookError as exc:
        assert "GroundingResult" in str(exc)
        return
    raise AssertionError("expected GroundingHookError")


def test_grounding_threshold_is_configurable() -> None:
    """Tightening the threshold must suppress the event on borderline turns."""
    monitor_default = FidelityMonitor()
    monitor_strict = FidelityMonitor(config=Config(grounding_required_threshold=0.95))

    sid_d = monitor_default.new_conversation()
    sid_s = monitor_strict.new_conversation()

    human = "Tell me about Postgres."
    agent = "Jones et al. (2023) reported 47% gains; see RFC 9999."

    r_d = monitor_default.process_turn(sid_d, human, agent)
    r_s = monitor_strict.process_turn(sid_s, human, agent)

    assert any(e.type == "signal.grounding_required" for e in r_d.events)
    assert not any(e.type == "signal.grounding_required" for e in r_s.events)
