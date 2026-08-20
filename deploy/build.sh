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
echo "[build:1/4] Verifying dependencies (installed by DO Python buildpack via requirements.txt)..."
python -m pip install --upgrade pip --quiet
# [mysql] is required whenever HORIZON_MEMENTO_STORE_DSN is set at RUN time.
# It must be installed at BUILD time even though nothing here uses it: the DSN
# is RUN_TIME-scoped, so the mission plane stays disabled during the build and
# the step-4 import check below cannot exercise the MySQL path. Omitting it
# builds green and then crashes the container on boot with
# "MySQL backend requires PyMySQL".
pip install -e ".[mcp,mysql]" --quiet   # idempotent

# ---------------------------------------------------------------------------
# 2. Pre-cache the embedding model
# ---------------------------------------------------------------------------
#
# SENTENCE_TRANSFORMERS_HOME pins the cache to an absolute repo-relative path
# so that the runtime container (which shares the same filesystem image as the
# build step) finds the model without re-downloading it.  The env var must be
# set identically in the DO App Platform environment (BUILD_AND_RUN scope) so
# the runtime Python process also resolves to this same path.

MODEL_CACHE_DIR="$REPO_ROOT/.cache/models"
export SENTENCE_TRANSFORMERS_HOME="$MODEL_CACHE_DIR"
export HF_HOME="$MODEL_CACHE_DIR"
mkdir -p "$MODEL_CACHE_DIR"

echo ""
echo "[build:2/4] Pre-caching embedding model → $MODEL_CACHE_DIR ..."
python - <<'PY'
import os
from sentence_transformers import SentenceTransformer
cache = os.environ["SENTENCE_TRANSFORMERS_HOME"]
m = SentenceTransformer("all-MiniLM-L6-v2", cache_folder=cache)
_ = m.encode(["warmup — model cache OK"])
print(f"  Model: all-MiniLM-L6-v2 cached OK → {cache}")
PY

# ---------------------------------------------------------------------------
# 3. Verify horizon CLI is importable and version is readable
# ---------------------------------------------------------------------------

echo ""
echo "[build:3/4] Verifying horizon package..."
python -c "from horizon_monitor import __version__; print(f'  horizon-monitor {__version__}  OK')"

# ---------------------------------------------------------------------------
# 4. Verify the MCP server and auth modules import cleanly
# ---------------------------------------------------------------------------

echo ""
echo "[build:4/4] Verifying MCP server imports..."
python - <<'PY'
from horizon_monitor.mcp.server import create_app
from horizon_monitor.mcp.auth import HorizonAuthMiddleware, generate_api_key
app = create_app()
print("  horizon_monitor.mcp.server  OK")
print("  horizon_monitor.mcp.auth    OK")

# The runtime env differs from the build env: HORIZON_MEMENTO_STORE_DSN is
# RUN_TIME-scoped, so create_app() above never touches the MySQL backend here.
# Import its driver explicitly, or a missing extra only surfaces as a boot
# crash after a green build.
import pymysql  # noqa: F401
from horizon_monitor.memento.backends.mysql import MySQLBackend  # noqa: F401
print(f"  pymysql {pymysql.__version__}          OK (mission-plane MySQL backend)")
PY

echo ""
echo "============================================================"
echo "  Build complete."
echo "============================================================"
