"""Every agent-instruction surface must route events by PLANE.

The conversation plane is invisible by contract; the mission plane is loud by
contract. Before this test, every shipped instruction surface said "silently
apply active_events[].suggested_behavior" with no plane qualifier — so any host
that enabled the mission plane would have silently absorbed mission signals,
which is precisely the failure that plane exists to prevent.

These are doc↔code consistency assertions: they fail if an instruction surface
is added or edited back into the unscoped form.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]

# Every surface that tells an agent what to do with active_events.
INSTRUCTION_SURFACES = [
    REPO / "docs" / "integrations" / "CLAUDE_CODE.md",
    REPO / "docs" / "integrations" / "CLAUDE_DESKTOP.md",
    REPO / "docs" / "integrations" / "CURSOR.md",
    REPO / "docs" / "cursor-rules" / "horizon-monitor.mdc",
]


@pytest.mark.parametrize("path", INSTRUCTION_SURFACES, ids=lambda p: p.name)
def test_instruction_surface_routes_by_plane(path: Path) -> None:
    assert path.is_file(), f"missing instruction surface: {path}"
    text = path.read_text()

    assert "plane" in text, (
        f"{path.name} never mentions the plane field, so an agent following it "
        "cannot tell a conversation signal from a mission signal"
    )
    assert "MEMENTO_MORI_AGENTS" in text, (
        f"{path.name} does not point at the canonical mission-plane rules"
    )

    # The unscoped instruction is the defect: "silently apply" must never appear
    # without a conversation-plane qualifier near it.
    for idx, line in enumerate(text.splitlines()):
        if "silently apply" in line:
            window = "\n".join(text.splitlines()[max(0, idx - 3) : idx + 3])
            assert "conversation" in window, (
                f"{path.name}:{idx + 1} tells the agent to apply signals silently "
                "without scoping that to the conversation plane"
            )


def test_mcp_server_instructions_route_by_plane() -> None:
    """The server's own _INSTRUCTIONS reach every MCP client automatically —
    the surface that matters most, and the one a docs-only fix would miss."""
    from horizon_monitor.mcp.server import _INSTRUCTIONS

    assert 'plane "mission"' in _INSTRUCTIONS
    assert 'plane "conversation"' in _INSTRUCTIONS
    assert "MEMENTO_MORI_AGENTS.md" in _INSTRUCTIONS
    assert "CONVERSATION plane only" in _INSTRUCTIONS, (
        "the invisibility contract must state which plane it governs"
    )


def test_integrations_index_lists_the_mission_plane() -> None:
    readme = (REPO / "docs" / "integrations" / "README.md").read_text()
    assert "MEMENTO_MORI_AGENTS.md" in readme, (
        "the integration index must list the mission plane, or nobody browsing "
        "integrations will find it"
    )
    assert "mission" in readme.lower()
