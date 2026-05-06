"""
Authentication middleware for the Horizon MCP server.

Reads API keys from the HORIZON_API_KEYS environment variable (comma-separated).

For local stdio:  auth not required (process isolation; no HTTP layer).
For remote HTTP:  Bearer token required in every request except /health.

Usage:
    Authorization: Bearer hzn_<username>_<token>

Key generation:
    python -c "import secrets; print('hzn_leo_' + secrets.token_urlsafe(24))"
"""

from __future__ import annotations

import hashlib
import logging
import os
import secrets
from typing import Optional, Tuple

from starlette.requests import Request
from starlette.responses import JSONResponse

_log = logging.getLogger("horizon.mcp.auth")

# ── Key store ─────────────────────────────────────────────────────────────────

_raw = os.environ.get("HORIZON_API_KEYS", "")
VALID_API_KEYS: set[str] = {k.strip() for k in _raw.split(",") if k.strip()}

# Set HORIZON_AUTH_DISABLED=true for local dev / unit tests only.
AUTH_DISABLED: bool = os.environ.get("HORIZON_AUTH_DISABLED", "false").lower() == "true"

# Paths that never require auth.
_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/healthz"})


# ── ASGI middleware ────────────────────────────────────────────────────────────


class HorizonAuthMiddleware:
    """ASGI middleware that validates Bearer tokens for all non-exempt paths."""

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")

        if path in _EXEMPT_PATHS or AUTH_DISABLED:
            await self.app(scope, receive, send)
            return

        err, key_id = _extract_and_validate(scope)
        if err is not None:
            response = JSONResponse(err, status_code=401)
            await response(scope, receive, send)
            return

        _log.info("AUTH  ok  key=%s  path=%s", key_id, path)
        await self.app(scope, receive, send)


# ── Validation helpers ────────────────────────────────────────────────────────


def _extract_and_validate(scope) -> Tuple[Optional[dict], Optional[str]]:
    """
    Extract and validate the Bearer token from scope headers.

    Returns:
        (error_body, key_id) — error_body is None on success.
    """
    headers: dict[bytes, bytes] = dict(scope.get("headers", []))
    raw_auth: str = headers.get(b"authorization", b"").decode("utf-8", errors="replace")

    if not raw_auth:
        _log.warning("AUTH  missing_header  path=%s", scope.get("path", ""))
        return {"error": "Missing Authorization header"}, None

    if not raw_auth.startswith("Bearer "):
        _log.warning("AUTH  bad_format  path=%s", scope.get("path", ""))
        return {"error": "Invalid Authorization header. Expected: Bearer <token>"}, None

    api_key = raw_auth[7:].strip()

    if not api_key:
        _log.warning("AUTH  empty_key  path=%s", scope.get("path", ""))
        return {"error": "Empty API key"}, None

    if not VALID_API_KEYS:
        # No keys configured at all — allow (mirrors local dev behaviour).
        _log.warning("AUTH  no_keys_configured  path=%s  — allowing", scope.get("path", ""))
        return None, "unconfigured"

    if api_key not in VALID_API_KEYS:
        _log.warning("AUTH  invalid_key  key_prefix=%s  path=%s", api_key[:8], scope.get("path", ""))
        return {"error": "Invalid API key"}, None

    return None, _key_id(api_key)


def _key_id(api_key: str) -> str:
    """Return a safe 8-char identifier for logging (never logs the full key)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:8]


# ── Starlette route-level helper (used by deploy/wsgi.py) ─────────────────────


async def validate_api_key(request: Request) -> Tuple[Optional[JSONResponse], Optional[str]]:
    """
    Validate the API key from a Starlette Request object.

    Returns (None, key_id) on success, (JSONResponse 401, None) on failure.
    Compatible with the IVD auth pattern.
    """
    if AUTH_DISABLED:
        return None, None

    path = request.url.path
    if path in _EXEMPT_PATHS:
        return None, None

    err, key_id = _extract_and_validate({"headers": list(request.headers.raw), "path": path})
    if err is not None:
        return JSONResponse(err, status_code=401), None
    return None, key_id


# ── Key generation utilities ──────────────────────────────────────────────────


def generate_api_key(username: str = "user") -> str:
    """Generate a new Horizon API key: hzn_{username}_{token}."""
    token = secrets.token_urlsafe(24)
    return f"hzn_{username}_{token}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage / comparison."""
    return hashlib.sha256(api_key.encode()).hexdigest()
