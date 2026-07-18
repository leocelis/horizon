# ── Builder stage: compiler toolchain + pip install stay out of the runtime image ──
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source first so the Dockerfile builds from the local repo rather than
# pulling horizon-monitor from PyPI. The docker-compose build.context is the
# repo root (see docker-compose.yml), so all paths below are repo-relative.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[mcp]"

# Pre-cache the default embedding model at build time — zero cold-start.
# Lands under the default huggingface_hub cache (~/.cache/huggingface, i.e.
# /root/.cache/huggingface since this stage runs as root) — copied into the
# runtime stage below.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('Model cached OK')"

# ── Runtime stage: just the venv + pre-cached model, no build tools ──
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /root/.cache/huggingface /root/.cache/huggingface
ENV PATH="/opt/venv/bin:$PATH"

RUN mkdir -p /data
ENV HORIZON_DB_PATH=/data/horizon.db

EXPOSE 3847

# Hits the real /health route (src/horizon/mcp/server.py, @mcp.custom_route)
# instead of just checking the import succeeds — catches a dead MCP service
# even though the interpreter is still alive.
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3847/health', timeout=3)" || exit 1

CMD ["horizon", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "3847"]
