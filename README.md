# Horizon Fidelity Monitor

> **"Quality is not a model property — it is a conversation property."**

Horizon is a real-time conversation health monitor for AI agents. It tracks the **structural dynamics** of multi-turn conversations — semantic drift, information gain, ontological gap width, temporal desynchronisation, circadian cognitive load, conversation velocity, and causal reachability — dimensions that every LLM is architecturally blind to.

Based on the Trans-Horizon Communication Protocol (THCP) research. Three independent no-go theorems prove why no LLM can self-monitor these properties from the inside.

---

## Why this exists

Multi-turn AI agents lose accuracy. [Our market research](docs/research/market-demand.md) puts the number at **39% accuracy degradation after 5 turns** — a structural property of conversations that standard observability tools (LangSmith, RAGAS, DeepEval) cannot see because they measure responses, not conversations.

Horizon was built to close that gap. In A/B experiments across four scenarios, adding Horizon monitoring produced **+15.7% composite quality lift** and **87% fewer hallucination events** when Horizon events triggered interventions. The math is grounded in 173 academic references across information theory, cognitive science, category theory, and Lorentzian geometry.

- Read the demand proof → [`docs/research/market-demand.md`](docs/research/market-demand.md)
- Read the category argument → [`docs/content/naming-the-category-conversation-dynamics-monitoring.md`](docs/content/naming-the-category-conversation-dynamics-monitoring.md)
- Read the engineering case → [`docs/content/why-every-production-agent-needs-conversation-dynamics-monitoring.md`](docs/content/why-every-production-agent-needs-conversation-dynamics-monitoring.md)

---

## Getting started

Three paths — pick the one that fits your workflow:

### Path 1 — Hosted MCP (fastest, zero install)

The fastest way to add Horizon to any Cursor or Claude Desktop workspace. No Python required.

Request an alpha key → [open a Discussion](https://github.com/leocelis/horizon/discussions/new?category=q-a), then add to `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "horizon": {
      "url": "https://horizon.leocelis.com/sse",
      "headers": { "Authorization": "Bearer YOUR_KEY_HERE" }
    }
  }
}
```

In Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "horizon": {
      "url": "https://horizon.leocelis.com/sse",
      "headers": { "Authorization": "Bearer YOUR_KEY_HERE" }
    }
  }
}
```

That's it. Reload your MCP client and three tools appear: `new_conversation`, `process_turn`, `configure_session`.

> **Alpha access:** Horizon's hosted endpoint is in private alpha. Keys are distributed to agent developers who want to monitor real projects. [Open a Discussion](https://github.com/leocelis/horizon/discussions/new?category=q-a) to request one — describe your use case and we'll send a key.

### Path 2 — pip install (library integration)

```bash
pip install horizon-monitor
```

Verify your install (exercises the full pipeline on 5 canonical scenarios, ~25s):

```bash
horizon-validate
```

### Path 3 — MCP server from source

```bash
pip install 'horizon-monitor[mcp]'
horizon serve                             # stdio — for Cursor, Claude Desktop
horizon serve --transport sse --port 3847 # SSE — for web/team deployments
```

Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "horizon": { "command": "horizon", "args": ["serve"] }
  }
}
```

Full Cursor and Claude Desktop setup guides: [`docs/integrations/`](docs/integrations/)

---

## What it monitors

Standard observability tools evaluate individual response quality. Horizon evaluates **conversation quality** — a structurally different problem:

| Tool | What it sees | What it misses |
|---|---|---|
| LangSmith, Braintrust | Latency, cost, per-response quality | Drift across turns |
| RAGAS, DeepEval | Faithfulness, relevance per turn | Temporal desync, cognitive load |
| Human raters | Subjective quality | Systematic structural decay |
| **Horizon** | **Conversation dynamics** | Intentionally nothing |

Horizon does not replace per-response quality tools. It adds the dimension they all lack.

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

---

## Framework integrations

### OpenAI SDK

```python
from openai import OpenAI
from horizon import FidelityMonitor

monitor = FidelityMonitor()
session_id = monitor.new_conversation()
client = monitor.wrap(OpenAI(), session_id)

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Tell me about quantum computing."}]
)

traj = monitor.get_trajectory(session_id)
print(f"Fidelity: {traj.current_fidelity:.2f}  T*: {traj.estimated_t_star}")
```

`monitor.wrap()` accepts custom timestamp and context providers for testing and replay.

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
    monitor.process_turn(session_id, human_message=user_message,
        agent_response=result.final_output, timestamp=datetime.now(timezone.utc).isoformat())
```

---

## 4D Spacetime Signals

Every `process_turn()` returns a `TurnResult` with 29 fields across five signal families:

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
    clarification_threshold=0.25,           # tighter D_JS gate
    event_modes={"alert.drift": "active"},  # activate one event
)

# Compound weight override
monitor.configure(
    fidelity_weights={"alpha": 0.35, "lambda_r": 0.12, "lambda_i": 0.28, "beta": 0.25},
    temporal_weights={"gamma": 0.08, "delta": 0.04},
    spacetime_coefficients={"alpha": 1.0, "beta": 1.0, "gamma": 0.8, "delta_st": 0.5},
)
```

---

## Export

```python
# JSON
result = monitor.export_to(session_id, target="json")

