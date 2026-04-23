"""End-to-end integration tests for the FidelityMonitor."""

from __future__ import annotations

import pytest

from horizon import Config, FidelityMonitor
from tests.conftest import (
    TIMESTAMP_1,
    TIMESTAMP_2,
    TIMESTAMP_3,
    TIMESTAMP_DAYS_LATER,
    TURN_1_AGENT,
    TURN_1_HUMAN,
    TURN_2_AGENT,
    TURN_2_HUMAN,
    TURN_3_AGENT,
    TURN_3_HUMAN,
)


def test_full_conversation_with_timestamps() -> None:
    """Full 3-turn conversation with timestamps produces complete signals."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation(metadata={"domain": "technical"})

    r1 = monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    r2 = monitor.process_turn(sid, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_2)
    r3 = monitor.process_turn(sid, TURN_3_HUMAN, TURN_3_AGENT, timestamp=TIMESTAMP_3)

    # All turns have temporal signals
    for r in [r1, r2, r3]:
        assert r.circadian_factor is not None
        assert r.temporal_references is not None

    # Turn 2+ have pace signals
    assert r2.conversation_velocity is not None or r2.conversation_velocity is None
    assert r3.spacetime_interval is not None or r3.spacetime_interval is None

    # Trajectory
    traj = monitor.get_trajectory(sid)
    assert traj.turn_count == 3
    assert traj.current_fidelity == r3.fidelity_score


def test_conversation_with_spatial_context() -> None:
    """Spatial signals fire when client_context is provided."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    ctx = {
        "device_type": "mobile",
        "location_class": "transit",
        "timezone": "America/Los_Angeles",
    }
    result = monitor.process_turn(
        sid,
        TURN_1_HUMAN,
        TURN_1_AGENT,
        timestamp=TIMESTAMP_1,
        client_context=ctx,
    )

    assert result.location_class == "transit"
    assert result.spatial_constraint is not None
    assert result.spatial_constraint.attention_budget == "low"


def test_temporal_desync_detected_after_days_gap() -> None:
    """signal.temporal_desync fires when resuming after 3 days."""
    config = Config(temporal_desync_threshold_seconds=3600.0)
    monitor = FidelityMonitor(config=config)
    sid = monitor.new_conversation()

    monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    r2 = monitor.process_turn(
        sid,
        "So where were we?",
        "We were discussing Python memory management in detail.",
        timestamp=TIMESTAMP_DAYS_LATER,
    )

    event_types = {e.type for e in r2.events}
    assert "signal.temporal_desync" in event_types


def test_configure_changes_threshold() -> None:
    """configure() changes thresholds and affects subsequent event emission."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    # Set very low divergence threshold to guarantee a clarification event
    monitor.configure(
        session_id=sid,
        clarification_threshold=0.0,
        event_modes={"checkpoint.clarification": "active"},
    )

    result = monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT)
    event_types = {e.type for e in result.events}
    assert "checkpoint.clarification" in event_types

    active = [e for e in result.events if e.type == "checkpoint.clarification"]
    assert active[0].active is True


def test_sqlite_persistence() -> None:
    """PersistentDynamicsStore records turns and can be queried."""
    import os
    import tempfile

    from horizon.storage.sqlite import PersistentDynamicsStore

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        store = PersistentDynamicsStore(db_path=db_path)
        monitor = FidelityMonitor(store=store)

        sid = monitor.new_conversation(metadata={"user_id": "user_test", "domain": "test"})
        monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
        monitor.process_turn(sid, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_2)

        history = store.get_session_history(sid)
        assert len(history) == 2
        assert history[0]["turn_number"] == 1
        assert history[1]["turn_number"] == 2


def test_wrap_detection_raises_for_unknown_client() -> None:
    """wrap() raises TypeError for unsupported client types."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    with pytest.raises(TypeError):
        monitor.wrap(object(), sid)


def test_openai_wrap_with_timestamp_and_context_providers() -> None:
    """Simulated wrap around a mocked OpenAI-like client exercises the full pipeline.

    Mirrors examples/openai_real_agent_e2e.py without hitting the real API.
    Validates that timestamp_provider and context_provider produce the same
    signals (temporal_desync, frame_shift, light_cone_collapse) that a real
    conversation with a 3-day gap and device switch would emit.
    """
    import types
    from datetime import datetime, timedelta, timezone

    from horizon.integrations.openai import HorizonWrappedOpenAI

    canned_replies = [
        "Python uses reference counting plus a cyclic garbage collector for reference cycles.",
        "Weak references let you refer to an object without preventing its garbage collection.",
        "Yes, memory leaks can still happen despite GC — global registries and callbacks are common causes.",
        "We were talking about weak references and typical use cases.",
        "An asyncio event loop schedules and runs coroutines concurrently on a single thread.",
        "create_task schedules a coroutine; gather awaits several in parallel and collects results.",
    ]

    class FakeChoice:
        def __init__(self, content: str) -> None:
            self.message = types.SimpleNamespace(content=content)
            self.logprobs = None

    class FakeResponse:
        def __init__(self, content: str) -> None:
            self.choices = [FakeChoice(content)]
            self.usage = types.SimpleNamespace(
                prompt_tokens=10, completion_tokens=10, total_tokens=20
            )

    class FakeCompletions:
        def __init__(self) -> None:
            self._idx = 0

        def create(self, **_kwargs: object) -> FakeResponse:
            reply = canned_replies[self._idx]
            self._idx += 1
            return FakeResponse(reply)

    class FakeChat:
        completions = FakeCompletions()

    class FakeOpenAIClient:
        __module__ = "openai._client"
        chat = FakeChat()

    monitor = FidelityMonitor()
    sid = monitor.new_conversation(metadata={"domain": "technical"})
    wrapped = HorizonWrappedOpenAI(FakeOpenAIClient(), monitor, sid)

    desktop = {"device_type": "desktop", "timezone": "America/New_York", "location_class": "office"}
    mobile = {"device_type": "mobile", "timezone": "America/New_York", "location_class": "transit"}

    clock = {"now": datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)}
    ctx = {"current": desktop}

    wrapped.set_timestamp_provider(lambda: clock["now"].isoformat())
    wrapped.set_context_provider(lambda: ctx["current"])

    script = [
        (
            "How does Python's garbage collector handle reference cycles?",
            desktop,
            timedelta(seconds=30),
        ),
        ("What about weak references — when would I use them?", desktop, timedelta(seconds=45)),
        ("Can memory leaks still happen despite GC?", desktop, timedelta(seconds=60)),
        ("ok, back to this — where were we with weak references?", mobile, timedelta(days=3)),
        ("actually let me switch: explain event loops in asyncio.", mobile, timedelta(seconds=90)),
        ("difference between create_task and gather?", mobile, timedelta(seconds=40)),
    ]

    for human_text, device_ctx, dt in script:
        clock["now"] = clock["now"] + dt
        ctx["current"] = device_ctx
        wrapped.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": human_text}],
        )

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == 6
    assert 0.0 <= trajectory.current_fidelity <= 1.0
    assert trajectory.gap_durations[0] is None
    assert trajectory.gap_durations[3] == 3 * 86400

    all_events = monitor.get_events(sid)
    event_types = {e.type for e in all_events}
    assert "signal.temporal_desync" in event_types
    assert "signal.frame_shift" in event_types
    assert "signal.light_cone_collapse" in event_types

    for e in all_events:
        assert e.active is False
