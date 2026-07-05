# ComplyEdge TrustLint — Horizon integration

Horizon uses [ComplyEdge](https://complyedge.io) TrustLint on LLM-facing artifacts: offline EU AI Act screening, optional runtime checks, and a public trust surface.

**Tenant slug:** `horizon`

---

## What runs where

| Layer | Mechanism | API key in repo? | Blocks merge? |
|-------|-----------|------------------|---------------|
| **Offline gate** | `trustlint check` via `./scripts/compliance/check.sh` | No | Yes (CI `compliance` job) |
| **Runtime enforcement** | `POST /v1/check` via `./scripts/compliance/runtime_check.sh` | No (BYOK env only) | No (opt-in local / scheduled) |
| **Public proof** | Live seal + trust JSON | No | N/A |

```
edit horizon_intent.yaml / horizon-monitor.mdc → check.sh → CI green
                    ↓ optional BYOK
              runtime_check.sh → /v1/check → audit trail → badge + trust page
```

---

## Public surfaces

| Surface | URL |
|---------|-----|
| Enforcement seal (SVG) | https://api.complyedge.io/v1/public/badge/horizon.svg |
| Trust JSON | https://api.complyedge.io/v1/public/trust/horizon |
| Trust page | https://trust.complyedge.io/horizon |
| Origin site (badge host) | https://github.com/leocelis/horizon |

The seal reflects **live runtime audit data** (checks in 24h / 7d). It is not a static marketing badge.

---

## LLM-facing scan scope

| File | Role |
|------|------|
| `docs/spec/horizon_intent.yaml` | IVD-style intent — constraints agents load |
| `docs/cursor-rules/horizon-monitor.mdc` | Canonical agent contract (+ `<BEGIN-COMPLYEDGE v1.0>`) |

MCP `_INSTRUCTIONS` in `src/horizon/mcp/server.py` is kept aligned with `.mdc` via `tests/unit/test_cursor_rules_alignment.py`.

---

## Operator setup (BYOK)

1. Provision a ComplyEdge tenant with slug `horizon` and store the API key in env only — `COMPLYEDGE_API_KEY` (GitHub Actions secret for optional runtime job, never in git).
2. Enable public trust:

```bash
curl -s -X PATCH https://api.complyedge.io/v1/tenant/trust \
  -H "Authorization: Bearer $COMPLYEDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"trust_public_enabled": true, "public_slug": "horizon", "display_name": "Horizon Fidelity Monitor", "website_url": "https://github.com/leocelis/horizon"}'
```

3. Seed runtime checks (feeds live seal):

```bash
export COMPLYEDGE_API_KEY=ce_...
./scripts/compliance/runtime_check.sh
```

---

## CI

| Job | Path | Secret required |
|-----|------|-----------------|
| `test` | `pytest tests/unit` | None |
| `compliance` | `./scripts/compliance/check.sh` | None |
| `compliance-runtime` (optional) | `./scripts/compliance/runtime_check.sh` | `COMPLYEDGE_API_KEY` |

Offline gate is the auditable merge blocker. Runtime is opt-in proof for live trust metrics.

---

## Local validation

```bash
pip install 'trustlint>=2.0.1'
./scripts/compliance/check.sh
pytest tests/unit/test_compliance_trustlint.py -q
export COMPLYEDGE_API_KEY=ce_...
./scripts/compliance/runtime_check.sh
```

---

## References

- Recipe: `recipes/compliance-trustlint.yaml`
- Agent rule: `<BEGIN-COMPLYEDGE v1.0>` in `docs/cursor-rules/horizon-monitor.mdc`
- CE embed guide: https://complyedge.io/docs/trust-badge.html
- CE OSS adoption guide: `complyedge-platform/docs/development/oss-trustlint-adoption-guide.md`
- IVD variant: [leocelis/ivd](https://github.com/leocelis/ivd) — same TrustLint recipe pattern
