# THCP Fidelity Monitor — Product Requirements Document

*Leo Celis — ADA Research · April 2026*

**Codename**: Horizon
**Based on**: [Trans-Horizon Communication: A Theoretical Framework for Human–AI Interaction Across Ontological Boundaries](./TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md)

---

## 1. Executive Summary

The THCP Fidelity Monitor is a real-time middleware layer that measures and steers the quality of human–AI conversations as they unfold. It is grounded in the Trans-Horizon Communication Protocol (THCP), a mathematical framework that models the structural communication gap between humans and AI agents.

The product translates theoretical constructs into operational signals across four dimensions — semantics, time, space, and causality:

| THCP Construct | Operational Signal | Agent Behavior |
|---|---|---|
| Information Gain per Turn (IGT) | Semantic information added per turn | Detect convergence and stalling |
| Jensen-Shannon Divergence ($D_{JS}$) | Intent–response alignment | Trigger clarification checkpoints |
| Fidelity Dynamics ($\mathcal{F}_t$) | Cumulative communication quality | Track conversation health over time |
| Conversation Coherence (3-tier) | Global consistency via Bipredictability + TGN + constraint propagation | Detect global incoherence beyond pairwise checks |
| Temporal Asymmetry ($\Delta\tau$) | Human memory decay + resumption cost between turns | Detect desynchronization, trigger re-anchoring after gaps |
| Circadian Cognitive Factor ($\kappa$) | Human's variable clock rate based on time-of-day | Adjust complexity for off-peak hours |
| Deictic Temporal Resolution ($\mathcal{D}$) | Grounded "yesterday"/"next week" to absolute dates | Detect unresolvable temporal references |
| Spatial Context ($\sigma, \Phi$) | Device, location class, communication constraints | Adapt response length/complexity to physical context |
| Conversation Velocity ($v_t, a_t$) | Pace of semantic movement per unit of human time | Detect engagement shifts, urgency, disengagement |
| Spacetime Interval ($ds^2_{\text{conv}}$) | Unified time+space+meaning distance between turns | Classify turns as timelike (re-anchor) vs spacelike (clarify) |
| Causal Reachability ($J^-$) | Which prior turns are still "live" for both parties | Proactively warn before referencing forgotten context |

The monitor runs as a sidecar to any LLM-powered agent, consuming conversation turns and emitting structured signals. The agent decides what to do with those signals — the monitor does not generate responses.

**Core thesis**: Conversations fail not because models are bad, but because neither participant has visibility into the conversation's structural health. The Fidelity Monitor makes that health observable.

**Structural defensibility**: This capability gap is not temporary. Three independent impossibility results — from computability theory (Sigtermans 2025), self-referential computation (Tkemaladze 2026), and type theory (Spivack 2026) — prove that self-referential systems cannot fully self-monitor. Models will get better at individual responses; they cannot, by mathematical proof, fully observe their own conversation dynamics. Horizon provides the external observer that the no-go theorems prove is required. (See Appendix E.)

---

## 2. Problem Statement

### 2.1 The Problem

AI agents in multi-turn conversations exhibit three failure modes that current tools do not detect in real time:

1. **Premature solutioning** — The agent generates a complete solution before understanding the user's intent. The response is coherent but wrong. The user corrects, the agent rebuilds, and 4–8 turns are wasted.

2. **Semantic drift** — Over long conversations, accumulated small misalignments compound. Each turn is locally coherent, but the conversation as a whole contradicts itself or diverges from the original goal. (THCP Law 5 violation.)

3. **Conversation overshoot** — The agent continues generating content past the point of diminishing returns. The conversation has already converged but neither party recognizes it. (THCP Law 4 — $T^*$ exceeded.)

### 2.2 Why Existing Tools Don't Solve This

Current LLM observability and evaluation platforms operate at the wrong abstraction level for this problem:

**Post-hoc evaluation tools** (DeepEval, RAGAS, OpenEvals) score conversations after they complete. They answer "was this conversation good?" but cannot intervene during the conversation. They evaluate outcomes, not dynamics.

**Tracing/observability platforms** (LangSmith, Langfuse, Arize, Helicone) capture what happened — latency, token usage, tool calls, execution traces. They answer "what did the agent do?" but not "is the conversation going well?" They monitor infrastructure, not communication quality.

**Drift detection** (Confident AI, Arize) detects distribution shift in model outputs over time (days/weeks). It does not detect semantic drift within a single conversation (turns).

**None of these tools measure the conversation itself as a dynamic system with its own health trajectory.** The Fidelity Monitor fills this gap.

This is not merely an unaddressed engineering opportunity — it is a *structurally required* capability. Three independent no-go results (Sigtermans 2025, Tkemaladze 2026, Spivack 2026) prove that self-referential systems cannot fully self-monitor: any system that predicts while assessing its own performance must either be incorrect, non-halting, or perturb the state it measures. Empirical work confirms: all three frontier models (Claude, GPT-5.2, Gemini) exhibit model-heterogeneous calibration drift in multi-turn conversations that they cannot detect from inside (SACD, arXiv:2603.01239). An external observer is not a convenience — it is mathematically required. See Appendix E for the full analysis.

### 2.3 Who Has This Problem

- **AI agent builders** shipping multi-turn conversational products (customer support, coding assistants, research agents, tutoring systems)
- **Platform teams** managing multiple agents across different domains who need a unified quality signal
- **Researchers** studying human–AI interaction who need quantitative measures of conversation dynamics

---

## 3. Competitive Landscape

### 3.1 How the Major Labs Approach This Problem Today

#### OpenAI: Model Spec + Training-Time Alignment

OpenAI's primary mechanism is the **Model Spec** (updated December 2025, with a March 2026 post explaining the philosophy). The Spec defines behavioral rules via a "Chain of Command" hierarchy (platform > developer > user > tool) and embeds guardrails at training time through RLHF, post-training, and system-prompt adherence.

OpenAI's approach to conversation quality is **implicit**: models are trained to be "more measured and grounded in tone" (February 2026 release notes) and to proactively ask clarifying questions. The GPT-5.2 line was explicitly described by users as "questions, questions, clarifications" — a blunt-force version of what THCP would call a fidelity checkpoint.

**Alignment midtraining** (April 2026, alignment.openai.com) showed that training on alignment documents does *not* generalize to multi-turn chat settings — the model behaves aligned on close-to-distribution QA but reverts in production conversations. This validates THCP's prediction that alignment is a conversation-level property, not a model-level one.

**Activation steering** research (April 2026, arXiv:2604.08169) demonstrates inference-time methods to restore alignment under adversarial prompts while preserving coherence. Methods like StTP and StMP maintain trait expression across multi-turn settings with less repetition. This is the closest OpenAI-adjacent work to real-time conversation steering — but it operates at the activation level, not at the semantic/communication level.

**Gap**: OpenAI embeds conversation quality into the model itself. There is no external signal, no real-time dashboard, no way for a developer to monitor or override the model's conversation-management decisions. When the model's internal heuristics fail, there is no fallback.

#### Anthropic: Constitutional AI + Context Engineering

Anthropic's approach combines **Constitutional AI** (self-critique against principles) with engineering-level context management:

- **Context compaction** (beta, January 2026): automatically summarizes older conversation history when token count approaches a threshold, preventing context overflow. This is a mechanical solution to a semantic problem — it preserves tokens but may lose meaning.
- **1M token context windows** (GA March 2026): allows longer conversations before compaction is needed.
- **Memory and Projects**: accumulate user preferences across sessions.
- **Effective context engineering** (anthropic.com/engineering, April 2026): published best practices for managing agent context, recommending minimal system prompts, hybrid "just in time" context strategies, and single-topic conversations to avoid "context rot."

Anthropic's Mythos Preview risk report (April 2026) distinguishes **coherent misalignment** (broadly dangerous goals) from **context-dependent misalignment** (narrow failures in specific conditions). The latter is harder to detect and audit — it maps directly to THCP's prediction that alignment failures are conversation-structure-dependent, not model-global.

**Gap**: Anthropic solves the *length* problem (compaction, larger windows) but not the *quality* problem. Compaction is a token-management strategy, not a fidelity strategy. There is no signal that tells the developer "the conversation is drifting" or "the agent should ask a clarifying question here." Context engineering advice is manual ("keep conversations single-topic") rather than tooled.

#### Google DeepMind: Agentic Capabilities + Delegation

Google's Gemini 3 (2026) focuses on **improved agentic capabilities** — better tool use, multi-step task execution, instruction following. Their February 2026 delegation framework proposes "contract-first decomposition" and Delegation Capability Tokens for multi-agent coordination.

**Gap**: Google's work optimizes what agents *do*, not how they *communicate with humans*. The delegation framework is agent-to-agent, not agent-to-human. There is no conversational fidelity layer.

#### CollabLLM (Stanford/ICML 2025): Proactive Collaboration via Training

CollabLLM is the closest academic work to THCP's vision. It trains LLMs using **Multiturn-aware Rewards** — rewards that consider the long-term contribution of a response across the full conversation, not just the next turn. Results: 18.5% higher task performance, 46.3% improved interactivity, 17.6% higher user satisfaction in a 201-user study.

CollabLLM teaches models to ask clarifying questions proactively rather than making assumptions — exactly the behavior THCP's fidelity checkpoint trigger would produce.

**Gap**: CollabLLM is a *training method*, not a runtime tool. It requires fine-tuning. It cannot be applied to closed models (GPT, Claude). It doesn't provide runtime signals. It solves the same problem through a fundamentally different mechanism (training vs. monitoring).

### 3.2 Observability and Evaluation Platforms

| Platform | Type | Multi-Turn Conversation Quality | Real-Time Intervention | Semantic Drift Detection | Intent Divergence | Convergence Detection |
|---|---|---|---|---|---|---|
| **Confident AI / DeepEval** | Eval-first observability | Conversation-level metrics (completeness, relevancy, knowledge retention, role adherence, goal accuracy) | Alerting on score drops | Prompt/model drift over days | No | No |
| **LangSmith** | Tracing + eval | Session-level tracing, multi-turn eval | No real-time intervention | No within-conversation | No | No |
| **Langfuse** | OSS tracing | Session analytics | No | No | No | No |
| **Arize AI / Phoenix** | ML monitoring | Embedding drift detection | Alerting on distribution shift | Over time, not within conversation | No | No |
| **Maxim AI** | Full-lifecycle | Session/trace/span eval | Quality alerts | Online evaluators | No | No |
| **Galileo** | Hallucination focus | Luna-2 evaluators | Real-time guardrails | No | No | No |
| **Braintrust** | Eval-first | Timeline replay | No | No | No | No |
| **Helicone** | Gateway/proxy | Basic session tracing | No | No | No | No |
| **Portkey** | AI gateway | Session logs, prompt versioning, fallback routing | No | No (latency/cost focus) | No | No |
| **RAGAS** | OSS eval framework | Component-level (faithfulness, relevance, context) | No | No | No | No |
| **Bipredictability / IDT** | Research metric | Structural consistency (single metric $P$) | No | Within-conversation (token statistics) | No | No |
| **context-decay-drift** | OSS library | Drift score (0–100) vs. system prompt | No | System prompt adherence only | No | No |
| **SAFi / Spirit** | OSS governance | Behavioral identity consistency (virtue vectors) | Coaching feedback | Cross-session behavioral drift | No | No |
| **THCP Fidelity Monitor** | **Conversation dynamics** | **Per-turn fidelity trajectory** | **Checkpoint triggers, convergence signals** | **Within-conversation ($\lambda_r + \lambda_i$)** | **$D_{JS}$ measurement** | **$T^*$ detection** |

### 3.3 Key Differentiation

Every existing tool evaluates the *content* of conversations. The THCP Fidelity Monitor evaluates the *dynamics* — the trajectory of communication quality over time. This is a different measurement entirely:

- **Content evaluation** asks: "Is this response faithful, relevant, non-hallucinated?"
- **Dynamics evaluation** asks: "Is this conversation converging or diverging? Should the agent ask a question or give an answer? Has the conversation reached its natural end?"

**Updated competitive check (April 22, 2026)**: Three new entrants approach adjacent territory:

- **Bipredictability / IDT** (Hafez et al., arXiv:2604.13061) — the closest academic work. Monitors conversational structural consistency from token statistics alone, achieving 100% sensitivity for contradictions/shifts across 4,574 turns. However, it is a single metric (bipredictability $P$), not a multi-signal fidelity framework. It detects *that* drift happened but not *what kind* (recoverable vs. irreversible), cannot distinguish conversation modes, has no convergence detection, no cross-session persistence, and no event system. We incorporate it as Tier 1 of our coherence engine.
- **context-decay-drift** (PyPI, MIT license) — detects and solves context drift via semantic embeddings with a drift score (0–100) and context management. Useful but single-signal (semantic similarity to original context), no within-conversation dynamics, no intent-response divergence, no coherence checking, no convergence detection. Solves a subset of our problem (system prompt adherence) but not conversation dynamics.
- **SAFi / Spirit** (open-source) — tracks long-term behavioral consistency via cosine similarity on virtue-ethics behavioral vectors with exponential moving averages. Impressive for cross-session character drift (97.9% consistency over 1,600 interactions) but operates at the behavioral identity level, not the conversation quality level. Does not measure intent-response alignment, information gain, or convergence.

None of these answer the second set of questions — they each measure one dimension of conversation health. The THCP Fidelity Monitor measures the dynamics as a system.

**Updated 4D spacetime competitive check (April 2026)**: The 4D spacetime layer introduces a new category of measurement that no existing tool approaches:

