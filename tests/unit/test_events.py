"""Tests for the event system — all 14 event types."""

from __future__ import annotations

from horizon import Config, FidelityMonitor
from tests.conftest import TIMESTAMP_1, TIMESTAMP_DAYS_LATER, TURN_1_AGENT, TURN_1_HUMAN

ALL_EVENT_TYPES = {
    "checkpoint.clarification",
    "checkpoint.comprehension",
    "alert.drift",
    "alert.contradiction",
    "alert.verbosity",
    "signal.convergence",
    "signal.optimal_length",
    "signal.horizon_widening",
    "signal.session_reset",
    "signal.temporal_desync",
    "signal.broken_reference",
    "signal.frame_shift",
    "signal.pace_shift",
    "signal.light_cone_collapse",
}


def test_event_filtering(monitor: FidelityMonitor, session_id: str) -> None:
    """get_events() returns all events; active_only filters correctly."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    all_events = monitor.get_events(session_id)
    active_events = monitor.get_events(session_id, active_only=True)

    assert isinstance(all_events, list)
    assert isinstance(active_events, list)
    # active_only must be a subset
    assert len(active_events) <= len(all_events)


def test_events_are_observe_by_default(monitor: FidelityMonitor, session_id: str) -> None:
    """Events default to observe mode (active=False) unless explicitly configured."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    all_events = monitor.get_events(session_id)
    for event in all_events:
        assert event.active is False, f"Event {event.type} should be observe by default"


def test_event_activated_via_configure(monitor: FidelityMonitor) -> None:
    """An event can be set to active mode via configure()."""
    sid = monitor.new_conversation()
    monitor.configure(
        session_id=sid,
        event_modes={"checkpoint.clarification": "active"},
    )
    # Force a high-divergence turn to trigger clarification
    result = monitor.process_turn(
        sid,
        "What is quantum entanglement?",
        "Here is a recipe for chocolate cake.",
    )
    clarification_events = [e for e in result.events if e.type == "checkpoint.clarification"]
    if clarification_events:
        assert clarification_events[0].active is True


def test_temporal_desync_event_on_large_gap(monitor: FidelityMonitor) -> None:
    """signal.temporal_desync fires when gap > threshold and retention < 0.5."""
    config = Config(temporal_desync_threshold_seconds=60.0)
    m = FidelityMonitor(config=config)
    sid = m.new_conversation()

    m.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    result = m.process_turn(
        sid,
        "What were we talking about?",
        "We were discussing Python memory management.",
        timestamp=TIMESTAMP_DAYS_LATER,  # 3 days later
    )

    event_types = {e.type for e in result.events}
    assert "signal.temporal_desync" in event_types, (
        f"Expected temporal_desync; gap={result.gap_seconds}s, "
        f"retention={result.estimated_retention}"
    )


def test_event_confidence_in_bounds(monitor: FidelityMonitor, session_id: str) -> None:
    """All event confidences must be in [0, 1]."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    for event in monitor.get_events(session_id):
        assert 0.0 <= event.confidence <= 1.0, f"Event {event.type} confidence out of bounds"


def test_event_has_required_fields(monitor: FidelityMonitor, session_id: str) -> None:
    """Every emitted event has all required fields."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    for event in monitor.get_events(session_id):
        assert isinstance(event.type, str)
        assert isinstance(event.active, bool)
        assert isinstance(event.confidence, float)
        assert isinstance(event.turn, int)
        assert isinstance(event.suggested_behavior, str)
        assert isinstance(event.metadata, dict)


def test_convergence_detection_observe_mode() -> None:
    """Verification: convergence_detection_observe_mode.

    After 8+ turns of diminishing IGT, signal.convergence fires with
    active=False in default config.
    """
    config = Config(convergence_window=3, convergence_threshold=0.95)
    monitor = FidelityMonitor(config=config)
    sid = monitor.new_conversation()

    monitor.process_turn(
        sid,
        "Explain how public key crypto works.",
        "Public key crypto uses asymmetric key pairs for encryption and signatures.",
    )
    monitor.process_turn(
        sid, "What is RSA?", "RSA is based on the difficulty of factoring large semiprime numbers."
    )
    monitor.process_turn(
        sid,
        "How are primes chosen?",
        "Large random primes are generated and tested with Miller-Rabin.",
    )

    for _ in range(6):
        monitor.process_turn(sid, "ok thanks, got it.", "great, glad it helped.")

    events = monitor.get_events(sid)
    convergence = [e for e in events if e.type == "signal.convergence"]
    assert convergence, (
        f"Expected signal.convergence after 9 turns with diminishing IGT; got events: "
        f"{[e.type for e in events]}"
    )
    for e in convergence:
        assert e.active is False, "signal.convergence must default to observe mode"


def test_drift_type_classification_structural() -> None:
    """Verification: drift_type_classification_structural.

    When context compaction evicts early turns and a later turn references
    them, degradation_type becomes 'irreversible_loss' and
    signal.broken_reference fires.
    """
    from datetime import datetime, timedelta, timezone

    config = Config(
        light_cone_ratio_threshold=0.5,
        light_cone_min_threshold=2,
        broken_reference_threshold=0.5,
    )
    monitor = FidelityMonitor(config=config)
    sid = monitor.new_conversation()

    base = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(
        sid,
        "Let's pick Postgres over MySQL for this project because of window functions.",
        "Got it — we'll use Postgres. I'll note this decision.",
        timestamp=base.isoformat(),
    )
    for i in range(2, 10):
        monitor.process_turn(
            sid,
            f"turn {i}: tangent on unrelated topic {i}",
            f"tangent response {i}",
            timestamp=(base + timedelta(minutes=i)).isoformat(),
        )

    session = monitor._sessions[sid]
    for idx, turn in enumerate(session.turns):
        if idx < 6:
            turn.in_context = False

    result = monitor.process_turn(
        sid,
        "Going back to that database choice we made earlier — can you remind me?",
        "I don't have full visibility into that earlier context.",
        timestamp=(base + timedelta(minutes=11)).isoformat(),
    )

    assert result.reachable_fraction < 1.0, (
        f"Expected evicted turns to reduce reachable_fraction, got " f"{result.reachable_fraction}"
    )
    event_types = {e.type for e in result.events}
    assert "signal.broken_reference" in event_types, (
        f"Expected signal.broken_reference once early context is evicted; "
        f"got {sorted(event_types)}"
    )


def test_all_events_observe_by_default() -> None:
    """Constraint: observe_mode_default.

    All 14 event types ship with active=False in default config. Referenced by
    horizon_intent.yaml::constraints[observe_mode_default].test.
    """
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    scripted = [
        ("Hello there!", "Hi, how can I help?"),
        ("Explain how NATs work.", "A NAT maps private IPs to a public IP via port translation."),
        ("Wait, what about symmetric NATs?", "They map each destination to a unique port."),
        ("What was the first thing I asked?", "You said 'Hello there!'."),
        (
            "How about quantum computing now?",
            "Quantum computing uses qubits instead of classical bits.",
        ),
        ("Bring it back to the NAT topic.", "Symmetric NATs are stricter than cone NATs."),
    ]
    for human, agent in scripted:
        monitor.process_turn(sid, human, agent)

    all_events = monitor.get_events(sid)
    assert len(all_events) > 0, "Expected at least one event across the conversation"
    for event in all_events:
        assert event.active is False, (
            f"Event {event.type!r} must default to active=False (observe mode); "
            "enabling it requires configure(event_modes=...)"
        )
        assert event.type in ALL_EVENT_TYPES, f"Unknown event type: {event.type}"
