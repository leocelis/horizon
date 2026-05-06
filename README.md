# Horizon Fidelity Monitor

> **"Quality is not a model property — it is a conversation property."**

Horizon is a real-time conversation health monitor for AI agents. It tracks the **structural dynamics** of multi-turn conversations — semantic drift, information gain, ontological gap width, temporal desynchronisation, circadian cognitive load, conversation velocity, and causal reachability — the dimensions that every LLM is architecturally blind to.

Based on the Trans-Horizon Communication Protocol (THCP) research paper. Three independent no-go theorems prove why no LLM can self-monitor these properties from the inside.

```
pip install horizon-monitor
```

---

## Why Horizon

Standard observability tools (LangSmith, RAGAS, DeepEval) evaluate **individual response quality**. Horizon evaluates **conversation quality** — a structurally different problem proven to diverge from per-response quality in Hafez et al. (2026).

| Tool | What it sees | What it misses |
|---|---|---|
| LangSmith, Braintrust | Latency, cost, per-response quality | Drift across turns |
| RAGAS, DeepEval | Faithfulness, relevance per turn | Temporal desync, cognitive load |
| Human raters | Subjective quality | Systematic structural decay |
| **Horizon** | **Conversation dynamics** | Intentionally nothing |

Horizon does not replace per-response quality tools. It adds the fourth dimension they all lack.

---

## Quickstart

```python
from horizon import FidelityMonitor
from datetime import datetime, timezone

monitor = FidelityMonitor()
session_id = monitor.new_conversation(metadata={"domain": "technical"})

result = monitor.process_turn(
    session_id,
    human_message="How does Python handle memory management?",
    agent_response="Python uses reference counting and a cyclic garbage collector...",
    timestamp=datetime.now(timezone.utc).isoformat(),
)

print(f"Fidelity:         {result.fidelity_score:.2f}")
print(f"Health:           {result.health_status}")
print(f"Circadian factor: {result.circadian_factor:.2f}")
print(f"Causal horizon:   {result.reachable_turns} reachable turns")
for event in result.events:
    print(f"  Event: {event.type} (confidence={event.confidence:.2f})")
```

### Verify your install

After `pip install`, run the bundled smoke test to confirm the pipeline produces sensible signals on five canonical scenarios (healthy, convergent, drifting, temporal desync, spatial shift). No API keys required:

```bash
horizon-validate
```

You should see all five scenarios pass in ~25s after the embedding model warm-up. This exercises the full end-to-end pipeline locally and prints the actual signal values, so you can confirm Horizon is wired correctly before integrating it into your stack.

---

## Integrations

### OpenAI SDK

```python
from openai import OpenAI
from horizon import FidelityMonitor

monitor = FidelityMonitor()
session_id = monitor.new_conversation()
client = monitor.wrap(OpenAI(), session_id)

# Identical to the standard OpenAI call — monitoring is transparent
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Tell me about quantum computing."}]
)

traj = monitor.get_trajectory(session_id)
print(f"Fidelity: {traj.current_fidelity:.2f}  T*: {traj.estimated_t_star}")
```

`monitor.wrap()` accepts custom timestamp and context providers for testing and replay:

```python
wrapped = monitor.wrap(OpenAI(), session_id)
wrapped.set_timestamp_provider(lambda: simulated_clock.isoformat())
wrapped.set_context_provider(lambda: {"device_type": "mobile", "timezone": "US/Pacific"})
```

### Anthropic SDK

```python
from anthropic import Anthropic
from horizon import FidelityMonitor

monitor = FidelityMonitor()
session_id = monitor.new_conversation()
client = monitor.wrap(Anthropic(), session_id)

response = client.messages.create(
    model="claude-3-5-sonnet-20241022",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Explain RLHF."}]
)
```

### LangChain

```python
from langchain_openai import ChatOpenAI
from horizon import FidelityMonitor
from horizon.integrations.langchain import HorizonCallback

monitor = FidelityMonitor()
session_id = monitor.new_conversation()
callback = HorizonCallback(monitor, session_id)

llm = ChatOpenAI(callbacks=[callback])
llm.invoke("Explain the CAP theorem.")

print(f"Fidelity: {callback.last_result.fidelity_score:.2f}")
```

### OpenAI Agents SDK

