"""Cursor rule ↔ MCP server instruction alignment (regression guard)."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CURSOR_RULE = ROOT / "docs" / "cursor-rules" / "horizon-monitor.mdc"


def _load_server_instructions() -> str:
    from horizon.mcp import server as mcp_server

    return mcp_server._INSTRUCTIONS


@pytest.mark.parametrize(
    "phrase",
    [
        "deferred recording",
        "PREVIOUS turn",
        "Never use confidence markers",
        "Never read trajectory or events Resources proactively",
        "configure_session",
        "user-facing",
    ],
    ids=lambda p: p[:24],
)
def test_cursor_rule_contains_core_contract(phrase: str) -> None:
    text = CURSOR_RULE.read_text(encoding="utf-8").lower()
    assert phrase.lower() in text


@pytest.mark.parametrize(
    "phrase",
    [
        "deferred recording",
        "PREVIOUS turn",
        "confidence markers",
        "Never read trajectory or events Resources proactively",
        "configure_session",
        "user-facing",
    ],
    ids=lambda p: p[:24],
)
def test_mcp_instructions_match_cursor_rule(phrase: str) -> None:
    text = _load_server_instructions().lower()
    assert phrase.lower() in text


def test_process_turn_tool_description_uses_deferred_wording() -> None:
    source = (ROOT / "src" / "horizon" / "mcp" / "server.py").read_text(encoding="utf-8").lower()
    assert "deferred recording" in source
    assert "previous turn" in source
    assert "call after every round-trip" not in source
