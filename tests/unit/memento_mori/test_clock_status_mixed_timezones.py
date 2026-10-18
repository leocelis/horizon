"""clock_status must not crash when the store mixes naive and UTC-aware times.

Incident 2026-10-18 (hosted horizon.leocelis.com): every clock_status call
returned "can't compare offset-naive and offset-aware datetimes", with or
without an injected timestamp. Items and events are stored as ISO strings;
some callers wrote offset-less strings ("2026-09-17T10:00:00"), while the
store itself writes created_tx / tx_time with +00:00. The read path parsed
them verbatim, so one report compared a naive datetime with an aware one.

Two progress events on ONE item, one with and one without an offset, are
enough: the engine sorts an item's events by valid_time and takes the max.

Property asserted: a store holding offset-less times still yields a report,
for both an injected naive timestamp, an injected "Z" timestamp and the
host clock. Naive values are read as UTC, the same convention
spacetime.temporal.parse_timestamp already applies to process_turn input.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from mcp.server.fastmcp import FastMCP

from horizon_monitor.mcp.server import register_memento_tools


async def _seed(app: FastMCP) -> str:
    root = await app.call_tool(
        "clock_register",
        {
            "item": {
                "kind": "horizon",
                "title": "root",
                "created_valid": "2026-01-01T00:00:00",  # no offset
                "end_date": "2030-01-01",
            }
        },
    )
    root_id = json.loads(root[0].text)["item_id"]
    mission = await app.call_tool(
        "clock_register",
        {
            "item": {
                "kind": "mission",
                "title": "M1",
                "parent_id": root_id,
                "created_valid": "2026-06-01T00:00:00+00:00",  # with offset
            }
        },
    )
    mission_id = json.loads(mission[0].text)["item_id"]
    await app.call_tool(
        "clock_progress",
        {
            "item_id": mission_id,
            "event": {"kind": "progress", "valid_time": "2026-09-01T12:00:00"},  # no offset
        },
    )
    await app.call_tool(
        "clock_progress",
        {
            "item_id": mission_id,
            "event": {"kind": "progress", "valid_time": "2026-09-15T12:00:00+00:00"},  # with offset
        },
    )
    return mission_id


@pytest.mark.parametrize(
    "timestamp",
    ["2026-10-18T12:00:00", "2026-10-18T12:00:00Z", None],
    ids=["injected-naive", "injected-zulu", "host-clock"],
)
def test_clock_status_reports_on_a_store_with_mixed_offsets(tmp_path, timestamp) -> None:
    app = FastMCP("test-mixed-tz")
    register_memento_tools(app, tmp_path / "store.db")

    async def _run() -> dict:
        mission_id = await _seed(app)
        args: dict = {"scope": mission_id}
        if timestamp is not None:
            args["timestamp"] = timestamp
        out = await app.call_tool("clock_status", args)
        return json.loads(out[0].text)

    report = asyncio.run(_run())
    assert "error" not in report, report
    assert report.get("eval_instant_source") in {"injected", "host_clock"}
