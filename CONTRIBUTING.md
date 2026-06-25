# Contributing to Horizon Fidelity Monitor

Thanks for your interest in contributing!

## Repository layout

```
horizon/
├── src/horizon/        # Library source (installable package)
├── tests/              # Unit, integration, E2E, perf, validation tests
├── examples/           # Runnable end-to-end examples
├── docs/               # Public documentation
│   ├── product/        #   public product overview
│   ├── content/        #   published articles
│   ├── spec/           #   intent.yaml + tech spec
│   ├── integrations/   #   per-framework how-tos (Cursor, Copilot, etc.)
│   ├── cursor-rules/   #   horizon-monitor.mdc
│   └── reviews/        #   E2E reviews, audit reports
├── deploy/docker/      # Dockerfile + docker-compose
├── pyproject.toml
├── README.md
├── CHANGELOG.md
└── LICENSE
```

This follows the [PyPA `src/` layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/),
which is also used by [arize-phoenix](https://github.com/Arize-ai/phoenix),
[pydantic](https://github.com/pydantic/pydantic), and
[langsmith-sdk](https://github.com/langchain-ai/langsmith-sdk).

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
```

The editable install is required because `src/` layout prevents accidental
imports from the working directory.

## Running tests

```bash
# Full suite (unit + integration + perf + E2E + validation scaffolds)
pytest

# Fast unit tests only
pytest tests/unit

# E2E integration tests (mocked — no network, no API keys)
pytest tests/e2e

# Performance tests
pytest tests/perf
```

Validation gates in `tests/validation/` auto-skip unless env vars point to local data:

| Variable | Gate | How to populate |
|----------|------|-----------------|
| `HORIZON_VALIDATION_DATA` | V1/V2/V3/V5 + leading indicator | `python scripts/build_validation_corpus.py --out data/validation_corpus` (synthetic), or adapt a third-party corpus |
| `HORIZON_OOD_DATA` | V6 OOD ρ | `python scripts/adapt_external_corpus.py --format mt-bench-human --in data/external_raw/mt_bench_human.parquet --out data/ood_corpus --limit 80` |

See [`docs/reviews/V0_2_0_EVIDENCE.md`](docs/reviews/V0_2_0_EVIDENCE.md) and
[CONTRIBUTING.md](CONTRIBUTING.md) for validation reproduction recipes.
Third-party downloads live under `data/` (gitignored).

## Code style

- `ruff` for linting (`ruff check src tests`)
- `black` for formatting (`black src tests`, line length 100)
- Type hints required on all public APIs; `py.typed` ships with the package.

## Pull request checklist

- [ ] Tests added or updated for the change
- [ ] `pytest` passes locally
- [ ] `ruff check` passes
- [ ] Public API changes documented in `CHANGELOG.md` (under `[Unreleased]`)
- [ ] No outbound network calls added to the core library (privacy constraint)
- [ ] No new framework imports in the core library (`src/horizon/` stays
      framework-agnostic; integrations live in `src/horizon/integrations/`)
