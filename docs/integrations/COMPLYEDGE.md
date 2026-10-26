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

## MCP tool calls

When the MCP server's environment has `COMPLYEDGE_API_KEY`, the `process_turn` tool sends
the turn's text to `POST /v1/check`, both calls in parallel
(`src/horizon_monitor/mcp/compliance.py`):

| Field | `human_message` check | `agent_response` check |
|-------|-----------------------|------------------------|
| `direction` | `prompt` | `output` |
| `agent_id` | `horizon-mcp` | `horizon-mcp` |
| `jurisdiction` | `EU` | `EU` |
| `context.user_id` | `hzkey:<first 12 hex of sha256(bearer key)>` remotely (never the key), `local:<login>` over stdio | same |
| `context.user_role` | `mcp_client` remotely, `maintainer` locally | same |
| `context.session_id` | the Horizon `session_id` | same |

Horizon records a turn after it happened, so it cannot block it. A violation comes back
as an active event `{"type": "alert.compliance", "plane": "conversation", "rule_ids",
"event_ids", "suggested_behavior"}`. If ComplyEdge cannot be reached the turn is recorded
as usual and the skip is logged (fail-open). Only `process_turn` carries model input and
output; the other tools carry settings and mission records and are not checked. Without
the key nothing is sent, and the core `FidelityMonitor` never calls out.

### Log IDs

ComplyEdge keeps a keyed fingerprint of each checked text, never the text. Every check
returns an `event_id` (the Log ID), and a Log ID only proves something next to a copy of
the text. Horizon keeps no raw text, so it hands both Log IDs back in the `process_turn`
result's `_meta`, outside the result text:

```json
{"complyedge": {"input_event_id": "...", "output_event_id": "..."}}
```

| Log ID | Text it covers |
|--------|----------------|
| `input_event_id` | the `human_message` you sent |
| `output_event_id` | the `agent_response` you sent |

A Log ID is `null` when that check did not run (ComplyEdge unreachable); without the key
there is no `_meta`. A text longer than 50,000 characters is checked on its first 50,000.
Store each Log ID next to your copy of the turn. Later, `POST /v1/audit/verify` with a Log
ID and that text answers whether they match
([how audit reconciliation works](https://complyedge.io/docs/audit-reconciliation.html)).
Requires `mcp>=1.19`.

Optional: `COMPLYEDGE_API_URL` (default `https://api.complyedge.io`),
`COMPLYEDGE_AGENT_ID`, `COMPLYEDGE_JURISDICTION`, `COMPLYEDGE_TIMEOUT_S` (default 5).
Tests: `tests/unit/test_runtime_compliance.py`, `tests/unit/test_complyedge_log_ids.py`.

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
- Public CE OSS: [ComplyEdge/complyedge](https://github.com/ComplyEdge/complyedge)
- IVD variant: [leocelis/ivd](https://github.com/leocelis/ivd) — same TrustLint recipe pattern
