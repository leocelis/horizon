"""
Production entry point for the Horizon MCP Server on DigitalOcean App Platform.

Serves both transports from a single process:
  /health  — unauthenticated health check (DO load balancer)
  /sse     — SSE transport (Cursor and legacy MCP clients)
  /mcp     — Streamable HTTP transport (Claude Desktop, modern clients)

Auth:  Bearer token via HorizonAuthMiddleware (reads HORIZON_API_KEYS env var).
       /health is always exempt.

Usage:
    python deploy/wsgi.py --port 8080
"""

from __future__ import annotations

import argparse
import os
import sys
import threading

# ── Path setup — works both on DO (/workspace) and locally ───────────────────
_here = os.path.dirname(os.path.abspath(__file__))
_repo = os.path.dirname(_here)
_src = os.path.join(_repo, "src")
for _p in (_repo, _src):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ── Env: signal production mode so server.py logs to stdout ──────────────────
os.environ.setdefault("HORIZON_ENV", "production")

from horizon.mcp.auth import HorizonAuthMiddleware  # noqa: E402
from horizon.mcp.server import create_app           # noqa: E402

import uvicorn                                       # noqa: E402
from starlette.applications import Starlette         # noqa: E402
from starlette.responses import JSONResponse         # noqa: E402
from starlette.routing import Mount, Route           # noqa: E402

from horizon import __version__                      # noqa: E402


def build_app():
    """
    Build the combined Starlette app:
      /health         — unauthenticated
      /sse + /messages — FastMCP SSE transport (Cursor)
      /mcp            — FastMCP Streamable HTTP transport (modern clients)
    Wrapped with HorizonAuthMiddleware (exempts /health).
    """
    fastmcp = create_app()

    # ── Preload the embedding model in a background thread ────────────────────
    # Loading sentence-transformers takes 15-30 s on a 512 MB instance.
    # Running it in a daemon thread lets the server start instantly (health
    # checks pass at T+20s) while the model warms up concurrently.
    # The first process_turn call after the thread finishes is instant; any
    # call that arrives before the thread finishes will wait on the internal
    # _ensure_loaded() lock — but loading from the pre-cached disk path is
    # seconds, not minutes.
    def _bg_preload() -> None:
        try:
            from horizon.mcp.server import _get_monitor as _get_horizon_monitor
            report = _get_horizon_monitor().preload_models()
            print(f"[Horizon MCP] Model preloaded: {report}", flush=True)
        except Exception as exc:
            print(f"[Horizon MCP] Model preload failed (lazy-load fallback): {exc}", flush=True)

    threading.Thread(target=_bg_preload, daemon=True, name="model-preload").start()

    # ── Get both transport ASGI apps from FastMCP ─────────────────────────────
    sse_starlette    = fastmcp.sse_app()             # serves GET /sse + POST /messages/
    http_starlette   = fastmcp.streamable_http_app() # serves POST /mcp

    # ── Health endpoint (no auth) ─────────────────────────────────────────────
    async def health(request):
        session_count = 0
        try:
            m = fastmcp._get_monitor() if hasattr(fastmcp, "_get_monitor") else None
            if m and hasattr(m, "_sessions"):
                session_count = len(m._sessions)
        except Exception:
            pass
        return JSONResponse({
            "status": "healthy",
            "server": "horizon-monitor",
            "version": __version__,
            "sessions_active": session_count,
            "transports": ["streamable-http", "sse"],
            "resumable": bool(os.environ.get("REDIS_URL")),
        })

    # ── Path dispatcher: preserves the full path so each app sees its own
    # prefix. Starlette's Mount() strips the prefix before forwarding, which
    # breaks FastMCP's Streamable HTTP app (it expects to see POST /mcp, not
    # POST /). Using a raw ASGI dispatcher avoids the stripping.
    class _Dispatcher:
        async def __call__(self, scope, receive, send):
            path = scope.get("path", "/")
            if path == "/mcp" or path.startswith("/mcp/"):
                await http_starlette(scope, receive, send)
            else:
                await sse_starlette(scope, receive, send)

    # ── Combined app: health routes first (exempt from auth), then dispatcher
    inner_app = Starlette(routes=[
        Route("/health",  health, methods=["GET"]),
        Route("/healthz", health, methods=["GET"]),
        Mount("/",        app=_Dispatcher()),
    ])

    # ── Auth middleware wraps everything; /health exempted inside middleware ──
    return HorizonAuthMiddleware(inner_app)


app = build_app()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Horizon MCP Server (production)")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    print(f"[Horizon MCP] Starting production server on {args.host}:{args.port}")
    print(f"[Horizon MCP] Version: {__version__}")
    print(f"[Horizon MCP] Auth: {'DISABLED' if os.environ.get('HORIZON_AUTH_DISABLED') else 'enabled'}")
    print(f"[Horizon MCP] Redis: {'configured' if os.environ.get('REDIS_URL') else 'not configured (sessions reset on restart)'}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        timeout_keep_alive=600,   # SSE connections are long-lived
        timeout_graceful_shutdown=30,
    )
