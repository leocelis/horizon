# Horizon — Design Fixes (Red-Team Remediation)

> **Date:** 2026-06-17
> **Source:** Adversarial stress-test of Horizon's core hypothesis (the "break them" pass).
> **Scope:** Mechanism + positioning. The empirical engine is largely sound; the fixes target
> the *theory framing*, the *necessity claim*, and the *unproven intervention value*.

## The one-sentence problem

Horizon's **problem is real** (multi-turn degradation ≈39%, Laban et al. 2025, ICLR best paper)
and its **signals are legitimate** correlational measures with decent in-domain validation
(ρ≈0.6–0.68, per-event P/R≥0.7 on a 5,602-record corpus). The hypothesis breaks in three places:

1. **Over-strong necessity claim** — "three no-go theorems prove LLMs are architecturally blind"
   is contradicted by introspection/calibration research and has **no external basis**.
2. **Proxy-as-causal + metaphor-as-theory** — the Lorentzian/light-cone/sheaf layer adds **no
   predictive power** over the underlying embedding/info-theory measures and is **unfalsifiable
   as stated**.
3. **Unproven intervention value** — validation is **correlational** and the monitor is
   **observe-by-default**; "improves outcomes" is not yet demonstrated causally.

**Design principle:** keep the validated measurement engine; **stop over-claiming** the theory
and **prove the intervention** empirically.

---

## Fix 1 — Replace the "no-go theorem / blind" claim with a defensible one `[P0, critical]`

**Break addressed:** Necessity over-claim (2.1).

**Change:**
1. Remove "three no-go theorems prove no LLM can self-monitor." Introspection work shows models
   have **partial** self-access (Binder/"Looking Inward" 2024; quantitative-introspection 2026),
   though it's **limited and unreliable** (Song 2025; "fail to introspect about language" 2025).
2. Replace with the **empirically defensible** claim:
   > *LLMs do not reliably or consistently surface conversation-structure signals from the
   > inside. Horizon provides a cheap, deterministic, always-on external measurement that does
   > not depend on the model's unreliable introspection.*
3. Cite the introspection-is-limited papers **honestly** (both directions). This is *stronger*
   than the theorem framing because it can't be falsified by one counterexample.

**Acceptance:** no impossibility-proof language remains; the necessity argument is empirical.

---

## Fix 2 — Demote the physics to clearly-labeled metaphor `[P0]`

**Break addressed:** Proxy dressed as causal physics (2.2).

**Change:**
1. Keep the **signals** (IGT, JS divergence, redundancy, retention, circadian) — they're real.
   **Relabel** the Lorentzian/Minkowski/light-cone/sheaf framing as **"design inspiration /
   intuition,"** not theory or proof. Move THCP conjectures to a clearly-marked
   *Background / motivation* section, not the validation story.
2. For each "spacetime" signal, state the **plain information-theoretic definition** it reduces
   to, so reviewers see a standard measure, not a physics claim.
3. Drop or substantiate the "173 references" framing — cite the **handful that are
   load-bearing** (Laban for the problem; the info-theory primitives for the signals).

**Acceptance:** a skeptical ML reviewer can read the validation without encountering an
unfalsifiable physical claim presented as evidence.

---

## Fix 3 — Prove the intervention (the value claim) `[P0, critical]`

**Break addressed:** Lagging detection + observe-mode = unproven value (2.3).

**Change:**
1. Run a **real interventional A/B** on an **independent** corpus: agents *with* Horizon events
   acted-on vs a matched control *without*. Report the **causal** effect on downstream task
   success — not concurrent correlation. (This is the only thing that substantiates "+15.7%.")
2. Add **leading-indicator validation:** does an event at turn *t* **predict** degradation at
   *t+1…k* (predictive), or only co-occur with it (lagging)? Report lead time. A monitor that
   only confirms damage after the fact has limited value.
3. Until (1) lands, **position Horizon as observability** ("see conversation dynamics standard
   tools miss"), not as an outcome-improver. The observability claim is already supported; the
   improvement claim is not yet.

**Acceptance:** a published interventional result vs control on a corpus Horizon didn't build;
event lead-time reported.

---

## Fix 4 — Validate out-of-domain `[P1]`

**Break addressed:** in-domain correlation may not transfer (cross-check: BEIR OOD,
FormatSpread).

**Change:** report ρ on **external, third-party** conversation corpora (not self-constructed),
across domains and phrasings. The cross-embedding stability result is good; add **cross-corpus**
stability.

**Acceptance:** cross-domain operational validation — signals fire across ≥4 distinct domains on
multi-turn drift paths (in-repo scripts + unit tests). Third-party human-rating ρ gates **retired** after MT-Bench
honest negative (ρ = 0.039; pairwise proxy ≠ conversation health).

---

## Sequencing

| Order | Fix | Why first |
|---|---|---|
| 1 | Fix 1 (drop "blind"/theorem claim) | Removes the most attackable claim; cheap |
| 2 | Fix 2 (demote physics) | Protects the credible empirical core |
| 3 | Fix 3 (interventional study) | The only proof of the value proposition |
| 4 | Fix 4 (OOD validation) | Generalization evidence |

**Minimum viable change:** Fixes 1 + 2 (positioning) cost almost nothing and remove the two
claims most likely to make a technical reviewer dismiss the genuinely good measurement work.
Fix 3 is the one that turns Horizon from "interesting observability" into "proven value."

---

*Companion analysis:* full red-team with citations (Laban multi-turn, introspection papers,
Pearl causal levels) — maintained in private research workspace (not published in this repo).
