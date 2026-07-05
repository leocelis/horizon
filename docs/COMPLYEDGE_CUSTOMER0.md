# ComplyEdge Customer #0 — Horizon Fidelity Monitor

**Status:** Active dogfooding (own OSS only)  
**Tenant slug:** `horizon`  
**Maps to:** CE M1.5-T1 · ADA #873 (offline + runtime + trust)

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

1. Use the dedicated Horizon Customer #0 tenant API key (provisioned 2026-07-05, slug `horizon`).
2. Store the key in env only — `COMPLYEDGE_API_KEY` (GitHub Actions secret for optional runtime job, never in git).
3. Public trust (slug `horizon`, display name *Horizon Fidelity Monitor*):

```bash
curl -s -X PATCH https://api.complyedge.io/v1/tenant/trust \
  -H "Authorization: Bearer $COMPLYEDGE_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"trust_public_enabled": true, "public_slug": "horizon", "display_name": "Horizon Fidelity Monitor"}'
```

4. Seed runtime checks (feeds green seal):

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

Offline gate is the auditable merge blocker. Runtime is opt-in proof for Customer #0 narrative.

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

## narrative_honesty

- **Shipped:** Offline TrustLint EU scan on Horizon LLM-facing intent + agent rule; CI `compliance` job.
- **Shipped:** Public trust slug `horizon`, live seal + trust page when runtime checks run.
- **Shipped (IVD phase 1):** Full stack on tenant `ivd` — see `leocelis/ivd/docs/COMPLYEDGE_CUSTOMER0.md`.
- **Not claimed:** External customer logo, cross-company data flywheel.

ConCntric and Laminr are **not** Customer #0 (US-based, no EU operations).

---

## References

- Recipe: `recipes/compliance-trustlint.yaml`
- Agent rule: `<BEGIN-COMPLYEDGE v1.0>` in `docs/cursor-rules/horizon-monitor.mdc`
- CE embed guide: https://complyedge.io/docs/trust-badge.html
- CE OSS adoption canon: `complyedge-platform/docs/development/oss-trustlint-adoption-guide.md`
- IVD Customer #0 (phase 1): `leocelis/ivd/docs/COMPLYEDGE_CUSTOMER0.md`
