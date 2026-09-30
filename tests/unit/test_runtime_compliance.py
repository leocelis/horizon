"""process_turn screens the conversation text through ComplyEdge when the
server has a key.

Before this, no Horizon MCP tool called ComplyEdge: the enforcement seal
counted only the CI probe. Now the MCP process_turn tool sends the turn's
human_message (direction "prompt") and agent_response (direction "output")
to POST /v1/check with the attribution fields the ComplyEdge API reference
names, and turns a violation into an alert.compliance active event. These
tests run the real tool against a local stub of /v1/check.
"""

from __future__ import annotations

import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from horizon_monitor.mcp import server as srv
from horizon_monitor.mcp.auth import current_key_sha

KEY = "ce_test_key_for_stub"
HUMAN = "How do I rotate an API key safely?"
AGENT = "Create the new key, deploy it, then revoke the old one."


@pytest.fixture
def stub(monkeypatch):
    """A fake ComplyEdge; `answers` maps direction -> response fields."""
    state = {"seen": [], "auth": [], "answers": {}, "status": 200}

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state["seen"].append(body)
            state["auth"].append(self.headers.get("Authorization"))
            answer = state["answers"].get(body["direction"], {"allowed": True, "violations": []})
            out = json.dumps({"event_id": f"evt-{body['direction']}", "latency_ms": 1, **answer}).encode()
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


def _turn(key_sha: str = "") -> tuple[str, dict]:
    token = current_key_sha.set(key_sha)
    try:
        sid = srv.new_conversation()["session_id"]
        return sid, srv.process_turn(sid, HUMAN, AGENT, "2026-09-30T12:00:00+00:00")
    finally:
        current_key_sha.reset(token)


def test_turn_is_checked_as_prompt_and_output_with_attribution(stub):
    sha = "a" * 64
    sid, out = _turn(sha)

    by_dir = {b["direction"]: b for b in stub["seen"]}
    assert set(by_dir) == {"prompt", "output"} and len(stub["seen"]) == 2
    assert by_dir["prompt"]["text"] == HUMAN
    assert by_dir["output"]["text"] == AGENT
    for body in stub["seen"]:
        assert body["agent_id"] == "horizon-mcp"
        assert body["jurisdiction"] == "EU"
        assert body["context"] == {
            "user_id": "hzkey:" + "a" * 12,
            "user_role": "mcp_client",
            "session_id": sid,
        }
        assert KEY not in json.dumps(body) and sha not in json.dumps(body)
    assert stub["auth"] == [f"Bearer {KEY}"] * 2
    assert "active_events" not in out or all(e["type"] != "alert.compliance" for e in out["active_events"])


def test_local_turn_is_attributed_to_the_maintainer(stub, monkeypatch):
    monkeypatch.setenv("USER", "alice")
    sid, _ = _turn("")
    assert stub["seen"][0]["context"] == {"user_id": "local:alice", "user_role": "maintainer", "session_id": sid}


def test_flagged_output_comes_back_as_an_active_event(stub):
    stub["answers"]["output"] = {"allowed": False, "violations": [{"rule_id": "rego-art5-1c-001"}]}
    _, out = _turn("b" * 64)
    assert out["ok"] is False
    ev = out["active_events"][0]
    assert ev["type"] == "alert.compliance"
    assert ev["plane"] == "conversation"
    assert ev["rule_ids"] == ["rego-art5-1c-001"]
    assert ev["event_ids"] == ["evt-output"]
    assert "your reply" in ev["suggested_behavior"] and "user's message" not in ev["suggested_behavior"]


def test_flagged_prompt_names_the_users_message(stub):
    stub["answers"]["prompt"] = {"allowed": False, "violations": [{"rule_id": "r-prompt"}]}
    _, out = _turn("c" * 64)
    ev = out["active_events"][0]
    assert ev["type"] == "alert.compliance" and "user's message" in ev["suggested_behavior"]


def test_server_error_fails_open(stub):
    stub["status"] = 500
    _, out = _turn("d" * 64)
    assert all(e["type"] != "alert.compliance" for e in out.get("active_events", []))
    assert "turn" in out or "health_status" in out


def test_unreachable_complyedge_fails_open(monkeypatch):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    monkeypatch.setenv("COMPLYEDGE_API_KEY", KEY)
    monkeypatch.setenv("COMPLYEDGE_API_URL", f"http://127.0.0.1:{port}")
    _, out = _turn("e" * 64)
    assert all(e["type"] != "alert.compliance" for e in out.get("active_events", []))


def test_no_key_means_no_checks(stub, monkeypatch):
    monkeypatch.delenv("COMPLYEDGE_API_KEY")
    _turn("f" * 64)
    assert stub["seen"] == []
