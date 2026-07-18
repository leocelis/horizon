"""Unit coverage for the MCP HTTP auth middleware (src/horizon_monitor/mcp/auth.py).

``VALID_API_KEYS`` and ``AUTH_DISABLED`` are computed once at import time
from the ``HORIZON_API_KEYS`` / ``HORIZON_AUTH_DISABLED`` env vars, so these
tests mutate the already-imported module's globals directly (monkeypatching
``os.environ`` after import would have no effect) and restore them via an
autouse fixture.

These tests exercise auth.py as it exists right now: unconfigured keys
fail CLOSED (401) unless ``HORIZON_AUTH_DISABLED=true`` is also set, and
key matching uses ``hmac.compare_digest`` per key rather than a plain
``in`` lookup. If this file's assertions ever disagree with the shipped
code, that is a signal to re-read auth.py, not a bug in this file.
"""

from __future__ import annotations

import hashlib

import pytest
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from horizon_monitor.mcp import auth as auth_module


async def _protected(request):
    return JSONResponse({"ok": True, "key_id": auth_module.current_key_id.get()})


async def _health(request):
    return JSONResponse({"status": "healthy"})


def _make_client() -> TestClient:
    app = Starlette(routes=[Route("/protected", _protected), Route("/health", _health)])
    wrapped = auth_module.HorizonAuthMiddleware(app)
    return TestClient(wrapped)


@pytest.fixture(autouse=True)
def _restore_auth_globals():
    """Snapshot/restore module-level auth state so tests don't leak into
    each other (or into other test files importing this module)."""
    orig_keys = set(auth_module.VALID_API_KEYS)
    orig_disabled = auth_module.AUTH_DISABLED
    yield
    auth_module.VALID_API_KEYS = orig_keys
    auth_module.AUTH_DISABLED = orig_disabled


# ── valid configured key ─────────────────────────────────────────────────────


def test_request_with_valid_configured_key_is_allowed() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Bearer hzn_test_validkey123"})

    assert resp.status_code == 200
    expected_key_id = hashlib.sha256(b"hzn_test_validkey123").hexdigest()[:8]
    assert resp.json()["key_id"] == expected_key_id


def test_valid_key_matches_among_multiple_configured_keys() -> None:
    """VALID_API_KEYS membership is checked via hmac.compare_digest per key
    (not a simple `in` lookup) — confirm it still finds a match correctly
    when more than one key is configured."""
    auth_module.VALID_API_KEYS = {"hzn_alice_aaa", "hzn_bob_bbb", "hzn_carol_ccc"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Bearer hzn_bob_bbb"})

    assert resp.status_code == 200
    assert resp.json()["key_id"] == hashlib.sha256(b"hzn_bob_bbb").hexdigest()[:8]


# ── invalid / missing key ────────────────────────────────────────────────────


def test_request_with_invalid_key_is_rejected() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Bearer wrong-key"})

    assert resp.status_code == 401
    assert "Invalid API key" in resp.json()["error"]


def test_request_with_missing_authorization_header_is_rejected() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected")

    assert resp.status_code == 401
    assert "Missing Authorization header" in resp.json()["error"]


def test_request_with_non_bearer_scheme_is_rejected() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Basic hzn_test_validkey123"})

    assert resp.status_code == 401
    assert "Invalid Authorization header" in resp.json()["error"]


def test_request_with_empty_bearer_token_is_rejected() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Bearer "})

    assert resp.status_code == 401
    assert "Empty API key" in resp.json()["error"]


# ── HORIZON_API_KEYS unset (no keys configured at all) ──────────────────────


def test_no_keys_configured_and_auth_not_disabled_is_fail_closed() -> None:
    """Pins down CURRENT behavior: with an empty ``VALID_API_KEYS`` set
    (i.e. ``HORIZON_API_KEYS`` unset/empty) and ``AUTH_DISABLED`` False, the
    middleware rejects every request with a 401 config error rather than
    letting traffic through. This is the fail-closed default.
    """
    auth_module.VALID_API_KEYS = set()
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/protected", headers={"Authorization": "Bearer anything-goes"})

    assert resp.status_code == 401
    assert "no API keys configured" in resp.json()["error"]


def test_no_keys_configured_with_auth_disabled_is_allowed_unconfigured() -> None:
    """When an operator explicitly opts into ``HORIZON_AUTH_DISABLED=true``
    for local dev AND no keys are configured, requests are allowed through
    with key_id "unconfigured". Note this path is distinct from the
    top-level AUTH_DISABLED short-circuit in HorizonAuthMiddleware itself
    (which bypasses ``_extract_and_validate`` entirely) — this exercises
    ``_extract_and_validate``'s own internal AUTH_DISABLED check, reachable
    when the function is called directly (e.g. via ``validate_api_key``).
    """
    auth_module.VALID_API_KEYS = set()
    auth_module.AUTH_DISABLED = True
    err, key_id = auth_module._extract_and_validate(
        {"headers": [(b"authorization", b"Bearer anything-goes")], "path": "/protected"}
    )
    assert err is None
    assert key_id == "unconfigured"


# ── exemptions ────────────────────────────────────────────────────────────


def test_health_path_is_exempt_from_auth_even_with_keys_configured() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = False
    client = _make_client()

    resp = client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "healthy"}


def test_auth_disabled_flag_bypasses_all_checks() -> None:
    auth_module.VALID_API_KEYS = {"hzn_test_validkey123"}
    auth_module.AUTH_DISABLED = True
    client = _make_client()

    resp = client.get("/protected")

    assert resp.status_code == 200


# ── key generation / hashing utilities ──────────────────────────────────────


def test_generate_api_key_has_expected_prefix_and_uniqueness() -> None:
    key1 = auth_module.generate_api_key("alice")
    key2 = auth_module.generate_api_key("alice")

    assert key1.startswith("hzn_alice_")
    assert key1 != key2


def test_hash_api_key_is_deterministic_sha256_hex() -> None:
    digest = auth_module.hash_api_key("hzn_test_validkey123")

    assert digest == hashlib.sha256(b"hzn_test_validkey123").hexdigest()
    assert len(digest) == 64
