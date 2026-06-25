# Horizon Documentation

Entry point for all `horizon-monitor` documentation (public OSS surfaces only).

## Getting started

- [Project README](../README.md) — installation, quick start, API overview
- [CHANGELOG](../CHANGELOG.md) — release history
- [CONTRIBUTING](../CONTRIBUTING.md) — development setup and validation reproduction

## Provenance chain

| Stage | Document | Purpose |
|-------|----------|---------|
| Product | [`product/THCP_FIDELITY_MONITOR_PRD.md`](./product/THCP_FIDELITY_MONITOR_PRD.md) | Public product overview — what to build and why |
| Intent (IVD) | [`spec/horizon_intent.yaml`](./spec/horizon_intent.yaml) | Authoritative interface, constraints, verification cases |
| Tech spec | [`spec/HORIZON_TECH_SPEC.md`](./spec/HORIZON_TECH_SPEC.md) | Typed data models, pseudocode, pipeline, package tree |
| Implementation | [`../src/horizon/`](../src/horizon/) | Library source |
| Tests | [`../tests/`](../tests/) | Gate + unit + integration + validation + perf — see [CONTRIBUTING](../CONTRIBUTING.md) |

Extended PRD, market research, and THCP research essays are **not** in this repository.

## Integration guides

[`docs/integrations/`](./integrations/):

| Integration | Guide |
|-------------|-------|
| Cursor (MCP) | [`integrations/CURSOR.md`](./integrations/CURSOR.md) — includes [`cursor-rules/horizon-monitor.mdc`](./cursor-rules/horizon-monitor.mdc) |
| Claude Desktop (MCP) | [`integrations/CLAUDE_DESKTOP.md`](./integrations/CLAUDE_DESKTOP.md) |
| Claude Code (MCP) | [`integrations/CLAUDE_CODE.md`](./integrations/CLAUDE_CODE.md) |
| GitHub Copilot | [`integrations/COPILOT.md`](./integrations/COPILOT.md) |
| Index (all) | [`integrations/README.md`](./integrations/README.md) |

Runnable examples: [`../examples/`](../examples/).

## Content (public)

- [`content/naming-the-category-conversation-dynamics-monitoring.md`](./content/naming-the-category-conversation-dynamics-monitoring.md)
- [`content/why-every-production-agent-needs-conversation-dynamics-monitoring.md`](./content/why-every-production-agent-needs-conversation-dynamics-monitoring.md)

## Reviews & reports

- [End-to-end review](./reviews/E2E_REVIEW.md) — PRD → intent → tech spec → implementation → tests
- [v0.2.0 validation evidence](./reviews/V0_2_0_EVIDENCE.md) — gate results + Fix 3/4 runs
- [Red-team gaps source](./reviews/DESIGN_FIXES_redteam_remediation.md) — four fixes and acceptance criteria
- JSON artifacts in `reviews/` — demo runs, throughput, embedding stability (see evidence doc)

## Folder layout

```
docs/
├── README.md              ← you are here
├── index.html             ← landing page (mirror of site/)
├── product/               public product overview (not full internal PRD)
├── content/               published articles on conversation dynamics monitoring
├── spec/                  intent.yaml + tech spec
├── integrations/          per-framework how-to guides
├── cursor-rules/          canonical Cursor agent rule (horizon-monitor.mdc)
├── reviews/               E2E reviews, validation evidence, JSON artifacts
└── site/                  GitHub Pages deploy target (index.html + README)
```

Non-public documents (full PRD, market research, session handoffs) live outside this repo.
