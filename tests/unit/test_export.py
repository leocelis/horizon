"""Tests for the export module."""

from __future__ import annotations

import pytest

from horizon import FidelityMonitor
from horizon.integrations.export import get_json_data
from tests.conftest import TURN_1_AGENT, TURN_1_HUMAN


def test_export_json_success(monitor: FidelityMonitor, session_id: str) -> None:
    """export_to 'json' returns success status with correct record count."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    result = monitor.export_to(session_id, target="json")
    assert result.status == "success"
    assert result.records_exported == 1
    assert result.target == "json"
    assert result.errors == []


def test_export_unknown_target_fails(monitor: FidelityMonitor, session_id: str) -> None:
    """Unknown export target returns failed status with error message."""
    result = monitor.export_to(session_id, target="unknown_platform")
    assert result.status == "failed"
    assert result.records_exported == 0
    assert len(result.errors) > 0


def test_get_json_data_structure(monitor: FidelityMonitor, session_id: str) -> None:
    """get_json_data returns expected keys."""
    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    session = monitor._sessions[session_id]
    data = get_json_data(session)

    assert "session_id" in data
    assert "turn_count" in data
    assert "turns" in data
    assert "fidelity_trajectory" in data
    assert len(data["turns"]) == 1


def test_export_multiple_turns(monitor: FidelityMonitor, session_id: str) -> None:
    """Export records all turns."""
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN

    monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    monitor.process_turn(session_id, TURN_2_HUMAN, TURN_2_AGENT)

    result = monitor.export_to(session_id, target="json")
    assert result.records_exported == 2
