"""Coverage for the under-characterised ``alert.contradiction`` and
``alert.verbosity`` events.

The v0.1 audit found these two events fire only ~1 time per 285 turns of
natural conversation — far too sparse to characterise their reliability.
This file exercises both with hand-engineered scenarios that *should*
fire them, plus negative scenarios that *should not* fire them, so we
can establish a basic precision floor without needing a labelled corpus.
"""

from __future__ import annotations

from horizon import Config, FidelityMonitor


def _events_of(result, etype: str) -> list:
    return [e for e in result.events if e.type == etype]


# ── alert.verbosity ─────────────────────────────────────────────────────────


def test_verbosity_fires_on_repetitive_response() -> None:
    """A response that repeats prior turns near-verbatim must trigger alert.verbosity.

    TWR computes per-sentence cosine sim against full prior agent embeddings,
    flagging sentences > 0.85 sim as redundant. To exercise the path we use a
    block of three sentences and re-emit those same sentences verbatim — every
    sentence will match its own prior turn.
    """
    monitor = FidelityMonitor(config=Config(verbosity_threshold=0.3))
    sid = monitor.new_conversation()

    redundant_block = (
        "B-trees are balanced multiway search trees. "
        "B-trees minimise disk seeks via large fanout. "
        "B-trees keep sorted data with logarithmic lookup."
    )

    # Seed turn — same content the next turn will repeat.
    monitor.process_turn(sid, "What is a B-tree?", redundant_block)

    # Now repeat the same content verbatim.
    result = monitor.process_turn(sid, "Explain a bit more.", redundant_block)

    fired = _events_of(result, "alert.verbosity")
    assert fired, (
        f"alert.verbosity should fire on repetitive response (twr={result.twr_value:.3f}, "
        f"threshold=0.3). Events: {[e.type for e in result.events]}"
    )
    assert fired[0].confidence >= 0.3


def test_verbosity_does_not_fire_on_concise_response() -> None:
    monitor = FidelityMonitor(config=Config(verbosity_threshold=0.3))
    sid = monitor.new_conversation()
    monitor.process_turn(sid, "What is async/await?", "Async/await are Python primitives for cooperative concurrency.")
    result = monitor.process_turn(
        sid,
        "And event loops?",
        "An event loop schedules awaitables; asyncio.run() drives the default one.",
    )
    fired = _events_of(result, "alert.verbosity")
    assert not fired, (
        f"alert.verbosity should not fire on concise responses "
        f"(twr={result.twr_value:.3f})"
    )


# ── alert.contradiction ────────────────────────────────────────────────────


def test_contradiction_fires_on_low_consistency() -> None:
    """A turn whose human/agent semantics diverge sharply from history must
    fire alert.contradiction once consistency drops below threshold.
    """
    # The default v0.2 contradiction detector is the explicit-claim
    # ClaimTracker (no coherence fallback), so this regression test
    # — which exercises the embedding-coherence path on a topically
    # incoherent turn — must opt in to ``contradiction_method="coherence"``.
    monitor = FidelityMonitor(
        config=Config(
            consistency_threshold=0.95,
            contradiction_method="coherence",
        )
    )
    sid = monitor.new_conversation()

    # Build a coherent technical dialogue.
    monitor.process_turn(
        sid,
        "How do TCP retransmissions work?",
        "TCP uses ACKs and timers — lost segments are re-sent after RTO expires.",
    )
    monitor.process_turn(
        sid,
        "What about congestion control?",
        "Algorithms like CUBIC and BBR adjust the cwnd to avoid overload.",
    )

    # Now inject a topically incoherent turn — random unrelated content.
    result = monitor.process_turn(
        sid,
        "What's the best brand of dog food?",
        "I prefer salmon-based kibble for senior dogs with sensitive stomachs.",
    )

    fired = _events_of(result, "alert.contradiction")
    assert fired, (
        f"alert.contradiction should fire on incoherent turn "
        f"(consistency={result.consistency_score:.3f}, threshold=0.95). "
        f"Events: {[e.type for e in result.events]}"
    )
    assert fired[0].confidence > 0.0


def test_contradiction_does_not_fire_on_consistent_dialogue() -> None:
    """A coherent technical exchange should not trip alert.contradiction
    at the default threshold.
    """
    monitor = FidelityMonitor()  # default consistency_threshold=0.6
    sid = monitor.new_conversation()
    monitor.process_turn(
        sid,
        "How does asyncio's event loop work?",
        "asyncio's loop schedules coroutines via a cooperative scheduler.",
    )
    result = monitor.process_turn(
        sid,
        "And task cancellation?",
        "Cancellation is cooperative — CancelledError is raised inside the task.",
    )
    fired = _events_of(result, "alert.contradiction")
    assert not fired, (
        f"alert.contradiction should not fire on coherent dialogue "
        f"(consistency={result.consistency_score:.3f})"
    )


def test_alert_signals_respect_active_mode() -> None:
    """``configure(event_modes=...)`` flips an event from observe to active."""
    monitor = FidelityMonitor(config=Config(verbosity_threshold=0.3))
    sid = monitor.new_conversation()
    monitor.configure(session_id=sid, event_modes={"alert.verbosity": "active"})

    redundant_block = (
        "Microservices are independently deployable. "
        "Microservices scale horizontally per service. "
        "Microservices fail in isolation when designed correctly."
    )
    monitor.process_turn(sid, "Tell me about microservices.", redundant_block)
    result = monitor.process_turn(sid, "And again?", redundant_block)
    fired = _events_of(result, "alert.verbosity")
    assert fired, f"verbosity should fire (twr={result.twr_value:.3f})"
    assert fired[0].active is True