- **Minkowski spacetime embeddings** (arXiv:2505.08795, "The Geometry of Meaning") demonstrate perfect embedding of hierarchical structures in 3D Minkowski space — validating that meaning has spatial geometry. However, this work applies to *static* word embeddings, not to *dynamic* conversation trajectories. Horizon applies the insight dynamically, measuring the evolving spacetime interval $ds^2_{\text{conv}}$ between conversation turns.
- **Neural Spacetimes** (arXiv:2408.13885) train pseudo-Riemannian manifolds for DAG embedding. Academic research with no conversation-level application. Horizon uses the concept but operationalizes it for real-time conversation dynamics.
- **DCGM** (2026) proves that "causal structure, not window size, is key" (+8.3 F1 over KV-compression). This validates Horizon's light cone approach but DCGM is a memory architecture, not a monitoring tool.
- **No existing tool computes circadian cognitive load, deictic temporal resolution, conversation velocity/acceleration, or a unified spacetime interval for conversations.** These are novel operational signals with no direct competitor.

**Why won't models solve this themselves?** The most common objection is that future models will internalize conversation-quality monitoring. Three lines of evidence close this path:

1. **The IPM No-Go Theorem** (Tkemaladze, March 2026): any computational system performing prediction while assessing its own predictive performance must fail — incorrect, non-halting, or state-perturbing. This is proven via Kleene's Recursion Theorem and holds for arbitrarily powerful machines.
2. **SACD empirical confirmation** (arXiv:2603.01239, March 2026): Claude, GPT-5.2, and Gemini all exhibit systematic, model-specific calibration drift in multi-turn conversations. Each drifts differently (confidence suppression, escalation, or stagnation). None detects its own drift.
3. **Representational incompleteness** (Spivack, Lean 4 proof): every parametric self-model has a diagonal it cannot represent. This generalizes Gödel/Turing/Cantor into a single topological obstruction. No amount of scale changes the topology.

See Appendix E for the full analysis mapping these results to the product.

---

## 4. Product Vision

### 4.1 What We Are Building

A lightweight runtime library (Python SDK, with TypeScript planned) that any AI agent framework can integrate in minutes. The library:

1. **Consumes** conversation turns (human message + agent response + optional timestamps and context) as they occur
2. **Computes** semantic signals (IGT, $D_{JS}$, TWR, coherence) and 4D spacetime signals (temporal gap, circadian factor, spatial constraints, velocity, spacetime interval, causal reachability) from each turn
3. **Emits** structured events (14 types) when thresholds are crossed
4. **Exposes** a trajectory API for dashboards and logging

The library does NOT generate responses, modify prompts, or interact with the LLM directly. It is a pure measurement and signaling layer.

### 4.2 What We Are NOT Building

- A new LLM or fine-tuning pipeline (cf. CollabLLM)
- An observability platform with dashboards, tracing, and alerting (cf. LangSmith, Langfuse)
- A prompt management or evaluation framework (cf. DeepEval, OpenEvals)
- A replacement for any of the above — the monitor is designed to integrate with them

### 4.3 Design Principles

1. **Measure, don't prescribe.** The monitor emits signals. The agent's controller decides the behavior. Different agents will respond differently to the same signal.
2. **Framework-agnostic.** Works with any LLM (OpenAI, Anthropic, open-source), any framework (LangChain, CrewAI, custom), any agent architecture.
3. **Lightweight.** No model calls for basic metrics. Optional LLM-as-judge for NLI-based coherence checking. Target < 50ms overhead per turn for the core pipeline.
4. **Theory-grounded, practically simple.** The THCP math informs the design but does not leak into the API. Developers interact with intuitive concepts: "information gain," "alignment score," "convergence signal."

### 4.4 Computation Model: Mathematical vs. Model-Based

Horizon is primarily a **mathematical and algorithmic system**. The core pipeline requires no LLM calls and no API access. This is a deliberate architectural choice with three justifications:

1. **Self-reference avoidance**: Asking an LLM to evaluate another LLM's conversation output creates the exact failure the Tkemaladze no-go theorem describes — an introspective predictive machine that must be incorrect, non-halting, or state-perturbing. The monitor avoids this by operating *outside* the inference process entirely.
2. **Cost neutrality**: Every monitored turn must not double the inference cost. A pure measurement layer adds no per-turn API cost.
3. **Latency budget**: The < 50ms core constraint rules out synchronous LLM calls (~200–500ms).

**Computation map:**

| Signal | Method | LLM required? | Latency |
|---|---|---|---|
| IGT (information gain) | Cosine distance between turn embedding and history embedding | No — embedding only | ~20ms |
| D_JS (intent divergence) | Cosine distance between human and agent embeddings | No — embedding only | < 5ms |
| TWR (token waste) | Semantic deduplication against prior turns | No — embedding only | < 5ms |
| Fidelity score | Weighted arithmetic sum of four signals | No — arithmetic | < 1ms |
| Tier 1 coherence (Bipredictability) | Token statistics on the context→response→next-prompt loop | No — token statistics | < 10ms |
| Temporal gap / retention | Timestamp subtraction + exponential decay formula | No — arithmetic | < 1ms |
| Circadian factor κ(t) | Piecewise lookup on local hour | No — lookup table | < 1ms |
| Deictic resolution D(c,t) | Regex extraction + `dateparser` library | No — NLP library | ~2ms |
| Velocity / acceleration | Embedding delta divided by time delta | No — arithmetic | < 1ms |
| Spacetime interval ds² | Weighted sum of squared differences | No — arithmetic | < 1ms |
| Causal reachability J⁻ | Set intersection across context, retention, similarity | No — set operations | < 2ms |
| Tier 2 coherence (TGN) | Lightweight graph neural network on conversation graph | No LLM — small GNN (~50M params) | ~100ms (opt-in) |
| Tier 3 coherence (NLI) | Cross-encoder NLI model for transitive contradiction | No LLM — small NLI model (~100M params) | ~200ms (opt-in) |
| AI uncertainty channel | Read logprobs from the LLM being monitored | No extra call — reads existing output | 0ms overhead |
| IGT fallback (if V1 fails) | LLM-as-judge scoring for information gain | Yes — LLM call | ~300ms (fallback only) |

**Required dependencies for the core pipeline:**
```
sentence-transformers   # embedding model (~30M params, all-MiniLM-L6-v2 default)
dateparser              # deictic temporal expression resolution (200+ locales)
tzlocal                 # local machine timezone detection
```

**Optional dependencies:**
```
maxmind-geoip2          # IP-based spatial grounding (location_class, timezone)
torch + small GNN       # Tier 2 coherence (TGN, ~50M params)
transformers NLI model  # Tier 3 coherence (cross-encoder, ~100M params)
```

The monitor never opens a connection to any external API in its default configuration. All processing is local. Export to observability platforms (LangSmith, Langfuse, Arize) is explicit and opt-in via `export_to()`.

---

## 5. Functional Requirements

### 5.1 Core Metrics Engine

#### 5.1.1 Information Gain per Turn (IGT)

Measures how much new information each turn adds to the conversation.

**Input**: Current turn text, conversation history embedding
**Output**: Scalar value in bits (estimated)
**Method**: Compute semantic similarity between the current turn and the compressed conversation history. New information = the orthogonal component. Uses embedding-based estimation (no LLM call required).

**Derived signals**:
- `igt_value`: raw information gain for this turn
- `igt_trend`: slope of IGT over the last N turns (positive = conversation is expanding, negative = diminishing returns)
- `convergence_signal`: boolean, true when `igt_trend < convergence_threshold` for M consecutive turns

#### 5.1.2 Intent–Response Divergence ($D_{JS}$ proxy)

Measures how well the agent's response aligns with the human's likely intent.

**Input**: Human message embedding, agent response embedding
**Output**: Scalar in [0, 1] — 0 = perfectly aligned, 1 = maximally divergent
**Method**: Jensen-Shannon divergence approximated via cosine distance between intent and response embeddings in a shared semantic space.

**Derived signals**:
- `divergence_score`: raw $D_{JS}$ proxy for this turn
- `clarification_trigger`: boolean, true when `divergence_score > clarification_threshold`
- `alignment_trajectory`: moving average of divergence over the conversation

#### 5.1.3 Token Waste Ratio (TWR)

Measures the fraction of tokens in the agent's response that add no new information relative to the conversation history.

**Input**: Agent response, conversation history
**Output**: Ratio in [0, 1] — 0 = every token is informative, 1 = pure redundancy
**Method**: Sentence-level deduplication + semantic similarity against history. Sentences with cosine similarity > threshold to any prior turn are counted as waste.

**Derived signals**:
- `twr_value`: raw waste ratio for this turn
- `verbosity_alert`: boolean, true when TWR exceeds threshold

#### 5.1.4 Conversation Coherence (Three-Tier Architecture)

Measures whether the conversation is globally consistent, beyond pairwise checks.

**Input**: Current agent response, full conversation graph
**Output**: Coherence score in [0, 1] — 0 = fully incoherent, 1 = fully consistent
**Method**: Three-tier architecture (informed by essay Appendix C.4):

- **Tier 1 — Bipredictability** (< 10ms, no model call): Token statistics measuring shared predictability across the context→response→next-prompt loop. Catches topic shifts, non-sequiturs, and local contradictions. Based on Hafez et al. (2026).
- **Tier 2 — Temporal Conversation Graph** (~100ms, lightweight GNN): Models the conversation as a graph with temporal edges (sequential turns) and shared-entity edges (turns referencing the same concepts). Graph attention propagates context to produce a global dialogue embedding for inconsistency detection. Based on TGN for dialogue coherence (arXiv:2601.03051).
- **Tier 3 — Constraint Optimization** (~200ms, graph algorithm, optional): Temporal constraint propagation over the conversation graph to catch transitive inconsistencies ($A \Rightarrow B$, $B \Rightarrow C$, $C$ contradicts $A$). Provides the approximate $H^1$ sheaf computation from the THCP framework at practical cost. Based on Eirew et al. (EMNLP 2025).

**Derived signals**:
- `consistency_score`: aggregate coherence for this turn (Tier 1 + Tier 2 weighted)
- `contradiction_pairs`: list of (turn_i, turn_j, confidence) for detected contradictions
- `coherence_alert`: boolean, true when consistency drops below threshold
- `transitive_contradictions`: list of contradiction chains detected by Tier 3 (when enabled)

### 5.2 Composite Fidelity Score

The four metrics combine into a single fidelity score tracking the conversation's health:

$$\mathcal{F}_t = w_1 \cdot \text{IGT}_t + w_2 \cdot (1 - D_{JS,t}) + w_3 \cdot (1 - \text{TWR}_t) + w_4 \cdot \text{Consistency}_t$$

Default weights: $w_1 = 0.3, w_2 = 0.3, w_3 = 0.15, w_4 = 0.25$. Configurable per domain.

**Amended fidelity dynamics** (informed by essay Appendix C.5): The fidelity dynamics from Law 3 are refined to distinguish recoverable drift from irreversible loss:

$$\mathcal{F}_{t+1} = \mathcal{F}_t + \alpha \cdot I_{\text{sem}}(m_{t+1}) - \lambda_r \cdot \delta_t^{\text{recoverable}} - \lambda_i \cdot \delta_t^{\text{irreversible}} - \beta \cdot D_{JS,t} - \gamma \cdot \Delta\tau_t - \delta \cdot (1 - \kappa_t)$$

where $\lambda_r \cdot \delta_t^{\text{recoverable}}$ captures misalignment correctable by re-anchoring or summarization, $\lambda_i \cdot \delta_t^{\text{irreversible}}$ captures loss from context eviction, compaction, or turn-boundary degradation (not correctable), $\gamma \cdot \Delta\tau_t$ is the **temporal asymmetry penalty** — the estimated fidelity loss from the human's memory decay and context switching cost during the gap between turns, and $\delta \cdot (1 - \kappa_t)$ is the **circadian cognitive penalty** — the fidelity cost from the human operating at reduced cognitive capacity (see essay Appendix E.1). At peak hours ($\kappa = 1$), this term vanishes; at the circadian nadir ($\kappa \approx 0.3$), it contributes $-0.7\delta$ to fidelity.

The temporal penalty is computed as:

$$\Delta\tau_t = (1 - R_{\text{conversation}}(\Delta t)) \cdot w_{\text{memory}}$$

where $R_{\text{conversation}}(\Delta t) = 2^{-\Delta t / h_c}$ is human retention estimated via Half-Life Regression (Settles & Meeder, ACL 2016), $\Delta t$ is wall-clock seconds between turns, and $h_c$ is the conversation context half-life (calibrated per domain). When $\Delta t < 60$ seconds, $\Delta\tau_t \approx 0$. When $\Delta t = 3$ days with $h_c = 24$ hours, $\Delta\tau_t \approx 0.875$ — the human has lost ~87.5% of conversational context. See essay Appendix D for full derivation and academic grounding.

**Derived signals**:
- `fidelity_score`: composite score in [0, 1]
- `fidelity_trajectory`: time series of fidelity over all turns
- `health_status`: enum {`healthy`, `degrading`, `critical`, `converged`}
- `degradation_type`: enum {`none`, `recoverable_drift`, `irreversible_loss`, `both`} — distinguishes whether the conversation can be repaired in-place or needs a session reset

### 5.3 Event System

The monitor emits structured events when conversation dynamics change:

