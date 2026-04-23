# Changelog

All notable changes to `horizon-monitor` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `configure()` now accepts the intent's compound parameters
  (`fidelity_weights`, `temporal_weights`, `spacetime_coefficients`) and
  flattens them onto the corresponding `Config` fields per Tech Spec §2.1.
- `configure(embedding_model=...)` now resolves the intent's logical values
  (`local-sentence-transformer`, `openai-text-embedding-3-small`, `custom`)
  to concrete model slugs.
- `export_to(target="arize")` is now implemented — logs per-turn Horizon
  metrics to Arize AX via `arize.pandas.logger` (requires `space_id`,
  `api_key`, `model_id` in the connection dict).
- `pyproject.toml` optional-dependency extras for export adapters:
  `[langsmith]`, `[langfuse]`, `[otel]`, `[arize]`; `[full]` now includes
  all export backends.
- 7 new regression tests covering compound-param flattening, logical
  embedding-model resolution, and the Arize export dispatch.
- `LICENSE` (MIT) at repository root.
- `CHANGELOG.md` (this file).
- `CONTRIBUTING.md` with development setup and test instructions.
- `.gitignore` covering Python, build, virtualenv, and runtime artifacts.
- `docs/README.md` as an entry point to all documentation.
- `docs-private/` folder (git-ignored) for internal/non-public documents —
  contains `HORIZON_MARKET_RESEARCH.md` moved from `ada/`.

### Changed
- Adopted PyPA-recommended `src/` layout; package source now lives under `src/horizon/`.
- Moved Docker assets to `deploy/docker/`.
- Moved integration guides (Cursor, Claude Desktop, GitHub Copilot) from
  `examples/integrations/` to `docs/integrations/`.
- Moved `E2E_REVIEW.md` to `docs/reviews/E2E_REVIEW.md`.
- Relocated all Horizon documentation out of the `ada/` repo and into this
  repo under `docs/`:
  - Research essay → `docs/research/TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md`
  - PRD → `docs/product/THCP_FIDELITY_MONITOR_PRD.md`
  - Intent (IVD) → `docs/spec/horizon_intent.yaml`
  - Tech spec → `docs/spec/HORIZON_TECH_SPEC.md`
- `horizon_intent.yaml::export_to.target` now lists all five supported
  targets (`json | langsmith | langfuse | otel | arize`) to match the
  implementation and Tech Spec §13.
- Tech Spec §12 package tree updated to reflect the `src/` layout with
  `deploy/docker/` at the repo root and the `docs/*` subtree.
- Renamed `tests/integration/test_export.py::test_export_json_end_to_end`
  to `test_json_export` to match the intent's verbatim test reference.

### Fixed
- Removed a dead `dataclasses.fields(Config).__class__.__name__` check in
  `FidelityMonitor.new_conversation` metadata filter (behaviour was masked
  by the adjacent correct clause, but the line was a no-op).
- `[mcp]` extra now includes `uvicorn` and `starlette`, so
  `horizon serve --transport sse` works after `pip install horizon-monitor[mcp]`
  (was previously silently broken for the SSE code path).
- `deploy/docker/Dockerfile` now installs Horizon from the local repository
  instead of from PyPI, so `docker compose -f deploy/docker/docker-compose.yml up`
  builds cleanly before an initial PyPI publish.

## [0.1.0] - 2026-04-23

### Added
- First end-to-end release of the Horizon Fidelity Monitor.
- 4D spacetime signal engine (fidelity, temporal, spatial, causal reachability).
- Event system with configurable thresholds (`signal.drift`, `signal.broken_reference`,
  `signal.light_cone_collapse`, `signal.convergence`, etc.).
- Agent framework integrations: OpenAI SDK, Anthropic SDK, LangChain callback,
  OpenAI Agents SDK, MCP server (Cursor / Claude Desktop).
- Export adapters (optional): LangSmith, Langfuse, OpenTelemetry, Arize.
- Comprehensive test suite: unit, integration, performance, validation gates, E2E.
