"""
Authentication middleware for the Horizon MCP server.

Reads API keys from the HORIZON_API_KEYS environment variable (comma-separated).

For local stdio:  auth not required (process isolation; no HTTP layer).
For remote HTTP:  Bearer token required in every request except /health.

Usage:
    Authorization: Bearer hzn_<username>_<token>

Key generation:
    python -c "import secrets; print('hzn_deploy_' + secrets.token_urlsafe(24))"
"""

from __future__ import annotations

import collections
import contextvars
import hashlib
import hmac
import logging
import os
import secrets
import threading
import time

from starlette.requests import Request
from starlette.responses import JSONResponse

# ── Per-request context: key_id of the currently authenticated caller ─────────
# Set by HorizonAuthMiddleware after successful auth; read by tool handlers
# for structured logging. Defaults to "local" so stdio/unit-test callers
# that bypass HTTP auth still produce readable log lines.
current_key_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "horizon_current_key_id", default="local"
)

_log = logging.getLogger("horizon_monitor.mcp.auth")

# ── Key store ─────────────────────────────────────────────────────────────────

_raw = os.environ.get("HORIZON_API_KEYS", "")
VALID_API_KEYS: set[str] = {k.strip() for k in _raw.split(",") if k.strip()}

# Set HORIZON_AUTH_DISABLED=true for local dev / unit tests only.
AUTH_DISABLED: bool = os.environ.get("HORIZON_AUTH_DISABLED", "false").lower() == "true"

# Paths that never require auth.
_EXEMPT_PATHS: frozenset[str] = frozenset({"/health", "/healthz"})

# ── Rate limiting ────────────────────────────────────────────────────────────
#
# Per-key token bucket, in-process. Correct for Horizon's hosted deployment
# (DigitalOcean App Platform, instance_count=1 as of this writing) — a
# distributed limiter (Redis-backed) would be required if the app ever scales
# to multiple instances, since each instance would otherwise enforce the limit
# independently and the effective ceiling would multiply by instance count.
#
# Only authenticated requests reach the limiter (see HorizonAuthMiddleware):
# rate-limiting unauthenticated attempts would not meaningfully slow a brute
# force (API keys are 192 bits of secrets.token_urlsafe(24) entropy — not
# brute-forceable regardless of request rate) and would let an attacker grow
# this dict unboundedly by presenting many distinct bogus tokens. Limiting
# only validated keys keeps the tracked-key set bounded by the number of keys
# actually issued.
RATE_LIMIT_PER_MINUTE: float = float(os.environ.get("HORIZON_RATE_LIMIT_PER_MINUTE", "120"))
RATE_LIMIT_BURST: float = float(os.environ.get("HORIZON_RATE_LIMIT_BURST", "20"))
_MAX_TRACKED_RATE_LIMIT_KEYS = 1000


class _TokenBucket:
    __slots__ = ("tokens", "last_refill")

    def __init__(self, capacity: float, now: float) -> None:
        # `now` is passed in (rather than calling time.monotonic() here) so a
        # freshly created bucket's timestamp exactly matches the caller's
        # already-captured `now` — otherwise construction takes strictly
        # longer than zero time, `last_refill` ends up a hair AFTER the
        # caller's `now`, and the first elapsed-time computation goes
        # negative. That epsilon is invisible most of the time but flips the
        # `>= 1.0` boundary check exactly at low burst values (burst=1 in
        # particular), causing the very first call to a fresh bucket to be
        # rejected and the second call to spuriously "refill" and succeed.
        self.tokens = capacity
        self.last_refill = now