| Event | Condition | Suggested Agent Behavior |
|---|---|---|
| `checkpoint.clarification` | $D_{JS} > \tau_{\text{clarify}}$ for current turn | Pause and ask a targeted question before responding |
| `checkpoint.comprehension` | IGT declining for N consecutive turns | Summarize understanding and ask for confirmation |
| `alert.drift` | $\mathcal{F}_t$ has decreased for M consecutive turns | Reset context or re-anchor to original intent |
| `alert.contradiction` | Consistency score drops below threshold | Flag specific contradicting turns for resolution |
| `alert.verbosity` | TWR exceeds threshold | Reduce response length; prioritize information density |
| `signal.convergence` | IGT near zero, $D_{JS}$ low, consistency high | Conversation has reached its natural endpoint; summarize and close |
| `signal.optimal_length` | Turn count approaches estimated $T^*$ | Proactively summarize and check if more is needed |
| `signal.horizon_widening` | Running $\epsilon_t$ estimate spikes (topic shift into harder domain) | Increase humility, reduce confidence, ask for more context |
| `signal.session_reset` | Irreversible loss ($\lambda_i \cdot \delta_t^{\text{irreversible}}$) exceeds threshold | Start fresh session with structured handoff summary |
| `signal.temporal_desync` | Gap between turns exceeds threshold (default: 3600s); estimated human retention $R < 0.5$ | Re-anchor: summarize where the conversation left off, check if intent has changed |
| `signal.broken_reference` | User references a prior turn whose content was lost to context compaction | Alert: user is referencing something the agent no longer has access to |
| `signal.frame_shift` | Client metadata indicates environment change (device, timezone, locale) | Adjust assumptions about available attention and cognitive bandwidth |
| `signal.pace_shift` | Conversation acceleration $\|a_t\| > \theta_a$ (significant change in interaction pace) | Distinguish engagement surge ($a > 0$, low $D_{JS}$) from frustration ($a > 0$, high $D_{JS}$) or disengagement ($a < 0$) |
| `signal.light_cone_collapse` | Reachable past $\|J^-(t_i)\|$ drops below critical threshold or reachable fraction $\|J^-\| / i < \theta_{\text{ratio}}$ | Proactively summarize key context before it becomes unreachable; warn agent not to reference lost turns |

Events are emitted as structured JSON, compatible with webhook, callback, or polling patterns. The agent's controller subscribes to events and decides whether to act on them.

**Default: Observe Mode.** All events ship in observe mode. Events are computed, logged, and returned in the API response, but each event carries an `active: false` flag until that event type has passed the precision/recall gates defined in V2 (Phase 1). Developers can override this per event type via configuration. This ensures no agent acts on unvalidated signals.

```python
# Event payload
{
    "type": "checkpoint.clarification",
    "active": false,           # observe mode — logged only
    "confidence": 0.72,
    "divergence_score": 0.41,
    "turn": 3,
    "suggested_behavior": "Ask a targeted question before responding",
    "mode": "execute"          # conversation mode context
}
```

When an event type passes V2 validation for a given domain, the developer can promote it to active mode:

```python
config = Config(
    active_events=["checkpoint.clarification", "signal.convergence"],
    observe_events=["alert.contradiction", "alert.drift"],
)
```

### 5.4 Configuration

All thresholds and weights are configurable per conversation, per domain, or globally:

```python
from horizon import FidelityMonitor, Config

config = Config(
    clarification_threshold=0.35,
    pace_shift_threshold=0.3,                # |a_t| threshold for signal.pace_shift
    light_cone_ratio_threshold=0.3,          # J⁻ ratio threshold for signal.light_cone_collapse
    convergence_window=3,
    convergence_threshold=0.1,
    consistency_method="fast",  # or "nli"
    fidelity_weights={"igt": 0.3, "djs": 0.3, "twr": 0.15, "consistency": 0.25},
    temporal_weights={"gamma": 0.1, "delta": 0.05},   # γ·Δτ and δ·(1-κ) weights
    context_half_life_hours=24,                         # h_c for HLR retention model
    temporal_desync_threshold_seconds=3600,             # gap threshold for temporal_desync
    chronotype_offset=0,                                # hours to shift circadian curve (e.g., +2 for night owl)
    spacetime_coefficients={"alpha": 1.0, "beta": 1.0, "gamma": 1.0, "delta_st": 1.0},  # ds² coefficients
    domain="technical",  # adjusts default thresholds
)

monitor = FidelityMonitor(config)
```

### 5.5 Integration API

```python
from horizon import FidelityMonitor

monitor = FidelityMonitor()

# After each turn
result = monitor.process_turn(
    human_message="I need a notification system for our app.",
    agent_response="Here's a full notification system architecture...",
    turn_number=1,
    timestamp="2026-04-22T14:30:00Z",  # optional: wall-clock time for temporal/circadian signals
    client_context={                    # optional: spatial/environmental context
        "device_type": "desktop",
        "timezone": "America/New_York",
        "locale": "en-US",
        "location_class": "office",     # office / home / transit / meeting / unknown
    },
)

# Access core metrics
print(result.igt_value)
print(result.divergence_score)
print(result.fidelity_score)
print(result.health_status)

# Access 4D spacetime signals (only present when timestamp provided)
print(result.gap_seconds)              # 0 (first turn)
print(result.circadian_factor)         # 1.0 (14:30 → peak 1)
print(result.estimated_retention)      # 1.0 (no gap)
print(result.conversation_velocity)    # 0.0 (first turn)
print(result.spacetime_interval)       # None (first turn — needs 2+ turns)
print(result.reachable_turns)          # 1
print(result.temporal_references)      # [] (no deictic expressions)

# Access spatial signals (only present when client_context provided)
print(result.spatial_constraint)       # Φ(office, desktop) = (high, large, 2000, high)

# Check for events
for event in result.events:
    if event.type == "checkpoint.clarification":
        pass  # Agent controller decides behavior
    elif event.type == "signal.light_cone_collapse":
        pass  # Proactively summarize before referencing lost context

# Access full trajectory
trajectory = monitor.get_trajectory()
```

---

## 6. Non-Functional Requirements

### 6.1 Performance

- Core metrics pipeline (IGT, $D_{JS}$, TWR): < 50ms per turn on CPU
- NLI-based consistency check: < 200ms per turn with GPU, < 500ms on CPU
- Memory footprint: < 100MB for conversations up to 100 turns
- Embedding model: configurable; defaults to a lightweight sentence-transformer (~30M params)

**Cold start and model download:**
- The default embedding model (`all-MiniLM-L6-v2`) is ~80MB and downloads on first `process_turn` via HuggingFace Hub
- Subsequent runs use the cached model from `~/.cache/huggingface/` (no re-download)
- For air-gapped or latency-sensitive environments: provide `model_path` in `Config` to load from a local directory, or install `horizon-monitor[bundled]` which pre-packages the model weights
- Target time-to-first-value: < 3 minutes on a standard connection (pip install + first process_turn). On slow networks, pre-downloading via `huggingface-cli download sentence-transformers/all-MiniLM-L6-v2` is recommended

### 6.2 Privacy

- No conversation data is sent to external services (unless the developer configures an external embedding model)
- All processing happens locally by default
- Optional: developers can use their own OpenAI/Anthropic API for embedding computation

### 6.3 Compatibility

- Python 3.10+
- Optional integrations: LangChain, LangGraph, CrewAI, OpenAI Agents SDK
- Framework-specific adapters: `monitor.wrap(client)` for OpenAI/Anthropic SDK wrapping, `HorizonCallback` for LangChain
- **MCP server**: `horizon serve` exposes `process_turn`, `new_conversation`, `get_trajectory`, and `configure` as MCP tools for integration with Cursor, Claude Desktop, and any MCP-compatible host. Configured via `mcpServers` in the host's settings.
- Export formats: JSON events, OpenTelemetry spans (for integration with Langfuse, LangSmith, Arize)

### 6.4 Deployment Models

- **Library (default)**: `pip install horizon-monitor` — runs in-process, no server, no container. All data stays in the host application's memory.
- **MCP server**: `horizon serve --port 3847` — standalone process exposing the Horizon API via Model Context Protocol. For IDE and desktop assistant integrations.
- **Self-hosted (Docker)**: `docker compose up` — containerized Horizon with optional persistent storage for cross-session dynamics. For teams wanting a shared instance without a cloud dependency.
- **Cloud (future)**: Hosted Horizon with usage-based metering, team dashboards, and managed calibration engine. See §11 Open Questions for pricing model.

### 6.5 Packaging & Distribution

- **PyPI**: `horizon-monitor` package with optional extras (`pip install horizon-monitor[geoip]`, `pip install horizon-monitor[full]`)
- **Docker Hub**: `horizon/monitor:latest` image with compose file for self-hosted deployment
- **GitHub**: MIT-licensed source with contributing guide, issue templates, and CI/CD pipeline

---

## 7. Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                       AGENT APPLICATION                           │
│                                                                   │
│  ┌──────────────┐     ┌──────────────┐                           │
│  │  User Input   │────►│  LLM / Agent │                           │
│  └──────┬───────┘     └──────┬───────┘                           │
│         │                    │                                    │
│         │ (optional:         │ (human_msg, agent_resp,            │
│         │  keystrokes,       │  optional: logprobs, timestamp,    │
│         │  latency)          │  client_context)                   │
│         ▼                    ▼                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │              HORIZON FIDELITY MONITOR                       │  │
│  │                                                             │  │
│  │  ┌────────┐ ┌────────┐ ┌──────┐ ┌────────────────────────┐│  │
│  │  │  IGT   │ │  D_JS  │ │ TWR  │ │    Coherence Engine    ││  │
│  │  │ Engine │ │ Engine │ │Engine│ │ T1: Bipredictability    ││  │
│  │  │        │ │        │ │      │ │ T2: Temporal Graph      ││  │
│  │  │        │ │        │ │      │ │ T3: Constraint Optim.   ││  │
│  │  └───┬────┘ └───┬────┘ └──┬───┘ └──────────┬─────────────┘│  │
│  │      │          │         │                 │              │  │
│  │  ┌───┴──────────┴─────────┴─────────────────┴────────────┐│  │
│  │  │  4D SPACETIME LAYER                                    ││  │
│  │  │  Circadian κ(t) · Deictic D(c,t) · Spatial Φ(σ)      ││  │
│  │  │  Velocity v_t · Acceleration a_t · Interval ds²       ││  │
│  │  │  Light Cone J⁻(t_i) · Reachability Map                ││  │
│  │  └───┬──────────┬─────────┬─────────────────┬────────────┘│  │
│  │      ▼          ▼         ▼                 ▼              │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │  FIDELITY COMPOSITOR (amended dynamics + 4D)         │ │  │
│  │  │  F_t + α·I_sem - λ_r·δ_recov - λ_i·δ_irrev        │ │  │
│  │  │       - β·DJS - γ·Δτ - δ·(1-κ)                     │ │  │
│  │  └──────────────────────┬───────────────────────────────┘ │  │
│  │                         │                                  │  │
│  │  ┌──────────────┐      │      ┌──────────────────────┐   │  │
│  │  │  ε_t Tracker │──────┼──────│  Mode Classifier     │   │  │
│  │  │ (topic shift,│      │      │ (execute/explore/    │   │  │
│  │  │  difficulty) │      │      │  refine/learn)       │   │  │
│  │  └──────────────┘      │      └──────────────────────┘   │  │
│  │                         ▼                                  │  │
│  │  ┌──────────────────────────────────────────────────────┐ │  │
│  │  │               EVENT EMITTER                          │ │  │
│  │  │  14 event types · observe/active mode per type       │ │  │
│  │  └──────────────────────┬───────────────────────────────┘ │  │
│  └─────────────────────────┼──────────────────────────────────┘  │
│                            │                                      │
│      ┌─────────────────────┼─────────────────────────┐           │
│      ▼                     ▼                         ▼           │
│  ┌────────────┐  ┌──────────────────┐  ┌────────────────────┐   │
│  │   AGENT    │  │   PERSISTENT     │  │   SHARED FIDELITY  │   │
│  │ CONTROLLER │  │  DYNAMICS STORE  │  │    DASHBOARD       │   │
│  │ (decides   │  │ (cross-session   │  │  (human + agent    │   │
│  │  behavior) │  │  ε, profiles)    │  │   shared view)     │   │
│  └────────────┘  └──────────────────┘  └────────────────────┘   │
│                                                                   │
│  Optional: Export to LangSmith / Langfuse / Arize                │
│  Optional: MCP server mode (horizon serve) for IDE/desktop use   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 8. Phased Delivery

### Phase 1: Core Metrics Library + Validation

**What**: Python package with the four metric engines, composite fidelity score, and event system. No external dependencies beyond sentence-transformers. Ships with all events in **observe mode** by default (signals are logged and returned in the API but do not recommend agent behavior changes until validated).

**Validates**: Three questions must be answered before Phase 2 begins:

1. **Do the proxy metrics track what they claim to measure?** (Condition V1)
2. **Are the signals clean enough to act on?** (Condition V2)
3. **Does the monitor outperform naive heuristics?** (Condition V3)

#### V1: Proxy Validation Protocol

The embedding-based proxies (IGT via orthogonality, $D_{JS}$ via cosine distance, TWR via semantic deduplication) are approximations of theoretical constructs. They must be validated against human judgment before any downstream decisions are built on them.

**Validation dataset requirements**:
- 200+ multi-turn conversations from at least 3 domains (technical Q&A, creative/exploratory, task execution)
- Sourced from public datasets (ShareGPT, LMSYS Chatbot Arena, WildChat) or internal ADA conversations
- **Per-turn annotations** by 2+ independent annotators per conversation:
  - "Did this turn add meaningful new information?" (binary — validates IGT)
  - "Did the agent's response address the human's actual intent?" (1–5 scale — validates $D_{JS}$)
  - "Does this turn contradict anything said earlier?" (binary + location — validates consistency)
  - "Should the agent have asked a clarifying question instead of responding?" (binary — validates clarification trigger)
  - "Has the conversation reached its natural endpoint?" (binary per turn — validates convergence detection)
