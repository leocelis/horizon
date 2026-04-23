"""Tests for session lifecycle: new_conversation, isolation, statefulness."""

from __future__ import annotations

import uuid

import pytest

from horizon import FidelityMonitor, SessionNotFoundError
from tests.conftest import TURN_1_AGENT, TURN_1_HUMAN


def test_new_conversation_returns_uuid(monitor: FidelityMonitor) -> None:
    """new_conversation() must return a valid UUID string."""
    sid = monitor.new_conversation()
    assert isinstance(sid, str)
    # Verify it parses as UUID without raising
    uuid.UUID(sid)


def test_new_conversation_with_explicit_id(monitor: FidelityMonitor) -> None:
    """Caller can provide an explicit session_id."""
    custom_id = "my-custom-session"
    sid = monitor.new_conversation(session_id=custom_id)
    assert sid == custom_id


def test_new_conversation_with_metadata(monitor: FidelityMonitor) -> None:
    """Metadata is accepted without error."""
    sid = monitor.new_conversation(metadata={"domain": "technical", "user_id": "u1"})
    assert isinstance(sid, str)


def test_process_turn_unknown_session_raises(monitor: FidelityMonitor) -> None:
    """process_turn on an unknown session_id must raise SessionNotFoundError."""
    with pytest.raises(SessionNotFoundError):
        monitor.process_turn("nonexistent", TURN_1_HUMAN, TURN_1_AGENT)


def test_session_isolation(monitor: FidelityMonitor) -> None:
    """Two sessions must not share state."""
    sid_a = monitor.new_conversation()
    sid_b = monitor.new_conversation()

    r_a = monitor.process_turn(sid_a, TURN_1_HUMAN, TURN_1_AGENT)
    r_b = monitor.process_turn(sid_b, TURN_1_HUMAN, TURN_1_AGENT)

    assert r_a.turn_number == 1
    assert r_b.turn_number == 1

    # Process a second turn in A only
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN
    monitor.process_turn(sid_a, TURN_2_HUMAN, TURN_2_AGENT)

    traj_a = monitor.get_trajectory(sid_a)
    traj_b = monitor.get_trajectory(sid_b)

    assert traj_a.turn_count == 2
    assert traj_b.turn_count == 1


def test_session_statefulness(monitor: FidelityMonitor) -> None:
    """Turn numbers increment correctly within a session."""
    sid = monitor.new_conversation()
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN, TURN_3_AGENT, TURN_3_HUMAN

    r1 = monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT)
    r2 = monitor.process_turn(sid, TURN_2_HUMAN, TURN_2_AGENT)
    r3 = monitor.process_turn(sid, TURN_3_HUMAN, TURN_3_AGENT)

    assert r1.turn_number == 1
    assert r2.turn_number == 2
    assert r3.turn_number == 3
