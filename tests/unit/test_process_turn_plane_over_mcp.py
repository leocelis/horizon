"""process_turn over MCP says which plane each event belongs to.

The agent rules route by `plane`: conversation events are applied silently,
mission events are surfaced with their numbers. The MCP response used to
return only {type, suggested_behavior}, so no MCP client could tell a due
mission from a drift alert, and the mission's derivation never reached it.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from mcp.server.fastmcp import FastMCP

from horizon_monitor.mcp import auth as auth_mod
from horizon_monitor.mcp import server as srv
from horizon_monitor.mcp.session_registry import SessionRegistry
from horizon_monitor.memento.models import ItemKind


def test_mission_events_carry_plane_item_and_derivation(tmp_path, monkeypatch):
    store, _cfg = srv.register_memento_tools(FastMCP("t"), tmp_path / "m.db")
    sha = hashlib.sha256(b"hzn_plane_key").hexdigest()
    try:
        store.provision_tenant("acme", "Acme", sha)
        scoped = store.scoped("acme")
        root = scoped.register_item(
            kind=ItemKind.HORIZON,
            title="Freedom",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=datetime(2030, 1, 1).date(),
        )
        mission = scoped.register_item(
            kind=ItemKind.MISSION,
            title="Revenue",
            parent_id=root,
            created_valid=datetime(2026, 1, 2, tzinfo=UTC),
            stall_days=1,
        )
        monkeypatch.setattr(srv, "_memento_store", store)
        monkeypatch.setattr(srv, "_monitor", None)
        monkeypatch.setattr(srv, "_registry", SessionRegistry(max_sessions_per_key=50))
        sha_tok = auth_mod.current_key_sha.set(sha)
        key_tok = auth_mod.current_key_id.set("acme")
        try:
            srv.new_conversation(session_id="app-chat:plane")
            srv._get_monitor().associate_mission("app-chat:plane", mission)
            out = srv.process_turn(
                session_id="app-chat:plane",
                human_message="How is revenue going?",
                agent_response="Let me check the numbers.",
                timestamp="2026-06-01T12:00:00+00:00",
            )
        finally:
            auth_mod.current_key_id.reset(key_tok)
            auth_mod.current_key_sha.reset(sha_tok)
        assert out["ok"] is False
        assert all(e["plane"] in ("conversation", "mission") for e in out["active_events"])
        mission_events = [e for e in out["active_events"] if e["plane"] == "mission"]
        assert mission_events, out
        assert mission_events[0]["item_id"] == mission
        assert mission_events[0]["derivation"]
    finally:
        srv._MEMENTO_SCOPE_RESOLVER = None
        store.close()