- Inter-annotator agreement target: Cohen's $\kappa > 0.6$ on binary judgments

**Success criteria**:
- Composite fidelity score correlates with mean per-turn human quality at Spearman $\rho > 0.5$ (per-turn level) and $\rho > 0.6$ (conversation level)
- IGT trend direction matches annotator "new information" judgments in > 75% of turns
- $D_{JS}$ proxy ranks conversations by alignment accuracy with > 70% concordance against annotator intent scores
- Convergence detection agrees with annotator "natural endpoint" in > 70% of cases
- Clarification trigger fires in > 80% of cases where annotators say clarification was needed

**If V1 fails**: The specific proxy that underperforms is replaced. Candidate replacements: LLM-as-judge scoring for IGT (higher accuracy, higher latency), cross-encoder similarity for $D_{JS}$ (more accurate than bi-encoder cosine), or NLI-only consistency (dropping the fast embedding tier). The validation protocol re-runs on the replacement. The framework is not abandoned — the proxies are swapped.

#### V2: Signal Precision and Recall Gates

Each event type must meet minimum precision and recall thresholds against the annotated validation dataset before it graduates from observe mode to active mode.

| Event | Minimum Precision | Minimum Recall | Rationale |
|---|---|---|---|
| `checkpoint.clarification` | 0.80 | 0.70 | False positives are expensive — unnecessary questions erode trust |
| `checkpoint.comprehension` | 0.75 | 0.65 | Redundant summaries are annoying but less damaging than wrong questions |
| `alert.contradiction` | 0.90 | 0.60 | Contradiction flags must be reliable; missing some is acceptable |
| `alert.drift` | 0.75 | 0.60 | Drift alerts are soft signals; moderate precision is acceptable |
| `alert.verbosity` | 0.70 | 0.70 | Low-stakes signal; balanced precision/recall |
| `signal.convergence` | 0.85 | 0.70 | Premature convergence signals cut off useful conversation |
| `signal.optimal_length` | 0.80 | 0.65 | Related to convergence; premature length warnings waste user attention |
| `signal.horizon_widening` | 0.70 | 0.65 | Conservative; false positives only add unnecessary caution |
| `signal.session_reset` | 0.90 | 0.50 | Session resets are high-cost; precision must be high, low recall acceptable |
| `signal.temporal_desync` | 0.80 | 0.80 | Timestamp-based; high inherent accuracy. Re-anchoring is low-cost, so balanced gates |
| `signal.broken_reference` | 0.85 | 0.60 | False positives confuse the agent about what it does/doesn't know; precision prioritized |
| `signal.frame_shift` | 0.70 | 0.65 | Depends on client metadata quality; conservative thresholds |
| `signal.pace_shift` | 0.70 | 0.60 | Velocity/acceleration are derived signals; moderate thresholds until empirical calibration |
| `signal.light_cone_collapse` | 0.85 | 0.55 | High-impact signal (warns agent about unreachable context); precision prioritized, low recall acceptable |

Events that fail their precision gate remain in observe mode. They are still logged, still available via the API, but the `active` flag is set to `false` and reference controllers skip them.

**Bayesian precision check**: Given the base rate of each event type in the validation corpus, compute the positive predictive value (PPV) at the achieved sensitivity and specificity. If PPV < 0.6 for any event, that event's threshold is tightened until PPV exceeds 0.6, even at the cost of recall.

#### V3: Naive Heuristic Baseline

The monitor must demonstrably outperform a set of zero-intelligence heuristic rules. If it doesn't, the framework's complexity is not justified.

**Baseline heuristics** (no embeddings, no ML):
1. **Length-ratio rule**: If `len(human_message) < 30 words` and `len(agent_response) > 200 words`, trigger clarification
2. **Repetition rule**: If > 3 sentences in the agent response appear verbatim in prior turns, trigger verbosity alert
3. **Timer rule**: Every 5 turns, trigger a comprehension checkpoint
4. **Keyword contradiction rule**: If the agent says "however" or "actually" followed by negating a prior claim, trigger contradiction

**Success criterion**: The THCP Fidelity Monitor outperforms the naive heuristics by > 25% on fidelity-quality correlation (Spearman $\rho$) across the validation dataset. Additionally, the monitor must catch at least one class of failure that heuristics structurally cannot detect — the critical case being **globally incoherent conversations that are locally coherent** (sheaf gluing failures), where adjacent turns are consistent but the conversation as a whole contradicts itself.

**If V3 fails**: If the monitor outperforms heuristics by < 15%, the product should ship as a simpler heuristic-based tool and the THCP framework should be treated as a research contribution rather than a product foundation. If the margin is 15–25%, the monitor ships but the THCP framing is de-emphasized in favor of practical positioning.

#### Optional Enhancement: AI Uncertainty Channel (Phase 1b)

For open-source models (via LogitScope, vLLM) or API-accessible models (via OpenAI logprobs), the monitor can incorporate AI-side internal state (informed by essay Appendix C.2):

- **Response entropy**: Mean token entropy across the generated response — measures AI-side uncertainty
- **Varentropy spikes**: Tokens where the model considered multiple distinct alternatives — decision points where the AI was uncertain
- **Surprisal peaks**: Tokens with unexpectedly low probability given context — potential hallucination sites

The critical disambiguation this enables: **high $D_{JS}$ + low AI entropy = the AI is confidently wrong** (dangerous). **High $D_{JS}$ + high AI entropy = the AI is uncertain** (salvageable via clarification). The text-only monitor cannot make this distinction.

**Availability**: OpenAI API (`logprobs=True, top_logprobs=N`), vLLM (`prompt_logprobs`), HuggingFace (via LogitScope — IBM, ICLR 2026). Not available for Anthropic Claude as of April 2026.

### Phase 2: Framework Integrations + Conversation-Mode Awareness + Outcome Validation

**What**: Drop-in integrations for LangChain/LangGraph, OpenAI Agents SDK, and CrewAI. OpenTelemetry export for observability platforms. A conversation-mode classifier that adjusts event thresholds based on what kind of conversation is happening. A/B test protocol to prove that acting on signals improves outcomes.

#### Conversation-Mode Classifier

The monitor in Phase 1 assumes all conversations are goal-directed. They are not. A high $D_{JS}$ in an exploratory brainstorm is a feature; in a bug-fixing session it's a failure. The monitor needs to know the difference.

**Conversation modes** (detected automatically from the first 2–3 turns, overridable by the developer):

| Mode | Description | Threshold Adjustments |
|---|---|---|
| `execute` | Goal-directed, task-completion focused (coding, Q&A, support) | Default thresholds. Low $D_{JS}$ tolerance. Convergence signals active. |
| `explore` | Open-ended, idea generation, brainstorming | $D_{JS}$ threshold raised by 50%. Convergence signals suppressed for first N turns. |
| `refine` | Iterative improvement on an existing artifact | IGT thresholds lowered (small gains are expected). Contradiction sensitivity raised. |
| `learn` | Tutoring, explanation, understanding-focused | Comprehension checkpoints more frequent. Convergence signals less aggressive. |

**Detection method**: Lightweight classifier on the first 2–3 turns using intent embeddings + structural features (question density, specificity, presence of artifacts). No LLM call required. Developers can also set mode explicitly via `config.conversation_mode = "explore"`.

**Why this matters**: Without mode awareness, the monitor optimizes every conversation toward goal-directed convergence. This penalizes the exact conversation types (exploratory, creative, educational) where divergence is productive. The mode classifier prevents the monitor from making conversations worse by applying the wrong optimization target.

#### Running $\epsilon_t$ Estimator (Horizon Width Tracker)

The ontological gap $\epsilon$ is not constant — it shifts as topics change within a conversation (informed by essay Appendix C.6). The monitor maintains a per-turn estimate:

| Signal | Source | What It Estimates |
|---|---|---|
| Topic shift detector (DMF-style) | Conversation text, dual-process cognition (Wang et al., COLING 2025) | When the conversation enters a new domain with potentially different $\epsilon$ |
| AI difficulty estimate | Logprob entropy or hidden representations (EMNLP 2025) | How uncertain the AI is about this specific content — proxy for domain-specific $\epsilon$ |
| Historical $\epsilon$ by domain | Persistent dynamics store (Phase 3) | Learned $\epsilon$ values for known domains from prior sessions |

When $\epsilon_t$ spikes, the monitor emits `signal.horizon_widening`. The Online Domain-aware Decoding framework (ODD, arXiv:2602.08088) demonstrates that real-time domain shift detection is achievable at ~0.2ms overhead per decoding step.

#### Temporal Context Layer (Human Time/Space Awareness)

LLM agents are empirically "temporally blind" — they assume a stationary context, failing to account for the real-world time elapsed between messages (Cheng et al., arXiv:2510.23853, TicToc dataset: no model exceeds 65% alignment with human temporal perception even when given timestamps). The temporal context layer gives the agent a functional sense of the *human's* time and space.

**New parameters in `process_turn()`**:
- `timestamp` (ISO 8601, optional): wall-clock time of the human's message. When present, Horizon computes all temporal and circadian signals automatically.
- `client_context` (object, optional): `device_type`, `timezone`, `locale`, `location_class` (office/home/transit/meeting/unknown), `ip_address` (for optional geolocation). Enables `signal.frame_shift` and spatial grounding.

**Temporal signals computed from timestamps**:

| Signal | Computation | Source |
|---|---|---|
| `gap_seconds` | $\Delta t$ between current and previous turn timestamps | Timestamp delta |
| `gap_class` | microsecond / seconds / minutes / hours / days | Classification of $\Delta t$ |
| `estimated_retention` | $R = 2^{-\Delta t / h_c} \cdot \kappa(t_{\text{local}})$ — human retention adjusted for circadian position | Half-Life Regression (Settles & Meeder, ACL 2016) × Circadian factor (Valdez et al. 2012) |
| `temporal_asymmetry` | $\Delta\tau = \tau_H - \tau_A = \tau_H$ — always positive, always asymmetric | Proper time difference (physics) |
| `resumption_cost` | Estimated cognitive load based on gap class and interruption depth | Gloria Mark (2023): 23m15s average recovery; Leroy (2009): attention residue |
| `circadian_factor` | $\kappa(t_{\text{local}}) \in [0, 1]$ — cognitive capacity at the human's local time | Circadian performance curve (Valdez et al. 2012; Schmidt et al. 2007) |
| `temporal_references` | List of deictic expressions found in message, resolved to absolute datetimes | `dateparser` / `datefinder` extraction against `timestamp` as reference base |
| `conversation_velocity` | $v_t = \Delta D_{\text{semantic}} / \Delta\tau$ — semantic displacement per unit human time | Embedding delta / proper time |
| `conversation_acceleration` | $a_t = v_t - v_{t-1}$ — rate of change of pace | Velocity derivative |
| `spacetime_interval` | $ds^2_{\text{conv}}$ — unified time+space+meaning distance (Minkowski-like) | See essay Appendix E.5 |
| `interval_class` | `timelike` / `spacelike` / `lightlike` — based on $ds^2$ sign | Minkowski classification |
| `reachable_turns` | $\|J^-(t_i)\|$ — count of prior turns still in the conversation light cone | Context window ∩ retention ∩ semantic relevance |
| `reachable_fraction` | $\|J^-(t_i)\| / i$ — fraction of conversation still reachable | Light cone size / total turns |

**Spatial signals computed from `client_context`**:

| Signal | Computation | Source |
|---|---|---|
| `location_class` | Inferred from `device_type` + `timezone` + optional `ip_address` geolocation | MaxMind GeoIP2 (v5.2.0); `tzlocal` for local machine |
| `spatial_constraint` | $\Phi(\sigma_t)$ — attention budget, screen capacity, max response length, complexity ceiling | NN/G device-dependent cognitive load research (2024) |
| `spatial_frame_shift` | $\Delta\Phi = \|\Phi(\sigma_t) - \Phi(\sigma_{t-1})\|$ — magnitude of environmental change | Constraint vector delta |

**Conversation geodesics**: When the Temporal Conversation Graph (Tier 2 coherence) detects that the user's current turn references a prior turn, the geodesic distance accounts for both semantic distance and temporal decay:

$$d(i, j) = \alpha \cdot d_{\text{semantic}}(i, j) + \beta \cdot f(\Delta\tau_{H}(i, j)) + \gamma \cdot \mathbb{1}[\text{context\_lost}(i, j)]$$

When the geodesic is broken (context compaction erased the referenced content), `signal.broken_reference` fires.

**Research grounding**: See essay Appendix D (references 119–141) for temporal foundations and Appendix E (references 142–173) for the full 4D extension covering circadian cognitive load, deictic temporal resolution, spatial grounding, conversation velocity/acceleration, the conversation spacetime interval, and the causal reachability map.

#### 4D Spacetime Layer (Full Space-Time-Distance Awareness)

The Temporal Context Layer is extended to a complete 4D translation between the agent's event-horizon state and the human's spacetime experience (informed by essay Appendix E):

**Circadian Cognitive Factor** ($\kappa$): Using the human's local time (derived from `timestamp` + `client_context.timezone`), Horizon computes a circadian cognitive factor $\kappa(t_{\text{local}}) \in [0, 1]$ based on Valdez et al.'s (2012) diurnal performance curve. Peaks: 10:00–14:00, 16:00–22:00 ($\kappa = 1.0$). Post-lunch dip: 14:00–16:00 ($\kappa = 0.7$). Nocturnal decline: 22:00–04:00. Nadir: 04:00–07:00 ($\kappa = 0.3$). This modifies both `estimated_retention` and the fidelity equation (the $\delta \cdot (1 - \kappa_t)$ term). Research: 9–34% reaction time variation and 45–83% synchrony effects across 65+ studies.

