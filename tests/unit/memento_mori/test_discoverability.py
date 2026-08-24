"""Setup discoverability — can a caller find out what to do?

An unconfigured mission plane and a broken one both return an empty report. A
user who installs the MCP sees six tools and no indication that a root horizon
must exist, that a mission must be registered, or that the agent-rules block
governs how signals are surfaced. The setup steps live in a document nobody
reads before trying.

These pin the two affordances that make the tool surface self-describing.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from horizon_monitor.mcp.server import (
    _setup_guidance,
    get_memento_agent_rules,
    register_memento_tools,
)
from horizon_monitor.memento import ItemKind

UTC = timezone.utc
REPO = Path(__file__).resolve().parents[3]


# ── guidance ─────────────────────────────────────────────────────────────────


def test_an_empty_store_says_what_to_do_next():
    g = _setup_guidance([])
    assert g and "clock_register" in g and "horizon" in g
    assert "end_date" in g


def test_the_guidance_never_invents_the_operators_date():
    """The whole point of the plane is that it accounts and does not estimate.
    A setup hint that suggested a horizon date would cross that line."""
    g = _setup_guidance([])
    assert "OPERATOR chooses" in g and "never" in g
    # no concrete year is offered as a suggestion
    assert not re.search(r"\b20\d\d-\d\d-\d\d\b", g)


def test_a_root_without_a_mission_is_told_the_next_step():
    g = _setup_guidance([{"kind": "horizon", "title": "h"}])
    assert g and "mission" in g
    assert "created_valid" in g and "not today" in g


def test_guidance_goes_quiet_once_a_mission_exists():
    """A setup affordance, not a running commentary."""
    items = [{"kind": "horizon"}, {"kind": "mission"}]
    assert _setup_guidance(items) is None


def test_clock_status_carries_the_guidance_field(tmp_path, monkeypatch):
    import asyncio
    import json

    monkeypatch.setenv("HORIZON_MEMENTO_TENANT_ID", "local")
    app = FastMCP("t")
    store, _cfg = register_memento_tools(app, tmp_path / "m.db")
    try:

        def status():
            res = asyncio.run(
                app.call_tool("clock_status", {"timestamp": "2026-08-18T12:00:00+00:00"})
            )
            body = res[1] if isinstance(res, tuple) else res
            if isinstance(body, list):
                body = json.loads(body[0].text)
            return body.get("result", body)

        empty = status()
        assert empty["setup_guidance"] is not None, "an empty store gave no way forward"

        root = store.register_item(
            kind=ItemKind.HORIZON,
            title="h",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        store.register_item(
            kind=ItemKind.MISSION,
            title="m",
            parent_id=root,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        )

        assert status()["setup_guidance"] is None, "guidance kept talking after setup"
    finally:
        store.close()


# ── agent-rules resource ─────────────────────────────────────────────────────


def test_the_agent_rules_block_is_served_from_the_installed_package():
    """Shipped as package data, so it exists in a wheel — not read from docs/."""
    text = get_memento_agent_rules()
    for section in (
        "SESSION START",
        "WHEN A MISSION EVENT ARRIVES",
        "NEW ITEMS",
        "WRITES",
        "PARKS AND DATES",
        "ACK DISCIPLINE",
        "PROHIBITIONS",
    ):
        assert section in text, f"the served rules block is missing {section!r}"


def test_the_served_block_matches_the_published_one():
    """Drift guard: two copies of a rules block is how they disagree.

    This project already shipped host rules that had silently lost a whole
    section relative to the published block.
    """
    doc = (REPO / "docs/integrations/MEMENTO_MORI_AGENTS.md").read_text(encoding="utf-8")
    published = (
        re.search(r"```text\n(.*?)```", doc.split("## 3.")[1].split("## 4.")[0], re.S)
        .group(1)
        .rstrip()
    )
    assert (
        get_memento_agent_rules().rstrip() == published
    ), "the shipped agent_rules.md has drifted from MEMENTO_MORI_AGENTS.md §3"


@pytest.mark.parametrize("uri", ["horizon://memento/agent-rules"])
def test_the_resource_is_registered_on_the_server(uri):
    import asyncio

    from horizon_monitor.mcp.server import mcp

    uris = {str(r.uri) for r in asyncio.run(mcp.list_resources())}
    assert uri in uris, f"{uri} is not discoverable; found {sorted(uris)}"
