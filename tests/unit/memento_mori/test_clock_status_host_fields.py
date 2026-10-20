"""clock_status carries what a host app needs to render missions from one read.

A host application that reaches Horizon only over MCP (no library, no store
credentials) must be able to show the root with its end date, the open
missions with theirs, which mission a task sits under, and what is due on a
mission. Before this, item rows had no end_date or parent_id and the response
had no signals at all, so a host had to keep a second path into the store.

Reading what is due must not spend it: the response's signals are evaluated
and never persisted (ledger MM-ASSOCIATION-CIRCULARITY), so a later
process_turn still raises the same signal.
"""

from __future__ import annotations

import asyncio
import json

from mcp.server.fastmcp import FastMCP

from horizon_monitor.mcp.server import register_memento_tools


def _call(app, name, args):
    out = asyncio.run(app.call_tool(name, args))
    blocks = out[0] if isinstance(out, tuple) else out
    return json.loads(blocks[0].text)


def _seed(app):
    root = _call(
        app,
        "clock_register",
        {
            "item": {
                "kind": "horizon",
                "title": "Freedom",
                "created_valid": "2026-01-01T00:00:00+00:00",
                "end_date": "2030-01-01",
            }
        },
    )["item_id"]
    mission = _call(
        app,
        "clock_register",
        {
            "item": {
                "kind": "mission",
                "title": "Revenue",
                "parent_id": root,
                "created_valid": "2026-01-02T00:00:00+00:00",
                "end_date": "2027-01-31",
            }
        },
    )["item_id"]
    task = _call(
        app,
        "clock_register",
        {
            "item": {
                "kind": "task",
                "title": "Ship the site",
                "parent_id": mission,
                "created_valid": "2026-01-03T00:00:00+00:00",
                "ttl_start": "2026-01-03",
                "ttl_end": "2026-02-01",
            }
        },
    )["item_id"]
    return root, mission, task


def test_rows_carry_end_date_and_parent_id(tmp_path):
    app = FastMCP("t")
    store, _ = register_memento_tools(app, tmp_path / "m.db")
    try:
        root, mission, task = _seed(app)
        rows = {
            r["item_id"]: r
            for r in _call(app, "clock_status", {"timestamp": "2026-06-01T00:00:00+00:00"})["items"]
        }
        assert rows[root]["end_date"] == "2030-01-01"
        assert rows[root]["parent_id"] is None
        assert rows[mission]["end_date"] == "2027-01-31"
        assert rows[mission]["parent_id"] == root
        assert rows[task]["parent_id"] == mission
    finally:
        store.close()


def test_signals_are_reported_scoped_and_never_persisted(tmp_path):
    app = FastMCP("t")
    store, _ = register_memento_tools(app, tmp_path / "m.db")
    try:
        root, mission, task = _seed(app)
        before = store.snapshot().fire_states
        out = _call(
            app,
            "clock_status",
            {"scope": mission, "timestamp": "2026-06-01T00:00:00+00:00"},
        )
        # The task's TTL ended 2026-02-01: something is due on this mission.
        assert any(s["item_id"] == task for s in out["signals"])
        assert all(s["item_id"] in {mission, task} for s in out["signals"])
        # Reading wrote no fire state.
        assert store.snapshot().fire_states == before
    finally:
        store.close()
