# Horizon Fidelity Monitor

> **"Quality is not a model property — it is a conversation property."**

Horizon is a real-time conversation health monitor for AI agents. It tracks the **structural dynamics** of multi-turn conversations — semantic drift, information gain, ontological gap width, temporal desynchronisation, circadian cognitive load, conversation velocity, and causal reachability — dimensions that LLMs do not reliably surface from inside the conversation.

Horizon is **not** a manipulation, sycophancy, or human-influence detector — it measures conversation *dynamics*, not whether an agent is steering or flattering the user. See [LEGAL.md §1](LEGAL.md#1-what-horizon-is--and-is-not).

Why an external monitor? LLMs have *limited and unreliable* self-knowledge: introspection research shows partial self-access that is brittle and degrades on complex or out-of-distribution tasks ([Binder et al. 2024](https://arxiv.org/abs/2410.13787); [arXiv:2512.12411](https://arxiv.org/abs/2512.12411)). So rather than depend on a model reporting its own conversation dynamics, Horizon measures them externally with cheap, deterministic, always-on arithmetic that does not call the model at all.

---

## Why this exists

Multi-turn AI agents lose accuracy. The ICLR 2026 Best Paper ["LLMs Get Lost In Multi-Turn Conversation"](https://iclr.cc/virtual/2026/poster/10009146) (Laban et al., Microsoft Research) reports **39% average accuracy degradation** across multi-turn evaluation — a structural property that standard observability tools (LangSmith, RAGAS, DeepEval) cannot see because they measure responses, not conversations.

Horizon was built to close that gap. **It is observability first:** it surfaces conversation dynamics that response-level tools miss, using cheap deterministic arithmetic with zero model calls. In four controlled A/B scenarios where Horizon events drove a re-grounding intervention we measured a **+15.7% composite quality lift** and **87% fewer hallucination events** — but those are *synthetic, scripted scenarios with a hand-tuned controller*, not a production result. Treat them as promising in-house evidence, not a guaranteed outcome (see [Validation](#validation) and [LEGAL.md §5](LEGAL.md#5-performance-claims--scope-and-substantiation)). Each signal reduces to a standard information-theory measure; the relativity / Lorentzian framing is **design metaphor, not a physical claim** (see [4D Spacetime Signals](#4d-spacetime-signals)).

- Read the demand proof → [ICLR 2026 Best Paper (Laban et al.)](https://iclr.cc/virtual/2026/poster/10009146)
- Read the category argument → [`docs/content/naming-the-category-conversation-dynamics-monitoring.md`](docs/content/naming-the-category-conversation-dynamics-monitoring.md)
- Read the engineering case → [`docs/content/why-every-production-agent-needs-conversation-dynamics-monitoring.md`](docs/content/why-every-production-agent-needs-conversation-dynamics-monitoring.md)

---

## Getting started

Three paths — pick the one that fits your workflow:

### Path 1 — Hosted MCP (fastest, zero install)

The fastest way to add Horizon to any Cursor, VS Code, or Claude Desktop workspace. No Python required.

Request an alpha key → [open a Discussion](https://github.com/leocelis/horizon/discussions/new?category=q-a), then add the config for your client:

**Cursor** (`~/.cursor/mcp.json`):

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

**VS Code / GitHub Copilot** (`.vscode/mcp.json` in your workspace):

```json
{
  "servers": {
    "horizon": {
      "type": "http",
      "url": "https://horizon.leocelis.com/sse",
      "headers": { "Authorization": "Bearer YOUR_KEY_HERE" }
    }
  }
}
```

> **VS Code note:** Use `"servers"` (not `"mcpServers"`) and `"type": "http"` — VS Code tries Streamable HTTP first and falls back to SSE automatically, so `"type": "http"` works with the `/sse` URL.

**Claude Desktop** (`~/Library/Application Support/Claude/claude_desktop_config.json`):

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

> **"Spacetime" here is a metaphor, not physics.** The relativity vocabulary (Minkowski interval,
> light cone, proper time) is *design inspiration* — it shaped which quantities we compute. Every
> signal below reduces to a standard information-theory or arithmetic measure on text embeddings and
> timestamps, listed in the **Plain definition** column. Nothing in Horizon's behavior or validation
> depends on the analogy being literally true, and the Lorentzian `interval_class` is emitted as
> descriptive metadata only — no event or score depends on it.

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

### Spacetime (requires `timestamp` + turn ≥ 2) — descriptive metadata only

| Signal | Description (metaphor) | Plain definition (what it computes) |
|---|---|---|
| `spacetime_interval` | ds² with Minkowski-like signature (−,+,+,+) | A 4-term weighted distance: `ds² = −α·log(1+Δt)² + β·ΔD_JS² + γ·Δε² + δ·ΔC²`. The minus sign on the time term is a convention, not a physical law. |
| `interval_class` | `timelike` / `spacelike` / `lightlike` | The sign bucket of `ds²` (`< −ε`, `> ε`, else lightlike). Emitted as metadata only — **no event or fidelity score consumes it**. |

### Causal (requires `timestamp`)

| Signal | Description (metaphor) | Plain definition (what it computes) |
|---|---|---|
| `reachable_turns` | Turns still inside the causal light cone | Count of prior turns where `in_context × retention(Δt) × cosine_similarity > θ` — still in-window, not yet memory-decayed, and topically related. |
| `reachable_fraction` | Fraction of history still causally reachable | `reachable_turns / (turn − 1)`. |

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

**What is proven, and what is not.** Horizon's signals are *correlational, in-domain*
measurements that track human quality ratings well. They are **observability**, not a
proven outcome guarantee. Here is the honest status of each claim:

| Claim | Status | Where |
|---|---|---|
| Fidelity correlates with human ratings (in-domain) | ✅ measured (ρ ≈ 0.6–0.7) | gates below |
| Signal beats naive heuristics | ✅ measured | V3 |
| Holds on a **third-party** corpus (out-of-domain) | ❌ tested — ρ = **0.039** on MT-Bench expert judgments (n=80; below 0.3 floor); needs direct quality labels | [`V0_2_0_EVIDENCE.md` §Fix 4](docs/reviews/V0_2_0_EVIDENCE.md#fix-4--cross-domain-in-repo), [`adapt_external_corpus.py`](scripts/adapt_external_corpus.py) |
| Events **predict** degradation (leading, not lagging) | ⚠️ tested on MT-Bench — **insufficient-data** (2-turn chats; events rarely fire); tool works | [`leading_indicator.json`](docs/reviews/leading_indicator.json), [`measure_leading_indicator.py`](scripts/measure_leading_indicator.py) |
| Acting on events **improves outcomes** (+15.7%) | ⚠️ synthetic A/B only; needs an independent corpus | [`run_interventional_ab.py`](scripts/run_interventional_ab.py), [LEGAL.md §5](LEGAL.md#5-performance-claims--scope-and-substantiation) |

The four gates below pass on a **labelled** 5,602-record corpus (not bundled — see the
[evidence pack](docs/reviews/V0_2_0_EVIDENCE.md); `scripts/build_validation_corpus.py`
regenerates a *synthetic* corpus that exercises the gate logic, not these exact numbers):

| Gate | Constraint | v0.2.0 |
|---|---|---|
| V1 — proxy correlation | per-conv ρ ≥ 0.6, per-turn ρ ≥ 0.5 | **0.685 / 0.659** |
| V2 — per-event P/R | every event P ≥ 0.7 AND R ≥ 0.7 | **all 16 events ≥ 0.70 / 0.70** |
| V3 — beats heuristics | rho lift > 25%, structural P ≥ 0.6 | **+202.4% lift, P=R=1.00** |
| V5 — cross-domain | per-turn ρ ≥ 0.4 AND per-conv ρ ≥ 0.48 | **min 0.517 / 0.718** |

Cross-embedding stability: ρ_conv spread **0.026**, ρ_turn spread **0.018** across three sentence-transformer backends (22M / 33M / 110M params). The fidelity signal lives in conversational structure, not in the embedding manifold. (Note: cross-*embedding* stability on the same corpus is distinct from cross-*corpus* OOD — first third-party run on MT-Bench pairwise labels gave ρ = 0.039; see evidence pack §Fix 4.)

Remediation gaps source: [`DESIGN_FIXES_redteam_remediation.md`](docs/reviews/DESIGN_FIXES_redteam_remediation.md)

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
pip install -r requirements-dev.txt

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
│   ├── product/         # public product overview
│   ├── content/         # published pieces on conversation dynamics monitoring
│   ├── integrations/    # Cursor / Claude Desktop / Copilot setup guides
│   ├── cursor-rules/    # horizon-monitor.mdc (canonical Cursor agent rule)
│   ├── spec/            # HORIZON_TECH_SPEC.md + intent.yaml
│   └── reviews/         # E2E reviews, validation evidence
└── pyproject.toml
```

---

## Background

Horizon's design was *inspired by* the Trans-Horizon Communication Protocol (THCP), a speculative framework that maps human–AI communication onto general-relativity metaphors. The five THCP "conjectures" are **design intuitions, not proven laws** — each is useful only because it pointed at a concrete, computable signal:

| THCP conjecture (metaphor) | Computable signal it inspired |
|---|---|
| **THCP-1** — irreducible ontological loss ε > 0 | `epsilon_t` — estimated intent/response gap width [0, 1] |
| **THCP-2** — an optimal length T\* exists beyond which fidelity decays | IGT-trend convergence detection (`signal.convergence`, `estimated_t_star`) |
| **THCP-3** — communication requires encode/decode adjunction | `consistency_score` — bidirectional embedding predictability |
| **THCP-4** — global coherence requires "sheaf gluing" across turns | cross-turn contradiction / claim-consistency checks |
| **THCP-5** — optimal trajectories lie near the "light cone" | `reachable_fraction` — retention × similarity over prior turns |

The metaphors are not load-bearing: drop the physics vocabulary and the signals are exactly the same standard measures. THCP is **design motivation only** — see [Background](#background) and [`docs/product/THCP_FIDELITY_MONITOR_PRD.md`](docs/product/THCP_FIDELITY_MONITOR_PRD.md).

---

## Community

- **Request alpha access:** [Open a Discussion →](https://github.com/leocelis/horizon/discussions/new?category=q-a)
- **Ask a question:** [GitHub Discussions](https://github.com/leocelis/horizon/discussions/new?category=q-a)
- **Bug reports:** [GitHub Issues](https://github.com/leocelis/horizon/issues/new)
- **Contributing:** [CONTRIBUTING.md](CONTRIBUTING.md)

---

## License

MIT — see [LICENSE](LICENSE).

---

## Legal

| Document | Purpose |
|----------|---------|
| [LEGAL.md](LEGAL.md) | Full legal notices: what Horizon is/is not, high-stakes domain warnings, performance claim scope, EU AI Act classification, grounding hook privacy, limitation of liability |
| [TERMS_OF_SERVICE.md](TERMS_OF_SERVICE.md) | Binding terms governing hosted server access and commercial use |
| [PRIVACY_POLICY.md](PRIVACY_POLICY.md) | GDPR Art. 13 compliant privacy notice — what data is collected and your rights |
| [DATA_PROCESSING_AGREEMENT.md](DATA_PROCESSING_AGREEMENT.md) | GDPR Art. 28 DPA template for EU enterprise users (request via email) |
| [SECURITY.md](SECURITY.md) | Responsible disclosure policy; known self-hosted security considerations |

**Performance claims:** The +15.7% quality lift and 87% fewer hallucination events
figures in this README are from **synthetic, scripted controlled A/B scenarios** with
hand-tuned reference controllers — not production traffic and not the in-domain
validation corpus (V1–V5 gates use a separate labelled set). Results may vary by domain,
model, and deployment configuration. Do not use these figures in external marketing
without conducting your own domain-specific evaluation. See
[LEGAL.md §5](LEGAL.md#5-performance-claims--scope-and-substantiation) for full scope
and evidentiary basis.

**High-stakes domains:** Do not enable event types in `active` mode in healthcare,
legal, financial, or emergency service contexts without domain-specific validation and
human oversight. See [LEGAL.md §4](LEGAL.md#4-high-stakes-domain-warning).

<!-- mcp-name: io.github.leocelis/horizon-fidelity-monitor -->
