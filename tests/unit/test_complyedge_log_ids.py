"""process_turn hands its ComplyEdge Log IDs back to the caller.

ComplyEdge keeps a keyed fingerprint of the checked text, never the text, and
Horizon keeps no raw text either, so a Log ID (event_id) proves something only
next to the caller's own copy of human_message and agent_response. The IDs go
in the tool result's _meta, outside the result text. These tests run the real
MCP request handler against a local stub of POST /v1/check.
"""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from mcp import types

from horizon_monitor.mcp import server as srv

KEY = "ce_test_key_for_stub"
HUMAN = "How do I rotate an API key safely?"
AGENT = "Create the new key, deploy it, then revoke the old one."


@pytest.fixture
def stub(monkeypatch):
    """A fake ComplyEdge; `answers` maps direction -> response fields."""
    state = {"seen": [], "answers": {}, "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["seen"].append(body)
            answer = state["answers"].get(body["direction"], {"allowed": True, "violations": []})
            out = json.dumps({"event_id": f"evt-{body['direction']}", **answer}).encode()
            self.send_response(state["status"])
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(out)

        def log_message(self, *a):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    monkeypatch.setenv("COMPLYEDGE_API_KEY", KEY)
    monkeypatch.setenv("COMPLYEDGE_API_URL", f"http://127.0.0.1:{server.server_port}")
    yield state
    server.shutdown()


def _wire(name: str, arguments: dict) -> dict:
    """One tools/call through the real low-level handler, as the client gets it."""
    handler = srv.mcp._mcp_server.request_handlers[types.CallToolRequest]
    req = types.CallToolRequest(
        method="tools/call", params=types.CallToolRequestParams(name=name, arguments=arguments)
    )
    result = asyncio.run(handler(req))
    return result.model_dump(by_alias=True, exclude_none=True, mode="json")


def _turn() -> dict:
    sid = srv.new_conversation()["session_id"]
    args = {
        "session_id": sid,
        "human_message": HUMAN,
        "agent_response": AGENT,
        "timestamp": "2026-10-26T12:00:00+00:00",
    }
    return _wire("process_turn", args)


def test_allowed_turn_returns_both_log_ids_outside_the_text(stub):
    wire = _turn()
    assert wire["_meta"]["complyedge"] == {
        "input_event_id": "evt-prompt",
        "output_event_id": "evt-output",
    }
    text = wire["content"][0]["text"]
    assert "evt-" not in text
    assert json.loads(text)["ok"] is True
    # The texts the IDs cover are the caller's own arguments, sent unchanged.
    by_dir = {b["direction"]: b["text"] for b in stub["seen"]}
    assert by_dir == {"prompt": HUMAN, "output": AGENT}


def test_flagged_turn_keeps_the_event_and_the_log_ids(stub):
    stub["answers"]["output"] = {"allowed": False, "violations": [{"rule_id": "r-out"}]}
    wire = _turn()
    assert wire["_meta"]["complyedge"]["output_event_id"] == "evt-output"
    ev = json.loads(wire["content"][0]["text"])["active_events"][0]
    assert ev["type"] == "alert.compliance" and ev["event_ids"] == ["evt-output"]


def test_fail_open_reports_null_log_ids(stub):
    stub["status"] = 500
    wire = _turn()
    assert wire["_meta"]["complyedge"] == {"input_event_id": None, "output_event_id": None}


def test_no_key_means_no_meta(stub, monkeypatch):
    monkeypatch.delenv("COMPLYEDGE_API_KEY")
    wire = _turn()
    assert "_meta" not in wire
    assert stub["seen"] == []


def test_other_tools_carry_no_meta(stub):
    wire = _wire("new_conversation", {})
    assert "_meta" not in wire
    assert stub["seen"] == []