class RateLimiter:
    """In-process, thread-safe, per-key token-bucket rate limiter.

    `allow(key)` refills `key`'s bucket based on elapsed time, then consumes
    one token if available. Bounded to `max_tracked_keys` distinct keys
    (LRU-evicted) as a defensive cap.
    """

    def __init__(
        self,
        rate_per_minute: float = RATE_LIMIT_PER_MINUTE,
        burst: float = RATE_LIMIT_BURST,
        max_tracked_keys: int = _MAX_TRACKED_RATE_LIMIT_KEYS,
    ) -> None:
        self._rate_per_second = rate_per_minute / 60.0
        self._burst = burst
        self._max_tracked = max_tracked_keys
        self._buckets: collections.OrderedDict[str, _TokenBucket] = collections.OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds). Never raises."""
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _TokenBucket(self._burst, now)
                self._buckets[key] = bucket
                if len(self._buckets) > self._max_tracked:
                    self._buckets.popitem(last=False)
            else:
                self._buckets.move_to_end(key)

            elapsed = now - bucket.last_refill
            bucket.tokens = min(self._burst, bucket.tokens + elapsed * self._rate_per_second)
            bucket.last_refill = now

            if bucket.tokens >= 1.0:
                bucket.tokens -= 1.0
                return True, 0.0

            deficit = 1.0 - bucket.tokens
            retry_after = deficit / self._rate_per_second if self._rate_per_second > 0 else 60.0
            return False, retry_after


_rate_limiter = RateLimiter()


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

        allowed, retry_after = _rate_limiter.allow(key_id)
        if not allowed:
            _log.warning(
                "AUTH  rate_limited  key=%s  path=%s  retry_after=%.1fs", key_id, path, retry_after
            )
            response = JSONResponse(
                {"error": "Rate limit exceeded", "retry_after_seconds": round(retry_after, 1)},
                status_code=429,
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    # draft-ietf-httpapi-ratelimit-headers (consolidated form,
                    # draft -07+): quota policy + remaining-in-window signal.
                    "RateLimit-Policy": f'"default";q={int(RATE_LIMIT_PER_MINUTE)};w=60',
                    "RateLimit": '"default";r=0',
                },
            )
            await response(scope, receive, send)
            return

        _log.info("AUTH  ok  key=%s  path=%s", key_id, path)
        token = current_key_id.set(key_id)
        try:
            await self.app(scope, receive, send)
        finally:
            current_key_id.reset(token)


# ── Validation helpers ────────────────────────────────────────────────────────


def _extract_and_validate(scope) -> tuple[dict | None, str | None]:
    """
    Extract and validate the Bearer token from scope headers.

    Fails closed: if the server has no HORIZON_API_KEYS configured, every
    request is rejected (a clear 401 config error) unless the operator has
    explicitly opted into HORIZON_AUTH_DISABLED=true for local dev. This
    mirrors HorizonAuthMiddleware / validate_api_key, which already check
    AUTH_DISABLED before reaching this function — checked again here so this
    function is safe to call on its own.

    Returns:
        (error_body, key_id) — error_body is None on success.
    """
    path = scope.get("path", "")

    if not VALID_API_KEYS and not AUTH_DISABLED:
        _log.warning("AUTH  no_keys_configured  path=%s  — rejecting (fail-closed)", path)
        return {
            "error": (
                "Server has no API keys configured (HORIZON_API_KEYS is unset). "
                "Refusing all requests. Set HORIZON_API_KEYS, or "
                "HORIZON_AUTH_DISABLED=true for local dev only."
            )
        }, None

    headers: dict[bytes, bytes] = dict(scope.get("headers", []))
    raw_auth: str = headers.get(b"authorization", b"").decode("utf-8", errors="replace")

    if not raw_auth:
        _log.warning("AUTH  missing_header  path=%s", path)
        return {"error": "Missing Authorization header"}, None

    if not raw_auth.startswith("Bearer "):
        _log.warning("AUTH  bad_format  path=%s", path)
        return {"error": "Invalid Authorization header. Expected: Bearer <token>"}, None

    api_key = raw_auth[7:].strip()

    if not api_key:
        _log.warning("AUTH  empty_key  path=%s", path)
        return {"error": "Empty API key"}, None

    if AUTH_DISABLED and not VALID_API_KEYS:
        # Explicit dev-mode opt-in with no keys configured — allow.
        _log.warning(
            "AUTH  no_keys_configured  path=%s  — allowed (HORIZON_AUTH_DISABLED=true)", path
        )
        return None, "unconfigured"

    if not _key_matches(api_key):
        _log.warning("AUTH  invalid_key  key_prefix=%s  path=%s", api_key[:8], path)
        return {"error": "Invalid API key"}, None

    return None, _key_id(api_key)


def _key_matches(candidate: str) -> bool:
    """Constant-time membership check of `candidate` against VALID_API_KEYS.

    Uses hmac.compare_digest per key (and never short-circuits early) instead
    of `candidate in VALID_API_KEYS`, so comparison time does not vary with
    which key matched or how many leading characters two keys share.
    """
    matched = False
    for valid_key in VALID_API_KEYS:
        if hmac.compare_digest(candidate, valid_key):
            matched = True
    return matched


def _key_id(api_key: str) -> str:
    """Return a safe 8-char identifier for logging (never logs the full key)."""
    return hashlib.sha256(api_key.encode()).hexdigest()[:8]


# ── Starlette route-level helper (used by deploy/wsgi.py) ─────────────────────


async def validate_api_key(request: Request) -> tuple[JSONResponse | None, str | None]:
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