```python
from openai_agents import Agent, Runner
from horizon import FidelityMonitor

monitor = FidelityMonitor()
session_id = monitor.new_conversation()

agent = Agent(name="assistant", model="gpt-4o-mini", instructions="You are helpful.")

for user_message in conversation:
    result = Runner.run_sync(agent, user_message)
    monitor.process_turn(
        session_id,
        human_message=user_message,
        agent_response=result.final_output,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )
```

### MCP Server — Cursor / Claude Desktop / GitHub Copilot

```bash
pip install horizon-monitor[mcp]
horizon serve                           # stdio transport (Cursor, Claude Desktop)
horizon serve --transport sse --port 3847  # SSE transport (web)
```

Add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "horizon": { "command": "horizon", "args": ["serve"] }
  }
}
```

Add to `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "horizon": { "command": "horizon", "args": ["serve"] }
  }
}
```

See [`docs/integrations/`](docs/integrations/) for Cursor, Claude Desktop, and Copilot setup guides.

---

## 4D Spacetime Signals

Every `process_turn()` call returns a `TurnResult` with the following signal families:

### Core (always present)

| Signal | Description |
|---|---|
| `fidelity_score` | Composite conversation health [0, 1] |
| `igt_value` | Information Gain per Turn — semantic novelty |
| `divergence_score` | Jensen-Shannon proxy for intent/response gap |
| `twr_value` | Token Waste Ratio — semantic redundancy |
| `consistency_score` | Bipredictability — structural coherence |
| `epsilon_t` | Estimated ontological gap width [0, 1] |
| `health_status` | `healthy` / `degrading` / `critical` / `converged` |
| `conversation_mode` | `execute` / `explore` / `refine` / `learn` (auto-detected) |

### Temporal (requires `timestamp`)

| Signal | Description |
|---|---|
| `gap_seconds` | Wall-clock gap since last turn |
| `estimated_retention` | Human memory retention (Ebbinghaus half-life model) |
| `circadian_factor` | Human cognitive capacity at this hour [0.3, 1.0] |
| `temporal_asymmetry` | Penalty for temporal desync |
| `resumption_cost` | `none` / `low` / `medium` / `high` / `extreme` |
| `temporal_references` | Resolved deictic expressions ("yesterday", "last week") |

### Pace (requires `timestamp` + turn ≥ 2)

| Signal | Description |
|---|---|
| `conversation_velocity` | Semantic displacement / proper time |
| `conversation_acceleration` | Velocity delta (requires turn ≥ 3) |

### Spacetime (requires `timestamp` + turn ≥ 2)

| Signal | Description |
|---|---|
| `spacetime_interval` | ds² with Minkowski-like signature (−,+,+,+) |
| `interval_class` | `timelike` / `spacelike` / `lightlike` |

### Causal (requires `timestamp`)

| Signal | Description |
|---|---|
| `reachable_turns` | Turns still inside the causal light cone |
| `reachable_fraction` | Fraction of history still causally reachable |

### Spatial (requires `client_context`)

| Signal | Description |
|---|---|
| `location_class` | `home` / `office` / `mobile_transit` / `unknown` |
| `spatial_constraint` | Attention budget, screen capacity, max response length |
| `spatial_frame_shift` | Context switch magnitude |

---

## 14 Event Types

All events default to **observe mode** (emitted, not acted on). Enable active mode via `configure()` once your event achieves ≥ 0.7 precision/recall on your domain.

| Event | Fires when |
|---|---|
| `checkpoint.clarification` | D_JS above clarification threshold |
| `checkpoint.comprehension` | Consistency drops below threshold |
| `alert.drift` | Fidelity declining for `drift_window` consecutive turns |
| `alert.contradiction` | Bipredictability below consistency threshold |
| `alert.verbosity` | Token Waste Ratio above verbosity threshold |
| `signal.convergence` | IGT trend consistently low — natural endpoint approaching |
| `signal.optimal_length` | T* (estimated optimal length) reached |
| `signal.horizon_widening` | IGT trend strongly positive — conversation expanding |
| `signal.session_reset` | Large temporal gap with low retention |
| `signal.temporal_desync` | Gap + retention drop below desync threshold |
| `signal.broken_reference` | Reachable fraction drops below broken-reference threshold |
| `signal.frame_shift` | Spatial constraint shifts significantly |
| `signal.pace_shift` | Conversation acceleration above pace threshold |
| `signal.light_cone_collapse` | Reachable fraction below light-cone threshold |

---

## Configure

```python
# Per-session override
monitor.configure(
    session_id=session_id,
    clarification_threshold=0.25,          # tighter D_JS gate
    event_modes={"alert.drift": "active"},  # activate one event
)