# LangSmith / Langfuse / OpenTelemetry / Arize
result = monitor.export_to(session_id, target="langsmith",
    connection={"api_key": "ls__..."})
```

```bash
pip install horizon-monitor[langsmith]   # or langfuse, otel, arize
```

---

## Architecture

```
Input: plain strings (human_message, agent_response, optional timestamp, optional client_context)

Core pipeline (< 50ms on CPU):
  1. Embed both turns (local sentence-transformers, lazy-loaded)
  2–6.  IGT · D_JS · TWR · Bipredictability · Epsilon
  7. Temporal signals  — gap, retention, circadian, deictic
  8. Fidelity dynamics — composite score
  9. Health classification
 10. Pace signals       — velocity, acceleration
 11. Spacetime interval — ds² and interval class
 12. Causal reachability — light-cone membership
 13. Spatial signals    — device, location, frame shift
 14. Mode detection     — auto-classify conversation type
 15. Event evaluation   — 14 threshold checks
 16. Optional: SQLite persistence

Output: TurnResult dataclass (29 fields)
```

**Design constraints (all test-enforced):**
- Zero LLM calls — pure arithmetic and local embeddings
- Zero external network calls by default — fully local
- Zero transitive framework dependencies in core
- < 50ms core pipeline on CPU
- < 100MB memory for 100-turn conversations
- All events observe-by-default — never interferes unless explicitly configured

---

## Validation

All four IVD validation gates pass on a 5,602-record labelled corpus:

| Gate | Constraint | v0.2.0 |
|---|---|---|
| V1 — proxy correlation | per-conv ρ ≥ 0.6, per-turn ρ ≥ 0.5 | **0.685 / 0.659** |
| V2 — per-event P/R | every event P ≥ 0.7 AND R ≥ 0.7 | **all 16 events ≥ 0.70 / 0.70** |
| V3 — beats heuristics | rho lift > 25%, structural P ≥ 0.6 | **+202.4% lift, P=R=1.00** |
| V5 — cross-domain | per-turn ρ ≥ 0.4 AND per-conv ρ ≥ 0.48 | **min 0.517 / 0.718** |

Cross-embedding stability: ρ_conv spread **0.026**, ρ_turn spread **0.018** across three sentence-transformer backends (22M / 33M / 110M params). The fidelity signal lives in conversational structure, not in the embedding manifold.

Full evidence pack: [`docs/reviews/V0_2_0_EVIDENCE.md`](docs/reviews/V0_2_0_EVIDENCE.md)

---

## Deployment

### Self-hosted Docker (MCP server on port 3847)

```bash
cd deploy/docker
docker compose up
```

Horizon serves the MCP API via SSE. Point `.cursor/mcp.json` to `http://localhost:3847/sse`. The Dockerfile pre-caches the `all-MiniLM-L6-v2` weights at build time — zero cold start.

### Hosted (DigitalOcean App Platform)

The official hosted endpoint is live at `https://horizon.leocelis.com`. It runs on DigitalOcean App Platform (single instance, Redis-backed session resumability) and requires a Bearer token. See [Path 1](#path-1--hosted-mcp-fastest-zero-install) above.

---

## Development

```bash
git clone https://github.com/leocelis/horizon.git
cd horizon
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/ -v                         # full suite
pytest tests/unit tests/integration tests/e2e -v   # fast path (~6 min)
ruff check src/ tests/
black --check src/ tests/
```

---

## Repository layout

```
horizon/
├── src/horizon/         # package source (PEP 517/518 src/ layout)
│   ├── engines/         # IGT, D_JS, TWR, coherence, fidelity, epsilon, mode
│   ├── spacetime/       # temporal, circadian, deictic, velocity, interval, light cone, spatial
│   ├── events/          # 14-event evaluator
│   ├── integrations/    # OpenAI, Anthropic, LangChain, export targets
│   ├── mcp/             # MCP server + CLI
│   └── storage/         # optional SQLite persistence
├── tests/               # unit / integration / e2e / perf / validation
├── examples/            # runnable framework demos
├── deploy/              # Procfile, build.sh, runtime.txt, docker/
├── docs/
│   ├── research/        # market-demand.md + THCP theoretical framework
│   ├── content/         # published pieces on conversation dynamics monitoring
│   ├── integrations/    # Cursor / Claude Desktop / Copilot setup guides
│   ├── spec/            # HORIZON_TECH_SPEC.md + intent.yaml
│   └── reviews/         # E2E reviews, validation evidence
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

The monitor instruments all five conjectures as computable signals.

---

## Community

- **Request alpha access:** [Open a Discussion →](https://github.com/leocelis/horizon/discussions/new?category=q-a)
- **Ask a question:** [GitHub Discussions](https://github.com/leocelis/horizon/discussions/new?category=q-a)
- **Bug reports:** [GitHub Issues](https://github.com/leocelis/horizon/issues/new)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License

MIT — see [LICENSE](LICENSE).

<!-- mcp-name: io.github.leocelis/horizon-fidelity-monitor -->
