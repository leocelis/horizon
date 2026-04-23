# Horizon Documentation

Entry point for all `horizon-monitor` documentation.

## Getting started

- [Project README](../README.md) — installation, quick start, API overview
- [CHANGELOG](../CHANGELOG.md) — release history
- [CONTRIBUTING](../CONTRIBUTING.md) — development setup

## Provenance chain

The Horizon library was built from an unbroken chain of artifacts — each one
citable from the next. They live here:

| Stage | Document | Purpose |
|-------|----------|---------|
| Research | [`research/TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md`](./research/TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md) | 4D spacetime framework, 13 conjectures, 173 refs |
| Product | [`product/THCP_FIDELITY_MONITOR_PRD.md`](./product/THCP_FIDELITY_MONITOR_PRD.md) | PRD — what to build and why |
| Intent (IVD) | [`spec/horizon_intent.yaml`](./spec/horizon_intent.yaml) | Authoritative interface, constraints, verification cases |
| Tech spec | [`spec/HORIZON_TECH_SPEC.md`](./spec/HORIZON_TECH_SPEC.md) | Typed data models, pseudocode, pipeline, package tree |
| Implementation | [`../src/horizon/`](../src/horizon/) | 4,005 lines of Python across 32 modules |
| Tests | [`../tests/`](../tests/) | 3,343 lines across 33 test files; 152 passing, 5 skipped by design |

## Integration guides

Framework- and tool-specific integration instructions live in
[`docs/integrations/`](./integrations/):

| Integration | Guide |
|-------------|-------|
| Cursor (MCP) | [`integrations/CURSOR.md`](./integrations/CURSOR.md) |
| Claude Desktop (MCP) | [`integrations/CLAUDE_DESKTOP.md`](./integrations/CLAUDE_DESKTOP.md) |
| GitHub Copilot | [`integrations/COPILOT.md`](./integrations/COPILOT.md) |
| Index (all) | [`integrations/README.md`](./integrations/README.md) |

For runnable Python examples against each agent framework, see
[`../examples/`](../examples/).

## Reviews & reports

- [End-to-end review](./reviews/E2E_REVIEW.md) — links research → intent → tech
  spec → implementation → tests.

## Folder layout

```
docs/
├── README.md              ← you are here
├── research/              theoretical background (academic essays, frameworks)
├── product/               product requirements documents (PRD)
├── spec/                  engineering specs (intent.yaml, tech spec)
├── integrations/          per-framework how-to guides (Cursor, Copilot, etc.)
└── reviews/               E2E reviews, release reports, audit reports
```

Non-public documents (market research, internal strategy, pricing) live in
`docs-private/` at the repo root, which is git-ignored.
