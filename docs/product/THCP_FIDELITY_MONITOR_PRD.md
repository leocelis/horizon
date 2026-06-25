# Horizon Fidelity Monitor — Product Overview (Public)

*Leo Celis · April 2026 · maintained in open source for contributors and integrators*

**Codename:** Horizon

> **Scope:** This is the **public product overview** shipped with the OSS repo. The full PRD
> (phases, validation gates, commercial open questions, extended appendices) and companion
> THCP research essay live in the private workspace — not in this repository.

**Design lineage:** Trans-Horizon Communication Protocol (THCP) — physics vocabulary is
**design metaphor only**. See [README § Background](../../README.md#background).

---

## 1. Executive Summary

Horizon is a real-time middleware layer that measures structural health of human–AI
conversations as they unfold. It emits signals across semantics, time, space, and causality
(IGT, intent–response divergence, fidelity dynamics, temporal gap, circadian factor, velocity,
spacetime interval, causal reachability, and 14 observe-by-default event types).

The monitor runs as a sidecar: it consumes turns and emits structured signals. The agent
controller decides how to act — Horizon does not generate responses.

**Core thesis:** Conversations fail because neither participant sees structural health. Horizon
makes that health observable.

**Why external measurement (empirical, not a proof):** We do *not* claim a theorem that LLMs
cannot self-monitor. Introspection is real but *limited and unreliable* on complex and
out-of-distribution tasks ([Binder et al. 2024](https://arxiv.org/abs/2410.13787);
[arXiv:2512.12411](https://arxiv.org/abs/2512.12411)). Horizon measures externally with cheap,
deterministic, zero-LLM-call arithmetic. (Earlier impossibility framing is **retracted** —
see Appendix E below.)

---

## 2. Problem Statement

### 2.1 Failure modes (multi-turn)

1. **Premature solutioning** — coherent but wrong; wasted turns.
2. **Semantic drift** — locally coherent turns, globally divergent goal.
3. **Conversation overshoot** — generating past diminishing returns.

### 2.2 Why existing tools miss this

| Category | Examples | Gap |
|----------|----------|-----|
| Post-hoc eval | DeepEval, RAGAS | After conversation ends |
| Tracing | LangSmith, Langfuse, Arize | Infrastructure, not conversation dynamics |
| Distribution drift | Confident AI | Days/weeks, not turns within a session |

**None measure the conversation as a dynamic system with its own health trajectory.**

### 2.3 Who has this problem

AI agent builders, platform teams running multiple agents, and researchers studying
human–AI interaction dynamics.

---

## 3. Competitive Landscape (summary)

Frontier labs embed conversation quality implicitly (model spec, training-time alignment).
Observability incumbents measure traces and per-response scores — not multi-turn structural
dynamics. Horizon adds a **conversation-dynamics layer** that complements (not replaces) them.

**Why won't models solve this themselves?** The most common objection is that future models
will internalize conversation-quality monitoring. The defensible answer is **empirical**,
not an impossibility proof:

1. **Introspection is partial and unreliable** ([Binder et al. 2024](https://arxiv.org/abs/2410.13787);
   [arXiv:2512.12411](https://arxiv.org/abs/2512.12411)): models sometimes surface internal state,
   but not consistently enough to trust for production conversation-health monitoring.
2. **SACD empirical confirmation** (arXiv:2603.01239, March 2026): Claude, GPT-5.2, and Gemini
   exhibit systematic, model-specific calibration drift in multi-turn conversations. Each drifts
   differently; none reliably detects its own drift.
3. **Self-reference results motivate external measurement** (Tkemaladze IPM trilemma; Spivack
   representational incompleteness): *design inspiration* for operating outside the inference loop —
   **not** proof that self-monitoring is impossible (see Appendix E retraction note).

Horizon's load-bearing claim: LLMs do not *reliably* surface conversation-structure signals from
the inside, so a cheap external monitor is the dependable measurement layer.

---

## 4. Product Vision

### 4.1 What we are building

A lightweight Python library (MCP server optional) that:

1. Consumes conversation turns (human, agent, optional timestamps/context)
2. Computes semantic and 4D spacetime signals per turn
3. Emits 14 structured event types when thresholds are crossed
4. Exposes trajectory and event resources for dashboards and controllers

Pure measurement — no response generation, no prompt mutation.

### 4.2 What we are NOT building

- A new LLM or fine-tuning pipeline
- A full observability platform (LangSmith-class)
- A post-hoc-only evaluation framework

### 4.3 Design principles

- **Observe by default** — events surface signals; controllers choose interventions
- **Zero LLM calls in core path** — embeddings + arithmetic only
- **Framework agnostic** — raw strings, OpenAI, Anthropic, LangChain, MCP

### 4.4 Computation Model: Mathematical vs. Model-Based

Horizon is primarily a **mathematical and algorithmic system**. The core pipeline requires no
LLM calls and no API access. This is a deliberate architectural choice with three justifications:

1. **Self-reference avoidance**: Asking an LLM to evaluate another LLM's conversation output
   *during* generation risks the Tkemaladze introspection trilemma (incorrect self-assessment,
   non-halting evaluation loops, or perturbation of the response under measurement). These results
   motivate external measurement — they are *design inspiration*, not a proof that self-monitoring is impossible. The monitor avoids the trilemma by operating *outside* the
   inference process entirely.
2. **Cost neutrality**: Every monitored turn must not double the inference cost. A pure
   measurement layer adds no per-turn API cost.
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

**Engineering reference:** [`docs/spec/HORIZON_TECH_SPEC.md`](../spec/HORIZON_TECH_SPEC.md) ·
[`docs/spec/horizon_intent.yaml`](../spec/horizon_intent.yaml) ·
[`docs/reviews/V0_2_0_EVIDENCE.md`](../reviews/V0_2_0_EVIDENCE.md)

---

## Appendix E: External Observer Rationale (Background / Motivation)

> **⚠️ Status: motivation, not evidence (retraction note, 2026-06-17).** Earlier drafts claimed
> three "no-go theorems" *prove* that no LLM can self-monitor. **That over-claim is retracted.**
> Introspection research shows partial — if limited and unreliable — self-access
> ([Binder et al. 2024](https://arxiv.org/abs/2410.13787);
> [arXiv:2512.12411](https://arxiv.org/abs/2512.12411)). The load-bearing claim is empirical:
> LLMs do not *reliably* surface conversation-structure signals from the inside.

### E.5 The Physics Parallel Is Not Decorative

The mapping between observer problems in physics and conversation dynamics informed Horizon's
architecture as **design inspiration**, not as physical proof. Three independent traditions
(physics, computability, type theory) converged on external-observer measurement — that
convergence motivated the product shape.

Horizon's load-bearing claim is **empirical**: LLMs do not *reliably* surface
conversation-structure signals from the inside, so a cheap external monitor is the dependable
measurement layer today — and remains valuable as introspection improves unevenly across models
and domains.

### E.6 When Horizon Becomes Unnecessary

1. **A model achieves ε ≈ 0 in production** across domains (would refute irreducible-gap framing).
2. **A model self-monitors multi-turn trajectory** with human-correlated ρ > 0.5 across domains
   without external measurement.
3. **Turn-boundary degradation disappears** with scaling (< 5% single- vs multi-turn gap on
   standard benchmarks).
4. **Naive heuristics match Horizon** on fidelity–quality correlation (V3 kill criterion).

Full falsifiability tables and phase gates: see validation evidence in-repo and private full PRD.
