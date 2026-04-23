"""Integration tests for export pipelines.

Referenced by horizon_intent.yaml::implementation.tests[tests/integration/test_export.py].

These tests exercise the end-to-end export flow (process_turn → get_trajectory →
export_to) rather than unit-testing individual export helpers.
"""

from __future__ import annotations

import json

import pytest

from horizon import FidelityMonitor


def _build_session_with_turns(turns: int = 3) -> tuple[FidelityMonitor, str]:
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    scripted = [
        ("How do B-trees work?", "B-trees keep data sorted with logarithmic ops."),
        ("What's the fanout?", "Typically 100-200 children for on-disk layouts."),
        ("Why not binary trees?", "Disk-friendly: fewer seeks per lookup."),
    ]
    for i in range(turns):
        human, agent = scripted[i % len(scripted)]
        monitor.process_turn(sid, human, agent)
    return monitor, sid


def test_json_export() -> None:
    """Full session → JSON export round-trip retains all turn data."""
    monitor, sid = _build_session_with_turns(3)
    result = monitor.export_to(sid, target="json")

    assert result.status == "success"
    assert result.target == "json"
    assert result.records_exported == 3
    assert result.errors == []


def test_export_json_is_serializable() -> None:
    """The JSON payload exposed by get_json_data round-trips through json.dumps."""
    from horizon.integrations.export import get_json_data

    monitor, sid = _build_session_with_turns(2)
    session = monitor._sessions[sid]
    payload = get_json_data(session)

    encoded = json.dumps(payload, default=str)
    decoded = json.loads(encoded)
    assert decoded["turn_count"] == 2
    assert len(decoded["turns"]) == 2
    assert "fidelity_trajectory" in decoded


def test_export_unknown_target_returns_failed() -> None:
    """Unknown export backends surface a clean ExportResult with errors."""
    monitor, sid = _build_session_with_turns(1)
    result = monitor.export_to(sid, target="not-a-real-platform")

    assert result.status == "failed"
    assert result.records_exported == 0
    assert result.errors, "expected at least one error message"


def test_export_langsmith_without_connection_fails_gracefully() -> None:
    """Missing connection parameter is reported, not raised."""
    monitor, sid = _build_session_with_turns(1)
    result = monitor.export_to(sid, target="langsmith", connection=None)
    assert result.status in {"failed", "skipped"}
    if result.status == "failed":
        assert result.errors


def test_export_arize_without_connection_fails_gracefully() -> None:
    """Missing space_id/api_key/model_id for arize is reported, not raised."""
    monitor, sid = _build_session_with_turns(1)
    result = monitor.export_to(sid, target="arize", connection=None)
    assert result.status == "failed"
    assert result.target == "arize"
    assert result.errors
    missing_msg = result.errors[0]
    assert "space_id" in missing_msg
    assert "api_key" in missing_msg
    assert "model_id" in missing_msg


def test_export_arize_is_registered_target() -> None:
    """Arize must be a recognised target (not fall through to 'unknown target')."""
    monitor, sid = _build_session_with_turns(1)
    result = monitor.export_to(
        sid,
        target="arize",
        connection={"space_id": "s", "api_key": "k", "model_id": "m"},
    )
    assert result.target == "arize"
    assert "Unknown export target" not in " ".join(result.errors)


def test_export_after_multi_turn_session_includes_all_events() -> None:
    """Every event emitted during the conversation must appear in the export."""
    from horizon.integrations.export import get_json_data

    monitor, sid = _build_session_with_turns(3)
    payload = get_json_data(monitor._sessions[sid])

    exported_turn_events = sum(len(t.get("events", [])) for t in payload["turns"])
    live_events = len(monitor.get_events(sid))
    assert exported_turn_events == live_events