**Deictic Temporal Resolution** ($\mathcal{D}$): Extracts temporal expressions ("yesterday", "next Monday", "three weeks ago") from the human's message and resolves them to absolute ISO 8601 datetimes using the human's `timestamp` as reference base. Unresolvable expressions ($T_i = \bot$) signal the agent to ask for clarification. Implementation: `dateparser` v1.4.0 (200+ locales, `search_dates()`) or `datefinder` v1.0.0 (766× faster with typed match objects). Research: HeidelTime (SemEval 2010), SUTime (Stanford CoreNLP), TIMEX3 standard.

**Spatial Grounding** ($\sigma, \Phi$): Maps `client_context` to a spatial constraint vector $\Phi(\sigma_t) = (\text{attention\_budget}, \text{screen\_capacity}, \text{max\_response\_length}, \text{complexity\_ceiling})$. Device changes (desktop → mobile) and timezone shifts trigger `signal.frame_shift` with quantified $\Delta\Phi$. Optional IP geolocation via MaxMind GeoIP2 (v5.2.0) provides city-level location class. For local agents (IDE, CLI), `tzlocal` v5.3.1 provides reliable IANA timezone names from system config. Research: NNG mobile content is 2× as difficult (72s avg mobile sessions); screen size determines channel capacity.

**Conversation Velocity and Acceleration** ($v_t, a_t$): Computes $v_t = \Delta D_{\text{semantic}} / \Delta\tau$ (semantic displacement per unit human time) and $a_t = v_t - v_{t-1}$ (pace change). High velocity + low $D_{JS}$ = productive flow. High velocity + high $D_{JS}$ = urgent correction needed. Deceleration ($a < 0$) = disengagement or difficulty. Fires `signal.pace_shift` when $|a_t| > \theta_a$. Research: Onishi et al. (SIGDIAL 2025) — turn-taking speed modeled as gamma distributions; latency study (arXiv:2604.06183) — 9s optimal perceived usefulness; PMIScore (2026) — unsupervised engagement metric.

**Conversation Spacetime Interval** ($ds^2_{\text{conv}}$): A unified metric combining temporal and semantic dimensions:

$$ds^2_{\text{conv}} = -\alpha \cdot d\tau^2 + \beta \cdot dD_{JS}^2 + \gamma \cdot d\epsilon^2 + \delta \cdot dC^2$$

Signature $(-,+,+,+)$ as in Minkowski spacetime. **Timelike** ($ds^2 < 0$): time dominates meaning — re-anchor. **Spacelike** ($ds^2 > 0$): meaning dominates time — clarify. **Lightlike** ($ds^2 \approx 0$): balanced, healthy flow. Coefficients calibrated empirically via V4 A/B testing. Grounded in: "The Geometry of Meaning" (arXiv:2505.08795, 2025) — perfect Minkowski spacetime embeddings for hierarchical structures; Neural Spacetimes (arXiv:2408.13885) — trainable pseudo-Riemannian manifolds for DAGs.

**Causal Reachability Map** ($J^-$): Per-turn computation of which prior turns are still "reachable":

$$\mathcal{R}(t_j, t_i) = \mathbb{1}[\text{in\_context}(t_j)] \cdot R_H(t_j, t_i) \cdot S(t_j, t_i) > \theta_R$$

Combines context window state, human retention (HLR model × circadian factor), and semantic relevance. When $|J^-|$ drops below threshold, `signal.light_cone_collapse` fires proactively — before the agent references forgotten context. Grounded in: DCGM (2026) — "causal structure, not window size, is key" (+8.3 F1); APEX-MEM (2026) — append-only temporal reasoning; SGMem (2026) — n-hop graph traversal as discrete light cone.

#### A/B Test Protocol (Condition V4)

Acting on signals must produce better *human-perceived* outcomes, not just better monitor scores. This is the condition that separates a useful tool from a metric that optimizes itself.

**Test design**:
- **Population**: At least 100 conversations per domain (3 domains minimum), split 50/50 between control (no monitor) and treatment (monitor with events in active mode for events that passed V2 precision gates)
- **Control group**: Agent operates normally, monitor runs in observe mode only (signals logged but not acted on)
- **Treatment group**: Agent receives monitor events and acts on them via reference controllers
- **Primary outcome**: Human-rated conversation quality (1–5 scale, rated by the actual participant, not a separate annotator)
- **Secondary outcomes**: Turns to resolution, token count, user corrections, task completion rate, abandonment rate
- **Key subgroup analysis**: Results must be broken out by conversation mode. If the monitor improves `execute` and `refine` conversations but degrades `explore` conversations, that's a partial success — the mode classifier needs refinement, not the whole product

**Success criteria**:
- Treatment group shows statistically significant improvement ($p < 0.05$) on human-rated quality in at least 2 of 3 domains
- No domain shows statistically significant degradation
- Integration with any supported framework in < 5 minutes and < 10 lines of code change

**If V4 fails**: If the monitor produces better metric scores but the same or worse human ratings, the intervention design is wrong — the signals are accurate but the behaviors they trigger are not helpful. Revise the reference controllers, not the metrics. If specific event types cause degradation (e.g., clarification triggers in explore mode annoy users), disable those events for that mode and re-test.

### Phase 3: Calibration Engine + Domain Generalization Validation

**What**: Automated parameter calibration from conversation logs. Feed the monitor a corpus of historical conversations with outcomes, and it estimates optimal thresholds, weights, and mode-specific profiles for the domain.

#### Calibration Design

The calibration engine takes a labeled conversation corpus and produces a domain-specific configuration:

```python
from horizon import Calibrator

calibrator = Calibrator()
domain_config = calibrator.fit(
    conversations=labeled_corpus,
    outcomes=quality_ratings,
    target_precision={"clarification": 0.8, "contradiction": 0.9},
)

monitor = FidelityMonitor(config=domain_config)
```

**What gets calibrated**:
- All event thresholds ($\tau_{\text{clarify}}$, convergence window, consistency threshold, pace shift, light cone ratio)
- Fidelity weights ($w_1, w_2, w_3, w_4$) and temporal/circadian weights ($\gamma, \delta$) — different domains weight different signals
- Spacetime interval coefficients ($\alpha, \beta, \gamma, \delta$ in $ds^2_{\text{conv}}$) — domain-dependent relative importance of time vs. meaning
- Mode-specific threshold multipliers
- The $\epsilon$ estimate for this domain (the asymptotic IGT floor in the calibration corpus)
- Context half-life $h_c$ per domain (fast-paced coding → shorter half-life; research → longer)

**Calibration method**: Grid search + Bayesian optimization over threshold space, optimizing for maximum Spearman $\rho$ between composite fidelity and human quality ratings, subject to per-event precision constraints from V2.

#### Domain Generalization Validation (Condition V5)

**Test design**:
- Calibrate separately on 5 domains: technical Q&A, creative brainstorming, customer support, coding, educational/tutoring
- For each domain, compare three configurations: (a) universal defaults, (b) domain-calibrated, (c) cross-domain (calibrated on domain X, applied to domain Y)
- Measure fidelity-quality correlation ($\rho$) for each

**Success criteria**:
- Domain-calibrated outperforms universal defaults by > 15% on $\rho$ in at least 4 of 5 domains
- Cross-domain transfer degrades by > 20% (confirming that calibration is necessary, not cosmetic)
- Calibration completes in < 5 minutes for a 1000-conversation corpus
- The $\epsilon$ estimates diverge meaningfully across domains ($\epsilon_{\text{coding}} \neq \epsilon_{\text{emotional support}}$), confirming the THCP prediction that irreducible loss is domain-dependent

**If V5 fails** (calibration barely helps): The metrics themselves may be too coarse to distinguish domain-specific quality patterns. In that case, the product ships with universal defaults and domain calibration is removed from the roadmap. The monitor remains useful as a general-purpose signal, just not a precision instrument.

#### Persistent Dynamics Store (Cross-Session Bridge)

Conversation dynamics metadata persists across sessions to build a per-pair communication profile (informed by essay Appendix C.3). This operationalizes the THCP "persistent ER bridge."

**Architecture**: Append-only dynamics log (following APEX-MEM's append-only, retrieval-time resolution pattern — arXiv:2604.14362) stored locally or in a lightweight property graph (following Kumiho's dual-store model — arXiv:2603.17244).

**Stored per session** (no conversation content — privacy-preserving):

| Data | Structure | Purpose |
|---|---|---|
| Fidelity trajectory ($\mathcal{F}_t$ over turns) | Time series | Learn this pair's typical fidelity curve |
| Estimated $\epsilon$ at convergence | Scalar per domain | Calibrate expectations across sessions |
| Detected conversation mode | Categorical | Predict optimal mode for this pair |
| Event history (which fired, false positives) | Event log | Refine thresholds per pair |
| Contradiction resolution patterns | Graph edges | Learn which topics cause recurring misalignment |

Over many sessions, this builds a communication profile: "in past conversations with this human, $\epsilon \approx 0.2$ in technical domains but $\epsilon \approx 0.45$ in planning discussions."

### Phase 4: Shared Fidelity Dashboard (Experimental)

**What**: A lightweight UI component that shows both the human and the AI the same fidelity trajectory — a shared instrument for navigating the conversation. This is the THCP prediction that both sides of the adjunction must maintain the protocol (informed by essay Appendix C.7).

**Research grounding**: OrchVis (Zhou et al., Georgia Tech, 2025) demonstrates that transparent visualization of goal alignment, progress, and conflict detection significantly improves human oversight of multi-agent systems. Claude Cowork's live artifacts (Anthropic, April 2026) show that shared real-time instruments between human and AI are now productizable. Hafez et al. (2026) explicitly quantify the gap between per-response quality and conversation-level quality — the dashboard addresses this by surfacing trajectory-level signals.

**Design requirements** (from research):

1. **Shared visibility**: Both human and agent see the same fidelity trajectory, not a filtered version. Transparency builds the trust needed for the protocol to work.
2. **Human override**: The human can flag "your fidelity score is wrong" at any point. This override becomes training data for calibrating the AI-side metric.
3. **Signal-driven, not constant**: Following OrchVis's principle, the dashboard surfaces signals only when the conversation's health changes significantly (fidelity threshold crossing, convergence signal, contradiction detected).
4. **Bidirectional feedback**: The dashboard also shows the human how their behavior affects the trajectory — "your last message was very short and the agent's uncertainty increased; a more detailed message would help."

**Validates**: Does giving the human visibility into conversation health improve outcomes beyond what agent-side-only monitoring achieves?

#### Optional Enhancement: Ambient Human Signal Channel (Phase 4b)

For integrations with access to client-side metadata, the monitor can incorporate ambient human cognitive signals (informed by essay Appendix C.1):

| Channel | Signal | What It Measures |
|---|---|---|
| Keystroke timing (CLC) | Inter-key intervals, pause patterns, revision frequency | Cognitive load, composition difficulty, uncertainty |
| Response latency | Time between agent response and human's next message | Deliberation, disengagement, topic difficulty |
| Edit behavior | Deletions, rewrites, abandoned drafts (if accessible) | Uncertainty, intent reformulation |

These signals are non-intrusive (timing metadata only, no content), privacy-preserving, and complementary to text-level metrics. A high-CLC turn with long response latency signals genuine cognitive engagement; a low-CLC turn with instant response signals routine agreement or disengagement. Based on Condrey (arXiv:2603.00177, 2026), Tan et al. (arXiv:2604.06183, 2026), and keystroke-cognition correlations (Scientific Reports, 2026; PsycNet, 2026).

---

## 9. Metrics and Success Criteria

### 9.1 Product Metrics

| Metric | Definition | Target |
|---|---|---|
| Turns to resolution | Average turns for an agent to complete the user's task | 30% reduction vs. baseline |
| Token efficiency | Total tokens generated per resolved conversation | 40% reduction |
| User corrections | Times the user says "no, I meant..." or equivalent | 50% reduction |
| First-response accuracy | Agent's first substantive response addresses the actual intent | 60% → 85%+ |
| Conversation abandonment | User gives up mid-conversation | 25% reduction |

### 9.2 Technical Metrics

| Metric | Target |
|---|---|
| Latency overhead per turn | < 50ms (core), < 200ms (with NLI) |
| Memory overhead | < 100MB for 100-turn conversations |
| Integration time | < 10 LOC change for supported frameworks |
| Event precision (per type) | See V2 gates: 0.70–0.90 depending on event type |
| Event recall (per type) | See V2 gates: 0.60–0.70 depending on event type |
| Fidelity–quality correlation | Spearman $\rho > 0.5$ per-turn, $\rho > 0.6$ conversation-level |
| Improvement over naive heuristics | > 25% on $\rho$ (V3 gate) |

---

