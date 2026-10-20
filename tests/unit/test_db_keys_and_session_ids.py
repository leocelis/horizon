"""DB-registered API keys and caller-chosen session ids on the hosted server.

Two host-application needs (a product that owns its users' identity and runs
one Horizon conversation per chat):

  * A key whose hash the host registers in horizon_api_keys must authenticate
    at once. Before this, the HTTP gate only knew HORIZON_API_KEYS, so a key
    registered at a user's sign-up was refused until a redeploy.
  * A host must be able to re-open the SAME session id after this server
    restarts, so the mission associations the store keeps under that id still
    feed process_turn. Before this, new_conversation always minted a new id.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, date, datetime

import pytest
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from horizon_monitor.mcp import auth as auth_mod
from horizon_monitor.mcp import server as srv
from horizon_monitor.memento.models import ItemKind


def _sha(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


@pytest.fixture
def auth_state():
    orig = (set(auth_mod.VALID_API_KEYS), auth_mod.AUTH_DISABLED, auth_mod.KEY_SHA_LOOKUP)
    auth_mod.clear_key_lookup_cache()
    yield
    auth_mod.VALID_API_KEYS, auth_mod.AUTH_DISABLED, auth_mod.KEY_SHA_LOOKUP = orig
    auth_mod.clear_key_lookup_cache()


@pytest.fixture
def store(tmp_path, auth_state):
    st, _cfg = srv.register_memento_tools(FastMCP("t"), tmp_path / "missions.db")
    yield st
    srv._MEMENTO_SCOPE_RESOLVER = None
    st.close()


def _client() -> TestClient:
    async def _protected(request):
        return JSONResponse({"ok": True, "sha": auth_mod.current_key_sha.get()})

    app = Starlette(routes=[Route("/p", _protected)])
    return TestClient(auth_mod.HorizonAuthMiddleware(app))


def _get(key: str):
    return _client().get("/p", headers={"Authorization": f"Bearer {key}"})


# ── DB-registered keys ───────────────────────────────────────────────────────


def test_key_registered_in_the_store_authenticates_without_env(store):
    auth_mod.VALID_API_KEYS = set()
    auth_mod.AUTH_DISABLED = False
    key = "hzn_acme_registered"
    store.provision_tenant("acme", "Acme", _sha(key), key_label="host-app")

    r = _get(key)
    assert r.status_code == 200
    assert r.json()["sha"] == _sha(key)


def test_unregistered_key_is_refused(store):
    auth_mod.VALID_API_KEYS = set()
    auth_mod.AUTH_DISABLED = False
    assert _get("hzn_nobody_unknown").status_code == 401


def test_revoked_key_is_refused_after_the_cache_window(store):
    auth_mod.VALID_API_KEYS = set()
    auth_mod.AUTH_DISABLED = False
    key = "hzn_acme_soon_revoked"
    store.provision_tenant("acme", "Acme", _sha(key))
    assert _get(key).status_code == 200

    assert store.revoke_key(_sha(key)) is True
    auth_mod.clear_key_lookup_cache()  # the 60 s window elapsing
    assert _get(key).status_code == 401


def test_env_keys_still_work_alongside_registered_keys(store):
    auth_mod.VALID_API_KEYS = {"hzn_env_key"}
    auth_mod.AUTH_DISABLED = False
    assert _get("hzn_env_key").status_code == 200


def test_store_error_during_lookup_is_a_refusal_not_a_crash(auth_state):
    auth_mod.VALID_API_KEYS = set()
    auth_mod.AUTH_DISABLED = False

    def _boom(_sha):
        raise RuntimeError("store down")

    auth_mod.KEY_SHA_LOOKUP = _boom
    assert _get("hzn_any_key").status_code == 401


def test_no_mcp_tool_can_register_a_key_or_a_tenant(tmp_path, auth_state):
    import asyncio

    app = FastMCP("t")
    st, _ = srv.register_memento_tools(app, tmp_path / "m.db")
    try:
        names = {t.name for t in asyncio.run(app.list_tools())}
        names |= {t.name for t in asyncio.run(srv.mcp.list_tools())}
        for forbidden in ("provision_tenant", "ensure_tenant", "revoke_key", "register_key"):
            assert not any(forbidden in n for n in names)
    finally:
        srv._MEMENTO_SCOPE_RESOLVER = None
        st.close()


# ── caller-chosen session ids ────────────────────────────────────────────────


@pytest.fixture
def fresh_server(monkeypatch):
    """A fresh monitor and registry, as after a server restart."""
    from horizon_monitor.mcp.session_registry import SessionRegistry

    monkeypatch.setattr(srv, "_monitor", None)
    monkeypatch.setattr(srv, "_registry", SessionRegistry(max_sessions_per_key=50))
    yield


def _as_key(key_id: str):
    return auth_mod.current_key_id.set(key_id)


def test_same_key_same_id_is_idempotent(fresh_server):
    tok = _as_key("key-a")
    try:
        first = srv.new_conversation(session_id="app-chat:111")
        second = srv.new_conversation(session_id="app-chat:111")
    finally:
        auth_mod.current_key_id.reset(tok)
    assert first == {"session_id": "app-chat:111"}
    assert second == {"session_id": "app-chat:111"}
    assert srv._get_monitor().session_count == 1


def test_another_keys_id_is_refused_like_an_unknown_session(fresh_server):
    tok = _as_key("key-a")
    try:
        srv.new_conversation(session_id="app-chat:222")
    finally:
        auth_mod.current_key_id.reset(tok)
    tok = _as_key("key-b")
    try:
        out = srv.new_conversation(session_id="app-chat:222")
    finally:
        auth_mod.current_key_id.reset(tok)
    assert "error" in out and "Unknown session_id" in out["error"]


def test_invalid_session_id_is_refused(fresh_server):
    out = srv.new_conversation(session_id="has spaces/and slashes")
    assert "error" in out


def test_omitting_session_id_still_mints_a_uuid(fresh_server):
    out = srv.new_conversation()
    assert len(out["session_id"]) == 36


def test_reopened_id_after_restart_still_receives_its_mission_association(
    tmp_path, monkeypatch, auth_state
):
    """The point of H2: the association lives in the store under the session
    id, so re-opening the same id after a restart reconnects it."""
    from horizon_monitor.mcp.session_registry import SessionRegistry

    st, _ = srv.register_memento_tools(FastMCP("t"), tmp_path / "missions.db")
    try:
        sha = _sha("hzn_acme_key")
        st.provision_tenant("acme", "Acme", sha)
        scoped = st.scoped("acme")
        root = scoped.register_item(
            kind=ItemKind.HORIZON,
            title="Acme horizon",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        mission = scoped.register_item(
            kind=ItemKind.MISSION,
            title="Acme mission",
            parent_id=root,
            created_valid=datetime(2026, 1, 2, tzinfo=UTC),
        )
        monkeypatch.setattr(srv, "_memento_store", st)
        sha_tok = auth_mod.current_key_sha.set(sha)
        key_tok = _as_key("acme-key")
        try:
            monkeypatch.setattr(srv, "_monitor", None)
            monkeypatch.setattr(srv, "_registry", SessionRegistry(max_sessions_per_key=50))
            srv.new_conversation(session_id="app-chat:333")
            srv._get_monitor().associate_mission("app-chat:333", mission)

            # restart: memory gone, store kept
            monkeypatch.setattr(srv, "_monitor", None)
            monkeypatch.setattr(srv, "_registry", SessionRegistry(max_sessions_per_key=50))
            assert srv.new_conversation(session_id="app-chat:333") == {"session_id": "app-chat:333"}
            assert mission in scoped.missions_for_session("app-chat:333")
        finally:
            auth_mod.current_key_id.reset(key_tok)
            auth_mod.current_key_sha.reset(sha_tok)
    finally:
        srv._MEMENTO_SCOPE_RESOLVER = None
        st.close()
