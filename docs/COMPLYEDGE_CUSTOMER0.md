# ComplyEdge Customer #0 — Horizon (phase 2)

**Status:** Active dogfooding — offline gate only  
**Maps to:** CE M1.5-T1 · ADA #873  
**Tenant slug:** none (runtime/badge live on IVD tenant `ivd`)

---

## What runs where

| Layer | Mechanism | API key in repo? | Blocks merge? |
|-------|-----------|------------------|---------------|
| **Offline gate** | `trustlint check` via `./scripts/compliance/check.sh` | No | Yes (CI `compliance` job) |
| **Runtime enforcement** | Not wired in Horizon | — | — |
| **Public proof** | Lives on IVD (`trust.complyedge.io/ivd`) | — | — |

```
edit horizon_intent.yaml / horizon-monitor.mdc → check.sh → CI green
```

Horizon is **phase 2** of Customer #0: same offline EU gate as IVD, scoped to Horizon’s LLM-facing artifacts. Live enforcement seal and trust page remain on the IVD tenant until a dedicated Horizon slug is provisioned.

---

## LLM-facing scan scope

| File | Role |
|------|------|
| `docs/spec/horizon_intent.yaml` | IVD-style intent — constraints agents load |
| `docs/cursor-rules/horizon-monitor.mdc` | Canonical agent contract (+ `<BEGIN-COMPLYEDGE v1.0>`) |

MCP `_INSTRUCTIONS` in `src/horizon/mcp/server.py` is kept aligned with `.mdc` via `tests/unit/test_cursor_rules_alignment.py`.

---

## CI

| Job | Path | Secret required |
|-----|------|-----------------|
| `test` | `pytest tests/unit` | None |
| `compliance` | `./scripts/compliance/check.sh` | None |

---

## Local validation

```bash
pip install 'trustlint>=2.0.1'
./scripts/compliance/check.sh
pytest tests/unit/test_compliance_trustlint.py -q
```

---

## narrative_honesty

- **Shipped:** Offline TrustLint EU scan on Horizon LLM-facing intent + agent rule; CI `compliance` job.
- **Shipped (IVD, not Horizon):** Runtime `/v1/check`, badge, trust page — see `leocelis/ivd` → `docs/COMPLYEDGE_CUSTOMER0.md`.
- **Not claimed:** Horizon-specific trust slug or external customer logo.

ConCntric and Laminr are **not** Customer #0 (US-based, no EU operations).

---

## References

- Recipe: `recipes/compliance-trustlint.yaml`
- Agent rule: `<BEGIN-COMPLYEDGE v1.0>` in `docs/cursor-rules/horizon-monitor.mdc`
- CE OSS adoption canon (IVD + Horizon): `complyedge-platform/docs/development/oss-trustlint-adoption-guide.md`
- IVD Customer #0 (phase 1 + runtime): `leocelis/ivd/docs/COMPLYEDGE_CUSTOMER0.md`