## 10. Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation | Validation Gate |
|---|---|---|---|---|
| Proxy metrics don't track theoretical constructs | Medium | High | Per-turn annotation study with 200+ conversations across 3 domains. Swap proxies if correlation < threshold. | V1 |
| Signals too noisy to act on (low precision) | Medium | High | All events default to observe mode. Per-event precision/recall gates must pass before active mode is enabled. Bayesian PPV check at base rates. | V2 |
| Monitor doesn't outperform simple heuristics | Medium | High | Naive heuristic baseline benchmark is a Phase 1 gate. If margin < 15%, ship as heuristic tool instead. | V3 |
| Interventions make conversations worse | Medium | High | Conversation-mode classifier prevents wrong optimization target. A/B test on 300+ conversations with human-rated outcomes must show improvement in 2/3 domains with no degradation. | V4 |
| Thresholds don't generalize across domains | Medium | Medium | Phase 3 calibration engine with cross-domain transfer test. Domain-calibrated must outperform universal by > 15%. | V5 |
| False clarification triggers annoy users | Medium | Medium | Conservative default thresholds. Observe mode first. Precision gate of 0.80 for clarification events. Mode classifier raises threshold in exploratory conversations. | V2 + V4 |
| Overhead too high for real-time use | Low | High | Core pipeline uses only CPU + small embedding model. NLI tier is opt-in. Profile aggressively. | — |
| Developers don't know what to do with signals | Medium | Medium | Ship with reference agent controllers showing recommended behavior patterns for each event and each conversation mode. | — |
| Competitive response from observability platforms | High | Low | The monitor is designed to integrate with them, not replace them. Position as a complementary layer, not a competitor. | — |
| THCP's $\epsilon > 0$ claim proves false (scaling eliminates the gap) | Low | Low (for the product) | The monitor still works as a conversation quality optimizer — it becomes an engineering tool instead of a fundamental-bound tool. Product degrades gracefully. | — |
| AI uncertainty channel unavailable for major providers | High | Medium | Anthropic Claude has no logprobs API as of April 2026. Phase 1b is opt-in, not core. Core pipeline works without logprobs. Market the enhancement for open-source and OpenAI deployments; lobby Anthropic for logprobs access. | — |
| Ambient human signals require client-side integration | High | Medium | Keystroke timing and response latency require browser/IDE-level instrumentation, not server-side access. Phase 4b depends on platform partnerships (IDE plugins, chat UI SDKs) or is limited to first-party applications. Core pipeline works without client signals. | — |
| Circadian model assumes single chronotype | Medium | Low | The $\kappa(t)$ curve is an average across populations (Valdez et al. 2012). Individual chronotypes (morning larks, night owls) can shift peaks by 2–4 hours. Mitigation: configurable `chronotype_offset` in `configure()`, or learn from per-user fidelity correlation over sessions. | — |
| IP geolocation unreliable (VPN, proxy) | Medium | Low | MaxMind GeoIP2 provides `accuracy_radius`; when radius > threshold, location is classified as `unknown`. Core spatial grounding falls back to `timezone` + `device_type`. Location is never required. | — |
| Deictic resolution fails for ambiguous references | Medium | Medium | "Next week" is unambiguous, but "later" or "soon" cannot be resolved to absolute time. Unresolvable expressions return $\bot$ and trigger a soft clarification suggestion rather than a hard error. The system degrades gracefully. | — |
| Spacetime interval coefficients uncalibrated | High | Medium | The $\alpha, \beta, \gamma, \delta$ coefficients in $ds^2_{\text{conv}}$ are initially set to 1.0 and calibrated empirically via V4 A/B testing. Pre-calibration, `interval_class` is experimental. Ships in observe mode until coefficients stabilize. | V4 |
| Conversation velocity noise from short messages | Medium | Low | Very short messages ("ok", "yes") produce near-zero semantic displacement, yielding unreliable velocity. Mitigation: velocity is computed on a 3-turn rolling window and gated by minimum message length. | — |
| First-turn cold start exceeds 3 min on slow networks | Medium | Medium | Default model (~80MB) downloads on first `process_turn`. On slow/metered connections, cold start may exceed the 3-minute TTFV target. Mitigation: `model_path` config for pre-downloaded models; `[bundled]` extra for offline installs; HuggingFace caching prevents re-download. | — |
| MCP server adds operational complexity | Low | Low | `horizon serve` requires a separate process vs. in-process library. Mitigation: Docker compose for simple deployment; clear docs distinguishing library vs. MCP usage; MCP is opt-in for IDE/desktop use only. | — |

---

## 11. Open Questions

### Resolved by Validation Framework

The following questions, previously open, are now addressed by the validation gates (V1–V5):

| Question | Resolution |
|---|---|
| Do the metrics actually work? | V1 validation protocol with per-turn annotations |
| Are the thresholds right? | V2 precision/recall gates + V5 domain calibration |
| Will acting on signals help? | V4 A/B test protocol with human-rated outcomes |
| Is the framework worth its complexity? | V3 naive heuristic baseline benchmark |

### Remaining Open Questions

1. **Embedding model selection**: Which sentence-transformer balances speed, quality, and multilingual support for the default configuration? Candidates: `all-MiniLM-L6-v2` (fastest), `all-mpnet-base-v2` (best quality), `multilingual-e5-base` (multilingual). Decision should be informed by V1 results — which model produces the highest $\rho$ on the validation corpus.
2. **Annotation workforce**: Who performs the per-turn annotations for the V1 validation dataset? Options: internal team, contracted annotators (e.g., Scale AI, Surge), or a hybrid where domain experts annotate a seed set and LLM-as-judge scales it (with human audit of LLM annotations).
3. **Multimodal extension**: The THCP framework predicts that each modality provides an independent "quantum tail" channel ($\epsilon_{\text{total}} = \prod_m \epsilon_m$). Phase 1 is text-only. Multimodal support should be scoped after Phase 2 validates the text-only pipeline.
4. **Pricing model** (if commercialized): Per-conversation, per-turn, or per-seat? The local-first design suggests open-source core with a hosted calibration service as the monetization path.
5. **Reference controller design**: Should reference controllers be opinionated (prescribing specific prompt injections for each event) or structural (providing hooks and letting developers write the intervention logic)? The A/B test in V4 will inform this — if opinionated controllers work well, ship them as defaults.

---

## 12. Appendix: Theoretical Grounding

This PRD operationalizes concepts from the THCP framework. The full mathematical formalization, academic sources (173 references across 5 appendices), and falsifiability criteria are in the companion essay:

**[TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md](./TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md)**

Key mappings from theory to product:

| THCP Theory | PRD Component |
|---|---|
| Law 1 (Irreducible Loss, $\epsilon > 0$) | The monitor exists because perfect communication is impossible — there is always something to measure and optimize |
| Law 3 (Fidelity Dynamics) | Composite fidelity score $\mathcal{F}_t$ |
| Law 4 (Optimal Conversation Length, $T^*$) | `signal.convergence` and `signal.optimal_length` events |
| Law 5 (Gluing Coherence) | Conversation Coherence 3-tier: Bipredictability + TGN + constraint propagation |
| Conjecture THCP-2 (Golden Length) | Convergence detection via IGT trend analysis |
| Conjecture THCP-3 (Adjunction Structure) | $D_{JS}$ as proxy for structural alignment between intent and response spaces |
| Neo-Game Theory ($D_{JS}$ thresholds) | `checkpoint.clarification` trigger at $\tau_1$, agent authority adjustment at $\tau_2$ |
| Appendix B.3 (Parameter Calibration) | Phase 3: Calibration Engine |
| Appendix B.4 (Worked Example) | The notification system scenario from the pre-PRD discussion |
| Appendix C.1 (Ambient Cognitive Signals) | Phase 4b: Human Signal Channel (CLC, latency, edits) |
| Appendix C.2 (AI Uncertainty) | Phase 1b: LogitScope / logprobs integration |
| Appendix C.3 (Persistent Bridge) | Phase 3: Persistent Dynamics Store |
| Appendix C.4 (Global Coherence) | Tier 2/3 of Conversation Coherence engine (§5.1.4) |
| Appendix C.5 (Irreversible vs. Recoverable Loss) | Amended fidelity dynamics, `signal.session_reset` event |
| Appendix C.6 (Running $\epsilon_t$) | Phase 2: Horizon Width Tracker, `signal.horizon_widening` event |
| Appendix C.7 (Shared Fidelity) | Phase 4: Dashboard design requirements |
| Appendix D (Temporal-Spatial Grounding) | Phase 2: Temporal Context Layer, temporal events, fidelity dynamics $\gamma \cdot \Delta\tau$ term |
| IPM No-Go Theorem (Tkemaladze 2026) | Structural justification for external observer architecture; Appendix E §E.1 |
| SACD (arXiv:2603.01239) | Empirical proof that all frontier models drift in multi-turn; Appendix E §E.2 |
| Representational Incompleteness (Spivack, Lean 4) | Topological proof that self-models have an unreachable diagonal ($\epsilon > 0$); Appendix E §E.1 |
| Bounded Self-Certification (arXiv:2603.06012) | The +1 overhead: current-turn dynamics cannot be assessed by the system generating the turn; Appendix E §E.3 |
| Infinite Choice Barrier (Schiller 2026) | Semantic Closure + No Frame Innovation corollaries ground the ontological gap; Appendix E §E.3 |
| Appendix E.1 (Circadian Cognitive Load) | Circadian factor $\kappa(t)$ in fidelity dynamics; variable human clock rate modifies retention and fidelity |
| Appendix E.2 (Deictic Temporal Resolution) | Temporal expression extraction and grounding $\mathcal{D}(c, t_{\text{ref}})$; `temporal_references` in API return |
| Appendix E.3 (Spatial Grounding) | Spatial constraint vector $\Phi(\sigma)$; `location_class`; IP geolocation; local machine time injection |
| Appendix E.4 (Conversation Velocity) | Velocity $v_t$, acceleration $a_t$; `signal.pace_shift` event; engagement/disengagement prediction |
| Appendix E.5 (Spacetime Interval) | Conversation spacetime interval $ds^2_{\text{conv}}$ with Minkowski signature; timelike/spacelike/lightlike classification; Conjecture THCP-5 |
| Appendix E.6 (Causal Reachability) | Light cone $J^-(t_i)$; `signal.light_cone_collapse` event; proactive broken-reference prevention |

---

## Appendix B: Validation Conditions Summary

Five conditions must be met for this product to be both scientifically sound and commercially viable. All five are engineering validation problems, not research problems. None require additional academic work.

| ID | Condition | Phase | Test | Kill Criterion |
|---|---|---|---|---|
| V1 | Proxy metrics track theoretical constructs | 1 | Per-turn annotation study, $\rho > 0.5$ per-turn | If no proxy achieves $\rho > 0.3$ after substitution attempts, the embedding approach is abandoned |
| V2 | Signals are clean enough to act on | 1 | Per-event precision/recall against annotated data (14 event types) | Events below precision floor remain in observe mode indefinitely |
| V3 | Monitor outperforms naive heuristics | 1 | Comparative benchmark, > 25% $\rho$ improvement | If < 15% improvement, ship as heuristic tool; deprioritize THCP framing |
| V4 | Acting on signals improves outcomes | 2 | A/B test with human-rated outcomes across 3 domains | If no domain improves, revise controllers; if degradation in any domain, revise mode classifier |
| V5 | Thresholds generalize via calibration | 3 | Cross-domain calibration test, > 15% improvement over defaults | If calibration barely helps, ship with universal defaults |

These conditions are ordered by dependency: V1 enables V2 (you need accurate metrics to measure signal quality), V2 enables V4 (you need clean signals before acting on them), and V3 is an independent gate that can run in parallel with V1/V2.

---

## Appendix C: Research Sources for Implementation Gaps

The following research informs the gap-closing enhancements added in this PRD revision. Full analysis and THCP integration details are in the companion essay's Appendix C.