# Compound weight override (flattened to Config fields)
monitor.configure(
    fidelity_weights={"alpha": 0.35, "lambda_r": 0.12, "lambda_i": 0.28, "beta": 0.25},
    temporal_weights={"gamma": 0.08, "delta": 0.04},
    spacetime_coefficients={"alpha": 1.0, "beta": 1.0, "gamma": 0.8, "delta_st": 0.5},
)

# Per-domain tuning
monitor.configure(
    domain="medical",
    context_half_life_hours=12.0,   # shorter memory decay for clinical sessions
    chronotype_offset=0.0,
)
```

---

## Export

```python
# JSON (always available)
result = monitor.export_to(session_id, target="json")

# LangSmith
result = monitor.export_to(session_id, target="langsmith",
    connection={"api_key": "ls__..."})

# Langfuse
result = monitor.export_to(session_id, target="langfuse",
    connection={"public_key": "pk_...", "secret_key": "sk_..."})

# OpenTelemetry
result = monitor.export_to(session_id, target="otel",
    connection={"endpoint": "http://localhost:4318/v1/traces"})

# Arize AX
result = monitor.export_to(session_id, target="arize",
    connection={"space_id": "...", "api_key": "...", "model_id": "my-agent"})
```

Install the extras for your target:
```bash
pip install horizon-monitor[langsmith]
pip install horizon-monitor[langfuse]
pip install horizon-monitor[otel]
pip install horizon-monitor[arize]
```

---

## Architecture

```
Input: plain strings (human_message, agent_response, optional timestamp, optional client_context)

Core pipeline (< 50ms on CPU):
  1. Embed both turns (local sentence-transformers, lazy-loaded)
  2. IGT (Information Gain per Turn)     — semantic novelty
  3. D_JS proxy                          — intent/response divergence
  4. TWR                                 — token waste
  5. Bipredictability                    — structural coherence
  6. Epsilon                             — ontological gap
  7. Temporal signals                    — gap, retention, circadian, deictic
  8. Fidelity dynamics                   — composite score update
  9. Health classification
 10. Pace signals                        — velocity, acceleration
 11. Spacetime interval                  — ds² and interval class
 12. Causal reachability                 — light-cone membership
 13. Spatial signals                     — device, location, frame shift
 14. Mode detection                      — auto-classify conversation type
 15. Event evaluation                    — 14 threshold checks
 16. Optional: SQLite persistence

Output: TurnResult dataclass (29 fields)
```

**Design constraints (all test-enforced):**
- Zero LLM calls — pure arithmetic and local embeddings
- Zero external network calls by default — fully local
- Zero transitive framework dependencies in core — works with any agent
- < 50ms core pipeline on CPU
- < 100MB memory for 100-turn conversations
- All events observe-by-default — never interferes unless explicitly configured

---

## Development

```bash
git clone https://github.com/leocelis/horizon.git
cd horizon

python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Run full test suite (unit + integration + e2e + perf + validation gates)
pytest tests/ -v

# Fast path (unit + integration + e2e only, ~6 min)
pytest tests/unit tests/integration tests/e2e -v

