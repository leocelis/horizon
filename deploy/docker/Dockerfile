FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy source first so the Dockerfile builds from the local repo rather than
# pulling horizon-monitor from PyPI. The docker-compose build.context is the
# repo root (see docker-compose.yml), so all paths below are repo-relative.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir ".[mcp]"

# Pre-cache the default embedding model at build time — zero cold-start.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2'); print('Model cached OK')"

RUN mkdir -p /data
ENV HORIZON_DB_PATH=/data/horizon.db

EXPOSE 3847

CMD ["horizon", "serve", "--transport", "sse", "--host", "0.0.0.0", "--port", "3847"]