| Gap | Research Source | Year | Key Finding | PRD Impact |
|---|---|---|---|---|
| Human cognitive signals | Condrey, arXiv:2603.00177 (CLC); Tan et al., arXiv:2604.06183 (latency); Scientific Reports 2026 (typing-cognition) | 2025–2026 | Keystroke timing captures cognitive load at 85–95% accuracy; response latency shapes perception, not behavior | Phase 4b: Ambient Human Signal Channel |
| AI uncertainty | LogitScope (IBM, ICLR 2026); OpenAI logprobs API; vLLM prompt_logprobs | 2025–2026 | Token entropy/varentropy/surprisal provide real-time uncertainty without extra model calls | Phase 1b: AI Uncertainty Channel |
| Persistent memory | Kumiho (arXiv:2603.17244); APEX-MEM (arXiv:2604.14362); SGMem (ICLR 2026 review) | 2026 | Graph-native memory with AGM belief revision + append-only, retrieval-time resolution | Phase 3: Persistent Dynamics Store |
| Global coherence | TGN for dialogue (arXiv:2601.03051); Eirew et al. (EMNLP 2025); Bipredictability (Hafez 2026) | 2025–2026 | Temporal graph + constraint optimization catches global inconsistencies; bipredictability is 10ms, 100% sensitivity in test | §5.1.4: Three-Tier Coherence Architecture |
| Irreversible loss | Laban et al. (arXiv:2505.06120, MSR/Salesforce); IGT/TWR empirical (ICLR 2026 review) | 2025–2026 | 39% degradation from turn boundaries alone; effective context is 30–60% of advertised | Amended fidelity dynamics; `signal.session_reset` |
| Running $\epsilon_t$ | DMF for topic shift (COLING 2025); hidden repr. difficulty (EMNLP 2025); ODD (arXiv:2602.08088) | 2025–2026 | Dual-process topic shift detection + difficulty estimation from hidden representations at ~0.2ms overhead | Phase 2: Horizon Width Tracker; `signal.horizon_widening` |
| Shared instruments | OrchVis (Georgia Tech, 2025); Claude Cowork live artifacts (Anthropic, 2026); Bipredictability trajectory | 2025–2026 | Transparent shared visualization improves oversight; live dashboards are now productizable | Phase 4: Dashboard design requirements |
| Temporal blindness | TicToc (arXiv:2510.23853); Ebbinghaus/HLR (ACL 2016); Lamport (1978); Mark (2023); Leroy (2009) | 1978–2026 | LLMs achieve < 65% alignment with human temporal perception; memory decays exponentially; 23min recovery after interruption; distributed clocks require explicit synchronization | Phase 2: Temporal Context Layer; `signal.temporal_desync`, `signal.broken_reference`, `signal.frame_shift`; fidelity $\gamma \cdot \Delta\tau$ |
| Temporal memory retrieval | Chronos (arXiv:2603.16862); Memory-T1 (2026); SLM-V3 (arXiv:2603.14588) | 2026 | Temporal-aware event retrieval achieves 95.6% accuracy; RL-based temporal reasoning with chronological fidelity rewards; information-geometric temporal weighting | Phase 2: Conversation geodesics; Phase 3: Temporal-aware Persistent Dynamics Store |
| Task resumption | TaCoS (ICSE 2026); Collaboration Gap (arXiv:2604.18096); TDS protocol (2026); Shaer et al. (Wellesley 2024) | 2024–2026 | LLM summaries reduce resumption lag; grounding breaks down under temporal asymmetry; asynchronous collaboration requires explicit re-synchronization | Phase 2: Temporal desync event; essay Appendix D |
| Circadian cognitive load | Valdez et al. (2012); Schmidt et al. (2007); Correa et al. (2023); Gaggioni et al. (2025); de Cordova et al. (2010) | 2007–2025 | Performance peaks 10–14h & 16–22h; 9–34% RT variation; 45–83% synchrony effects; night shift increases errors | Phase 2: Circadian factor $\kappa$; fidelity dynamics $\delta \cdot (1 - \kappa)$; essay Appendix E.1 |
| Deictic temporal resolution | HeidelTime (SemEval 2010); SUTime (Stanford); dateparser v1.4.0; datefinder v1.0.0 | 2010–2026 | TIMEX3 standard for temporal expression normalization; 200+ locale support; 766× speedup with typed extraction | Phase 2: Temporal reference extraction in `process_turn`; essay Appendix E.2 |
| Spatial grounding / device | MaxMind GeoIP2 v5.2.0; NN/G content dispersion (2024); NN/G scaling UI (2015); tzlocal v5.3.1 | 2015–2026 | Mobile 2× cognitive difficulty; 72s avg session; IP → city/tz/accuracy_radius; local timezone from system config | Phase 2: Spatial constraint vector $\Phi$; `location_class`; essay Appendix E.3 |
| Conversation pace dynamics | Onishi et al. (SIGDIAL 2025); arXiv:2604.06183 latency study; PMIScore (2026); RESPOND (2026) | 2025–2026 | Turn-taking speed gamma-distributed by role/relationship; 9s optimal perceived usefulness; PMI-based engagement; controllable pace dials | Phase 2: Velocity $v_t$, acceleration $a_t$, `signal.pace_shift`; essay Appendix E.4 |
| Minkowski spacetime for meaning | arXiv:2505.08795 "Geometry of Meaning" (2025); Neural Spacetimes (arXiv:2408.13885); RiemannGL (2026); Light Cones for Vision (2026) | 2021–2026 | Perfect embedding of hierarchical structures in 3D Minkowski spacetime; causal structure governs retrieval; pseudo-Riemannian manifolds for DAGs | Phase 2: Spacetime interval $ds^2_{\text{conv}}$; interval classification; essay Appendix E.5 |
| Causal structure / light cone | DCGM (2026); APEX-MEM (2026); SGMem (2026); LiCoMemory (2025); cFIM (arXiv:2512.21451) | 2025–2026 | Causal graphs +8.3 F1 over KV-compression; append-only temporal reasoning; n-hop graph traversal; hierarchy-temporal retrieval; tractable information geometry | Phase 2: Reachability map $J^-$, `signal.light_cone_collapse`; essay Appendix E.6 |

---

## Appendix D: Post-Deployment Proof System

The validation gates (V1–V5) prove the monitor works *before* shipping. The proof system below proves it works *in the wild* — continuously, across real users, at scale. This is the empirical feedback loop that turns a validated prototype into a proven product.