# Code quality
ruff check src/ tests/
black --check src/ tests/
```

Test suite: unit, integration, e2e, performance, and validation gates.
Validation gates (V1/V2/V3/V5) auto-skip without a labeled dataset
(`HORIZON_VALIDATION_DATA` env var). v0.2.0 ships with a synthetic
labeled corpus generator (`ada/playground/horizon/build_validation_corpus.py`)
that produces 5,602 labeled records, and **all four gates pass on it**:

| Gate | Constraint | v0.2.0 |
|------|------------|--------|
| V1 — proxy correlation | per-conv ρ ≥ 0.6, per-turn ρ ≥ 0.5 | **0.685 / 0.659** |
| V2 — per-event P/R   | every event P ≥ 0.7 AND R ≥ 0.7 (320 labels each) | **all 16 events ≥ 0.70 / 0.70** |
| V3 — beats heuristics | rho lift > 25%, structural P ≥ 0.6 | **+202.4% lift, P=R=1.00** |
| V5 — cross-domain | per-turn ρ ≥ 0.4 AND per-conv ρ ≥ 0.48 across 5 domains | **min 0.517 / 0.718** |

See [`docs/reviews/V0_2_0_EVIDENCE.md`](docs/reviews/V0_2_0_EVIDENCE.md)
for the full evidence pack and reproduction steps.

**Audit follow-up: cross-embedding stability.** V1 was re-measured
across three sentence-transformer backends (22 M / 33 M / 110 M
parameters, 384 / 384 / 768 dimensions) on the same 222-conversation
corpus. Every backend clears the V1 gate, ρ_conv spread is **0.026**
and ρ_turn spread is **0.018** — confirming the fidelity signal lives
in conversational structure, not in any specific embedding manifold.
Reproduce with `python scripts/measure_embedding_stability.py`.

In addition to the V1–V5 synthetic gates, v0.2.0 ships two real-data
integration suites that exercise the spacetime layer end-to-end (no
mocks, no fakes):

- `tests/integration/test_geoip_real.py` — 14 tests against the
  canonical MaxMind reference test databases shipped under
  `tests/integration/fixtures/`. Covers real high-precision inference
  (London / Milton / Linköping), real low-precision rejection (Bhutan
  radius 534 km, US country-block radius 1000 km), real Anonymous-IP
  suppression (VPN / hosting / Tor / anonymous proxy), and end-to-end
  propagation through `FidelityMonitor.process_turn`.
- `tests/integration/test_spacetime_real.py` — 16 tests driving the
  *full* 4D stack (temporal gap + circadian κ + retention + velocity +
  ds² + light cone + deictic + spatial) through real ISO-8601
  timestamps spanning seconds → days, real timezones (UTC nadir /
  peak / decline), and real GeoIP. Asserts cross-feature invariants
  the kernel-level unit tests cannot — e.g. ds² monotonically declines
  as the time gap grows for the same semantic transition, κ at 04:00
  reduces retention vs κ at 11:00, and `signal.light_cone_collapse`
  fires from the *composed* signal (decay × similarity).

---

## Deployment

### Self-hosted Docker (MCP server on port 3847)

```bash
cd deploy/docker
docker compose up
```

Horizon serves the MCP API via SSE. Configure `.cursor/mcp.json` to point to `http://localhost:3847/sse`.

The Dockerfile pre-caches the `all-MiniLM-L6-v2` embedding weights at build time — zero cold start on first request.

---

## Repository Layout

```
horizon/
├── src/horizon/         # package source (src/ layout, PEP 517/518)
│   ├── engines/         # IGT, D_JS, TWR, coherence, fidelity, epsilon, mode
│   ├── spacetime/       # temporal, circadian, deictic, velocity, interval, light cone, spatial
│   ├── events/          # 14-event evaluator
│   ├── integrations/    # OpenAI, Anthropic, LangChain, export (json/langsmith/langfuse/otel/arize)
│   ├── mcp/             # MCP server + CLI
│   ├── storage/         # optional SQLite persistence
│   └── context/         # context-window tracking
├── tests/               # unit / integration / e2e / perf / validation
├── examples/            # runnable demos for each framework
├── deploy/docker/       # Dockerfile + docker-compose
├── docs/
│   ├── research/        # THCP theoretical framework (5 conjectures, 173 refs)
│   ├── product/         # PRD
│   ├── spec/            # horizon_intent.yaml + HORIZON_TECH_SPEC.md
│   └── integrations/    # Cursor / Claude Desktop / Copilot setup guides
└── pyproject.toml
```

---

## Background

Horizon is grounded in the Trans-Horizon Communication Protocol (THCP), a theoretical framework for human–AI communication. Five conjectures establish:

- **THCP-1** — Irreducible ontological loss ε > 0 in every domain
- **THCP-2** — An optimal conversation length T* exists beyond which fidelity decays
- **THCP-3** — Communication requires encode/decode adjunction (bipredictability)
- **THCP-4** — Global coherence requires sheaf gluing across all turns
- **THCP-5** — Optimal trajectories lie on or near the conversation light cone

The monitor instruments all five conjectures as computable signals. The math is grounded in 173 academic references across information theory, cognitive science, category theory, and Lorentzian geometry.

---

## License

MIT — see [LICENSE](LICENSE).
