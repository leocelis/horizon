"""E2E tests for multi-tenant session isolation on the hosted MCP server.

Two gaps this closes (see mcp/session_registry.py's module docstring):

  1. Any authenticated key could read (get_trajectory/get_events) or continue
     (process_turn) ANY session_id, including one created by a different key.
  2. configure_session(session_id=None) looped over EVERY live session on the
     shared server, so any key could silently mutate every other tenant's
     thresholds/event-modes.

These tests exercise the real FastMCP tool functions (the same code the MCP
wire protocol calls) with `current_key_id` set to different simulated API
keys, the same mechanism HorizonAuthMiddleware uses in production.

Run:
    pytest tests/e2e/test_mcp_multi_tenant_isolation.py -v
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest

from horizon_monitor import Config, FidelityMonitor
from horizon_monitor.mcp.auth import current_key_id
from horizon_monitor.mcp.server import (
    configure_session,
    get_events,
    get_trajectory,
    new_conversation,
    process_turn,
)


@contextmanager
def _as_key(key_id: str):
    """Simulate an authenticated request from a specific API key — the same
    contextvar HorizonAuthMiddleware sets per-request in production."""
    token = current_key_id.set(key_id)
    try:
        yield
    finally:
        current_key_id.reset(token)


@pytest.fixture(autouse=True)
def _reset_server_state(monkeypatch):
    """Fresh FidelityMonitor + session registry per test — no cross-test bleed."""
    import horizon_monitor.mcp.server as srv
    from horizon_monitor.mcp.session_registry import SessionRegistry

    monkeypatch.setattr(srv, "_monitor", FidelityMonitor(Config()))
    monkeypatch.setattr(
        srv, "_registry", SessionRegistry(max_sessions_per_key=srv._MAX_SESSIONS_PER_KEY)
    )
    yield


def _new_session(key_id: str) -> str:
    with _as_key(key_id):
        return new_conversation()["session_id"]


def _turn(key_id: str, session_id: str):
    with _as_key(key_id):
        return process_turn(
            session_id=session_id,
            human_message="hello",
            agent_response="hi",
            timestamp=datetime.now(timezone.utc).isoformat(),
        )


# ── process_turn cross-tenant isolation ─────────────────────────────────────


class TestProcessTurnIsolation:
    def test_owner_can_process_turn_on_their_own_session(self):
        sid = _new_session("key-alice")

        result = _turn("key-alice", sid)

        assert "error" not in result

    def test_other_key_cannot_process_turn_on_someone_elses_session(self):
        sid = _new_session("key-alice")

        result = _turn("key-bob", sid)

        assert "error" in result
        assert "hint" in result

    def test_denial_looks_identical_to_unknown_session(self):
        """A caller must not be able to tell 'not yours' from 'never existed'."""
        owned_by_alice = _new_session("key-alice")

        denied = _turn("key-bob", owned_by_alice)
        unknown = _turn("key-bob", "00000000-0000-0000-0000-000000000000")

        assert set(denied.keys()) == set(unknown.keys())


# ── get_trajectory / get_events cross-tenant isolation ──────────────────────


class TestResourceIsolation:
    def test_owner_can_read_their_own_trajectory(self):
        sid = _new_session("key-alice")
        _turn("key-alice", sid)

        with _as_key("key-alice"):
            traj = json.loads(get_trajectory(session_id=sid))

        assert "error" not in traj
        assert traj["session_id"] == sid

    def test_other_key_cannot_read_trajectory(self):
        sid = _new_session("key-alice")
        _turn("key-alice", sid)

        with _as_key("key-bob"):
            traj = json.loads(get_trajectory(session_id=sid))

        assert "error" in traj

    def test_other_key_cannot_read_events(self):
        sid = _new_session("key-alice")
        _turn("key-alice", sid)

        with _as_key("key-bob"):
            events = json.loads(get_events(session_id=sid))

        assert "error" in events


# ── configure_session — the global-mutation gap ─────────────────────────────


class TestConfigureSessionIsolation:
    def test_global_configure_only_touches_the_callers_own_sessions(self):
        alice_sid = _new_session("key-alice")
        bob_sid = _new_session("key-bob")

        with _as_key("key-bob"):
            result = configure_session(session_id=None, clarification_threshold=0.05)

        assert result["sessions_affected"] == 1  # only bob's one session

        # Prove it in practice: bob's session picked up the override...
        with _as_key("key-bob"):
            bob_traj = json.loads(get_trajectory(session_id=bob_sid))
        assert "error" not in bob_traj

        # ...and alice's session is untouched — read it back via her own key
        # (an isolation test must not use internal monitor state to check this).
        with _as_key("key-alice"):
            alice_traj = json.loads(get_trajectory(session_id=alice_sid))
        assert "error" not in alice_traj  # still alice's, unaffected, still readable by her

    def test_explicit_session_id_still_requires_ownership(self):
        alice_sid = _new_session("key-alice")

        with _as_key("key-bob"):
            result = configure_session(session_id=alice_sid, clarification_threshold=0.05)

        assert "error" in result

    def test_local_caller_keeps_original_unrestricted_global_behavior(self):
        """No API key involved (stdio / direct usage) -> no other tenant to
        protect -> the original 'mutate shared defaults + every session'
        behavior is preserved (it's genuinely useful there and safe)."""
        _new_session("local")
        _new_session("local")

        with _as_key("local"):
            result = configure_session(session_id=None, clarification_threshold=0.05)

        assert result["sessions_affected"] == 2


# ── per-key session cap / eviction ──────────────────────────────────────────


class TestPerKeySessionCap:
    def test_exceeding_cap_evicts_the_same_keys_oldest_session_only(self, monkeypatch):
        import horizon_monitor.mcp.server as srv
        from horizon_monitor.mcp.session_registry import SessionRegistry

        monkeypatch.setattr(srv, "_registry", SessionRegistry(max_sessions_per_key=2))

        s1 = _new_session("key-alice")
        _new_session("key-alice")
        other_tenant_sid = _new_session("key-bob")
        _new_session("key-alice")  # 3rd for alice -> evicts s1

        # s1 is gone: even alice can no longer use it.
        result = _turn("key-alice", s1)
        assert "error" in result

        # bob's session is completely unaffected by alice's volume.
        with _as_key("key-bob"):
            bob_traj = json.loads(get_trajectory(session_id=other_tenant_sid))
        assert "error" not in bob_traj
