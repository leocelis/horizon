# Horizon Fidelity Monitor

> **"Quality is not a model property — it is a conversation property."**

<p align="center">
  <a href="https://github.com/leocelis/horizon/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/leocelis/horizon/ci.yml?branch=main&style=flat-square&label=tests" alt="Tests"></a>
  <a href="https://trust.complyedge.io/horizon" rel="noopener noreferrer">
    <img src="https://api.complyedge.io/v1/public/badge/horizon.svg" alt="ComplyEdge — runtime enforcement status" height="26">
  </a>
</p>

Horizon is a real-time conversation health monitor for AI agents. It tracks the **structural dynamics** of multi-turn conversations — semantic drift, information gain, ontological gap width, temporal desynchronisation, circadian cognitive load, conversation velocity, and causal reachability — dimensions that LLMs do not reliably surface from inside the conversation.

Horizon ships **two measurement planes**. The **conversation plane** (above, always
present) measures the health of a dialogue turn by turn. The optional **mission plane**
— *Memento Mori* — measures elapsed **calendar** time against goals: ages, deadlines,
stalls, per-entity latency, and share of a finite horizon. It is inert until you
configure a store. See [Mission plane](#mission-plane-memento-mori).

Horizon is **not** a manipulation, sycophancy, or human-influence detector — it measures conversation *dynamics*, not whether an agent is steering or flattering the user. See [LEGAL.md §1](LEGAL.md#1-what-horizon-is--and-is-not).

Why an external monitor? LLMs have *limited and unreliable* self-knowledge: introspection research shows partial self-access that is brittle and degrades on complex or out-of-distribution tasks ([Binder et al. 2024](https://arxiv.org/abs/2410.13787); [arXiv:2512.12411](https://arxiv.org/abs/2512.12411)). So rather than depend on a model reporting its own conversation dynamics, Horizon measures them externally with cheap, deterministic, always-on arithmetic that does not call the model at all.

---

## Why this exists

Multi-turn AI agents lose accuracy. The ICLR 2026 Outstanding Paper ["LLMs Get Lost In Multi-Turn Conversation"](https://iclr.cc/virtual/2026/poster/10009146) (Laban, Hayashi, Zhou & Neville — Microsoft Research / Salesforce Research) reports **39% average accuracy degradation** across multi-turn evaluation — a structural property that standard observability tools (LangSmith, RAGAS, DeepEval) cannot see because they measure responses, not conversations.

Horizon was built to close that gap. **It is observability first:** it surfaces conversation dynamics that response-level tools miss, using cheap deterministic arithmetic with zero model calls. In four controlled A/B scenarios where Horizon events drove a re-grounding intervention we measured a **+15.7% composite quality lift** and **87% fewer hallucination events** — but those are *synthetic, scripted scenarios with a hand-tuned controller*, not a production result. Treat them as promising in-house evidence, not a guaranteed outcome (see [Validation](#validation) and [LEGAL.md §5](LEGAL.md#5-performance-claims--scope-and-substantiation)). Every signal — information gain, divergence, estimated ontological gap width, causal reachability — is a standard information-theory or arithmetic measure computed on text embeddings and timestamps; see [4D Spacetime Signals](#4d-spacetime-signals) for the full definitions.

- Read the demand proof → [ICLR 2026 Outstanding Paper (Laban et al.)](https://iclr.cc/virtual/2026/poster/10009146)
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

**Not yet published to PyPI — until it is, use [Path 3](#path-3--mcp-server-from-source) (install from source) below.**

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
| LangSmith, Braintrust | Latency, cost, per-response quality | Deterministic, every-turn structural signals |
| RAGAS, DeepEval | Faithfulness, relevance per turn (DeepEval also has sampled multi-turn LLM-judge metrics) | Zero-LLM-call, real-time scoring on every turn |
| Langfuse, Arize Phoenix | Session-level LLM-judge evaluation | Deterministic, always-on scoring at sub-50ms |
| Human raters | Subjective quality | Systematic structural decay |
| **Horizon** | **Conversation dynamics** | Intentionally nothing |

Horizon does not replace per-response or LLM-judge quality tools. The differentiator is *how* it measures: deterministic, zero-LLM-call arithmetic on every single turn — effectively free and always-on — versus the alternative of sampled LLM-judge evaluations, which cost per sample and typically run offline or async rather than in real time.

---

## Quickstart

```python
from horizon_monitor import FidelityMonitor
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
from horizon_monitor import FidelityMonitor

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
from horizon_monitor import FidelityMonitor

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
from horizon_monitor import FidelityMonitor
from horizon_monitor.integrations.langchain import HorizonCallback

monitor = FidelityMonitor()
session_id = monitor.new_conversation()
callback = HorizonCallback(monitor, session_id)

llm = ChatOpenAI(callbacks=[callback])
llm.invoke("Explain the CAP theorem.")
print(f"Fidelity: {callback.last_result.fidelity_score:.2f}")
```

### OpenAI Agents SDK

```python
from agents import Agent, Runner
from horizon_monitor import FidelityMonitor

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

Every `process_turn()` returns a `TurnResult` with 32 fields across five signal families:

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

## 16 Event Types (conversation plane)

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
| `signal.grounding_required` | Heuristic grounding-need score crosses threshold — agent should hedge or cite grounding evidence |
| `signal.pace_premature_report` | User replied faster than a previously flagged deferred action could plausibly complete, with no completion signal |

---


## Mission plane (Memento Mori)

> **"Progress is not a turn property — it is a calendar property."**

The conversation plane answers *is this dialogue degrading?* The mission plane answers a
different question: *is this goal still moving, and against what clock?* A month of
individually healthy conversations that advance nothing is, to a conversation monitor, a
month of perfect health.

**The name is the design.** Every store has exactly one **root horizon** — a finite end
date you choose. Everything else hangs off it, so every day an item spends is a share of
a budget that is visibly running out. Without a finite root, deferring work costs
nothing and "later" is free forever. That is the failure this plane exists to make
visible.

**It is off by default.** With no store configured, its six tools do not register and
nothing in your integration changes.

### The problem it catches

A task was given until 20 July. It is now 18 August and nobody has touched the mission
since 2 July. A decision was parked "until things calm down" with a revisit date of
10 August that has quietly passed. The work has been sitting with one party for three
weeks. None of that is visible in any conversation, in any tracker's status column, or
in a model's context window — and each turn of each conversation about it looks healthy.

The mission plane reports it as: mission 78 days old, 47 days since progress, task
lifespan expired, park 8 days overdue, currently blocked on `operator` for 21 days and
counting.

### Vocabulary

Everything is an **item** in a tree under the root horizon. There are eight kinds:

| Kind | What it is |
|---|---|
| `horizon` | the finite root — exactly one per store, and the denominator for every share |
| `mission` | a goal with a clock; the thing that can stall |
| `task` | a unit of work with a **TTL** — an agreed window whose expiry means *investigate*, never *you estimated badly* |
| `deadline` | an external date (regulatory, contractual, market), ideally linked to the internal work it gates |
| `gate` | a checkpoint with an age budget |
| `entity` | something the work passes through and waits on — a queue, a vendor, a system, you |
| `deferral` | a park. **Requires a revisit date**; the store refuses one without it |
| `probe` | a small, dated trial of an alternative way of working, so routes are compared by measurement rather than opinion |

Two more terms appear in the outputs: a **sojourn** is one recorded stay in a stage
(enter → exit), and the **incumbent** is the way you are working today, as opposed to a
probe of some alternative.

### Quickstart

```bash
export HORIZON_MEMENTO_STORE_PATH=~/.horizon/missions.db   # the default: one local file
```

<details>
<summary>Running it somewhere durable and multi-tenant (MySQL)</summary>

A file-backed store is the right default, but it is the wrong choice on any host whose
filesystem resets between deploys — the plane would look correct and silently forget
everything, which is worse than not running at all. For those, point it at MySQL 8:

```bash
pip install "horizon-monitor[mysql]"
export HORIZON_MEMENTO_STORE_DSN='mysql://user:pass@host:3306/horizon'  # wins over _PATH
export HORIZON_MYSQL_SSL_CA=/path/to/server-ca.pem   # or ..._CA_B64 for a PEM in an env var
```

TLS verification is mandatory — the backend refuses to connect without a CA. Each API key
maps to an **assigned** tenant id (`scripts/provision_tenant.py`), so rotating a key keeps
that tenant's history; unknown or revoked keys get no mission access at all.

</details>

<details>
<summary>Feeding it from work you already do (artifact ingestion)</summary>

A clock is only as good as what reaches it, and a record that depends on
remembering to write is worth nothing on the day you forget. So the plane can
derive events from append-only sources you already produce:

```bash
python scripts/ingest_artifacts.py --store ~/.horizon/missions.db \
    --repo /path/to/repo --item-id <mission-id>
```

Each commit becomes an `ARTIFACT` event carrying the source's own provenance, and
the event's `valid_time` is the commit's timestamp — not the moment you ingested
it. Safe to run from cron: it dedupes on the source's native id and asks only for
what is new.

Two things it will not do. It will not guess which mission an artifact belongs to
— `--item-id` is required, and the adapter interface has no parameter capable of
attaching one. And it will not judge what counts as progress. Those are yours.

Not sure what to register in the first place? Ask what your history suggests:

```bash
python scripts/ingest_artifacts.py --store ~/.horizon/missions.db \
    --repo /path/to/repo --propose
```

It reports the shape — how many artifacts, over what span, starting when — and
proposes a `created_valid` equal to the earliest one. It proposes no title,
because what the work *is* cannot be read off a commit log. Nothing is written;
registering the mission is your call.

`GitLocalAdapter` is the reference implementation; trackers and mail metadata fit
the same `ArtifactAdapter` interface.

</details>

```python
from datetime import date, datetime, timezone

from horizon_monitor.memento import (
    EventKind, ItemKind, MementoConfig, MementoStore, evaluate,
)

store = MementoStore("missions.db")   # a real file; set this up once

root = store.register_item(
    kind=ItemKind.HORIZON, title="engagement horizon",
    created_valid=datetime(2026, 1, 1, tzinfo=timezone.utc),
    end_date=date(2030, 1, 1),
)
mission = store.register_item(
    kind=ItemKind.MISSION, title="ship-the-thing", parent_id=root,
    stall_days=14,                    # silence longer than this is a stall
    created_valid=datetime(2026, 6, 1, tzinfo=timezone.utc),
)
store.record_event(                   # progress: a side-effect of the work
    item_id=mission, kind=EventKind.PROGRESS,
    valid_time=datetime(2026, 7, 2, tzinfo=timezone.utc),
)

# The evaluation instant is always a parameter — the engine never reads a clock,
# so the same store at the same instant always yields the same report.
report = evaluate(
    store.snapshot(), datetime(2026, 8, 18, 12, tzinfo=timezone.utc), MementoConfig()
)

row = next(r for r in report.items if r.item_id == mission)
print(f"age:             {row.age_days} days")            # 78 days
print(f"since progress:  {row.days_since_progress} days") # 47 days
print(f"recording path:  {row.recording_path}")           # no recent work
print(f"horizon share:   {row.horizon_share:.4f}")        # 0.0595
```

The store is a real database, so run the setup once — registering a second root raises
`DuplicateRootError` by design, which is the one-finite-root guarantee working, not a
bug. For the full picture — an expired task, an overdue park, the blocking entity, a
refused write and a fired signal — run
[`examples/memento_mori_mission_clock.py`](examples/memento_mori_mission_clock.py) (no
arguments, no network, no API key; it uses a fresh temporary store each time).

### What it measures

| Output | Meaning |
|---|---|
| Age, days-remaining, TTL state | how old work is, how long is left, whether a task outlived its window |
| Days-since-progress + recording-path check | a stall — and whether it is *no work* or *no records*, never conflated |
| Slowest entity / blocking entity | the longest recorded wait, and separately what the work waits on **right now** |
| Horizon share | what fraction of the remaining root horizon this item has consumed |
| Cost-of-delay, break-even date | only when *you* declare an hourly rate and amounts |
| Path comparison | a probe's recorded sojourn beside the incumbent's accrued delay |

### 12 signal types (mission plane)

Separate from the conversation plane's [16 event types](#16-event-types-conversation-plane),
not an extension of them. Each fires **once on an edge** — when its predicate becomes
true — never again while the condition persists, and at most one new signal per turn, so
a bad week cannot flood you. Tiers order that cap: **P1** is time-critical, **P2**
structural, **P3** informational.

| Signal | Fires when | Tier |
|---|---|---|
| `signal.deadline_window` | an external deadline enters its warning window | P1 |
| `signal.ttl_expired` | a task outlives its ratified lifespan — *investigate the blocker* | P1 |
| `signal.deferral_expired` | a deferral passes its revisit date | P2 |
| `signal.gate_aging` | a gate exceeds its age budget with no progress | P2 |
| `signal.mission_stalled` | no progress events for the mission's threshold (paired with the recording-path check) | P2 |
| `signal.slowest_entity` | the identity of a mission's slowest recorded entity changes | P2 |
| `signal.clock_unpaired` | a deadline exists with no linked internal state | P2 |
| `signal.horizon_share` | an item's elapsed time crosses a threshold share of the remaining root horizon | P3 |
| `signal.cost_of_delay` | accrued cost-of-delay crosses an operator threshold (rate + amount + threshold all declared) | P3 |
| `signal.probe_ready` | a probe sojourn completes — enough to *compare numbers*, never a powered test | P3 |
| `signal.path_ahead` | a probe's recorded sojourn is shorter than the incumbent's accrued delay (descriptive only) | P3 |
| `signal.breakeven_passed` | a ratified break-even date passes without the measured improvement | P3 |

These ride the existing `process_turn` contract for sessions bound with
`associate_mission`. Every event carries `plane: "mission"`, and the contract is
deliberately **loud** — mission signals are surfaced to the operator with their numbers,
unlike conversation signals, which apply silently. See
[agent rules](docs/integrations/MEMENTO_MORI_AGENTS.md) for the block to paste into your
host.

### What it refuses

Accounting, never estimation. The engine never invents a duration, date, or amount:

- no forecasts, no completion predictions, no counterfactual "what the other path would
  have cost"
- no NPV/IRR/DCF, no discount rates, no currency conversion — money only ever multiplies
  measured time
- no p-values, confidence intervals, or sequential tests on path latencies: at
  single-operator sample sizes no dominance claim survives audit, so comparison is
  descriptive only
- no people analytics — entity latency is reported on functional **slots**; a person's
  wait is measured but never becomes a score, a ranking, or a resolvable identifier
- missing inputs degrade **by omission with an explanatory field**, never by substitution

Every row carries a `derivation` string spelling out the arithmetic it came from, and
any summary statistic additionally carries the `n` it summarised. Identical store plus
identical evaluation instant produces a byte-identical report.

**Docs:** [product requirements](docs/product/MEMENTO_MORI_PRD.md) ·
[technical spec](docs/spec/MEMENTO_MORI_TECH_SPEC.md) ·
[agent rules](docs/integrations/MEMENTO_MORI_AGENTS.md) ·
[acceptance test plan](docs/spec/MEMENTO_MORI_TEST_PLAN.md)

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

**Not yet published to PyPI — see [Path 3](#path-3--mcp-server-from-source) for a source install in the meantime.**

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
 15. Event evaluation   — 16 threshold checks
 16. Optional: SQLite persistence

Output: TurnResult dataclass (32 fields)
```

**Design constraints (test-enforced):**
- Zero LLM calls — pure arithmetic and local embeddings
- Zero external network calls by default — fully local
- Zero transitive framework dependencies in core
- < 50ms core pipeline on CPU — soft target (CI flags regressions past 50ms and hard-fails at 150ms)
- < 100MB memory for 100-turn conversations — hard-enforced at the claimed value
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

The official hosted endpoint is live at `https://horizon.leocelis.com`. It runs on DigitalOcean App Platform (single instance, in-process session state — sessions do not survive a restart) and requires a Bearer token, rate-limited and isolated per key. See [Path 1](#path-1--hosted-mcp-fastest-zero-install) above.

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
./scripts/compliance/check.sh              # EU AI Act offline gate
```

### ComplyEdge TrustLint — EU AI Act

Horizon integrates **[ComplyEdge](https://complyedge.io)** TrustLint on LLM-facing artifacts — same offline + runtime + trust pattern as [IVD](https://github.com/leocelis/ivd).

| Layer | What |
|-------|------|
| **Offline (required)** | `./scripts/compliance/check.sh` — scans `horizon_intent.yaml` + `horizon-monitor.mdc` |
| **Runtime (BYOK)** | `./scripts/compliance/runtime_check.sh` — feeds [live seal](https://api.complyedge.io/v1/public/badge/horizon.svg) + [trust page](https://trust.complyedge.io/horizon) |
| **CI gate** | `.github/workflows/ci.yml` jobs `compliance` + optional `compliance-runtime` |
| **Agent rule** | `<BEGIN-COMPLYEDGE v1.0>` in `docs/cursor-rules/horizon-monitor.mdc` |

Integration guide: [`docs/integrations/COMPLYEDGE.md`](docs/integrations/COMPLYEDGE.md). CE adoption guide: [`oss-trustlint-adoption-guide.md`](https://github.com/ComplyEdge/complyedge-platform/blob/main/docs/development/oss-trustlint-adoption-guide.md).

---

## Repository layout

```
horizon/
├── src/horizon/         # package source (PEP 517/518 src/ layout)
│   ├── engines/         # IGT, D_JS, TWR, coherence, fidelity, epsilon, mode
│   ├── spacetime/       # temporal, circadian, deictic, velocity, interval, light cone, spatial
│   ├── events/          # 16-event evaluator
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

THCP is **design motivation only** — see [`docs/product/THCP_FIDELITY_MONITOR_PRD.md`](docs/product/THCP_FIDELITY_MONITOR_PRD.md) for the full conjecture-to-signal mapping.

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