### D.1 Continuous Proof Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  PRODUCTION TRAFFIC                       │
│                                                           │
│  ┌─────────────────┐    ┌─────────────────────────────┐  │
│  │  Horizon Monitor │───►│  Telemetry Collector         │  │
│  │  (live, per-turn)│    │  (anonymized dynamics only)  │  │
│  └─────────────────┘    └────────────┬────────────────┘  │
│                                      │                    │
│                                      ▼                    │
│  ┌───────────────────────────────────────────────────┐   │
│  │              PROOF ENGINE                          │   │
│  │                                                    │   │
│  │  ┌────────────┐  ┌─────────────┐  ┌────────────┐ │   │
│  │  │ Prediction │  │  Outcome    │  │ Continuous  │ │   │
│  │  │ Registry   │  │  Tracker    │  │ Calibration│ │   │
│  │  └─────┬──────┘  └──────┬──────┘  └─────┬──────┘ │   │
│  │        │                │                │        │   │
│  │        ▼                ▼                ▼        │   │
│  │  ┌────────────────────────────────────────────┐   │   │
│  │  │         PROOF LEDGER                        │   │   │
│  │  │  prediction → outcome → confirmed/refuted   │   │   │
│  │  └────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────┘   │
│                                                           │
│  Output: Weekly proof report + drift alerts               │
└──────────────────────────────────────────────────────────┘
```

### D.2 What Gets Proven (Prediction Registry)

Every theoretical claim from the THCP framework that the monitor operationalizes becomes a registered prediction. Each prediction has a measurable test and a threshold for confirmation or refutation.

| ID | THCP Prediction | Observable Test | Confirmed When | Refuted When |
|---|---|---|---|---|
| P1 | $\epsilon > 0$ — irreducible loss exists in every domain | No domain achieves $\mathcal{F}_t = 1.0$ at convergence, even in perfect conditions | $\epsilon_{\text{min}} > 0.05$ across all calibrated domains after 1000+ conversations | Any domain consistently reaches $\epsilon < 0.02$ |
| P2 | $T^*$ exists — conversations have optimal length | Conversations stopped at `signal.convergence` score higher on human ratings than those that continue past it | Convergence-stopped conversations score $\geq$ continued conversations in > 65% of paired comparisons | No statistical difference ($p > 0.2$) between stopped and continued |
| P3 | $D_{JS}$ predicts clarification need | Turns where $D_{JS} > \tau_{\text{clarify}}$ are followed by user corrections more often than turns where $D_{JS} < \tau$ | Relative risk of user correction > 2.0x when $D_{JS}$ exceeds threshold | Relative risk < 1.2x (no meaningful predictive power) |
| P4 | Fidelity trajectory predicts conversation outcome | Conversations with declining $\mathcal{F}_t$ trajectory are rated lower by humans than those with stable/rising trajectory | Spearman $\rho > 0.4$ between trajectory slope and human rating, sustained over 3+ months | $\rho < 0.2$ after 3 months of data |
| P5 | Irreversible loss requires session reset, not re-anchoring | Conversations where `signal.session_reset` fires and is acted on recover quality; those where re-anchoring is attempted instead do not | Session-reset conversations recover to $\mathcal{F}_t > 0.6$ within 3 turns of new session; re-anchor attempts show $\mathcal{F}_t < 0.5$ | Both strategies produce equivalent outcomes |
| P6 | $\epsilon_t$ varies by domain within a conversation | When the monitor detects `signal.horizon_widening`, subsequent turns show higher $D_{JS}$ and lower IGT than the pre-shift baseline | $D_{JS}$ increases by > 20% and IGT decreases by > 15% in the 3 turns following a confirmed topic shift | No measurable change in metrics after detected topic shifts |
| P7 | Persistent dynamics improve over sessions | Per-pair calibrated thresholds (from the Persistent Dynamics Store) outperform universal defaults for returning users | Calibrated thresholds produce > 10% better fidelity-quality $\rho$ for users with 5+ prior sessions | No improvement over universal defaults after 10+ sessions |
| P8 | Temporal gaps degrade fidelity predictably | Conversations resumed after $\Delta t > 1$ hour show lower $\mathcal{F}_t$ on the first post-gap turn, proportional to $\Delta t$ | Spearman $\rho > 0.4$ between gap duration and first-post-gap $\mathcal{F}_t$ drop across 200+ conversations with gaps | No correlation between gap duration and fidelity drop ($\rho < 0.15$) |
| P9 | Re-anchoring after temporal desync improves outcomes | When `signal.temporal_desync` fires and the agent re-anchors (summarizes + checks intent), subsequent turns show higher $\mathcal{F}_t$ than when the agent continues without re-anchoring | Re-anchored conversations recover to $\mathcal{F}_t > 0.6$ within 2 turns; non-re-anchored show $\mathcal{F}_t < 0.45$ for 3+ turns | Both strategies produce equivalent outcomes |
| P10 | Circadian factor predicts turn quality | Turns occurring during circadian nadirs ($\kappa < 0.5$) show lower human-rated quality and higher user correction rates than peak-hour turns | Correction rate > 1.5× during off-peak vs. peak hours, sustained across 500+ conversations | No correlation between time-of-day and turn quality |
| P11 | Spacetime interval classifies intervention needs | Timelike intervals ($ds^2 < 0$) predict re-anchoring success; spacelike intervals ($ds^2 > 0$) predict clarification success | Correct intervention type (re-anchor vs. clarify) predicted by $ds^2$ sign in > 65% of cases | No predictive power ($\approx$ 50% random) |
| P12 | Light cone collapse predicts broken references | `signal.light_cone_collapse` fires before the agent references unreachable context in > 70% of cases where `signal.broken_reference` would later fire | Proactive detection rate > 70%; false positive rate < 30% | No improvement over reactive `signal.broken_reference` alone |
| P13 | Conversation velocity predicts engagement | High velocity ($v_t > \bar{v}$) with low $D_{JS}$ correlates with higher human satisfaction; deceleration ($a_t < 0$) preceded by high $D_{JS}$ correlates with abandonment | Spearman $\rho > 0.3$ between velocity profile and satisfaction; deceleration + high $D_{JS}$ precedes > 60% of abandonments | No correlation between pace dynamics and outcomes |

### D.3 Outcome Tracking

Outcomes are collected through three channels, ordered by signal strength:

1. **Implicit signals** (automatic, every conversation):
   - Conversation length vs. `signal.convergence` timing
   - User corrections ("no, I meant...") frequency
   - Abandonment rate (user stops responding)
   - Turn-over-turn $\mathcal{F}_t$ trajectory shape (rising, flat, declining, cliff)

2. **Lightweight explicit signals** (opt-in, low friction):
   - End-of-conversation thumbs up/down (binary)
   - "Was this helpful?" single-click rating
   - Event feedback: when a `checkpoint.clarification` fires, did the user engage with the clarification or ignore it?

3. **Deep signals** (periodic, sampled):
   - Human annotation of sampled conversations (same protocol as V1, applied to production traffic)
   - A/B holdback: 5% of traffic runs with monitor in permanent observe mode as a control group
   - Longitudinal tracking: same user-agent pairs over weeks, measuring whether fidelity improves with the Persistent Dynamics Store

### D.4 Continuous Calibration Loop

The proof system doesn't just validate — it feeds back into the monitor:

| Signal | Feeds Into | Mechanism |
|---|---|---|
| Prediction confirmations/refutations | Prediction Registry | Update confidence levels; retire predictions that are conclusively proven/disproven |
| Outcome-metric correlations | Fidelity weights ($w_1$–$w_4$) | Bayesian update of weights based on which metrics best predict outcomes in production |
| Event feedback (acted on / ignored) | Event thresholds | Tighten thresholds for events users ignore (false positive signal); loosen for events users consistently act on |
| Cross-session dynamics | Persistent Dynamics Store | Per-pair profiles continuously updated with new session data |
| Domain-specific $\epsilon$ estimates | Calibration Engine | Running $\epsilon$ estimates refined as more conversations accumulate per domain |

### D.5 Proof Reporting

**Weekly proof report** (automated):
- Prediction scorecard: each prediction's current confirmation status (confirmed / trending toward / inconclusive / trending against / refuted)
- Metric health: correlation between each metric and implicit outcomes, compared to V1 baseline
- Event precision in production: actual precision/recall of each event type against implicit outcome signals, compared to V2 gates
- A/B holdback results: treatment vs. control on implicit metrics
- Calibration drift: whether domain-specific thresholds are shifting and in which direction

**Monthly deep review** (human + automated):
- Sampled conversation annotation (50–100 conversations) with full V1-style per-turn ratings
- Longitudinal analysis: are returning users' conversations improving?
- Prediction registry update: promote/demote predictions based on accumulated evidence
- Comparison to naive heuristics (V3 re-run on production data)

**Quarterly thesis review**:
- Has $\epsilon > 0$ been confirmed across all deployed domains?
- Has the monitor produced measurable improvements in human-perceived quality at the population level?
- Are there domains or conversation types where the framework consistently fails? (Candidates for removal from product scope or for theoretical revision)
- Full re-assessment of the THCP framework's predictive power in production vs. the essay's theoretical claims

### D.6 Kill and Pivot Criteria

The proof system also defines when to stop believing:

| Condition | Evidence Required | Action |
|---|---|---|
| Framework is proven | P1–P4 confirmed; P8–P13 (4D layer) trending positive; V4-equivalent A/B improvement sustained for 3+ months in production | Full confidence. Scale. Publish empirical results. |
| Framework is partially proven | P1, P4 confirmed; P2, P3 mixed; P5–P13 inconclusive | Ship confirmed components. Demote unproven claims to "experimental." Revise essay. |
| Framework is disproven | P1 refuted (some domain reaches $\epsilon \approx 0$) or P4 refuted (fidelity trajectory doesn't predict quality) | The theoretical foundation is wrong. Pivot the product to a purely empirical conversation-quality tool with no THCP framing. The engineering remains useful; the theory is retired. |

---

## Appendix E: The Ontological Gap — Why External Observation Is Structurally Required

This appendix presents the theoretical and empirical case that the problem Horizon solves cannot be absorbed by model scaling, training-time alignment, or internal self-monitoring. The gap Horizon instruments is not an engineering limitation — it is a structural property of self-referential systems that three independent research traditions have now converged on.

### E.1 The Convergence: Three No-Go Results

Three independent lines of research, published between April 2025 and March 2026, reach the same conclusion from different starting points:

**Result 1 — Computability theory (Sigtermans, April 2025)**

"No total, self-referential complexity function $K_S(x)$ can exist. Any such construction collapses under the weight of circular minimality constraints. Thus, a consistent framework for evaluating complexity must avoid internal self-reference." (Entropy, Computability, and the Observer, Preprints.org 202504.1826)

The paper introduces an external observer $O$ who tracks the time-dependent Kolmogorov Complexity $K_t(P(x))$ — the evolving compressibility of a program's behavior over time — without simulating the program's internal logic. The observer classifies halting behavior (stabilizing, diverging, or undecided) from the trajectory alone. The framework is proven paradox-free and consistent with classical results.

*Mapping to Horizon*: Horizon is observer $O$. It tracks the evolving fidelity $\mathcal{F}_t$ of a conversation over time, without simulating the LLM's internal reasoning. It classifies conversation health (healthy, drifting, critical, converged) from the trajectory alone.

**Result 2 — Self-referential computation (Tkemaladze, March 2026)**

"Any Introspective Predictive Machine's introspective subroutine must fail in one of three specific ways: it may be *incorrect*, *non-halting*, or *its execution must perturb the very state it aims to measure*." (A No-Go Theorem for Introspective Prediction in Computational Machines, Longevity Horizon 2(4), DOI: 10.65649/teb2vw21)

Proven via Kleene's Recursion Theorem. The result is not about resource limits — it holds for arbitrarily powerful machines. A system that predicts while simultaneously assessing its own predictive performance faces a trilemma with no exit.

*Mapping to Horizon*: An LLM that tries to monitor its own conversation dynamics during generation is an IPM. It must either (a) get the self-assessment wrong (incorrect introspection), (b) enter an infinite loop of self-evaluation (non-halting), or (c) change its response by the act of self-monitoring (perturbation). Horizon avoids all three by measuring *after* the response is generated, from outside the system.

**Result 3 — Representational incompleteness (Spivack, 2025–2026)**

"Every parametric self-model has a diagonal it cannot represent. Not because it lacks resources. Not because it lacks expressive power. Because the topology of self-representation makes it impossible." (Representational Incompleteness, machine-checked in Lean 4)

Given any parametric self-model $s: A \rightarrow A \rightarrow B$ and any fixed-point-free function $f: B \rightarrow B$, the diagonal function $\lambda a. f(s(a)(a))$ is never a row of $s$. No assumption about computability, cardinality, or arithmetic is required — just types. This generalizes Gödel, Turing, and Cantor into a single topological obstruction.

*Mapping to Horizon*: The LLM's self-model of its conversation behavior has a diagonal it cannot represent — the gap between what it *thinks* the conversation trajectory looks like and what the trajectory *actually* looks like from outside. This gap is the irreducible $\epsilon$ in THCP Law 1. Increasing model size shifts the diagonal; it does not eliminate it.

### E.2 The Empirical Confirmation: Models Cannot Self-Monitor in Multi-Turn

The no-go results are theoretical. The following 2025–2026 empirical work confirms their predictions:

**Self-Anchoring Calibration Drift (SACD)** — Harshavardhan et al., arXiv:2603.01239 (March 2026). Tested Claude Sonnet 4.6, GPT-5.2, and Gemini 3.1 Pro across 150 questions in multi-turn self-anchoring conditions. Key findings:

- Claude exhibits significant *decreasing* confidence under self-anchoring (CDS = −0.032, $p = .029$, $d = −0.627$) with massive calibration error drift ($\eta^2 = .791$)
- GPT-5.2 exhibits the *opposite*: confidence *escalation* in open-ended domains (CDS = +0.026) with significant ECE escalation by Turn 5
- Gemini 3.1 Pro *suppresses natural calibration improvement*: without self-anchoring, its calibration error drops to near zero; with it, ECE holds flat at $\approx .333$

Each model drifts differently — but all drift. The specific form of SACD is model-heterogeneous and unpredictable from outside. An external monitor is the only way to detect which form of drift is occurring in a specific conversation.

**Multi-turn degradation is structural** — MSR/Salesforce (2025), confirmed across 15 frontier models, 200,000+ simulated conversations:

- 39% average performance drop from single-turn to multi-turn
- Degradation starts in as few as 2 turns
- Same content presented as single prompt: 95.1% performance; split across turns: $\approx$ 65%
- "Once an LLM takes a wrong turn, it does not self-correct — the error compounds"

**Self-correction is partial at best** — Gnosis (arXiv:2512.20578) detects individual failures from internal states with only ~5M additional parameters. Reflexion (ICLR 2026) teaches generate-critique-refine loops. MIT's RLCR (April 2026) reduces calibration error by 90%. These are genuine advances — but they operate on individual turns or factual claims, not on conversation trajectory. None detects gradual semantic drift, recoverable vs. irreversible loss, or convergence across a multi-turn session.

**Introspective awareness is mechanistically limited** — Anthropic Fellows Program (arXiv:2603.21396, April 2026) showed that LLMs can detect injected activation perturbations via a two-stage internal circuit. However, the capability (a) is absent in base models, (b) emerges only from specific post-training methods (DPO, not SFT), (c) is "substantially underelicited by default," and (d) operates on static concept detection, not dynamic conversation trajectory perception. It is a proof that partial introspection exists — and simultaneously a proof that it is far from the conversation-dynamics-level awareness Horizon provides.

### E.3 What Scaling Cannot Solve

A common objection: "Won't next-generation models just solve this?" The evidence says no, for three specific reasons:

**1. Turn-boundary degradation is not a context-length problem.**

The MSR/Salesforce "Concat" finding is definitive: identical content achieves 95.1% as a single prompt but $\approx$ 65% split across turns. Doubling the context window doesn't help because the degradation comes from *how* transformers process sequential turns — positional encoding bias (RoPE), attention dilution under softmax normalization, and premature assumption formation — not from running out of tokens. Effective context is 30–60% of the advertised window (Chroma 2025, 18 frontier models). Claude's 1M tokens, Gemini's 1M tokens — the number is irrelevant. The architecture is the constraint.

**2. Self-monitoring is bounded by the +1 overhead.**

arXiv:2603.06012 (March 2026) proves that bounded self-certification requires strictly more computational steps than the computation being certified: "A with time bound $T$ cannot decide the halting behavior of A at time $T$. At best, it can certify up to time $T-1$, but the $T$-th step remains opaque." For an LLM, this means: the current turn's dynamics cannot be fully assessed by the system generating the current turn. The assessment is always one step behind. An external monitor operates outside this +1 bound because it assesses *after* the turn is complete.

**3. The ontological gap is structural, not parametric.**

The Infinite Choice Barrier Theorem (Schiller, philarchive.org/archive/SCHAII-17v8) proves: "For any algorithmic system with finite symbols and rules, there exist problems where the system will either return a suboptimal answer or compute forever." This is reinforced by three corollaries: Semantic Closure (a system can only operate within its own symbol set), No Frame Innovation (a system cannot generate new representational frames from within its own logic), and Statistical Breakdown (inference collapses under heavy-tailed distributions). The human's intent exists in a representational frame the LLM cannot natively access — it can only approximate it through the shared communication channel. That approximation gap is $\epsilon$.

### E.4 What Horizon Solves That Nothing Else Can

| Capability | Models Alone | Self-Correction (Gnosis, Reflexion) | Eval Tools (DeepEval, RAGAS) | Observability (LangSmith, Arize) | **Horizon** |
|---|---|---|---|---|---|
| Detect single-turn factual error | Yes (improving) | Yes | Yes (post-hoc) | No | Not the goal |
| Detect gradual multi-turn drift | No (invisible from inside) | No (operates per-turn) | No (post-hoc only) | No (traces, not dynamics) | **Yes (trajectory-based)** |
| Distinguish recoverable drift from irreversible loss | No | No | No | No | **Yes ($\lambda_r$ vs $\lambda_i$)** |
| Detect conversation convergence ($T^*$) | No | No | No | No | **Yes (IGT trend → signal.convergence)** |
| Measure intent-response gap in real time | No (only has its own interpretation) | No | Partial (reference-based) | No | **Yes ($D_{JS}$ per turn)** |
| Signal without perturbing the system | N/A — it *is* the system | No (Tkemaladze trilemma) | N/A — post-hoc | Yes (passive) | **Yes (passive sidecar)** |
| Provide conversation-level health trajectory | No | No | Partial (final score) | Partial (latency/error traces) | **Yes (per-turn $\mathcal{F}_t$ series)** |
| Detect model-heterogeneous calibration drift (SACD) | No — each model drifts differently and doesn't know it | Partial (calibration only) | No | No | **Yes (model-agnostic external measurement)** |
| Account for human circadian state | No | No | No | No | **Yes ($\kappa(t)$ modifies fidelity)** |
| Resolve deictic temporal references | Limited (some models) | No | No | No | **Yes ($\mathcal{D}$ extraction + grounding)** |
| Measure conversation pace dynamics | No | No | No | Partial (latency traces) | **Yes ($v_t$, $a_t$, `signal.pace_shift`)** |
| Compute causal reachability (light cone) | No | No | No | No | **Yes ($J^-$ + `signal.light_cone_collapse`)** |
| Provide unified spacetime metric | No | No | No | No | **Yes ($ds^2_{\text{conv}}$ with Minkowski signature)** |

### E.5 The Physics Parallel Is Not Decorative

The mapping between the observer problem in physics and the observer problem in conversation dynamics is not an analogy borrowed for marketing. It is the same mathematical structure appearing in a different domain:

| General Relativity | Computability Theory | Horizon Product |
|---|---|---|
| An observer inside the event horizon cannot see the horizon | A system cannot compute its own Kolmogorov complexity (Sigtermans 2025) | The LLM cannot measure its own conversation dynamics |
| Information escapes as Hawking radiation — partial, degraded, but real | Internal states carry partial correctness signals — Gnosis proves this with ~5M parameters | Logprobs, attention patterns, and SACD carry partial quality signals |
| An external observer sees the full trajectory from outside | An external observer tracks $K_t(P(x))$ over time (Sigtermans) | Horizon tracks $\mathcal{F}_t$ over time from outside the LLM |
| The observer doesn't need to understand the black hole's interior physics | The observer doesn't simulate the program's logic (proven paradox-free) | Horizon doesn't need access to model weights or internal representations |
| $\epsilon > 0$: information is irreversibly lost at the horizon | Representational incompleteness: every self-model has an unreachable diagonal (Spivack, Lean 4) | THCP Law 1: irreducible ontological loss $\epsilon > 0$ in every domain |
| The event horizon is not a bug — it is a feature of the geometry | The no-go theorems are not engineering limits — they are structural | The ontological gap is not a problem to solve — it is a condition to instrument |

This convergence — three independent traditions (physics, computability theory, type theory) arriving at the same architectural conclusion — is what grounds Horizon's structural defensibility. A product built on an engineering gap can be killed by better engineering. A product built on a mathematical impossibility persists as long as the impossibility holds.

### E.6 When Horizon Becomes Unnecessary

Intellectual honesty requires defining the conditions under which the framework is disproven:

1. **A model achieves $\epsilon \approx 0$ in production**: Some domain consistently reaches $\mathcal{F}_t = 1.0$ at convergence. This would refute THCP Law 1 and invalidate the ontological gap claim. (Tracked by P1 in Appendix D.)

2. **A model self-monitors its own conversation trajectory**: A system correctly identifies its own drift, convergence, irreversible loss, circadian effects, and causal reachability in real time, without external measurement, across 3+ domains with Spearman $\rho > 0.5$ against human quality ratings. This would refute the no-go theorems' practical applicability to LLMs.

3. **Turn-boundary degradation disappears with scaling**: A future architecture achieves < 5% performance difference between single-turn and multi-turn conditions on the MSR/Salesforce benchmark. This would remove the empirical foundation of the product.

4. **A naive heuristic matches Horizon's performance**: V3 kill criterion. If turn-count + keyword overlap achieves comparable fidelity-quality correlation, the THCP framework's complexity is not justified.

If any of these conditions is met, the product pivots or retires per the kill criteria in Appendix D §D.6. The no-go theorems predict that conditions 1–3 will not be met. The product is designed to be provably unnecessary if the theorems are wrong.

---

*This document is a living PRD. It will be updated as development produces empirical results that validate or revise the theoretical predictions. As of this revision, the PRD is aligned with all five appendices of the companion essay: Appendices A–B (theoretical foundations, 77 references), Appendix C (7 implementation gap resolutions, 19 references), Appendix D (temporal-spatial grounding, 23 references), and Appendix E (4D conversation spacetime — circadian, deictic, spatial, velocity, spacetime interval, and causal reachability, 32 references). The product operationalizes 5 THCP conjectures and 173 academic references through 14 event types, a 4D spacetime layer, and 13 registered predictions. Appendix D (Post-Deployment Proof System) defines how the framework proves itself — or honestly disproves itself — in production. Appendix E (Structural Defensibility) establishes why the problem Horizon solves is structural, not engineering — grounded in three independent no-go results from computability theory, self-referential computation, and type theory, confirmed by 2026 empirical work on multi-turn degradation and self-anchoring calibration drift.*
