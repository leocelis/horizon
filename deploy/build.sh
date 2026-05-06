#!/usr/bin/env bash
# deploy/build.sh — Horizon MCP Server build script for DigitalOcean App Platform.
#
# Set the DO build_command to:   bash deploy/build.sh
# Run command stays in:          deploy/Procfile
#
# Steps:
#   1. Install Python dependencies (mcp + starlette + uvicorn extras)
#   2. Pre-cache the MiniLM-L6-v2 embedding model (zero cold start)
#   3. Verify the horizon CLI is available
#   4. Verify the health endpoint code is importable

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

echo "============================================================"
echo "  Horizon MCP Server — build"
echo "  Repo root: $REPO_ROOT"
echo "============================================================"

# ---------------------------------------------------------------------------
# 1. Install dependencies
# ---------------------------------------------------------------------------

echo ""
echo "[build:1/4] Installing Python dependencies..."
python -m pip install --upgrade pip
pip install -e ".[mcp]"

# ---------------------------------------------------------------------------
# 2. Pre-cache the embedding model
# ---------------------------------------------------------------------------

echo ""
echo "[build:2/4] Pre-caching embedding model (all-MiniLM-L6-v2)..."
python - <<'PY'
from sentence_transformers import SentenceTransformer
m = SentenceTransformer("all-MiniLM-L6-v2")
_ = m.encode(["warmup — model cache OK"])
print("  Model: all-MiniLM-L6-v2 cached OK")
PY

# ---------------------------------------------------------------------------
# 3. Verify horizon CLI is importable and version is readable
# ---------------------------------------------------------------------------

echo ""
echo "[build:3/4] Verifying horizon package..."
python -c "from horizon import __version__; print(f'  horizon-monitor {__version__}  OK')"

# ---------------------------------------------------------------------------
# 4. Verify the MCP server and auth modules import cleanly
# ---------------------------------------------------------------------------

echo ""
echo "[build:4/4] Verifying MCP server imports..."
python - <<'PY'
from horizon.mcp.server import create_app
from horizon.mcp.auth import HorizonAuthMiddleware, generate_api_key
app = create_app()
print("  horizon.mcp.server  OK")
print("  horizon.mcp.auth    OK")
PY

echo ""
echo "============================================================"
echo "  Build complete."
echo "============================================================"
