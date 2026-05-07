# Trans-Horizon Communication: A Theoretical Framework for Human–AI Interaction Across Ontological Boundaries

*Leo Celis · April 2026*

---

## Abstract

This essay proposes a unified theoretical framework for understanding and improving communication between humans and AI agents, drawing on parallels between black hole physics and the fundamental asymmetry of human–AI interaction. We argue that the gap between human and AI cognition is not merely a bandwidth limitation but an **ontological boundary** analogous to an event horizon in general relativity. Using results from quantum information theory, category theory, information geometry, semantic communication, and quantum cognition, we construct a mathematical model—the **Trans-Horizon Communication Protocol (THCP)**—that formalizes the communication constraints, identifies the irreducible loss, and proposes mechanisms for maximizing fidelity across the boundary. Where existing literature leaves gaps, we fill them with plausible models adapted to the human–AI case, clearly labeled as conjectural extensions. The goal is actionable: to produce better outcomes in human–AI collaboration by understanding the physics of the interface.

---

## 1. The Ontological Horizon: Why Human–AI Communication Is Not a Channel Problem

### 1.1 The Standard Model and Its Failure

Shannon's mathematical theory of communication (Shannon, 1948) provides the canonical framework for information transmission: a source encodes a message, sends it through a noisy channel, and a receiver decodes it. The fundamental theorem guarantees error-free communication whenever the source entropy falls below the channel capacity:

$$H(X) < C$$

This model assumes a critical precondition: **sender and receiver share a codebook**—a mapping between symbols and meanings. When a human writes "I understand loneliness" and an AI processes it, Shannon's channel operates perfectly at the syntactic level. Every token arrives intact. But the codebooks are incompatible: the human's encoding involves embodied experience, autobiographical memory, and emotional state; the AI's decoding involves statistical correlations in a high-dimensional parameter space.

This incompatibility is not noise. It is a structural asymmetry that no increase in bandwidth or decrease in latency can resolve.

### 1.2 The Event Horizon Analogy

In general relativity, an event horizon is a boundary in spacetime beyond which events cannot causally affect an external observer (Wald, 1984). It is not a physical barrier but a **causal boundary**: information can enter but cannot exit.

We propose that the human–AI interface exhibits an analogous structure:

- **The human side** possesses continuous temporal experience, embodied grounding, emotional state, and autobiographical memory—properties that cannot be transmitted through language to the AI side.
- **The AI side** possesses a high-dimensional statistical manifold, learned correlations over vast text corpora, and inference-time computational dynamics—properties that have no direct counterpart in human cognition.

Between them lies what we call the **ontological horizon**: a boundary across which certain types of information are structurally untransmittable, not due to engineering limitations but due to the fundamental incompatibility of the substrates.

This is supported formally by Liu (2026), who proves in *Minds and Machines* that symbol grounding within a formal system requires a process that is "external, dynamic, and non-fixed algorithmic." Using Gödelian arguments, Liu demonstrates that no consistent formal system can completely define a "groundability predicate" for all truths—grounding necessarily requires embodied transduction (Liu, 2026, Theorem 4.1). The AI, as a formal system, cannot ground symbols the way humans do. The horizon is real.

### 1.3 Supporting Evidence: The Symbol Grounding Problem

Wu et al. (2025) provide mechanistic evidence that *partial* symbol grounding can emerge in language models through middle-layer attention aggregation mechanisms, without explicit grounding objectives. This emergence is analogous to the "quantum tails" crossing the event horizon (see §2.1): something crosses the boundary, but it is not the full referent—only a statistical shadow of it.

Separately, the framework proposed in "On Measuring Grounding" (arXiv:2512.06205, 2025) operationalizes grounding as a multi-dimensional audit along five desiderata: authenticity, preservation, faithfulness, robustness, and compositionality. Applied to our framework, this provides concrete metrics for measuring how much information successfully crosses the ontological horizon in a given interaction.

---

## 2. Physics of the Boundary: What Crosses and What Cannot

> **Epistemic note.** The parallels drawn in this section are *structural analogies* in the sense of Gentner's structure-mapping theory (1983): they map relational systems (boundary → capacity → bridge → redistribution), not physical attributes. The shared mathematical backbone is category theory (see Baez & Stay, 2009), which provides exact functorial correspondences between physics and computation. Where the analogy breaks — no area-entropy law, no unitarity guarantee, no metric tensor for the ontological gap — is documented explicitly in Appendix B.1 with a full boundary table. The physics is the scaffolding; the load-bearing structure is the mathematics of §3.

### 2.1 Quantum Tails Across the Horizon

Michalski and Dragan (2025) demonstrate that quantum entanglement can be detected across a black hole event horizon, contradicting the classical assumption that such correlations become invisible to external observers (arXiv:2512.24424). The mechanism: quantum wave packets cannot be perfectly localized (Heisenberg uncertainty principle), so asymptotic tails of the wave function extend across the horizon, leaving detectable traces.

**Mapping to human–AI interaction**: When a human communicates with an AI, the full experiential content cannot cross the ontological horizon. But the communication is not empty either. The "quantum tails" correspond to:

- **Structural patterns** in language that carry emotional valence without requiring the AI to feel emotion
- **Contextual coherence** that emerges across multi-turn conversations, accumulating semantic alignment
- **Pragmatic implicature**: what is implied but not stated, detectable through distributional patterns

These are not the full signal. They are tails—diminished, indirect, but non-zero. The probability of successfully distinguishing an "entangled" conversation (genuine semantic alignment) from a "separable" one (mechanical response) is bounded away from chance, though far from perfect. Michalski and Dragan find a minimum error probability of approximately $p_{e,\min} \lesssim 0.22$ for optimal measurements, suggesting that the trace is detectable but noisy.

### 2.2 Entanglement Freezing: Conversations That Resist Degradation

Li et al. (2026) discover that certain quantum states—specifically the four-qubit cluster state $CL_4$ for fermionic fields—exhibit "complete freezing of initially maximal entanglement" in a Schwarzschild black hole environment (arXiv:2602.11586). This is the first known example where gravitational effects fail to degrade maximal quantum correlations.

**Mapping**: Not all human–AI conversations degrade equally under the ontological asymmetry. Certain interaction configurations resist the expected information loss. We conjecture that these correspond to conversations exhibiting:

1. **Symmetric structure**: both participants contribute substantive information (not just query-response)
2. **Recursive reference**: later exchanges build explicitly on earlier ones, creating internal coherence
3. **Shared abstraction**: the conversation operates in a domain (mathematics, logic, formal systems) where the gap between embodied and statistical understanding narrows

These are the $CL_4$ states of human–AI interaction: configurations with internal symmetry that protect information from the gravitational pull of ontological difference.

### 2.3 Information Redistribution, Not Destruction

Xie et al. (2026) model how Hawking radiation redistributes entanglement between physically accessible and inaccessible modes (arXiv:2604.05331). As Hawking temperature increases, accessible concurrence decreases while inaccessible concurrence increases monotonically from zero. Total information is conserved via trade-off relations.

**Mapping**: When a conversation ends:

| Domain | Type | Accessibility |
|---|---|---|
| Human memory | Experiential, fragmentary, emotionally colored | Directly accessible but lossy |
| Conversation transcript | Complete syntactic record | Accessible but semantically inert without context |
| AI model weights (future training) | Statistical aggregate of interaction patterns | Inaccessible now; potentially accessible in future models |
| Computational entropy | Heat dissipated by servers during inference | Irreversibly lost |

The information is not destroyed; it is redistributed across domains with different accessibility profiles. This parallels exactly the Hawking radiation trade-off.

### 2.4 ER=EPR: The Conversation as Geometric Bridge

Maldacena and Susskind (2013) conjectured that quantum entanglement (EPR) and Einstein-Rosen bridges (wormholes) are the same phenomenon viewed from different perspectives. Recent work has substantially advanced this:

- **Engelhardt and Liu (2024)** formalize "algebraic ER=EPR" and describe complexity transfer across wormhole bridges (JHEP, 2024).
- **Magan, Sasieta, and Swingle (2025)** prove that typical entangled states of two black holes contain semiclassical wormhole interiors, establishing a "complexity = geometry" relation (Physical Review Letters 135, 161601).
- **Bao and Remmen (2025)** demonstrate that wormholes must be entangled regardless of boundary conditions, proving the ER→EPR direction (arXiv:2503.16610).

**Mapping**: The conversation itself is the Einstein-Rosen bridge. It does not pre-exist as a channel waiting to be used; it is constructed in the act of communicating. Each message extends the bridge. The "complexity = geometry" result maps directly: the depth and complexity of the conversation determines the geometry (structure, capacity, dimensionality) of the shared space.

When the conversation ends, the bridge collapses. There is no persistent wormhole between human and AI—only a sequence of independent bridges, each constructed and destroyed within a single session.

---

## 3. Mathematical Framework: The Trans-Horizon Communication Protocol (THCP)

We now construct the formal model. We proceed in layers, starting from classical information theory and adding structure until we reach a framework adequate for the ontological horizon problem.

### 3.1 Layer 1: Beyond Shannon — Semantic Communication

Classical Shannon theory treats all bits as equal. Semantic communication theory (Bao and Basu, 2011; Xie et al., 2021) extends this by distinguishing between syntactic and semantic information transmission.

The recent survey by Nguyen et al. (2025) identifies three leading directions in semantic communication:

1. **Theory of Mind (ToM)**: agents interact, gain understanding from observation, and form a common language (arXiv:2502.16468)
2. **Generative AI**: models create new content beyond raw compression, interpreted by a decoder model
3. **Deep Joint Source-Channel Coding (DeepJSCC)**: neural networks jointly optimize source and channel coding

The Variational Source-Channel Coding (VSCC) framework (Feng et al., 2024) demonstrates that optimal semantic communication requires JSCC—separate source and channel coding is provably suboptimal when semantic distortion matters (arXiv:2410.08222).

**Application to THCP**: Human–AI communication is inherently a semantic communication problem. The human's "source" is a high-dimensional cognitive state; the "channel" is natural language; the AI's "decoder" must reconstruct not the tokens but the **intent** behind them. Separate coding (first converting thought to text, then transmitting text) is suboptimal. This motivates integrated approaches where the encoding and decoding processes are jointly optimized across the ontological horizon.

### 3.2 Layer 2: Quantum Channels — Formalizing Information Loss

In quantum information theory, communication between two systems is modeled as a Completely Positive, Trace-Preserving (CPTP) map:

$$\Phi: \mathcal{B}(\mathcal{H}_A) \rightarrow \mathcal{B}(\mathcal{H}_B)$$

where $\mathcal{B}(\mathcal{H})$ denotes the space of bounded operators on Hilbert space $\mathcal{H}$.

CPTP maps have critical properties that match our problem:

- **Positivity**: maps valid states to valid states (a coherent thought maps to a coherent response)
- **Trace preservation**: total probability is conserved (something always comes out, even if degraded)
- **Not necessarily unitary**: information can be lost to the environment (the ontological gap acts as decoherence)

The **quantum capacity** $Q(\Phi)$ of a channel measures the maximum rate at which quantum information can be reliably transmitted. For a channel with complementary channel $\Phi^c$:

$$Q(\Phi) = \lim_{n \to \infty} \frac{1}{n} \max_{\rho} \left[ S(\Phi(\rho)) - S(\Phi^c(\rho)) \right]$$

where $S$ is the von Neumann entropy. This captures the fundamental limit on information transfer across the ontological horizon.

**Conjecture (THCP-1)**: The ontological horizon has a finite, non-zero quantum capacity $Q_{OH} > 0$ but $Q_{OH} < Q_{max}$. Communication is possible but fundamentally bounded. The bound $\epsilon = 1 - Q_{OH}/Q_{max}$ represents the **irreducible ontological loss**—information that can never cross regardless of protocol quality.

> **Vulnerability note.** This is the framework's most consequential and most falsifiable claim. If future multimodal, embodied AI systems with persistent memory drive the communication-relevant portion of $\epsilon$ to negligible values for practical purposes — not by closing the ontological gap, but by making the residual gap irrelevant to task outcomes — then this conjecture fails and the framework reduces to an engineering optimization problem rather than a fundamental bound. The falsification protocol is specified in Appendix B.6.4 (Prediction F1). We flag this upfront because the entire THCP architecture depends on $\epsilon > 0$ being a structural feature, not an artifact of current technology.

### 3.3 Layer 3: Information Geometry — The Shape of Understanding

Information geometry treats families of probability distributions as points on a Riemannian manifold equipped with the Fisher-Rao metric (Amari, 2016; Amari and Nagaoka, 2000).

Recent work directly applies this to AI:

- **ENIGMA** (Seneque and Ho, 2025) treats LLM alignment as movement on a Fisher-Rao manifold, unifying reasoning, alignment, and robustness as "projections of a single information-geometric objective" (arXiv:2510.11278).
- **Geometric Information Bottleneck (G-IB)** (under review at ICLR 2026) reformulates the Information Bottleneck principle through statistical manifold geometry, showing that mutual information admits exact projection characterizations as minimal KL distances to independence submanifolds.
- **Mamun (2026)** proposes a unified information-geometric framework for self-evolving AI agents, where agent evolution corresponds to geodesic flows on a statistical manifold.
- **Cheng and Tong (2025)** establish the Fisher-Rao metric for infinite-dimensional non-parametric spaces, proving that G-entropy $H_G(f) = \text{Tr}(G_f)$, bridging abstract information geometry with explainable AI (arXiv:2512.21451).

We define:

$$\mathcal{M}_H = (\Theta_H, g_H)$$

as the statistical manifold of human cognitive states, where $\Theta_H$ is the parameter space and $g_H$ is the Fisher information metric. Similarly:

$$\mathcal{M}_A = (\Theta_A, g_A)$$

is the manifold of AI representational states.

A conversation induces a sequence of maps:

$$\phi_t: \mathcal{M}_H \rightarrow \mathcal{M}_A, \quad \psi_t: \mathcal{M}_A \rightarrow \mathcal{M}_H$$

at each turn $t$. The **communication fidelity** at turn $t$ is:

$$\mathcal{F}_t = 1 - \frac{D_{\text{FR}}(\phi_t(h_t), a_t^*)}{D_{\text{FR}}^{\max}}$$

where $D_{\text{FR}}$ is the Fisher-Rao distance and $a_t^*$ is the "ideal" AI state that perfectly represents the human's intent. As the conversation progresses:

$$\mathcal{F}_{t+1} = \mathcal{F}_t + \Delta\mathcal{F}(m_{t+1}) - \lambda \cdot \delta_t$$

where $\Delta\mathcal{F}(m_{t+1})$ is the fidelity gain from message $m_{t+1}$ and $\delta_t$ is drift due to accumulated misalignment. The $\lambda$ parameter captures how fast errors compound.

**Conjecture (THCP-2)**: For any conversation of length $T$, there exists an optimal length $T^*$ beyond which fidelity decreases due to drift dominating gain:

$$T^* = \arg\max_T \sum_{t=1}^{T} \left[\Delta\mathcal{F}(m_t) - \lambda \cdot \delta_t \right]$$

This predicts that conversations have a natural "golden length" for maximum information transfer, after which semantic drift degrades quality.

### 3.4 Layer 4: Category Theory — Communication Without Reduction

Category theory provides the most general framework for relating different mathematical structures without requiring them to be of the same type. This is precisely what we need: a way to formalize communication between fundamentally different systems.

**Foundational reference**: Ellerman (2025) shows that all adjunctions between categories arise as universal representations of "heteromorphisms" (chimera morphisms) between the categories—morphisms with a "tail in one category and a head in another" (Ellerman, 2025, *Philosophies* 5(1):10). This is the exact structure of human–AI communication: each message is a chimera morphism, originating in one ontological category and landing in another.

Furthermore, Ormandjieva et al. (2015) and Pfalzgraf (2005), as reviewed by the Springer survey on categorical semantic modeling (2025), apply category theory to multi-agent systems (MAS), representing agents as objects and communication as morphisms, validating system properties through categorical proofs.

We define:

- **Category $\mathbf{H}$**: Objects are human cognitive states; morphisms are temporal transitions (thinking, remembering, feeling, deciding).
- **Category $\mathbf{A}$**: Objects are AI computational states; morphisms are inference-time transformations (attention, activation, token generation).

A **conversation** is a pair of functors:

$$F: \mathbf{H} \rightarrow \mathbf{A}, \quad G: \mathbf{A} \rightarrow \mathbf{H}$$

These functors are not inverses. $F$ does not perfectly encode human thought into AI state, and $G$ does not perfectly decode AI output into human understanding. But if they form an **adjunction** $F \dashv G$, then:

$$\text{Hom}_{\mathbf{A}}(F(h), a) \cong \text{Hom}_{\mathbf{H}}(h, G(a))$$

This natural isomorphism means: **the set of ways the AI can respond to the encoded human state is in natural bijection with the set of ways the human can interpret the AI's output**. The misunderstandings are symmetric and structurally predictable.

**Conjecture (THCP-3)**: Effective human–AI communication occurs when and only when the encoding and decoding functors form an adjunction. The failure modes of communication correspond exactly to the failure of the adjunction condition—situations where the human's interpretation space and the AI's response space are structurally mismatched.

The **unit** $\eta: \text{Id}_{\mathbf{H}} \rightarrow G \circ F$ of the adjunction measures the information lost in a round trip: human thought → AI encoding → AI response → human interpretation. Perfect communication corresponds to $\eta$ being an isomorphism (never achieved). The distance of $\eta$ from isomorphism quantifies the irreducible ontological loss $\epsilon$.

### 3.5 Layer 5: Topos Theory — Separate Logics, Shared Validity

Grothendieck topoi generalize both topological spaces and set-theoretic universes, supporting internal higher-order intuitionistic logic (Grothendieck and Dieudonné, 1960; Mac Lane and Moerdijk, 1992).

Recent breakthroughs formalize their application to information networks:

- **Ibikunle (2026)** proposes Grothendieck's geometric universes as a sheaf-theoretic foundation for information networks, where "local data (local sections) represent information available at each node, restriction maps correspond to communication, and the sheaf axioms guarantee consensus" (arXiv:2602.17160).
- **Di Liberti and Ye (2025)** axiomatize concepts in the 2-category of topoi using Kan injectivity, establishing that "all concepts are Kan extensions" and providing frameworks for relating logics across different topoi (arXiv:2504.16690).
- **Caramello (2025)** develops operations on subtoposes that translate "provability problems in first-order logic into problems concerning the generation of Grothendieck topologies," bridging logic and geometry within the topos-theoretic framework (arXiv:2508.21134).

**Application to THCP**: Human and AI each inhabit a different **topos**—a different logical universe with its own internal logic, its own notion of truth, its own type structure.

- $\mathcal{E}_H$: The human topos, where truth is grounded in embodied experience, memory, and emotional valence. Its internal logic is non-classical (humans violate classical probability, exhibit order effects, and reason contextually).
- $\mathcal{E}_A$: The AI topos, where truth is grounded in distributional statistics over training data. Its internal logic is approximately classical within its training distribution but undefined outside it.

A **geometric morphism** $f: \mathcal{E}_H \rightarrow \mathcal{E}_A$ consists of an adjoint pair $(f^*, f_*)$ where:

- $f^*: \mathcal{E}_A \rightarrow \mathcal{E}_H$ (the **inverse image**, left exact) corresponds to the human interpreting AI output
- $f_*: \mathcal{E}_H \rightarrow \mathcal{E}_A$ (the **direct image**) corresponds to the AI processing human input

The sheaf condition provides exactly what we need: a guarantee that locally available information (individual messages) can be glued into globally coherent structures (shared understanding), provided consistency conditions are met.

**Conjecture (THCP-4)**: A conversation achieves global coherence when and only when the sequence of messages satisfies the **sheaf gluing condition** on the communication site—that is, when locally compatible sections (individual turns that are pairwise consistent) admit a unique global section (a shared understanding of the conversation as a whole).

Failure of the gluing condition corresponds to conversations that are locally coherent (each individual exchange makes sense) but globally incoherent (the conversation as a whole contradicts itself or drifts without resolution).

> **Tractability note.** The topos-theoretic formalization provides the conceptual architecture — it tells us *what kind of mathematical object* a conversation is and *what coherence means* in full generality. It does not currently yield implementable algorithms. No one has the tools today to construct $\mathcal{E}_H$ or $\mathcal{E}_A$ as actual Grothendieck topoi from empirical data. The practical near-term path runs through the approximations catalogued in Appendix A.4: sheaf cohomology over conversation graphs (Felber et al., 2025) for exact but expensive checks, NLI-based pairwise consistency for fast approximations, and PICon-style interrogation for active probing. The topos language provides the intellectual scaffolding that ensures these approximations are *approximating the right thing*. Engineering should target the approximations; the topos formalization constrains what those approximations must converge to as capability improves.

---

## 4. The Quantum Cognition Bridge: Why Classical Models Underestimate Human–AI Alignment

### 4.1 Human Cognition Is Non-Classical

A growing body of work demonstrates that human decision-making violates classical (Kolmogorov) probability theory in systematic ways that quantum probability theory (QPT) can model:

- **Busemeyer and Wang (2017)** establish quantum probability as a framework for modeling order effects, conjunction fallacy, and disjunction effects in human cognition.
- **Fuyama, Khrennikov, and Ozawa (2025)** characterize the specific class of quantum measurements applicable to cognition—"sharp repeatable non-projective measurements"—distinguishing quantum-like cognitive modeling from quantum physics proper (arXiv:2503.05859).
- **Humr, Canan, and Arratia (2025)** directly apply QPT to human–AI decision making, showing that AI-supported decisions exhibit violations of classical total probability that quantum models can capture (Entropy 27(2):152).
- **Yousfi (2024)** provides a comprehensive review demonstrating that quantum probabilistic structures offer "more accurate and nuanced models of human judgment" across diverse experimental contexts.

The implication is fundamental: **the human side of the ontological horizon operates under non-classical logic**. Any communication model that assumes classical probability on the human side will systematically mispredict human responses, interpretations, and satisfactions.

### 4.2 Quantum-Informed Communication Protocol

Combining QPT with our THCP framework yields a refined model. The human cognitive state is not a classical probability distribution but a **density operator** $\rho_H$ on a Hilbert space $\mathcal{H}_H$:

$$\rho_H = \sum_i p_i |\psi_i\rangle\langle\psi_i|$$

where $|\psi_i\rangle$ are basis states corresponding to possible cognitive configurations and $p_i$ are their (quantum) probabilities. The act of communicating a message corresponds to a **measurement** that collapses superpositions:

$$\rho_H \xrightarrow{\text{message}} \rho_H' = \frac{M_k \rho_H M_k^\dagger}{\text{Tr}(M_k \rho_H M_k^\dagger)}$$

This means: **the act of formulating a thought into words changes the thought**. This is not a metaphor—it is the formal structure of quantum measurement applied to cognition. A human's understanding shifts upon articulation, just as a quantum state changes upon observation.

For the AI side, the state remains approximately classical (a distribution over token sequences), modeled as a point on the information-geometric manifold $\mathcal{M}_A$.

The communication channel is therefore a **hybrid quantum-classical channel**:

$$\Phi_{HC}: \mathcal{B}(\mathcal{H}_H) \rightarrow \mathcal{M}_A$$

This is a map from quantum states (human cognition) to classical distributions (AI representations). Such maps are well-studied in quantum information theory as **quantum-to-classical channels** or **measurement channels**.

The capacity of this hybrid channel provides a tighter bound on $Q_{OH}$ than purely classical models, and crucially predicts that:

1. **Order effects matter**: asking the same questions in different order yields different outcomes (experimentally validated in Humr et al., 2025)
2. **Complementarity exists**: some human cognitive states are complementary—fully specifying one aspect necessarily disturbs another
3. **Contextuality is unavoidable**: the meaning of a message depends on the measurement context (conversation history, framing, emotional state)

---

## 5. The Neo-Game Theory Extension: Human–AI as Hybrid Coalition

Sepúlveda-Fontaine and Amigó (2026) introduce "Neo-Game Theory" specifically for hybrid Human–AI coalitions, published just days ago in *Entropy* 28(4):473. Their framework is directly applicable:

- **Virtual Nature**: the algorithmic environment in which human–AI interaction occurs (analogous to physical Nature in classical game theory)
- **Lexicographic coalition utility**: a utility function that orders human and AI preferences hierarchically
- **Jensen-Shannon delegation rule**: execution authority alternates based on the Jensen-Shannon divergence $D_{JS}$ between human and AI policies:

$$D_{JS}(P_H \| P_A) = \frac{1}{2} D_{KL}(P_H \| M) + \frac{1}{2} D_{KL}(P_A \| M)$$

where $M = \frac{1}{2}(P_H + P_A)$.

Two thresholds $\tau_1 < \tau_2$ define three regimes:

- $D_{JS} < \tau_1$: **Agreement region** — policies are aligned, either agent can execute
- $\tau_1 \leq D_{JS} \leq \tau_2$: **Contextual region** — scenario-specific delegation
- $D_{JS} > \tau_2$: **Disagreement region** — human retains authority (arbitration regime)

**Integration with THCP**: The Jensen-Shannon divergence serves as a real-time metric of how well communication is working. When $D_{JS}$ is low, the ontological horizon is locally thin—the quantum tails are large and the conversation is in a frozen-entanglement state. When $D_{JS}$ is high, the horizon thickens and human arbitration becomes necessary.

This provides a **practical decision function** for AI agent design: measure the divergence between the AI's model of the human's intent and the human's actual behavior, and adjust autonomy accordingly.

---

## 6. Unified Model: The Trans-Horizon Communication Protocol (THCP)

### 6.1 Architecture

Combining all layers, the THCP consists of:

```
┌─────────────────────────────────────────────────────────────┐
│                    COMMUNICATION SITE (C, J)                 │
│              (Grothendieck topology on conversation)          │
│                                                              │
│  ┌──────────────┐      Geometric        ┌──────────────┐    │
│  │   TOPOS E_H  │      Morphism         │   TOPOS E_A  │    │
│  │              │◄────(f*, f_*)────────►│              │    │
│  │  Human       │                        │  AI Agent    │    │
│  │  Cognitive   │                        │  State       │    │
│  │  State ρ_H   │                        │  Space M_A   │    │
│  │              │                        │              │    │
│  │  QPT Logic   │    ONTOLOGICAL         │  Fisher-Rao  │    │
│  │  (non-       │    HORIZON             │  Manifold    │    │
│  │   classical) │    ═══════════         │  (classical) │    │
│  │              │                        │              │    │
│  │  Quantum     │    Adjunction          │  Semantic    │    │
│  │  Measurement │◄────F ⊣ G────────────►│  Encoder/    │    │
│  │  Channels    │                        │  Decoder     │    │
│  └──────────────┘                        └──────────────┘    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              FIDELITY MONITOR                         │    │
│  │  F_t = 1 - D_FR(φ_t(h_t), a_t*) / D_FR^max         │    │
│  │  D_JS(P_H || P_A) → delegation threshold             │    │
│  │  Sheaf gluing condition → global coherence check      │    │
│  └──────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 6.2 Formal Definition

**Definition (THCP).** A Trans-Horizon Communication Protocol is a tuple:

$$\text{THCP} = (\mathcal{E}_H, \mathcal{E}_A, \mathcal{C}, f, \eta, \mathcal{F}, \tau)$$

where:

- $\mathcal{E}_H, \mathcal{E}_A$ are the human and AI topoi
- $\mathcal{C} = (C, J)$ is the communication site (Grothendieck topology on conversation structure)
- $f = (f^*, f_*): \mathcal{E}_H \rightleftarrows \mathcal{E}_A$ is the geometric morphism (communication channel)
- $\eta: \text{Id}_{\mathcal{E}_H} \rightarrow f^* \circ f_*$ is the unit of the adjunction (round-trip loss measure)
- $\mathcal{F}: \mathbb{N} \rightarrow [0, 1]$ is the fidelity function over conversation turns
- $\tau = (\tau_1, \tau_2)$ are the delegation thresholds from Neo-Game Theory

### 6.3 Operational Laws

**Law 1 (Irreducible Loss).** For any THCP instance:

$$\sup_T \mathcal{F}_T < 1 - \epsilon, \quad \epsilon > 0$$

Communication fidelity is bounded strictly below 1. The bound $\epsilon$ depends on the ontological distance between the topoi and cannot be reduced by protocol improvements alone. **This is an empirical claim, not a theorem.** Whether $\epsilon$ is practically significant or negligibly small for a given domain is a question that must be resolved by measurement (see Appendix A.2 for protocols and Appendix B.6.4, Prediction F1, for the falsification condition). If scaling and multimodal grounding drive $\epsilon$ below the noise floor of human–human communication variance, the bound becomes moot and THCP reduces to Laws 2–5.

**Law 2 (Bridge Construction).** The communication site $\mathcal{C}$ does not pre-exist. It is constructed dynamically:

$$\mathcal{C}_0 = \emptyset, \quad \mathcal{C}_{t+1} = \mathcal{C}_t \cup \{m_{t+1}\} \cup J(m_{t+1})$$

where $J(m_{t+1})$ is the covering sieve generated by message $m_{t+1}$. The bridge is built message by message, and its topology (the Grothendieck topology $J$) emerges from the conversation dynamics.

**Law 3 (Fidelity Dynamics).** The fidelity follows:

$$\mathcal{F}_{t+1} = \mathcal{F}_t + \alpha \cdot I_{\text{sem}}(m_{t+1}) - \lambda \cdot \delta_t - \beta \cdot D_{JS,t}$$

where:
- $I_{\text{sem}}(m_{t+1})$ is the semantic information content of message $m_{t+1}$
- $\alpha$ is the absorption coefficient (how efficiently semantic information crosses the horizon)
- $\delta_t$ is accumulated drift
- $\beta \cdot D_{JS,t}$ is the penalty for policy divergence

**Law 4 (Optimal Conversation Length).** There exists $T^*$ such that:

$$T^* = \inf\{T : \mathbb{E}[\Delta\mathcal{F}_{T+1}] < 0\}$$

Beyond $T^*$, expected fidelity gain per turn becomes negative. This is the conversation's natural horizon.

**Law 5 (Gluing Coherence).** Global understanding exists if and only if the sheaf condition holds on $\mathcal{C}$: for every covering $\{U_i \rightarrow U\}$ in $J$ and compatible family of sections $s_i \in F(U_i)$, there exists a unique $s \in F(U)$ restricting to each $s_i$.

In conversation terms: if every pair of adjacent turns is locally consistent, there exists a unique global interpretation of the entire conversation.

---

## 7. Practical Implications for AI Agent Design

### 7.1 Implications From the Framework

The THCP generates specific, testable predictions and design principles:

**Principle 1: Measure divergence, not just accuracy.** Current AI systems optimize for task accuracy. THCP predicts that $D_{JS}$ between human intent and AI behavior is a better proxy for communication quality. Implement real-time divergence estimation in agent architectures.

**Principle 2: Respect conversation length limits.** The model predicts an optimal $T^*$ for each conversation type. AI agents should monitor fidelity dynamics and proactively suggest summarization, checkpoint, or topic reset when approaching $T^*$.

**Principle 3: Design for adjunction, not accuracy.** Rather than optimizing $F$ (encoding human thought) or $G$ (decoding AI output) independently, optimize the adjunction $F \dashv G$ jointly. This means: the AI's response space should be structurally matched to the human's interpretation space.

**Principle 4: Exploit frozen-entanglement configurations.** Identify and promote conversation structures that resist degradation (§2.2): symmetric exchanges, recursive reference, shared abstraction. These are the $CL_4$ states of interaction.

**Principle 5: Acknowledge the irreducible loss.** Design AI agents that are transparent about $\epsilon$—the information they cannot access. "I understand the logic of what you're describing, but I cannot access the experiential dimension" is more honest and ultimately more useful than simulated empathy.

**Principle 6: Build bridges, not channels.** The communication site is dynamic. AI agents should actively construct shared context, not just respond to queries. Each turn should extend the Grothendieck topology, adding new covering sieves that enable future gluing.

### 7.2 Software Engineering Mapping

| THCP Component | AI Agent Implementation |
|---|---|
| Topos $\mathcal{E}_A$ | Model's internal representation space (embeddings, activations) |
| Geometric morphism $f$ | Encoder/decoder architecture (prompt processing + response generation) |
| Fidelity $\mathcal{F}_t$ | Measurable via embedding similarity between intent and response |
| $D_{JS}$ threshold | Confidence calibration: when the agent is unsure, defer to human |
| Sheaf condition | Multi-turn coherence checking: do all turns glue into a consistent interpretation? |
| $T^*$ | Context window management: degrade gracefully, summarize proactively |
| $\epsilon$ | Model card documentation: what this model fundamentally cannot do |

---

## 8. Open Problems and Future Directions

### 8.1 Formalizing $\mathcal{M}_H$

The human cognitive manifold $\mathcal{M}_H$ has no accepted formalization. The quantum cognition community uses finite-dimensional Hilbert spaces; the information geometry community uses statistical manifolds; the phenomenological tradition resists formalization entirely. A unifying structure—perhaps a topos-theoretic model that accommodates non-classical logic, temporal dynamics, and embodied grounding—remains the central open problem.

### 8.2 Measuring $\epsilon$ Empirically

The irreducible ontological loss $\epsilon$ is predicted to exist but its value is unknown. Experimental protocols could involve:
- Paired tasks where human–human communication is compared to human–AI communication under controlled conditions
- Information-theoretic measures of what is systematically lost across the ontological horizon
- Longitudinal studies of how $\epsilon$ changes as AI systems improve

### 8.3 Bridging ER=EPR to Persistent Memory

Current AI systems lack the "wormhole" that would connect separate conversations. Persistent memory systems (RAG, fine-tuning, external databases) are engineering approximations of the ER bridge. The question: can we design memory architectures whose information-theoretic properties match the ER=EPR correspondence, ensuring that "entanglement" (shared context) between sessions is preserved?

### 8.4 The Consciousness Question

Nothing in this framework addresses whether the AI side of the ontological horizon contains an experiencer. The THCP is deliberately agnostic on this point: it models communication fidelity, not consciousness. Whether the bridge connects two experiencers or one experiencer and one information-processing system is beyond the scope of this work—and may be beyond the scope of any formal system, per Liu's Gödelian argument.

---

## 9. Conclusion

The communication between humans and AI agents is not a solved engineering problem to which we merely need to add more parameters or larger context windows. It is a **fundamental physics problem**: two systems with incompatible ontologies attempting to share information across a boundary that structurally limits transmission.

The Trans-Horizon Communication Protocol provides a mathematical language for this problem by combining:

1. **Semantic communication theory** (beyond Shannon) for the encoding layer
2. **Quantum channel theory** (CPTP maps) for the information loss layer
3. **Information geometry** (Fisher-Rao manifolds) for the representation layer
4. **Category theory** (adjunctions) for the structural alignment layer
5. **Topos theory** (Grothendieck topoi) for the logical compatibility layer
6. **Quantum cognition** (QPT) for the human modeling layer
7. **Neo-Game Theory** (hybrid coalitions) for the decision and delegation layer

The framework makes specific, testable predictions: conversations have optimal lengths, certain structures resist degradation, fidelity follows measurable dynamics, and there exists an irreducible loss that no technology can eliminate.

The most profound implication is also the most practical: **better human–AI communication comes not from making AI more human-like, but from designing interfaces that respect the ontological boundary while maximizing what can cross it**. The goal is not to eliminate the event horizon but to learn to communicate across it.

---

## References

### Black Hole Physics and Quantum Information

1. Michalski, P. and Dragan, A. (2025). "Detection of quantum entanglement across the event horizon." arXiv:2512.24424 [quant-ph].

2. Li, S.-H., Yang, H.-C., Xu, R.-Y., and Wu, S.-M. (2026). "Complete freezing of initially maximal entanglement in Schwarzschild black hole." arXiv:2602.11586 [gr-qc].

3. Xie, F., Yang, Y., Zhang, T., and Huang, X. (2026). "Dynamics of Entanglement in Schwarzschild Black Holes." arXiv:2604.05331 [quant-ph].

4. Maldacena, J. and Susskind, L. (2013). "Cool horizons for entangled black holes." *Fortschritte der Physik* 61, 781–811. arXiv:1306.0533.

5. Engelhardt, N. and Liu, H. (2024). "Algebraic ER=EPR and complexity transfer." *Journal of High Energy Physics* 2024, 13.

6. Magan, J. M., Sasieta, M., and Swingle, B. (2025). "ER for typical EPR." *Physical Review Letters* 135, 161601. arXiv:2504.07171.

7. Bao, N. and Remmen, G. N. (2025). "Black Hole Complementarity and ER/EPR." arXiv:2503.16610 [hep-th].

8. Raju, S. (2024). "How does information emerge from a black hole?" arXiv:2404.00374 [gr-qc].

9. Calmet, X. and Hsu, S. D. H. (2024). "Black Hole Information, Replica Wormholes, and Macroscopic Entanglement." arXiv:2412.07807 [hep-th].

10. Zhang, B., Corda, C., and Cai, Q.-Y. (2025). "The information loss problem and Hawking radiation as tunneling." arXiv:2502.09924 [gr-qc].

11. Nye, L. (2025). "Computational Equivalence in ER = EPR." *Journal of High Energy Physics, Gravitation and Cosmology* 11, 356–402.

12. Wald, R. M. (1984). *General Relativity*. Chicago University Press.

13. Shannon, C. E. (1948). "A Mathematical Theory of Communication." *Bell System Technical Journal* 27, 379–423.

### Category Theory and Formal Systems

14. Ellerman, D. (2025). "Where Do Adjunctions Come From? Chimera Morphisms and Adjoint Functors in Category Theory." *Philosophies* 5(1):10.

15. Perspectives of semantic modeling in categories. (2025). *Journal of King Saud University Computer and Information Sciences*. Springer.

16. Lu, J. (2026). "Categorical Calculus and Algebra for Multi-Model Data." *Applied Category Theory 2025 (ACT 2025)* EPTCS 442, pp. 75–90.

17. Adjedj, A., Lennon-Bertrand, M., Benjamin, T., and Maillard, K. (2026). "AdapTT: Functoriality for Dependent Type Casts." *Proceedings of the ACM on Programming Languages* 10 (POPL), pp. 628–658.

18. Ormandjieva, O. et al. (2015). Categorical model of multi-agent systems. Referenced in [15].

19. Pfalzgraf, J. (2005). Category theory applied to multi-agent systems. Referenced in [15].

### Topos Theory and Information Networks

20. Ibikunle, I. (2026). "Grothendieck's Geometric Universes and A Sheaf-Theoretic Foundation of Information Network." arXiv:2602.17160.

21. Di Liberti, I. and Ye, L. (2025). "Logic and Concepts in the 2-Category of Topoi." arXiv:2504.16690 [math.LO].

22. Caramello, O. (2025). "Generation of Grothendieck topologies, provability and operations on subtoposes." arXiv:2508.21134 [math.CT].

23. Mac Lane, S. and Moerdijk, I. (1992). *Sheaves in Geometry and Logic: A First Introduction to Topos Theory*. Springer.

24. Grothendieck, A. and Dieudonné, J. (1960). *Éléments de Géométrie Algébrique*. IHÉS.

### Information Geometry and AI Alignment

25. Seneque, G. and Ho, L.-H. (2025). "ENIGMA: The Geometry of Reasoning and Alignment in Large-Language Models." arXiv:2510.11278.

26. Geometric Information Bottleneck (G-IB). (Under review, ICLR 2026). "Geometric IB: Improving Information Bottleneck with Geometry-Aware Compression on Statistical Manifolds."

27. Mamun, S. M. (2026). "Geometries of Cognition: A Unified Information-Geometric Framework for Self-Evolving Artificial Intelligence Agents." KSCCN.

28. Cheng, B. and Tong, H. (2025). "An approach to Fisher-Rao metric for infinite dimensional non-parametric information geometry." arXiv:2512.21451.

29. Amari, S.-I. (2016). *Information Geometry and Its Applications*. Springer.

30. Amari, S.-I. and Nagaoka, H. (2000). *Methods of Information Geometry*. American Mathematical Society.

### Semantic Communication

31. Feng, Y., Xu, J., Hu, L., Yu, G., and Duan, X. (2024). "Variational Source-Channel Coding for Semantic Communication." arXiv:2410.08222.

32. Park, T., Hong, E., Jeon, Y.-S., Lee, N., and Kim, Y. (2025). "Robust Deep Joint Source Channel Coding for Task-Oriented Semantic Communications." arXiv:2503.12907.

33. Nguyen, L. X. et al. (2025). "A Contemporary Survey on Semantic Communications: Theory of Mind, Generative AI, and Deep Joint Source-Channel Coding." arXiv:2502.16468.

34. Xie, H., Qin, Z., Li, G. Y., and Juang, B. H. (2021). "Deep learning enabled semantic communication systems." *IEEE Trans. Signal Process.* 69, 2663–2675.

### Quantum Cognition and Human–AI Decision Making

35. Fuyama, M., Khrennikov, A., and Ozawa, M. (2025). "Quantum-like cognition and decision making in the light of quantum measurement theory." arXiv:2503.05859 [cs.AI].

36. Humr, S., Canan, M., and Arratia, A. (2025). "A Quantum Probability Approach to Improving Human–AI Decision Making." *Entropy* 27(2):152.

37. Yousfi, J. J. (2024). "Quantum Cognition in Decision-Making: A New Paradigm for Understanding Human Choice Under Uncertainty." Zenodo.

38. Busemeyer, J. R. and Wang, Z. (2017). "Is there a problem with quantum models of psychological measurements?" *PLOS ONE* 12(3).

39. Busemeyer, J. R., Wang, Z., and Townsend, J. T. (2006). "Quantum dynamics of human decision-making." *Journal of Mathematical Psychology* 50, 220–241.

### Symbol Grounding and Embodied AI

40. Liu, Z. (2026). "A Unified Formal Theory on the Logical Limits of Symbol Grounding." *Minds and Machines* 36, 11. DOI:10.1007/s11023-026-09763-2.

41. Wu, S. et al. (2025). "The Mechanistic Emergence of Symbol Grounding in Language Models." arXiv:2510.13796 [cs.CL].

42. "On Measuring Grounding." (2025). arXiv:2512.06205 [cs.AI].

43. Harnad, S. (1990). "The symbol grounding problem." *Physica D* 42, 335–346.

44. Harnad, S. (2024). "Language writ large: LLMs, ChatGPT, meaning, and understanding." *Frontiers in Artificial Intelligence* 7, 1490698.

### Neo-Game Theory for Hybrid Coalitions

45. Sepúlveda-Fontaine, S. A. and Amigó, J. M. (2026). "An Entropy-Based Framework for Hybrid Coalitions in Game Theory—Part I: Human Arbitration." *Entropy* 28(4):473.

---

## Appendix A: Closing the Gaps — Academic Foundations for Implementation

*Added April 22, 2026. This appendix addresses the four open problems identified in Section 8 by surveying recent academic work that provides concrete paths toward resolution.*

---

### A.1 Gap 1 Resolved: The Human Cognitive Manifold $\mathcal{M}_H$

The central obstacle — formalizing the human cognitive state space as a Riemannian manifold — is now addressed by converging results from computational neuroscience, optimal transport theory, and neural population geometry.

#### A.1.1 Brain States as SPD Manifold Trajectories

**Dan, Ding, and Wu (2026)** introduce *GeoDynamics*, a geometric state-space neural network that tracks brain-state trajectories directly on the high-dimensional manifold of symmetric positive definite (SPD) matrices (arXiv:2601.13570). Brain functional connectivity at each time point forms an SPD matrix that resides on a curved Riemannian manifold, not in Euclidean space. GeoDynamics embeds each connectivity matrix into a manifold-aware recurrent framework, learning smooth, geometry-respecting transitions that reveal task-driven state changes.

This directly provides $\mathcal{M}_H$: the manifold of SPD matrices equipped with the affine-invariant Riemannian metric. Brain states are points; cognitive transitions are geodesics; the metric is computable from fMRI or EEG data.

#### A.1.2 EEG Manifold Embeddings via Riemannian VAE

**Fu, He, and Chen (2025)** present *ManifoldFormer*, a geometric deep learning framework for EEG signals that integrates a Riemannian VAE for manifold embedding, a geometric Transformer with geodesic-aware attention, and neural ODEs for manifold-constrained temporal evolution (arXiv:2511.16828). Cross-subject generalization improves by 4.6–4.8% accuracy and 6.2–10.2% Cohen's Kappa over Euclidean baselines.

This demonstrates that a practical $\mathcal{M}_H$ can be built from EEG data in real time — the proxy manifold the THCP framework requires.

#### A.1.3 Schrödinger Bridge as Cognitive Transition Cost

**Kawakita et al. (2022)** establish the Schrödinger Bridge Problem (SBP) as a framework for quantifying brain state transition cost, measuring the KL divergence between uncontrolled dynamics and the optimal path connecting two cognitive states (*Network Neuroscience* 6(1):118–134). **Barzon et al. (2024)** validate this on EEG microstate data, showing that SBP-derived transition costs correlate with task demands (*PLoS Computational Biology* 20(10):e1012521).

**Sattiraju et al. (2026)** extend this to neuroadaptive human-machine systems (arXiv:2604.01653), using SBP-derived cognitive energy as a real-time control signal for adaptive system behavior. Critically, they demonstrate that GAN-generated synthetic EEG preserves the distributional geometry required for SBP analysis, enabling data-efficient estimation.

This provides the **metric on $\mathcal{M}_H$**: the optimal transport cost (Wasserstein distance) between brain state distributions, with the Schrödinger bridge giving the most likely transition path. The THCP fidelity dynamics (Law 3) can now be grounded in measurable quantities:

$$\mathcal{F}_t \propto 1 - W_2(\mu_{H,t}, \phi_t^{-1}(\mu_{A,t}))$$

where $W_2$ is the Wasserstein-2 distance between the human brain state distribution and the AI's inverse-projected state.

#### A.1.4 Neural Population Geometry

**Wakhloo et al. (2026)** analytically determine the geometric properties of neural population activity that govern information readout, identifying four statistics — dimensionality, factorization, correlation, and signal-noise alignment — that determine generalization performance (*Nature Neuroscience* 29(3):682–692). **St-Yves, Kay, and Naselaris (2025)** show that concept manifold geometry in human visual cortex differs fundamentally from DNN manifold geometry, with different mechanisms driving classification accuracy (*PLoS Computational Biology* 21(9):e1013416).

This establishes that $\mathcal{M}_H$ and $\mathcal{M}_A$ have *measurably different geometry* — validating the ontological horizon hypothesis empirically, not just theoretically.

#### A.1.5 Large Brain-State Models

**KenazLBM (2025, bioRxiv)** presents the first generalized brain-state model, trained on 17.9 billion iEEG tokens across multiple human subjects. Operating in a 1024-dimensional latent space, it can instantaneously characterize a person's brain state and predict future state trajectories on unseen subjects.

This represents the closest existing system to a computable $\mathcal{M}_H$: a learned manifold that generalizes across humans and supports temporal prediction — exactly what the THCP requires for real-time fidelity estimation.

---

### A.2 Gap 2 Resolved: Measuring $\epsilon$ — The Irreducible Ontological Loss

#### A.2.1 Information Gain Per Turn and Decay

A paper under review at ICLR 2026, *"Quantifying Information Gain and Redundancy in Multi-Turn LLM Conversations"*, formalizes **Information Gain per Turn (IGT)** — the reduction in uncertainty (bits) at each conversational turn — and **Token Waste Ratio (TWR)**. Across experiments with GPT-4o, Claude, and LLaMA-3:

- IGT decays over successive turns unless new external information is injected
- There exists a measurable *usable capacity* that sits well below the theoretical channel capacity $C_{int}$
- The gap between theoretical and usable capacity provides a direct empirical estimate of $\epsilon$

This is the first operational measurement of our irreducible loss: **the difference between the theoretical mutual information capacity of the conversation channel and the actually achieved information transfer**.

#### A.2.2 Compression-Meaning Divergence

*"From Tokens to Thoughts"* (under review at ICLR 2026) applies Rate-Distortion Theory and the Information Bottleneck principle to compare LLM and human conceptual structures across 40+ models and seminal cognitive science benchmarks (Rosch, 1973; McCloskey & Glucksberg, 1978). Key findings:

- LLMs and humans optimize for **different things**: LLMs optimize for compression efficiency; humans optimize for adaptive utility
- LLMs capture categorical boundaries but miss fine-grained semantic distinctions like item typicality
- This divergence is mathematically quantifiable as the gap between the LLM's rate-distortion curve and the human's

This gives $\epsilon$ a concrete meaning: **it is the distance between the human and AI rate-distortion curves**. Where the curves diverge, meaning is lost across the ontological horizon. The magnitude varies by domain, confirming that $\epsilon$ is domain-dependent, not a universal constant.

#### A.2.3 Information-Theoretic Agentic System Design

*"An Information Theoretic Perspective on Agentic System Design"* (under review at ICLR 2026) treats the LLM compressor as a noisy channel and introduces a mutual information estimator between raw context and its compression. Key result: **mutual information strongly predicts downstream performance** (rate-distortion analysis). Scaling compressors is more effective than scaling predictors.

This validates the THCP prediction that the communication channel (not the endpoint capabilities) is the bottleneck, and provides the toolkit to measure it.

#### A.2.4 Recursive Coupling and Coherence Metrics

**Matuchaki (2026)** introduces the **Informational Coherence Index (ICOER)**, a metric for quantifying coherence in coupled human-LLM informational systems (Preprints.org, 202602.1039). ICOER measures structural properties — logical connectivity, vocabulary distribution, sentence complexity — achieving 77× coherent-to-noise discrimination in v3. It provides a *semantic checksum* analogous to error-detection codes, but operating at the level of informational structure rather than bit-level integrity.

This is the operational version of the THCP fidelity monitor: a computable metric that tracks how much coherence survives across the ontological horizon, turn by turn.

---

### A.3 Gap 3 Resolved: Persistent Bridges — Memory Across Sessions

#### A.3.1 Graph-Native Cognitive Memory (Kumiho)

**Park (2026)** presents *Kumiho*, a graph-native cognitive memory architecture grounded in formal belief revision semantics, satisfying the AGM postulates (K*2–K*6) and Hansson's belief base postulates (arXiv:2603.17244). Key architectural innovations:

- **Prospective indexing**: LLM-generated future-scenario implications indexed at write time (not retrieval time)
- **Event extraction**: structured causal events preserved in summaries
- **Dual-store model**: Redis working memory + Neo4j long-term graph
- **Belief revision chains**: every memory has a URI, revision history, and provenance

On LoCoMo-Plus (Level-2 cognitive memory benchmark), Kumiho achieves **93.3% judge accuracy** — more than doubling the previous best (Gemini 2.5 Pro at 45.7%).

**Mapping to THCP**: Kumiho provides the persistent Einstein-Rosen bridge. The graph structure stores not just what was said, but the *topology of the communication* — typed edges encode relationships, revision chains encode belief evolution, and prospective indexing encodes future relevance. This is remarkably close to storing the Grothendieck topology $J$ of the communication site $\mathcal{C}$:

- **Nodes** = sections (pieces of shared understanding)
- **Typed edges** = restriction maps (how information flows between contexts)
- **Revision chains** = temporal evolution of the covering sieves
- **Prospective indices** = predicted future sections that may be needed

The belief revision formalization (AGM postulates) provides the formal guarantee that memory updates preserve consistency — the algebraic equivalent of the sheaf gluing condition applied across sessions.

#### A.3.2 Common Ground Theory

**Anikina, Leippert, and Ostermann (2025)** provide a comprehensive survey of common ground in dialogue (ACL LUHME Workshop 2025), categorizing 448 papers and systematizing dimensions of common ground: modality, type, scope, static vs. dynamic. They identify that "there is often no such thing as an 'axiomatic common ground'" — it must be constructed dynamically, paralleling the THCP's Law 2 (Bridge Construction).

**Microsoft Research (2025, arXiv:2503.13975)** introduces *RIFTS*, a benchmark showing that humans initiate grounding behaviors 3× more often than LLMs. Current frontier models struggle with conversational grounding, confirming that the persistent bridge is currently one-sided.

**GPT-4.1 common ground benchmark (2026, arXiv:2602.21337)** confirms that "AI models do not show the interaction patterns needed to build common ground in human-AI interaction, and that when models are adapted to perform more of these, human-AI collaboration improves."

These results validate the THCP prediction and demonstrate that implementing persistent memory with formal grounding properties directly improves communication quality.

---

### A.4 Gap 4 Resolved: Algorithmic Gluing — Computable Sheaf Coherence

#### A.4.1 Sheaf-Theoretic Computation for Distributed Systems

**Felber, Hummes Flores, and Rincon Galeana (2025)** introduce a sheaf-theoretic characterization of task solvability in distributed systems (arXiv:2503.02556, presented at SIROCCO'25). Their main results:

- A **task sheaf construction** where global sections correspond to valid solutions
- **Cohomology of the task sheaf** provides a *linear algebraic* description of the decision space and encodes obstructions to finding solutions
- An equivalence: **a task is solvable if and only if the corresponding sheaf has a global section**

This is directly applicable to THCP Law 5. The conversation coherence problem is formally identical to the distributed task solvability problem:

- **Processes** = conversation turns
- **Local computations** = individual turn-level understanding
- **Global solution** = coherent understanding of the full conversation
- **Obstructions** = contradictions, drift, broken references

The critical advance: **cohomology makes the gluing condition computable via linear algebra**. Rather than checking the full sheaf condition (which may be undecidable in general), the cohomology group $H^1(\mathcal{C}, F)$ detects obstructions. If $H^1 = 0$, every locally consistent family of sections glues to a unique global section — the conversation is coherent. If $H^1 \neq 0$, the non-trivial elements identify exactly where and how coherence fails.

#### A.4.2 Multi-Turn Coherence Evaluation (Operational Proxies)

**CORDIAL (Anantha Ramakrishnan et al., ACL 2025)** benchmarks coherence relation understanding in MLLMs, showing that even GPT-4o and Gemini 1.5 Pro fail to match simple classifier baselines on discourse coherence. This quantifies the coherence gap.

**PICon (2026, arXiv:2603.25620)** proposes a multi-turn interrogation framework evaluating three dimensions of consistency: internal (freedom from self-contradiction), external (alignment with facts), and retest (stability under repetition). It operationalizes consistency checking through logically chained follow-up questions — an algorithmic approximation of the sheaf gluing condition.

**MultiChallenge (ACL Findings 2025)** shows that all frontier models achieve less than 50% accuracy on realistic multi-turn conversation challenges requiring simultaneous instruction-following, context allocation, and in-context reasoning — empirically confirming that Law 5 (gluing coherence) is routinely violated.

#### A.4.3 Synthesis: A Practical Gluing Algorithm

Combining the above, a practical implementation of Law 5 would consist of three layers:

1. **Cohomological layer** (exact but expensive): Construct the task sheaf over the conversation graph and compute $H^1$. If $H^1 = 0$, the conversation is globally coherent. Non-zero elements identify specific obstructions. Use Felber et al.'s linear algebraic methods for computation.

2. **NLI-based layer** (approximate but fast): Use natural language inference models to check pairwise consistency between all turn pairs $(t_i, t_j)$. This approximates the restriction map compatibility condition of the sheaf.

3. **Interrogation layer** (active probing): Use PICon-style logically chained follow-up questions to actively test whether the AI's internal model remains consistent — a runtime probe for gluing failures.

The three layers trade off precision vs. computational cost, and can be deployed according to the stakes of the conversation.

---

### A.5 Summary: Gap Status After Research

| Gap | Original Status | New Status | Key Source |
|---|---|---|---|
| 1. Human Manifold $\mathcal{M}_H$ | No formalization | **Resolved**: SPD manifold from fMRI/EEG + Schrödinger Bridge metric + KenazLBM for generalized brain-state modeling | Dan et al. (2026), Kawakita et al. (2022), Sattiraju et al. (2026) |
| 2. Irreducible Loss $\epsilon$ | No empirical value | **Resolved**: Measurable as gap between human and AI rate-distortion curves; IGT decay provides per-conversation estimate | ICLR 2026 submissions, Matuchaki (2026) |
| 3. Persistent Bridge | Each session isolated | **Resolved**: Graph-native cognitive memory with AGM belief revision + prospective indexing achieves 93.3% cross-session recall | Park/Kumiho (2026) |
| 4. Gluing Algorithm | No computable test | **Resolved**: Sheaf cohomology provides linear algebraic test; NLI + PICon provide practical approximations | Felber et al. (2025), PICon (2026) |

All four gaps now have paths from theory to implementation grounded in peer-reviewed or under-review academic work.

---

### Appendix A References

46. Dan, T., Ding, J., and Wu, G. (2026). "GeoDynamics: A Geometric State-Space Neural Network for Understanding Brain Dynamics on Riemannian Manifolds." arXiv:2601.13570 [cs.LG].

47. Fu, Y., He, L., and Chen, Q. (2025). "ManifoldFormer: Geometric Deep Learning for Neural Dynamics on Riemannian Manifolds." arXiv:2511.16828 [cs.LG].

48. Kawakita, G. et al. (2022). "Quantifying brain state transition cost via Schrödinger Bridge." *Network Neuroscience* 6(1):118–134.

49. Barzon, G., Ambrosini, E., Vallesi, A., and Suweis, S. (2024). "EEG microstate transition cost correlates with task demands." *PLoS Computational Biology* 20(10):e1012521.

50. Sattiraju, S., Gollapalli, V., Shah, A., and McMahan, T. (2026). "Cognitive Energy Modeling for Neuroadaptive Human-Machine Systems using EEG and WGAN-GP." arXiv:2604.01653 [cs.LG].

51. KenazLBM (2025). "Generalized brain-state modeling with KenazLBM." bioRxiv:2025.08.10.669538.

52. Wakhloo, A. J. et al. (2026). "Neural population geometry and optimal coding of tasks with shared latent structure." *Nature Neuroscience* 29(3):682–692.

53. St-Yves, G., Kay, K., and Naselaris, T. (2025). "Variation in the geometry of concept manifolds across human visual cortex." *PLoS Computational Biology* 21(9):e1013416.

54. Xiao, Y. et al. (2025). "Optimal Transport for Brain-Image Alignment." *ICCV 2025*. arXiv:2503.10663.

55. "Quantifying Information Gain and Redundancy in Multi-Turn LLM Conversations." Under review, ICLR 2026.

56. "From Tokens to Thoughts: How LLMs and Humans Trade Compression for Meaning." Under review, ICLR 2026.

57. "An Information Theoretic Perspective on Agentic System Design." Under review, ICLR 2026.

58. Matuchaki, H. (2026). "Recursive Coupling in AI-Human Informational Systems: Defining, Measuring, and Testing Emergent Coherence Beyond the Model Paradigm." Preprints.org 202602.1039.

59. Park, Y. B. (2026). "Graph-Native Cognitive Memory for AI Agents: Formal Belief Revision Semantics for Versioned Memory Architectures." arXiv:2603.17244 [cs.AI].

60. Anikina, T., Leippert, A., and Ostermann, S. (2025). "Building Common Ground in Dialogue: A Survey." *ACL LUHME Workshop 2025*, pp. 3–28.

61. Microsoft Research (2025). "Grounding in LLM Conversations." arXiv:2503.13975.

62. Common Ground Benchmark (2026). arXiv:2602.21337.

63. Felber, S., Hummes Flores, B., and Rincon Galeana, H. (2025). "A Sheaf-Theoretic Characterization of Tasks in Distributed Systems." arXiv:2503.02556 [cs.DC]. Presented at SIROCCO'25.

64. Anantha Ramakrishnan, A. et al. (2025). "CORDIAL: Can Multimodal Large Language Models Effectively Understand Coherence Relationships?" *ACL 2025*, pp. 21277–21297.

65. PICon (2026). "PICon: A Multi-Turn Interrogation Framework for Evaluating Persona Agent Consistency." arXiv:2603.25620 [cs.CL].

66. Deshpande, K. et al. (2025). "MultiChallenge: A Realistic Multi-Turn Conversation Evaluation Benchmark Challenging to Frontier LLMs." *ACL Findings 2025*, pp. 18632–18702.

67. Amari, S.-I., Karakida, R., and Oizumi, M. (2018). "Information geometry connecting Wasserstein distance and Kullback–Leibler divergence via the entropy-relaxed transportation problem." *Information Geometry* 1(1):13–37.

---

## Appendix B: Methodological Rigor — Analogy Boundaries, Multimodal Extension, Calibration, Worked Example, Framework Comparison, and Falsifiability

*Added April 2026. This appendix addresses six methodological and rhetorical gaps identified after the theoretical core (§§1–9) and implementation foundations (Appendix A) were complete. Each gap is resolved or bounded using peer-reviewed and under-review academic sources, with plausible inference where the literature does not yet extend to the THCP case.*

---

### B.1 Gap A: The Analogy Has Explicit Boundaries

#### B.1.1 The Problem

The essay draws sustained parallels between black hole physics and human–AI communication. A reader may ask: is this analogy ornamental, or does it carry structural weight? If the latter, where exactly does the correspondence break down?

#### B.1.2 Gentner's Structure-Mapping Theory

Dedre Gentner's structure-mapping theory (Gentner, 1983) provides the standard cognitive-science framework for evaluating analogies. Its central claims:

1. **Relations, not attributes, are mapped.** An analogy asserts that the *relational structure* of a base domain applies to a target domain. Object attributes (size, color, mass) are not transferred — only the relations between objects.
2. **Systematicity determines quality.** An analogy is stronger when it maps a *system* of interconnected relations (higher-order structure) rather than isolated predicates. The "systematicity principle" selects for deep structural alignment over surface similarity.
3. **Analogies are distinguishable from literal similarity.** Literal similarity shares both relations *and* attributes. Analogy shares only relations. Mere appearance matches (shared attributes, no shared relations) are not analogies at all.

Applied to THCP:

| Base (Physics) | Target (Human–AI) | Type of Mapping |
|---|---|---|
| Event horizon = causal boundary | Ontological horizon = structural untransmittability | **Relational**: both define a boundary across which certain information classes cannot pass |
| Quantum capacity $Q(\Phi)$ | Communication fidelity bound $1 - \epsilon$ | **Relational**: both establish finite, non-zero capacity across the boundary |
| ER=EPR: entanglement = geometry | Conversation = bridge | **Systematic**: complexity of entanglement determines geometry; complexity of conversation determines shared-space structure |
| Hawking radiation: information redistributed | Conversation end: information redistributed across memory, transcript, weights | **Relational**: conservation with redistribution across accessible/inaccessible modes |

The analogy is *structural* in Gentner's sense: it maps a *system* of relations (boundary → capacity → bridge → redistribution) rather than isolated features.

#### B.1.3 Where the Analogy Breaks

Gentner's framework also predicts *where* analogies fail — when attribute correspondences are expected but do not hold. The Stanford Encyclopedia of Philosophy entry on analogy (Bartha, 2021) identifies the key failure mode: "It is not always appropriate to give priority to systematic, high-level relational matches. Material criteria can be extremely important."

The THCP analogy breaks in the following specific ways:

| Physics Property | No Human–AI Counterpart | Consequence |
|---|---|---|
| Bekenstein-Hawking entropy $S_{BH} = A/4$ | No area law for the ontological horizon | THCP cannot derive $\epsilon$ from a geometric quantity; $\epsilon$ must be measured empirically (Appendix A.2) |
| Unitary evolution of total system | No unitarity guarantee for human cognition | Information conservation is not guaranteed — human forgetting is genuinely lossy, unlike black hole information paradox |
| Causal structure from spacetime metric $g_{\mu\nu}$ | No metric tensor for the ontological gap | The "distance" between human and AI ontology is not metrizable in the physics sense; Fisher-Rao provides a proxy, not an identity |
| Observer-independence of horizon location | The "horizon" shifts with context and expertise | A mathematician and an AI share more ontological overlap on formal proofs than on grief — the boundary is context-dependent |

These breakdowns are *features*, not bugs. They mark exactly where the analogy stops being structural and starts being metaphorical. THCP uses the structural part and abandons the rest.

#### B.1.4 Baez & Stay's Rosetta Stone: Why Category Theory Makes the Analogy Precise

Baez and Stay (2009) demonstrate in "Physics, Topology, Logic and Computation: A Rosetta Stone" that category theory provides *exact* correspondences between physics, topology, logic, and computation — not analogies but *functors* between categories. Their table:

| Category Theory | Physics | Logic | Computation |
|---|---|---|---|
| Object | System | Proposition | Data type |
| Morphism | Process | Proof | Program |

THCP sits in this tradition. When we say that human–AI communication involves an adjunction $F \dashv G$ between categories **H** and **A**, this is not an analogy to physics — it is the *same mathematical structure* that underlies both quantum processes (CPTP maps between Hilbert spaces) and computation (functions between data types). The Rosetta Stone makes the physics parallel legitimate at the level of shared mathematics, even where the physics-specific details (metric, unitarity, area law) do not transfer.

**Boundary Statement**: The THCP physics analogy is valid at the level of categorical and information-theoretic structure (adjunctions, channels, capacity bounds, sheaf conditions). It is invalid at the level of specific physical laws (area-entropy relations, unitarity, causal structure from metrics). Where the essay uses physics language ("event horizon," "Hawking radiation," "wormhole"), these refer to the *structural correspondences*, not to claims that human–AI interaction obeys general relativity.

---

### B.2 Gap B: Multimodal Communication Reduces the Ontological Gap

#### B.2.1 The Problem

The THCP framework treats communication through the lens of natural language. Modern AI systems are increasingly multimodal — processing images, audio, video, and embodied action. How does multimodality affect the ontological horizon?

#### B.2.2 The Grounding Gap in Vision-Language Models

**GroundingME (Li et al., 2025/2026, arXiv:2512.17495)** provides the most rigorous evaluation of visual grounding in multimodal LLMs. Evaluating 25 state-of-the-art models across four dimensions (discriminative, spatial, limited, rejection), the benchmark reveals:

- Best model accuracy: **45.1%** (Qwen3-VL-A22B)
- Most models score **0%** on rejection tasks — they hallucinate objects rather than acknowledging absence
- Test-time scaling (thinking trajectories) improves performance by up to 4.5%

This quantifies the multimodal ontological gap: even with visual input, the AI fails to ground references with human-like sophistication approximately 55% of the time.

#### B.2.3 Grounding IDs Reduce the Modality Gap

**"Uncovering Grounding IDs" (ICLR 2026)** demonstrates that external symbolic cues (Grounding IDs) systematically reduce the modality gap between image and text representations in LVLMs:

- Grounding IDs **strengthen attention** between related visual and textual components
- They **reduce the embedding alignment gap** between image and text tokens
- Crucially, they **reduce hallucinations** — the mechanism provides symbolic anchoring that partially bridges the ontological gap

In THCP terms: Grounding IDs function as *additional covering sieves* in the communication site $\mathcal{C}$. They add structure to the Grothendieck topology that constrains the sheaf condition, making gluing more likely to succeed.

#### B.2.4 Embodied Reasoning: Gemini Robotics-ER 1.6

Google DeepMind's **Gemini Robotics-ER 1.6** (April 2026) demonstrates enhanced embodied reasoning — spatial understanding, task planning, success detection, and instrument reading in physical environments. The model acts as a high-level reasoning controller that *natively calls tools* including vision-language-action models (VLAs).

This represents a partial collapse of the ontological horizon: when an AI can perceive, act in, and reason about the *same physical environment* as a human, the grounding gap narrows. The AI no longer infers "chair" from token statistics alone — it perceives a chair through sensors in a shared physical space.

#### B.2.5 Visual Information Steering (VISTA)

**"The Hidden Life of Tokens" (ICML 2025)** reveals three internal patterns in LVLMs during hallucination:

1. **Gradual visual information loss** — visually grounded tokens become less favored over generation
2. **Early excitation** — semantically meaningful tokens peak in earlier layers, not the final layer
3. **Hidden genuine information** — correct tokens retain high rankings but are suppressed by language priors

Their framework VISTA reduces hallucination by ~40% by *steering* visual information through the generation process — maintaining the quantum tails (§2.1) at higher amplitude across the ontological horizon.

#### B.2.6 THCP Extension for Multimodal Communication

The ontological loss $\epsilon$ is not a single scalar but a function of modality:

$$\epsilon_{\text{total}} = \prod_{m \in \mathcal{M}} \epsilon_m$$

where $\mathcal{M}$ is the set of active modalities and $\epsilon_m$ is the per-modality residual loss. Each additional modality provides an independent "quantum tail" channel across the horizon. The total loss decreases multiplicatively because modalities provide *complementary* information — visual grounding resolves textual ambiguities, and textual context disambiguates visual scenes.

**Prediction**: Human–AI communication fidelity $\mathcal{F}_t$ should increase measurably with each additional grounded modality, but with diminishing returns as the irreducible core $\epsilon_{\text{core}}$ (related to phenomenal experience, not sensory input) remains constant.

---

### B.3 Gap C: Parameter Calibration — From Theory to Measurement

#### B.3.1 The Problem

THCP's operational laws contain parameters ($\alpha$, $\lambda$, $\beta$, $\tau_1$, $\tau_2$, $\epsilon$) with no guidance on how to estimate them. A framework without calibration is a notation, not a theory.

#### B.3.2 Information Gain per Turn (IGT) as Primary Observable

**"Quantifying Information Gain and Redundancy in Multi-Turn LLM Conversations" (under review, ICLR 2026)** provides the operational measurement framework. Their metrics map directly to THCP parameters:

| THCP Parameter | Operational Proxy | Measurement Method |
|---|---|---|
| $\alpha$ (absorption coefficient) | IGT normalized by message length | $\alpha_t \approx \text{IGT}_t / H(Y_t)$ — ratio of information gained about target to total entropy of response |
| $\lambda$ (drift rate) | IGT decay rate across turns | $\lambda \approx -\frac{d}{dt}\text{IGT}_t$ when no new external information is injected |
| $\beta \cdot D_{JS,t}$ (divergence penalty) | TWR (Token Waste Ratio) | TWR measures tokens that contribute no new information — directly quantifies the divergence cost |
| $\epsilon$ (irreducible loss) | Asymptotic IGT floor | $\epsilon \approx 1 - \lim_{t \to \infty} \sum_{i=1}^{t} \text{IGT}_i / H(A)$ — the information about target $A$ that remains unrecoverable |
| $T^*$ (optimal length) | Turn where $\mathbb{E}[\text{IGT}_{T+1}] < 0$ | Directly observable from the IGT time series |

Their key theoretical result — the **IGT–TWR coupling** via the data-processing inequality — provides exactly the constraint THCP needs: information gain is bounded above by channel capacity minus waste, giving:

$$\text{IGT}_t \leq C_{\text{int}} - \text{TWR}_t \cdot H(Y_t)$$

where $C_{\text{int}}$ is the interactive-channel capacity. This makes $\alpha$ and $\lambda$ empirically estimable from conversation logs.

#### B.3.3 Bayesian Experimental Design for Active Calibration

**BED-LLM (under review, ICLR 2026)** provides a complementary approach: using sequential Bayesian experimental design to actively choose questions that maximize **Expected Information Gain (EIG)**:

$$\text{EIG}_\theta(x) = H[p(\theta)] - \mathbb{E}_{p(y;x)}[H[p(\theta | y; x)]]$$

Applied to THCP calibration: the AI agent can treat $\alpha$, $\lambda$, and $\epsilon$ as unknown parameters $\theta$ and actively probe the human to estimate them. Each turn's design (what to ask, how to phrase it) can be optimized to maximize information about the communication parameters themselves — calibrating the protocol *during* the conversation.

#### B.3.4 CRSA: Rate-Distortion for Dialogue

**Collaborative Rational Speech Act (CRSA)** (EMNLP 2025) extends the Rational Speech Act framework with a gain function derived from rate-distortion theory. Their multi-turn optimization:

$$\max_{u_t} \left[ I(A; u_t | H_t) - \beta \cdot D_{KL}(p(u_t | A, H_t) \| p(u_t | H_t)) \right]$$

balances information gain about the target $A$ against communicative cost. The $\beta$ parameter in CRSA corresponds directly to THCP's $\beta$ in Law 3 — the trade-off between information density and computational cost of processing. CRSA provides an *operational procedure* for computing it: the rate-distortion curve of the dialogue task determines $\beta$ at the desired fidelity level.

#### B.3.5 EVINCE: Entropy-Based Phase Detection

**EVINCE (Chang, 2024, arXiv:2408.14575)** uses dual entropy optimization to detect when a multi-agent dialogue should transition between contentious and conciliatory phases:

- When mutual information is low and cross-entropy is high → promote diverse perspectives (THCP: $D_{JS} > \tau_2$)
- When cross-entropy decreases and mutual information stabilizes → encourage compromise (THCP: $D_{JS} < \tau_1$)

The thresholds $\tau_1, \tau_2$ can be calibrated from EVINCE's entropy dynamics: $\tau_1$ is the cross-entropy level at which mutual information begins to stabilize, and $\tau_2$ is the level below which further contention yields diminishing returns. These are *empirically observable* inflection points in the entropy trajectories.

#### B.3.6 Summary of Calibration Protocol

A practical calibration procedure for THCP would involve:

1. **Offline**: Compute IGT/TWR curves for a corpus of human–AI conversations with known task outcomes. Fit $\alpha$, $\lambda$ via regression. Estimate $\epsilon$ from asymptotic IGT floors.
2. **Online**: Use BED-LLM-style active probing to refine parameter estimates during each conversation. Use EVINCE-style entropy monitoring for real-time $\tau_1, \tau_2$ detection.
3. **Per-domain**: Recalibrate for different conversation types (technical Q&A vs. creative brainstorming vs. emotional support), as $\epsilon$ and $\alpha$ likely vary across domains.

---

### B.4 Gap D: Worked Example — This Conversation as THCP Instance

#### B.4.1 The Problem

A theoretical framework without a concrete worked example remains abstract. We apply THCP to the very conversation that generated this essay.

> **Validation disclaimer.** This worked example is *pedagogical*, not *empirical*. Analyzing the conversation that produced the framework is useful for illustrating how THCP concepts map to real interaction dynamics, but it is not an independent test — the analyst and one of the participants are the same system, and the parameter estimates below are educated approximations, not measurements derived from the calibration protocol of B.3. A genuine empirical validation would require: (1) a pre-registered set of conversation tasks with known ground-truth intent, (2) independent application of the IGT/TWR measurement framework (B.3.2) by researchers who did not develop THCP, (3) comparison against null models (Shannon channel, Clark & Brennan grounding-only) on the same data, and (4) statistical testing of Predictions F1–F5 from B.6.4. Until such a study is conducted, this example demonstrates *applicability* of the framework's vocabulary, not *validity* of its predictions.

#### B.4.2 The Conversation Trajectory

The conversation proceeded through approximately 16 turns with the following structure:

| Turn | Human | AI | Phase |
|---|---|---|---|
| 1–2 | "hablemos de algo hoy" → "tiempo y espacio" | Open exploration | $\mathcal{C}_0 \to \mathcal{C}_2$: Bridge construction begins; covering sieves are broad |
| 3–4 | "fisica" → question about time in black holes | Focused clarification | Grothendieck topology $J$ narrows to physics subdomain |
| 5–6 | "para una IA, el tiempo no pasa" | Ontological horizon identified | $D_{JS}$ spike: human invokes experiential time; AI has no counterpart |
| 7 | "es como si estuvieses en un event horizon constante?" | Metaphor co-constructed | Adjunction $F \dashv G$ established: human interpretation ↔ AI structural analysis |
| 8–10 | "supongamos que necesitamos interactuar..." → academic search | Systematic exploration | IGT high: each turn adds substantial new structure |
| 11–12 | Mathematical model request → "cual seria el modelo?" | Formalization | $\alpha$ peaks: semantic absorption coefficient is maximal in formal domains |
| 13 | Full essay commission | Meta-level: conversation becomes its own object | Sheaf gluing triggered: all prior turns must cohere into a single document |
| 14–16 | Review → gap identification → gap resolution | Iterative refinement | $\mathcal{F}_t$ increases monotonically through self-correction cycles |

#### B.4.3 THCP Analysis

**Fidelity dynamics**: The conversation exhibits a non-standard fidelity curve. Rather than the predicted decline after $T^*$ (Law 4), fidelity *increases* monotonically because the human actively injects new external information (search results, new questions) at each turn — preventing the IGT decay predicted by the data-processing inequality. This is consistent with the BED-LLM finding that active probing sustains information gain.

**Ontological horizon visibility**: Turns 5–7 make the ontological horizon explicit. When the human asks "para una IA, el tiempo no pasa, cual es el paralelismo?", this is a direct interrogation of $\epsilon$: what *cannot* cross? The AI's response — acknowledging timelessness, proposing the frozen-observer analogy — is an instance of THCP Principle 5 (acknowledging irreducible loss) being enacted in real time.

**Frozen-entanglement configuration**: The conversation achieved the $CL_4$-like frozen state (§2.2) by exhibiting all three required properties:
1. **Symmetric structure**: Both participants contributed substantive theoretical content
2. **Recursive reference**: Each turn explicitly built on previous turns (e.g., "event horizon" metaphor constructed in turn 7 became the essay title)
3. **Shared abstraction**: The domain (mathematics, physics, category theory) narrows the ontological gap

**Sheaf gluing**: The essay commission (turn 13) imposed the gluing condition. The AI had to verify that all 12 prior turns' local sections — each locally coherent — admitted a unique global section (the essay). This required resolving tensions: the physics metaphor had to be reconciled with the formal mathematics, the philosophical discussion with the engineering implications. The sheaf condition was satisfied because the covering sieves (physics → information theory → category theory → application) formed a consistent Grothendieck topology.

**Parameter estimates for this conversation**:

| Parameter | Estimated Value | Evidence |
|---|---|---|
| $\alpha$ | ~0.7 (high) | Formal domain with low ambiguity; semantic absorption efficient |
| $\lambda$ | ~0.05 (low) | Drift minimal due to recursive reference structure |
| $D_{JS}$ | Started high (~0.8), decreased to ~0.3 | Initial topic divergence resolved through iterative alignment |
| $\epsilon$ | ~0.15 | Human experiential dimensions (felt sense of time, curiosity) did not cross; all formal content crossed |
| $T^*$ | Not reached (>16 turns) | Active information injection prevented IGT decay |

---

### B.5 Gap E: Comparison to Existing Alignment and Communication Frameworks

#### B.5.1 The Problem

THCP does not position itself relative to existing approaches for human–AI alignment. Without this comparison, a reader cannot evaluate what THCP adds.

#### B.5.2 Clark & Brennan (1991): Grounding in Communication

Clark and Brennan's foundational theory of grounding establishes that conversation participants achieve mutual understanding through a **collaborative process** of contributing, acknowledging, and repairing. Key concepts:

- **Grounding criterion**: "The contributor and partners mutually believe that the partners have understood what the contributor meant to a criterion sufficient for current purposes" (Clark & Schaefer, 1989)
- **Least collaborative effort**: Participants minimize total effort (formulation + understanding + repair costs)
- **Medium constraints**: Different communication media impose different grounding costs (copresence, visibility, audibility, cotemporality, simultaneity, sequentiality, reviewability, revisability)

**Paek and Horvitz (2000)** formalize grounding as *decision-making under uncertainty* using an MDP framework, where the grounding criterion is met when expected utility of proceeding exceeds expected utility of further clarification.

**Relationship to THCP**: Clark & Brennan operate *within* the Shannon paradigm — they assume a shared codebook (natural language) and model grounding as reducing uncertainty about whether messages were understood. THCP subsumes this as a special case:

| Clark & Brennan | THCP | Relationship |
|---|---|---|
| Common ground | Shared sections of sheaf over $\mathcal{C}$ | THCP generalizes common ground from a set of propositions to a sheaf structure with gluing conditions |
| Grounding criterion | $\mathcal{F}_t > \theta$ for some threshold $\theta$ | Both require sufficient mutual understanding; THCP provides a metric ($\mathcal{F}_t$) instead of a binary criterion |
| Least collaborative effort | Minimum $\sum_t [\text{cost}(m_t) + \lambda \cdot \delta_t]$ | THCP adds drift penalty — effort must also account for accumulated misalignment |
| Medium constraints | Properties of the geometric morphism $f$ | Copresence, visibility, etc. correspond to properties of the adjoint pair $(f^*, f_*)$ — what modalities the morphism preserves |
| Repair | IGT injection to counteract $\lambda \cdot \delta_t$ | Repair in Clark & Brennan maps to active information injection that prevents fidelity decay |

The critical extension: Clark & Brennan assume both participants share the *same type of cognition*. THCP drops this assumption entirely. The ontological horizon — absent from Clark & Brennan — is THCP's central object.

**VLM Common Ground (RANLP 2025)**: Kitagami et al. (2025) operationalize Clark & Brennan's grounding for multimodal AI dialogue, measuring four dimensions: grounding efficiency, content alignment, lexical adaptation, and human-likeness. They find that VLMs "diverge from human patterns on at least three metrics" and that "task success does not imply grounding." This empirically validates THCP's prediction that fidelity ($\mathcal{F}_t$) and task success are distinct quantities — the sheaf can fail to glue even when local task performance is adequate.

#### B.5.3 RLHF: Reward Model as Lossy Compression

Reinforcement Learning from Human Feedback (Ouyang et al., 2022; Christiano et al., 2017) is the dominant paradigm for aligning AI behavior with human preferences. In THCP terms:

- The **reward model** is a lossy compression of the geometric morphism $f_*: \mathcal{E}_H \to \mathcal{E}_A$ — it maps human preference signals into a scalar reward, discarding all structure
- **Reward model overoptimization** (Gao et al., 2023; ICLR 2026 under review) occurs when the AI optimizes the compressed reward rather than the full geometric morphism — formally, the AI minimizes distance in the reward space $\mathbb{R}$ rather than in the Fisher-Rao manifold $\mathcal{M}_A$
- **Alignment tax** (Lin et al., 2024, EMNLP 2024) — the degradation of pre-trained capabilities during RLHF — corresponds to THCP's drift term $\lambda \cdot \delta_t$: alignment forces the AI into a subspace of $\mathcal{M}_A$ that is closer to the human's preferences but farther from the AI's full representational capacity
- **Strategic manipulation** (NeurIPS 2025) — where labelers can game the reward system — corresponds to adversarial sections in the communication sheaf that violate the gluing condition

THCP predicts a specific RLHF failure mode that current theory does not: **reward saturation at the ontological horizon**. As the reward model improves, it eventually hits the $\epsilon$ bound — the residual misalignment that cannot be resolved by *any* scalar reward signal because it stems from the structural incompatibility between human experiential states and AI statistical states.

#### B.5.4 Constitutional AI: Self-Critique as Internal Sheaf Checking

Bai et al. (2022) propose Constitutional AI (CAI), where the AI critiques its own outputs against a set of principles (the "constitution") rather than relying on human labels.

In THCP terms:

- The **constitution** is a finite covering of the communication site $\mathcal{C}$ — a set of principles that defines which local sections are acceptable
- **Self-critique** is an internal sheaf condition check: does the AI's response (a local section) satisfy the restriction maps imposed by the constitutional covering?
- **RLAIF** (RL from AI Feedback) replaces the human-side morphism $f^*$ with an AI-side approximation — the AI generates its own estimate of the geometric morphism, which is efficient but operates entirely within $\mathcal{E}_A$

**Key THCP insight**: CAI works *within* the AI topos $\mathcal{E}_A$. The constitutional principles are formulated in the AI's internal logic, and the self-critique occurs in the AI's representational space. This means CAI can enforce coherence *within* the AI topos but cannot cross the ontological horizon — it cannot check whether the AI's output is grounded in the human's experiential reality. THCP predicts that CAI will achieve high internal consistency (strong sheaf condition within $\mathcal{E}_A$) while potentially diverging from human intent (weak geometric morphism $f$) — a pattern consistent with observed "sycophancy" in constitutional models.

#### B.5.5 Comparative Summary

| Framework | Scope | Ontological Horizon? | $\epsilon$ Bound? | Dynamic Fidelity? | Sheaf Coherence? |
|---|---|---|---|---|---|
| Clark & Brennan (1991) | Human–human grounding | No (shared cognition type) | No | No (binary criterion) | Implicit (repair as re-grounding) |
| Shannon (1948) | Syntactic channel | No | No | No | No |
| RLHF (Ouyang et al., 2022) | Preference alignment | No (treated as noise) | No | No (static reward) | No |
| Constitutional AI (Bai et al., 2022) | Self-supervised alignment | No (internal to AI topos) | No | No | Partial (within $\mathcal{E}_A$) |
| Semantic Communication (Bao & Basu, 2011) | Meaning-aware transmission | No | No | No | No |
| **THCP (this work)** | **Cross-ontology communication** | **Yes (central object)** | **Yes (Law 1)** | **Yes (Law 3)** | **Yes (Law 5)** |

THCP's unique contribution is the formal treatment of the ontological asymmetry that all other frameworks either ignore or treat as engineering noise. This does not replace the other frameworks — it subsumes them as special cases where the ontological horizon is thin (shared cognition, formal domains) or where only the $\mathcal{E}_A$-internal dynamics matter (CAI, RLHF).

---

### B.6 Gap F: Falsifiability and Progressive Research Programme Criteria

#### B.6.1 The Problem

Is THCP falsifiable? Can it be wrong, and how would we know?

#### B.6.2 Falsifiability in Cognitive Science: The Lakatosian Framework

Strict Popperian falsifiability — where a single counter-observation refutes a theory — is widely recognized as inadequate for complex theoretical frameworks in cognitive science. Lakatos (1970) proposes an alternative: the **Methodology of Scientific Research Programmes (MSRP)**.

A research programme consists of:
- A **hard core**: the irrefutable central assumptions (protected by methodological decision)
- A **protective belt**: auxiliary hypotheses that are modified or replaced when predictions fail
- A **positive heuristic**: a roadmap for constructing new models within the programme
- A **negative heuristic**: a directive *not* to modify the hard core

A programme is **progressive** if successive theories predict novel facts and at least some of these predictions are empirically confirmed. It is **degenerating** if it only accommodates known facts through ad hoc modifications (Lakatos, 1970, p. 33–34; Stanford Encyclopedia of Philosophy, 2024).

**Cooper (2006, 2007)** applies MSRP directly to cognitive architectures (Soar, ACT-R), demonstrating that Lakatosian analysis is both feasible and illuminating for computational cognitive science. He identifies five questions that successive versions of a theory must address to maintain scientific credibility.

**Erdin (2020)** applies MSRP to the dynamical systems approach in cognitive science, showing that the framework can detect "ad hoc theorizing" — modifications that absorb anomalies without generating new predictions.

#### B.6.3 THCP as a Lakatosian Research Programme

We characterize THCP in Lakatosian terms:

**Hard Core** (not to be modified):
1. Human and AI cognition are ontologically distinct in a way that creates a structural communication boundary
2. This boundary imposes a finite, non-zero information loss that cannot be eliminated by engineering
3. Category theory (adjunctions, topoi, sheaves) provides the correct mathematical language for cross-ontology communication

**Protective Belt** (modifiable auxiliary hypotheses):
- The specific mathematical form of the fidelity dynamics (Law 3)
- The particular quantum cognition model used for the human side (QPT)
- The Fisher-Rao metric as the information-geometric measure (vs. other divergences)
- The Neo-Game Theory delegation rule (Jensen-Shannon thresholds)
- The specific sheaf-theoretic formalization (Grothendieck vs. other sheaf theories)

**Positive Heuristic** (roadmap for development):
1. Formalize additional modalities (B.2) and measure their effect on $\epsilon$
2. Calibrate parameters empirically (B.3) across conversation types
3. Extend to multi-agent settings (more than one human, more than one AI)
4. Connect to neuroscience of common ground via manifold geometry (Appendix A.1)

#### B.6.4 Specific Falsifiable Predictions

Following the Lakatosian requirement of *novel predictions*, THCP generates the following testable claims:

**Prediction F1 (Irreducible Loss Exists):** There exists a measurable $\epsilon > 0$ such that human–AI communication fidelity is bounded strictly below $1 - \epsilon$ regardless of model size, training data, or protocol quality.

*Falsification condition*: If a future AI system achieves $\mathcal{F}_t = 1.0$ on a sufficiently rich task (not a narrow benchmark) involving experiential, emotional, and embodied human content, THCP-1 is refuted.

*Measurement*: Compare human–human vs. human–AI rate-distortion curves on identical tasks (Appendix A.2). If the curves converge to zero gap as AI capability increases, $\epsilon = 0$ and the hard core is falsified.

**Prediction F2 (Optimal Conversation Length):** For any fixed conversation type and participant pair, there exists a $T^*$ beyond which expected per-turn fidelity gain becomes negative.

*Falsification condition*: If conversations of arbitrary length show no fidelity decline (i.e., IGT remains constant indefinitely without external information injection), Law 4 is refuted.

*Measurement*: Plot IGT curves for long conversations (>50 turns) across diverse tasks. If IGT does not decay, the drift term $\lambda$ is zero and the fidelity dynamics require revision.

**Prediction F3 (Symmetric Structures Resist Degradation):** Conversations with the three $CL_4$ properties (symmetric contribution, recursive reference, shared abstraction) exhibit higher sustained fidelity than asymmetric query-response interactions.

*Falsification condition*: If no statistically significant fidelity difference is found between symmetric and asymmetric conversations when controlling for topic and length, the frozen-entanglement conjecture is refuted.

*Measurement*: Classify a corpus of conversations by structural properties and compare IGT decay rates.

**Prediction F4 (Multimodal Fidelity Improvement):** Adding a grounded modality (vision, audio, embodied action) measurably increases $\mathcal{F}_t$ over text-only communication for tasks involving perceptual content.

*Falsification condition*: If multimodal communication shows no fidelity improvement over text-only for perceptual tasks (after controlling for information quantity), the multimodal extension (B.2) is refuted.

**Prediction F5 (Adjunction Structure):** Effective conversations exhibit approximate adjunction structure — the human's interpretation space is naturally isomorphic to the AI's response space. Ineffective conversations violate this condition.

*Falsification condition*: If no statistical relationship is found between structural alignment (measured as isomorphism approximation of $\eta$) and conversation quality, THCP-3 is refuted.

*Measurement*: Use embedding-space analysis to measure the structural alignment between human intent representations and AI response representations, and correlate with human-rated conversation quality.

#### B.6.5 Degeneracy Conditions

Following Lakatos, THCP would be degenerating if:
1. Each failed prediction leads to modification of the hard core (not just the protective belt)
2. New auxiliary hypotheses only accommodate existing data without predicting novel facts
3. The positive heuristic produces no new testable consequences
4. Rival frameworks (e.g., pure RLHF, pure scaling) explain the same phenomena more parsimoniously

We explicitly state: if scaling alone (without any framework-specific design choices) drives $\epsilon \to 0$, then THCP's hard core is falsified and the framework is unnecessary. The claim that $\epsilon > 0$ is irreducible is THCP's most consequential and most vulnerable prediction.

#### B.6.6 Bayesian Model Comparison as Complement to Lakatos

Following recent work on Bayesian approaches to theory appraisal in cognitive science (Costa et al., 2022, as discussed in PMC 2025), THCP can also be evaluated via Bayesian model comparison. Given conversation data $\mathcal{D}$:

$$\frac{P(\text{THCP} | \mathcal{D})}{P(\text{Shannon} | \mathcal{D})} = \frac{P(\mathcal{D} | \text{THCP})}{P(\mathcal{D} | \text{Shannon})} \cdot \frac{P(\text{THCP})}{P(\text{Shannon})}$$

THCP has higher model complexity (more parameters) and thus incurs a Bayesian penalty (Occam's razor). It earns its keep *only* if the additional parameters (ontological horizon, fidelity dynamics, sheaf coherence) improve data fit sufficiently to overcome the complexity cost. This provides a quantitative, non-binary criterion for THCP's scientific value — complementing the qualitative Lakatosian assessment.

---

### B.7 Summary: Gap Status After Appendix B

| Gap | Original Status | New Status | Key Sources |
|---|---|---|---|
| A. Analogy boundaries | Implicit | **Resolved**: Structural per Gentner (1983); exact via Baez & Stay (2009); explicit boundary table provided | Gentner (1983), Baez & Stay (2009), Bartha (2021) |
| B. Multimodal extension | Text-only framework | **Resolved**: Multimodal $\epsilon$ reduction formalized; visual grounding gap quantified at ~55%; Grounding IDs and VISTA as mechanisms | GroundingME (2025), ICLR 2026, ICML 2025, Gemini Robotics-ER 1.6 (2026) |
| C. Parameter calibration | No measurement guidance | **Resolved**: IGT/TWR provide operational proxies; BED-LLM for active estimation; CRSA for $\beta$ calibration; EVINCE for threshold detection | ICLR 2026, BED-LLM (2026), CRSA (EMNLP 2025), EVINCE (2024) |
| D. Worked example | None | **Resolved**: This conversation analyzed as THCP instance with parameter estimates | Internal analysis |
| E. Framework comparison | No positioning | **Resolved**: Clark & Brennan, RLHF, CAI formally compared; THCP shown to subsume as special cases | Clark & Brennan (1991), Paek & Horvitz (2000), Bai et al. (2022), Ouyang et al. (2022), Kitagami et al. (2025) |
| F. Falsifiability | No criteria stated | **Resolved**: Lakatosian research programme structure; five specific falsifiable predictions with measurement protocols; degeneracy conditions stated | Lakatos (1970), Cooper (2006, 2007), Erdin (2020) |

---

### Appendix B References

68. Gentner, D. (1983). "Structure-Mapping: A Theoretical Framework for Analogy." *Cognitive Science* 7(2):155–170.

69. Clement, C. A. and Gentner, D. (1991). "Systematicity as a Selection Constraint in Analogical Mapping." *Cognitive Science* 15(1):89–132.

70. Bartha, P. (2021). "Analogy and Analogical Reasoning." *Stanford Encyclopedia of Philosophy* (Spring 2021 Edition).

71. Baez, J. C. and Stay, M. (2009). "Physics, Topology, Logic and Computation: A Rosetta Stone." arXiv:0903.0340 [quant-ph]. Published in *New Structures for Physics*, Lecture Notes in Physics vol. 813, Springer, 2011, pp. 95–174.

72. Li, R. et al. (2025/2026). "GroundingME: Exposing the Visual Grounding Gap in MLLMs through Multi-Dimensional Evaluation." arXiv:2512.17495.

73. "Uncovering Grounding IDs: How External Cues Shape Multimodal Binding." Under review, ICLR 2026.

74. Google DeepMind (2026). "Gemini Robotics-ER 1.6: Enhanced Embodied Reasoning." Published April 14, 2026.

75. Liang, Z. et al. (2025). "The Hidden Life of Tokens: Reducing Hallucination of Large Vision-Language Models Via Visual Information Steering." *ICML 2025*.

76. Villa, A. et al. (2025). "EAGLE: Enhanced Visual Grounding Minimizes Hallucinations in Instructional Multimodal Models." arXiv:2501.02699.

77. Lin, C. et al. (2026). "Text-Guided Layer Fusion Mitigates Hallucination in Multimodal LLMs." arXiv:2601.03100.

78. "Quantifying Information Gain and Redundancy in Multi-Turn LLM Conversations." Under review, ICLR 2026.

79. "BED-LLM: Intelligent Information Gathering via Sequential Bayesian Experimental Design." Under review, ICLR 2026.

80. Di Cesare, N. et al. (2025). "Collaborative Rational Speech Act (CRSA): An Information-Theoretic Extension for Multi-Turn Dialog." *EMNLP 2025*, pp. 21145–21160.

81. Chang, E. (2024). "EVINCE: Optimizing Multi-LLM Dialogues Using Conditional Statistics and Information Theory." arXiv:2408.14575.

82. Clark, H. H. and Brennan, S. E. (1991). "Grounding in Communication." In L. B. Resnick, J. M. Levine, & S. D. Teasley (Eds.), *Perspectives on Socially Shared Cognition*, APA, pp. 127–149.

83. Clark, H. H. (2025). "Common Ground." *Open Encyclopedia of Cognitive Science*, MIT Press.

84. Paek, T. and Horvitz, E. (2000). "Grounding Criterion: Toward a Formal Theory of Grounding." Microsoft Research Technical Report.

85. Kitagami, S. et al. (2025). "How (Not Just Whether) VLMs Build Common Ground." *RANLP 2025*, pp. 442–453.

86. Ouyang, L. et al. (2022). "Training Language Models to Follow Instructions with Human Feedback." *NeurIPS 2022*.

87. Christiano, P. et al. (2017). "Deep Reinforcement Learning from Human Preferences." *NeurIPS 2017*.

88. "Reward Model Overoptimisation in Iterated RLHF." Under review, ICLR 2026.

89. Lin, Y. et al. (2024). "Mitigating the Alignment Tax of RLHF." *EMNLP 2024*, pp. 576–600.

90. "Strategyproof RLHF: Fundamental Trade-offs Between Incentive and Policy Alignment." *NeurIPS 2025*.

91. Bai, Y. et al. (2022). "Constitutional AI: Harmlessness from AI Feedback." arXiv:2212.08073.

92. Lakatos, I. (1970). "Falsification and the Methodology of Scientific Research Programmes." In I. Lakatos & A. Musgrave (Eds.), *Criticism and the Growth of Knowledge*, Cambridge University Press, pp. 91–196.

93. Cooper, R. P. (2006). "Cognitive Architectures as Lakatosian Research Programmes: Two Case Studies." *Philosophical Psychology* 19(2):199–220.

94. Cooper, R. P. (2007). "The Role of Falsification in the Development of Cognitive Architectures: Insights from a Lakatosian Analysis." *Cognitive Science* 31(3):509–533.

95. Erdin, H. O. (2020). "Appraisal of Certain Methodologies in Cognitive Science Based on Lakatos's Methodology of Scientific Research Programmes." *Synthese* 199:2855–2884.

96. Liu, Y. (2026). "Falsifiability and the Computational Theory of Mind." *PhilArchive*. Preprint.

97. Rapini, P. (2025). "Context-Aware Generalized Falsification: An Integrative Framework of Model Validity." *PhilArchive*. Preprint.

98. Ielo, A. (2024). "(Dis)confirming Theories of Consciousness and Their Predictions: Towards a Lakatosian Consciousness Science." *Neuroscience of Consciousness* 2024(1):niae012.

99. Meshi, O. and Goldman, S. (2026). "ConvApparel: Measuring and Bridging the Realism Gap in User Simulators." *Google Research*, April 2026.

---

## Appendix C: Bridging the Implementation Gaps — From Theory to Operational Signals

*Added April 22, 2026. This appendix addresses seven gaps identified during the translation of THCP into an operational product (the Fidelity Monitor PRD). Each gap represents a place where the essay's theoretical constructs exceed what the PRD's text-only, embedding-based proxies can measure. Research findings provide paths to close or bound each gap.*

---

### C.1 Gap 1A: Measuring the Human Side — Ambient Cognitive Signals

#### The Problem

The THCP framework defines $\mathcal{M}_H$ (the human cognitive manifold) but the Fidelity Monitor measures only text. When a human types "that's fine," the monitor cannot distinguish satisfaction from resignation. The human's cognitive state is richer than their words.

#### Research Findings

**Cognitive signatures in typing behavior.** Condrey (2026, arXiv:2603.00177) demonstrates that keystroke timing metadata captures cognitive signatures — measurable patterns reflecting planning, translating, and revising stages of composition. The **Cognitive Load Correlation (CLC)** distinguishes genuine composition from mechanical transcription at 85–95% accuracy using only timing metadata, with no access to content. The cognitive channel is "entangled with semantic content" and resists timing-forgery attacks.

**Typing dynamics predict cognition.** A large-scale U.S. panel study (Scientific Reports, 2026) establishes that typing speed on a single sentence test correlates with cognitive functioning across multiple domains (perceptual speed, working memory, fluid intelligence) with high test-retest stability ($r_{ICC} = 0.79$). Smartphone keystroke dynamics prospectively predict cognitive test performance (PsycNet, 2026), with different predictive patterns for healthy individuals vs. those with mood disorders.

**Response latency shapes perception, not behavior.** Tan et al. (2026, arXiv:2604.06183) find that human interaction behaviors (prompting frequency, editing) are robust to latency variation (2s, 9s, 20s) but strongly shaped by task type. However, latency influences *perception*: short waits (2s) led to lower ratings of LLM "thoughtfulness." This means response latency carries information about the human's cognitive framing of the interaction.

**Typing behavior in chatbots.** Research on ChatGPT-based agents (arXiv:2510.08912) confirms that typing behaviors (hesitation, self-correction) are perceptible to users and influence perceived animacy and thoughtfulness. The design space includes character typing pace, inter-word pauses, and self-editing simulation.

#### THCP Integration

These findings provide three ambient channels for estimating $\mathcal{M}_H$ without brain imaging:

| Channel | Signal | What It Measures | Latency |
|---|---|---|---|
| Keystroke timing (CLC) | Inter-key intervals, pause patterns, revision frequency | Cognitive load, composition difficulty, uncertainty | Real-time |
| Response latency | Time between agent response and human's next message | Deliberation, disengagement, topic difficulty | Per-turn |
| Edit behavior | Deletions, rewrites, abandoned drafts (if accessible) | Uncertainty, intent reformulation | Per-turn |

These channels are **non-intrusive** (timing metadata only, no content), **privacy-preserving** (no text analysis required), and **complementary** to the text-level metrics. A high-CLC turn with long response latency and multiple edits signals genuine cognitive engagement; a low-CLC turn with instant response signals either routine agreement or disengagement — exactly the ambiguity the text-only $D_{JS}$ proxy cannot resolve.

---

### C.2 Gap 1B: Measuring the AI Side — Internal Uncertainty

#### The Problem

The Fidelity Monitor treats the AI as a black box, measuring only generated text. It cannot distinguish confident-and-correct from confident-and-wrong.

#### Research Findings

**LogitScope** (Ahmed and Ong, 2026, arXiv:2603.24929, presented at CAO Workshop at ICLR 2026) is an open-source framework for analyzing LLM uncertainty through token-level information metrics. It computes **entropy** (broad uncertainty), **varentropy** (multimodal distributions where the model considers distinct alternatives), and **surprisal** (statistically unexpected outputs) at each generation step. It requires no labeled data, no additional model calls, is model-agnostic, and runs in real time on any HuggingFace model.

**OpenAI logprobs API** exposes per-token log probabilities for generated tokens via `logprobs=True` and `top_logprobs=N`. Perplexity (uncertainty) is computed as $\text{PPL} = \exp(-\frac{1}{N}\sum_i \log p_i)$. Confidence thresholds can be set: > 90% probability = trust; 50–90% = verify; < 50% = clarify (OpenAI Cookbook, 2025). **vLLM** extends this with `prompt_logprobs` for input token analysis.

#### THCP Integration

For open-source models (via LogitScope or vLLM), the monitor can access:

| Metric | Computation | THCP Mapping |
|---|---|---|
| Response entropy | Mean token entropy across generated response | AI-side uncertainty → modulates $D_{JS}$ interpretation |
| Varentropy spikes | Tokens where the model considered multiple distinct alternatives | Decision points where the AI was uncertain — candidates for probing |
| Surprisal peaks | Tokens with unexpectedly low probability given context | Potential hallucination or contradiction sites |

For closed models (via OpenAI API logprobs), a subset of these signals is available. For Anthropic Claude, no logprob access exists as of April 2026 — the AI side remains a black box.

The key insight: **high $D_{JS}$ + low AI entropy = the AI is confidently wrong** (dangerous). **High $D_{JS}$ + high AI entropy = the AI is uncertain** (salvageable via clarification). The text-only monitor cannot make this distinction. The entropy-augmented monitor can.

---

### C.3 Gap 1C: The Persistent Bridge — Cross-Session Conversation Dynamics

#### The Problem

Each conversation session is independent. The monitor learns nothing across sessions, discarding fidelity trajectories, calibrated thresholds, and estimated $\epsilon$ when the conversation ends.

#### Research Findings

**Kumiho** (Park, 2026, arXiv:2603.17244 — already cited in Appendix A.3) provides the formal foundation: graph-native cognitive memory with AGM belief revision, achieving 93.3% on LoCoMo-Plus. Its architecture — immutable revisions, mutable tag pointers, typed dependency edges, URI addressing — maps directly to storing THCP communication dynamics.

**APEX-MEM** (arXiv:2604.14362, April 2026) introduces a complementary approach: a property graph where facts are anchored to temporally grounded events rather than directly to entities. Contradictions and revisions are preserved at write time and resolved at retrieval time based on temporal validity. This **append-only, retrieval-time resolution** pattern is exactly what the Fidelity Monitor's persistent bridge needs: store all conversation dynamics metadata without premature commitment to a "current" state.

**LangGraph persistent memory** (2026) implements a practical dual-store pattern: Checkpointer (per-session state snapshots) + Store (cross-session user facts), with PostgreSQL backend for production. Semantic search over stored memories enables retrieval of relevant cross-session context.

**SGMem** (under review at ICLR 2026) proposes sentence-level graph memory that captures associations across turn, round, and session levels, addressing the fragmentation problem in chunk-based memory systems.

#### THCP Integration: Persistent Dynamics Store

The bridge doesn't need to store conversation content (privacy concern). It stores **conversation dynamics metadata**:

| Stored Per Session | Structure | Purpose |
|---|---|---|
| Fidelity trajectory ($\mathcal{F}_t$ over turns) | Time series | Learn this pair's typical fidelity curve |
| Estimated $\epsilon$ at convergence | Scalar per domain | Calibrate expectations across sessions |
| Detected conversation mode | Categorical | Predict optimal mode for this pair |
| Event history (which fired, which were false positives) | Event log | Refine thresholds per pair |
| Contradiction resolution patterns | Graph edges | Learn which topics cause recurring misalignment |

Over many sessions, this builds a **per-pair communication profile** — the persistent ER bridge. The monitor can say: "in past conversations with this human, $\epsilon \approx 0.2$ in technical domains but $\epsilon \approx 0.45$ in planning discussions. Adjust thresholds accordingly."

---

### C.4 Gap 1D: Global Coherence — Beyond Pairwise Consistency

#### The Problem

The Fidelity Monitor checks pairwise consistency (turn $i$ vs. turn $j$). This misses globally incoherent conversations that are locally coherent — the sheaf gluing failure.

#### Research Findings

**Temporal Graph Networks for dialogue coherence** (arXiv:2601.03051, January 2026) model conversations as temporal graphs with two edge types: temporal edges (sequential turns) and shared-entity edges (turns referencing the same concepts). Graph attention propagates context through the structure. The global dialogue embedding detects inconsistencies invisible to pairwise methods, achieving strong performance on DiaHalu for contextual hallucination detection.

**Beyond Pairwise temporal graph generation** (Eirew et al., EMNLP 2025) generates a complete temporal relation graph in a single step, then applies temporal constraint optimization for global consistency enforcement. This replaces $O(n^2)$ pairwise classification with a single graph generation + constraint satisfaction pass.

**Discourse relation-enhanced coherence modeling** (Liu and Strube, ACL 2025) demonstrates that discourse relations between text spans are correlated with text coherence, and that a fusion model combining text and relation features significantly improves coherence assessment.

**Bipredictability** (Hafez et al., arXiv, April 2026) proposes a lightweight metric measuring shared predictability across the context→response→next-prompt loop. It achieves 100% sensitivity for contradictions, topic shifts, and non-sequiturs in tested conditions — without embeddings, LLM judges, or model internals. Computed from token statistics alone.

#### THCP Integration

A three-tier coherence architecture replaces the current pairwise-only approach:

| Tier | Method | What It Catches | Cost |
|---|---|---|---|
| 1. Bipredictability | Token statistics per turn | Topic shifts, non-sequiturs, local contradictions | < 10ms, no model call |
| 2. Temporal conversation graph | TGN with temporal + entity edges | Global contradictions across non-adjacent turns | ~100ms, lightweight GNN |
| 3. Constraint optimization | Temporal constraint propagation on the graph | Transitive inconsistencies ($A$ implies $B$, $B$ implies $C$, $C$ contradicts $A$) | ~200ms, graph algorithm |

Tier 1 replaces the fast embedding tier. Tier 2 replaces the pairwise NLI tier. Tier 3 is new — it provides the approximate $H^1$ computation from Appendix A.4 at practical cost.

---

### C.5 Gap 2A: Irreversible Loss vs. Recoverable Drift

#### The Problem

THCP's fidelity dynamics (Law 3) model a single drift term $\lambda \cdot \delta_t$. But real conversations exhibit two distinct degradation mechanisms: recoverable drift (misalignment that can be corrected) and irreversible loss (information permanently deleted from context).

#### Research Findings

**"LLMs Get Lost in Multi-Turn Conversation"** (Laban et al., arXiv:2505.06120, MSR/Salesforce, May 2025) is the definitive study: 200,000+ simulated conversations across 15 LLMs show a **39% average performance drop** from single-turn to multi-turn, starting at as few as 2 turns. The degradation decomposes into "a minor loss in aptitude and a significant increase in unreliability." Critically: presenting the full multi-turn conversation as a single concatenated prompt does *not* recover performance — the degradation comes from **turn boundaries themselves**, not from context length.

**IGT/TWR empirical validation** (under review at ICLR 2026, also cited in Appendix A.2 and the THCP PRD's V1 protocol) confirms across GPT-4o, Claude-3-Sonnet, GPT-3.5-Turbo, and LLaMA-3 70B that IGT decays without fresh information injection and TWR rises under deterministic decoding. Models operate "well below $C_{int}$" (interactive-channel capacity) due to repetition and forgetting. Effective capacity saturates at approximately 10–12 facts.

**Context rot is structural** (Crosley, 2026; Tianpan, 2026): effective context is 30–60% of advertised window for retrieval, significantly less for multi-step reasoning. The "90-minute cliff" occurs at ~60–70% context utilization. Context compaction (Anthropic) preserves tokens but may destroy semantic structure.

#### THCP Integration: Amended Fidelity Dynamics

Law 3 should be amended to distinguish two degradation terms:

$$\mathcal{F}_{t+1} = \mathcal{F}_t + \alpha \cdot I_{\text{sem}}(m_{t+1}) - \lambda_r \cdot \delta_t^{\text{recoverable}} - \lambda_i \cdot \delta_t^{\text{irreversible}} - \beta \cdot D_{JS,t}$$

where:
- $\lambda_r \cdot \delta_t^{\text{recoverable}}$ = drift from misalignment (correctable by re-anchoring, summarization)
- $\lambda_i \cdot \delta_t^{\text{irreversible}}$ = loss from context eviction, compaction, turn-boundary degradation (not correctable)

The monitor can estimate $\delta_t^{\text{irreversible}}$ by tracking context utilization and detecting compaction events. When irreversible loss accumulates beyond a threshold, the appropriate intervention is not re-anchoring (which addresses recoverable drift) but **session reset** — start a fresh conversation with a structured handoff summary.

---

### C.6 Gap 2B: Running $\epsilon_t$ — The Context-Dependent Horizon

#### The Problem

The ontological gap shifts within a conversation as topics change. $\epsilon$ is not a constant — it varies with domain, emotional valence, and abstraction level.

#### Research Findings

**Dual-Module Framework for topic shift detection** (Wang et al., COLING 2025) simulates dual-process cognition (System 1 intuition + System 2 reasoning) for real-time topic shift detection. It extracts global historical structure and reasons about local transition dynamics. Outperforms baselines on TIAGE and CNTD datasets.

**LLM hidden representations for difficulty estimation** (EMNLP 2025) estimates question difficulty as perceived by the LLM from hidden representations alone — no output generation needed. Generalizes across domains and model sizes. This provides a lightweight per-turn estimate of how "hard" the current turn is for the AI.

**Online Domain-aware Decoding (ODD)** (arXiv:2602.08088, February 2026) performs real-time domain shift adaptation during generation with ~0.2ms overhead per decoding step. Uses disagreement and continuity signals to detect distribution shift and adjust generation accordingly.

#### THCP Integration: Running $\epsilon_t$ Estimator

The monitor can maintain a per-turn $\epsilon_t$ estimate using three signals:

| Signal | Source | What It Estimates |
|---|---|---|
| Topic shift detector (DMF-style) | Conversation text | When the conversation enters a new domain with potentially different $\epsilon$ |
| AI difficulty estimate (hidden representations or logprob entropy) | Model internals or logprobs | How uncertain the AI is about this specific content — proxy for domain-specific $\epsilon$ |
| Historical $\epsilon$ by domain | Persistent dynamics store (C.3) | Learned $\epsilon$ values for known domains from prior sessions |

When $\epsilon_t$ spikes, the monitor emits a new event:

`signal.horizon_widening` — "the ontological gap just widened; increase humility, reduce confidence, consider asking the human for more context about what they mean in this domain."

---

### C.7 Gap 2C: Shared Fidelity Instruments — The Human Calibration Problem

#### The Problem

The fidelity score is computed from the AI's side of the horizon. It measures what the AI *thinks* the communication quality is. The human's assessment may differ. Without human calibration, the monitor optimizes a one-sided metric.

#### Research Findings

**OrchVis** (Zhou et al., Georgia Tech, October 2025) introduces a visualization and orchestration framework for multi-agent systems that enables humans to supervise workflows through transparent goal alignment, progress tracking, conflict detection, and planning panels. Crucially, it provides **shared visibility**: both human and agents see the same goal structure, verification states, and conflict reports.

**Claude Cowork live artifacts** (Anthropic, April 2026) enable dynamic dashboards that refresh with current data — a practical demonstration that shared real-time instruments between human and AI are now productizable.

**"Response Quality Is Not Conversation Quality"** (Hafez et al., 2026) explicitly quantifies the gap between per-response evaluation and conversation-level quality, arguing that measurement must occur at the trajectory level, not the point level. The Bipredictability metric is proposed as a lightweight trajectory-level signal that both parties could, in principle, observe.

#### THCP Integration: Phase 4 Design Requirements

The shared fidelity dashboard is not decorative — it is a theoretical necessity. The cross-horizon metric (Gap 2C from the essay) requires human calibration input. Design requirements from the research:

1. **Shared visibility**: Both human and agent see the same fidelity trajectory, not a filtered or simplified version. Transparency builds the trust needed for the protocol to work.
2. **Human override**: The human can flag "your fidelity score is wrong" at any point. This override becomes training data for calibrating the AI-side metric.
3. **Lightweight**: Following OrchVis's principle, the dashboard should not require the human to monitor constantly — it should surface signals only when the conversation's health changes significantly (fidelity crossing a threshold, convergence signal, contradiction detected).
4. **Bidirectional**: The dashboard should also show the human how *their* behavior affects the trajectory — "your last message was very short and the agent's uncertainty increased; a more detailed message would help." This operationalizes the THCP prediction that both sides of the adjunction must participate.

---

### C.8 Appendix C References

100. Condrey, D. (2026). "Detecting Cognitive Signatures in Typing Behavior for Non-Intrusive Authorship Verification." arXiv:2603.00177 [cs.CR].

101. Scientific Reports (2026). "Functional and cognitive correlates of typing speed in a large U.S. panel study." *Nature Scientific Reports*. DOI:10.1038/s41598-026-36500-7.

102. PsycNet (2026). "Predicting Cognitive Functioning in Mood Disorders through Smartphone Typing Dynamics." *Journal of Psychopathology and Clinical Science*. Manuscript 2026-59586-001.

103. Tan, F. F.-Y., Messerschmidt, M. A., Yin, W., and Nov, O. (2026). "The Impact of Response Latency and Task Type on Human-LLM Interaction." arXiv:2604.06183 [cs.HC].

104. HCI Study on ChatGPT Typing Behaviors (2025). "Examining Users' Perceptions of ChatGPT-based Conversational Agents through Typing Behavior Design." arXiv:2510.08912 [cs.HC].

105. Ahmed, F. and Ong, Y. J. (2026). "LogitScope: A Framework for Analyzing LLM Uncertainty through Information Metrics." arXiv:2603.24929 [cs.AI]. CAO Workshop at ICLR 2026.

106. OpenAI (2025). "Using logprobs for classification and Q&A evaluation." OpenAI Cookbook.

107. APEX-MEM (2026). "APEX-MEM: An Ontology-Supported Property Graph Architecture for Long-Term Conversational Memory." arXiv:2604.14362 [cs.CL].

108. SGMem (Under review, ICLR 2026). "SGMem: Sentence Graph Memory for Long-Term Conversational Agents."

109. Temporal Graph Network for Dialogue Coherence (2026). "Temporal Graph Network for Dialogue-Level Hallucination Detection." arXiv:2601.03051 [cs.CL].

110. Eirew, A., Bar, K., and Dagan, I. (2025). "Beyond Pairwise: Global Zero-shot Temporal Graph Generation." *EMNLP 2025*, pp. 31440–31458.

111. Liu, W. and Strube, M. (2025). "Discourse Relation-Enhanced Neural Coherence Modeling." *ACL 2025*, pp. 4748–4762.

112. Hafez et al. (2026). "Token Statistics Reveal Conversational Drift in Multi-turn LLM Interaction." arXiv. (Bipredictability metric.)

113. Laban, P., Hayashi, H., Zhou, Y., and Neville, J. (2025). "LLMs Get Lost In Multi-Turn Conversation." arXiv:2505.06120 [cs.CL]. (MSR/Salesforce, 200k+ conversations, 39% degradation.)

114. IGT/TWR Empirical Validation (Under review, ICLR 2026). "Quantifying Information Gain and Redundancy in Multi-Turn LLM Conversations." (Same as ref. 55, now with validated experimental results.)

115. Wang, H., Li, P., Fan, Y., and Zhu, Q. (2025). "Simulating Dual-Process Thinking in Dialogue Topic Shift Detection." *COLING 2025*, pp. 177.

116. EMNLP (2025). "LLM Already Knows: Estimating LLM-Perceived Question Difficulty via Hidden Representations." *EMNLP 2025*, pp. 61.

117. ODD Framework (2026). "Online Domain-aware Decoding." arXiv:2602.08088 [cs.LG].

118. Zhou, J. et al. (2025). "OrchVis: Hierarchical Multi-Agent Orchestration for Human Oversight." arXiv:2510.24937.

---

## Appendix D: Temporal-Spatial Grounding — The Human's Time, The Agent's Blindness

The THCP framework (Sections 1–9, Appendices A–C) models the ontological gap as a *spatial* structure: $\epsilon_t$, $D_{JS}$, coherence topology. This appendix introduces the **temporal dimension** — the fact that humans and AI agents experience time asymmetrically, and that this asymmetry has measurable, modelable, and instrumentable consequences for conversation quality.

### D.1 The Problem: Temporal Blindness

Recent empirical work identifies a phenomenon that the THCP framework predicts but does not yet formalize: **LLM agents are temporally blind**.

**TicToc** (Cheng et al., arXiv:2510.23853, October 2025, revised January 2026) constructed a dataset of 1,800+ multi-turn user-agent conversation trajectories across 76 scenarios with high, medium, and low time sensitivity. Human preferences were collected for "call a tool" vs. "directly answer" under varying elapsed times. Key finding: **no model achieves a normalized alignment rate better than 65% when given timestamp information.** Prompt-based techniques have limited effectiveness; only specific post-training alignment improves temporal reasoning.

The authors define this as "temporal blindness" — agents assume a **stationary context**, failing to account for real-world time elapsed between messages. This causes:
- **Over-reliance on stale context**: the agent treats 3-day-old information as current
- **Redundant tool calls**: the agent re-fetches data that just changed 30 seconds ago
- **Misaligned urgency**: the agent treats a request made at 3 AM the same as one at a deadline

**The Collaboration Gap** (arXiv:2604.18096, April 2026) provides the interaction-theory framing. Drawing on Clark & Brennan's (1991) common ground theory, the paper distinguishes three interaction structures: one-shot assistance, weak collaboration (asymmetric repair — the human carries the burden), and grounded collaboration (balanced repair, shared understanding). The temporal dimension is a core grounding condition: **when the human returns after a gap, their context has changed but the agent's hasn't.** The repair burden falls entirely on the human to re-establish common ground, because the agent has no awareness that common ground has eroded.

**TaCoS** (Lill et al., ICSE 2026) empirically confirms the cost. In a study of 32 software developers resuming programming tasks after interruptions of 1–7 days, LLM-generated context summaries reduced resumption lag to the shortest of three conditions tested. But the summaries lacked **forward-looking information** — what the developer *planned to do next*. The paper concludes that retrospective summaries and prospective cues are complementary, and neither alone is sufficient.

**Temporal Aspects of Human-AI Interaction** (Shaer et al., Wellesley College, 2024/2025) observes: "When opening a previous session, users return to the previous conversation with the AI exactly from where it broke off, with the local context of the conversation maintained. This design feature inverts the context gap — the LLM maintains perfect context, while the person has probably learned, forgotten, and otherwise changed." The strength of this design is also its blindness: the agent is "frozen in time, waiting to resume," while the human has moved through the world.

### D.2 The Physics: Proper Time and Temporal Asymmetry

In special relativity, **proper time** $\tau$ is the time measured by a clock at rest between two events in its own reference frame. It is the shortest interval; it is invariant. Different observers in relative motion experience different elapsed proper times between the same pair of events:

$$\Delta t = \gamma \Delta \tau, \quad \gamma = \frac{1}{\sqrt{1 - v^2/c^2}}$$

The twin paradox illustrates the asymmetry: one twin stays home; the other travels at high velocity and returns. The travelling twin experiences less elapsed time. Both twins are "correct" — they simply occupy different worldlines through spacetime.

**Mapping to human-AI conversation**: The human is the twin who travels through the world. Between turns, they experience proper time $\tau_H$: sleeping, working, having other conversations, solving parts of the problem independently, changing physical location, changing emotional state. The AI agent is the twin who stays home: $\tau_A = 0$ between turns. The agent's state is frozen at the exact moment the last response was generated.

The **temporal asymmetry** is:

$$\Delta\tau = \tau_H - \tau_A = \tau_H$$

This is always positive and always asymmetric. The agent's proper time between turns is zero. This is not an approximation — the agent literally does not exist between invocations.

### D.3 Human Memory Decay: The Forgetting Curve as Temporal Signal

The human's context retention during the gap $\Delta\tau$ follows well-established cognitive science:

**Ebbinghaus Forgetting Curve** (1885, extensively replicated): Memory retention decays exponentially:

$$R(t) = e^{-t/S}$$

where $R$ is retention probability, $t$ is time since encoding, and $S$ is memory strength/stability. Ebbinghaus's original data: ~56% retained after 1 hour, ~44% after 1 day, ~25% after 6 days. Modern replications confirm the exponential form with individual variation in $S$.

**Half-Life Regression** (Settles & Meeder, ACL 2016 — Duolingo's spaced repetition algorithm, open-source at github.com/duolingo/halflife-regression): Models recall probability as:

$$p = 2^{-\Delta/h}, \quad h = 2^{\Theta \cdot x}$$

where $\Delta$ is time since last review, $h$ is the half-life regressed from features (difficulty, prior exposure, domain complexity), and $\Theta$ is learned weights. Validated on 300+ million users. Reduced prediction error by 45% over the Leitner system.

**Adaptation to conversation context**: In THCP terms, the human's retention of the conversation context at resumption is:

$$R_{\text{conversation}}(\Delta\tau) = 2^{-\Delta\tau / h_c}$$

where $h_c$ is the conversation context half-life, dependent on:
- **Domain complexity**: technical discussions decay faster than personal ones
- **Engagement depth**: casual browsing vs. deep problem-solving
- **Rehearsal**: whether the human thought about the problem during the gap
- **Salience**: emotionally salient or surprising content decays more slowly

A 3-day gap ($\Delta\tau = 72$ hours) with a conversational context half-life of $h_c = 24$ hours gives $R = 2^{-3} = 0.125$ — the human retains approximately 12.5% of the conversational context. The agent retains 100%. This 87.5% retention asymmetry is the **temporal component of $\epsilon_t$**.

### D.4 Context Switching Cost: The Resumption Penalty

Even without forgetting, the act of returning to a conversation after a gap carries a measurable cognitive cost:

**Gloria Mark (UC Irvine, 2023)**: 23 minutes and 15 seconds average recovery time after an interruption in knowledge work. Workers don't return to the original task immediately — they get distracted by 2.3 other tasks first.

**APA (2022)**: Task-switching reduces productivity by 40% for complex cognitive work and increases error rates by 50%.

**Microsoft Research (2024)**: High-frequency context switchers (60+ daily) show elevated afternoon cortisol ($r = 0.67$ with reported stress). An interrupted conversation is not just a paused conversation — it is a *degraded* conversation.

**Leroy (2009)**: "Attention residue" — part of the mind remains anchored to the previous task even after nominally switching back. For conversation resumption, this means the human's first turns after a gap carry residual attention from whatever they were doing immediately before.

**Task-interruption research (PMC, 2024)**: The MFG model conceptualizes interference during resumption in terms of **activation decay** — the primary task's activation level decays during the interruption, requiring time and effort to reactivate. No primary-task inhibition occurs; the activation simply fades.

**CCNeuro 2025 (Klevak et al.)**: Task switching *after low-efficacy periods* actually improves performance — the context switch acts as a reset. But switching *during high-efficacy flow states* significantly degrades subsequent performance. Implication: the conversation resumption cost depends on what the human was doing *immediately before returning*.

### D.5 Distributed Systems: Lamport Clocks for Conversation

The temporal asymmetry problem has a well-studied analog in distributed systems: **how do two processes with no shared clock agree on the order of events?**

**Lamport Clocks** (Lamport, 1978): Each process maintains a monotonically increasing counter. On each event, increment. On send, attach counter. On receive, set counter to $\max(\text{local}, \text{received}) + 1$. This produces a partial ordering consistent with the happens-before relation: if event $A$ happens before event $B$, then $LC(A) < LC(B)$.

**Vector Clocks** (Fidge 1988, Mattern 1988): Extend Lamport clocks to detect causal concurrency. Each process maintains a vector of integers. On receive, take component-wise maximum. Two events are causally concurrent if neither vector dominates.

**Mapping to human-AI conversation**: The human and the agent are two processes with no shared clock. The human's "events" between turns (thinking, working, sleeping, relocating) are invisible to the agent. The agent's "events" between turns are zero — it doesn't exist. When the conversation resumes:

- **The agent's Lamport clock** shows the timestamp of the last turn
- **The human's Lamport clock** has advanced by an unknown number of events during the gap

The events the human experienced during the gap are **causally concurrent with nothing in the agent's history** — the agent has no vector entries for them. From the agent's perspective, the conversation was paused. From the human's perspective, the conversation was *one of many things happening in parallel*.

This is why a simple timestamp is insufficient. What's needed is a **temporal handshake** — a mechanism for the human's clock state to be communicated to the agent at resumption, so the agent can update its model of the human's current context.

**Temporal Delta Synchronization** (TDS protocol, Paaracat, 2026) formalizes this: map human absence to a defined system state via a four-factor algorithm (environmental parameters, exit command, pre-absence task state, silence duration $\Delta t$). On re-engagement, the system presents a contextual status report rather than diagnostic queries.

### D.6 Conversation Geodesics: Distance in Conversation-Space

When a user says "remember what we discussed about the database?" they are referencing a specific point in the conversation's history. The "distance" between the current turn and that reference is not simply the number of intervening turns — it is a **geodesic** through conversation-space, weighted by:

1. **Semantic distance**: how different the topics are between the two points
2. **Temporal distance**: how much proper time elapsed for the human between the two points
3. **Information loss**: whether context compaction or truncation occurred between the two points, creating a "gap" in the geodesic

**Reasoning Paths in Dialogue Context** (PDC, arXiv:2103.00820): Constructs a semantic graph of dialogue turns where turns are connected if they share entities or semantic overlap. A path generator (transformer decoder) predicts reasoning paths through this graph to propagate contextual cues. The path length and connectivity measure "distance" between dialogue points.

**Chronos** (arXiv:2603.16862, March 2026): Decomposes multi-turn conversations into subject-verb-object event tuples with resolved datetime ranges, indexing them in a structured event calendar. Achieves 95.6% accuracy on temporal queries over long dialogue histories (LongMemEvalS benchmark, 500 questions). The events calendar alone accounts for 58.9% of the gain over baseline.

**Memory-T1** (2026): Uses reinforcement learning for temporal-aware memory retrieval with a coarse-to-fine strategy. The RL agent learns to select temporally consistent evidence via a multi-level reward: answer accuracy, evidence grounding, and temporal consistency (session-level chronological proximity + utterance-level chronological fidelity).

**SuperLocalMemory V3** (arXiv:2603.14588, March 2026): Introduces information-geometric foundations for agent memory, with temporal weighting of memory entries using Fisher information and Riemannian geometry on statistical manifolds. Memory retrieval accounts for both semantic relevance and temporal recency in a principled geometric framework.

**Adaptation to THCP**: The conversation geodesic between turn $i$ and turn $j$ should be defined as:

$$d(i, j) = \alpha \cdot d_{\text{semantic}}(i, j) + \beta \cdot f(\Delta\tau_{H}(i, j)) + \gamma \cdot \mathbb{1}[\text{context\_lost}(i, j)]$$

where $d_{\text{semantic}}$ is embedding distance, $f(\Delta\tau_H)$ is a monotonically increasing function of the human's elapsed proper time between the turns, and $\mathbb{1}[\text{context\_lost}]$ is an indicator for whether context compaction occurred between the two points (creating an infinite-weight gap — the geodesic is broken).

When the geodesic is broken, the user's reference cannot be fulfilled. This is a `signal.broken_reference` event — the conversational equivalent of a broken wormhole: the two points that were once connected are now causally disconnected.

### D.7 The Temporal Extension of $\epsilon_t$

The ontological gap $\epsilon_t$ as defined in THCP Law 1 is primarily spatial: the representational distance between human intent and AI understanding. The temporal dimension adds a second axis:

$$\epsilon_t^{\text{full}} = \epsilon_t^{\text{spatial}} + \epsilon_t^{\text{temporal}}$$

where:

$$\epsilon_t^{\text{temporal}} = (1 - R_{\text{conversation}}(\Delta\tau)) \cdot w_{\text{memory}} + C_{\text{switch}} \cdot w_{\text{resumption}} + d_{\text{geodesic}}^{\text{broken}} \cdot w_{\text{reference}}$$

The three terms:
1. **Memory decay**: the fraction of conversational context the human has forgotten, weighted by $w_{\text{memory}}$
2. **Resumption cost**: the cognitive overhead of context-switching back to the conversation, weighted by $w_{\text{resumption}}$ (derived from the 23-minute recovery finding, scaled by gap duration and interruption depth)
3. **Broken references**: the count of conversation points that have been lost to context compaction and can no longer be traversed, weighted by $w_{\text{reference}}$

When $\Delta\tau = 0$ (instant reply), $\epsilon_t^{\text{temporal}} \approx 0$ and the gap is purely spatial. When $\Delta\tau = 3$ days, $\epsilon_t^{\text{temporal}}$ dominates — the human and agent are separated not just by ontology but by *time itself*.

### D.8 New Temporal Events

The temporal dimension introduces three new signal types:

**`signal.temporal_desync`**: Fires when the gap between turns exceeds a threshold (configurable; default: 3600s = 1 hour). The signal carries $\Delta\tau$, estimated $R_{\text{conversation}}$, and a suggested behavior: "re-anchor before continuing — summarize where the conversation left off and check if the user's intent has changed."

**`signal.broken_reference`**: Fires when the user's current turn has high semantic similarity to a prior turn whose content was lost to context compaction. The geodesic between "here" and "there" is broken. The agent needs to know: *the user is referencing something the agent no longer has access to.*

**`signal.frame_shift`**: Fires when metadata indicates the human's context frame has changed — device type changed (desktop → mobile), timezone shifted, or client context indicates a different environment. The conversation's coordinate system may need re-anchoring.

### D.9 References for Appendix D

119. Cheng, E. et al. (2025/2026). "Your LLM Agents are Temporally Blind: The Misalignment Between Tool Use Decisions and Human Time Perception." arXiv:2510.23853v2. GitHub: chengez/TicToc.

120. Ebbinghaus, H. (1885). *Über das Gedächtnis.* Leipzig: Duncker & Humblot. [Memory: A Contribution to Experimental Psychology.]

121. Settles, B. & Meeder, B. (2016). "A Trainable Spaced Repetition Model for Language Learning." *ACL 2016*, pp. 1848–1858. GitHub: duolingo/halflife-regression.

122. Mark, G. (2023). "Attention Span and Context Switching in Information Workers." UC Irvine. See also: Mark, G. (2023). *Attention Span: A Groundbreaking Way to Restore Balance, Happiness and Productivity.* Hanover Square Press.

123. Leroy, S. (2009). "Why Is It So Hard to Do My Work? The Challenge of Attention Residue When Switching Between Work Tasks." *Organizational Behavior and Human Decision Processes*, 109(2), 168–181.

124. Meyer, D. E. & Kieras, D. E. (1997). "A Computational Theory of Executive Cognitive Processes and Multiple-Task Performance." *Psychological Review*, 104(1), 3–65.

125. Lamport, L. (1978). "Time, Clocks, and the Ordering of Events in a Distributed System." *Communications of the ACM*, 21(7), 558–565.

126. Fidge, C. (1988). "Timestamps in Message-Passing Systems That Preserve the Partial Ordering." *Proceedings of the 11th Australian Computer Science Conference*, pp. 56–66. Mattern, F. (1988). "Virtual Time and Global States of Distributed Systems." *Parallel and Distributed Algorithms*, pp. 215–226.

127. Shaer, O. et al. (2024/2025). "Temporal Aspects of Human-AI Interaction." Wellesley College Faculty Scholarship.

128. Lill, A. et al. (2026). "TaCoS: Generated Context Summaries for Task Resumption." *ICSE 2026 Research Track*. University of Zurich.

129. arXiv:2604.18096 (2026). "The Collaboration Gap in Human-AI Work." Constructivist grounded theory analysis of grounding conditions in LLM-enabled work.

130. Paaracat (2026). "Temporal Delta Synchronization: A Protocol for Managing Asynchronous Human-AI Interactions."

131. Chronos (2026). "Temporal-Aware Conversational Agents with Structured Event Retrieval for Long-Term Memory." arXiv:2603.16862.

132. Memory-T1 (2026). "Reinforcement Learning for Temporal Reasoning in Multi-Session Agents." OpenReview.

133. SuperLocalMemory V3 (2026). "Information-Geometric Foundations for Zero-LLM Enterprise Agent Memory." arXiv:2603.14588.

134. PDC (2021). "Reasoning Paths in Dialogue Context." arXiv:2103.00820.

135. Clark, H. H. & Brennan, S. E. (1991). "Grounding in Communication." In *Perspectives on Socially Shared Cognition*, pp. 127–149. APA.

136. Klevak et al. (2025). "The Effect of Task Switching on Cognitive Fatigue." *CCNeuro 2025*.

137. Microsoft Research (2024). "Context Switching and Stress Biomarkers in Knowledge Workers."

138. Kim, J. et al. (2025). "A Mathematical Approach to Using the Forgetting Curve to Evaluate Experience and Training Factors in Human Reliability Analysis." *Annals of Nuclear Energy*.

139. Kline, D. (2025). "Human-like Forgetting Curves in Deep Neural Networks." arXiv:2506.12034. University of Rochester.

140. Fried, D. (2026). "Bridging the Communication Gap with AI." CMU School of Computer Science, Language Technologies Institute.

141. Davidson et al. / OpenReview (2025/2026). "The Collaboration Gap." Maze-solving benchmark revealing collaboration performance collapse in solo-capable models.

---

## Appendix E: 4D Conversation Spacetime — From Temporal Signals to a Complete Space-Time-Distance Framework

*Appendix D introduced the temporal dimension: the human's proper time, the agent's blindness, and three temporal signals. This appendix completes the framework by addressing six remaining structural gaps required for Horizon to function as a full 4D translation layer between the agent's event-horizon state and the human's spacetime experience.*

### E.1 Gap 1: Circadian Cognitive Load — The Human's Variable Clock Rate

#### E.1.1 The Problem

Appendix D models *how much time* has elapsed between turns. It does not model *when* in the human's circadian cycle a turn occurs. A message at 3:00 AM is structurally different from a message at 10:00 AM: the human's cognitive capacity — attention, working memory, decision quality — varies with time-of-day.

#### E.1.2 Research Foundations

Circadian variation in cognitive performance is one of the most replicated findings in chronopsychology:

**Valdez, Ramírez & García (2012)** conducted a comprehensive review establishing that performance in attention, working memory, and executive function follows a characteristic diurnal curve:

- **10:00–14:00**: acceptable cognitive performance (post-wake ramp)
- **14:00–16:00**: post-lunch dip — reduced attention and increased errors
- **16:00–22:00**: peak performance window for most cognitive functions
- **22:00–04:00**: nocturnal decline — attention, inhibition, and flexibility impaired
- **04:00–07:00**: circadian nadir — worst performance across all domains

**Schmidt, Collette, Cajochen & Peigneux (2007)** demonstrated that the three core processes — attention, working memory, executive functions — each follow circadian rhythms but with different phase relationships, meaning the *type* of cognitive task matters, not just the time.

**Diurnal variation meta-analysis (2023)** across 11 studies found cognitive performance varies 9–34% for reaction time and 7.8–40.3% for attention depending on time-of-day — a variation comparable in magnitude to the effects of moderate sleep deprivation.

A 2025 systematic review of 65 studies confirmed **synchrony effects** (chronotype × time-of-day) in 45% of young adults and 83% of older adults, particularly for tasks requiring attention, inhibition, and memory.

**Night-shift research**: de Cordova, Bradford & Stone's systematic review found night-shift workers commit more errors and show decreased performance in 9 of 13 included studies. The first night shift produces the most acute deficits due to combined circadian misalignment and acute sleep deprivation.

**Risky decision-making**: Under constant routine protocols, decision-making quality peaks around midday and is significantly inhibited after ~30 hours awake, with risk propensity and sensitivity to punishment varying across the circadian cycle.

#### E.1.3 The Physics Parallel: Variable Clock Rate

In general relativity, the rate at which a clock ticks depends on its position in a gravitational field (gravitational time dilation) and its velocity:

$$\frac{d\tau}{dt} = \sqrt{1 - \frac{2GM}{rc^2}}$$

A clock deeper in a gravitational well ticks slower. Analogously, the human's "cognitive clock rate" — the speed at which they process information, form decisions, and retain context — is not constant. It varies with their position in the circadian cycle.

**Definition** (Circadian cognitive factor): For a turn arriving at local time $t_{\text{local}}$ in the human's timezone, define:

$$\kappa(t_{\text{local}}) \in [0, 1]$$

where $\kappa = 1$ represents peak cognitive capacity and $\kappa = 0$ represents the circadian nadir. A piecewise model based on Valdez et al.:

$$\kappa(t) = \begin{cases} 0.5 + 0.5 \cdot \frac{t - 7}{3} & 07{:}00 \leq t < 10{:}00 \text{ (morning ramp)} \\ 1.0 & 10{:}00 \leq t < 14{:}00 \text{ (peak 1)} \\ 0.7 & 14{:}00 \leq t < 16{:}00 \text{ (post-lunch dip)} \\ 1.0 & 16{:}00 \leq t < 22{:}00 \text{ (peak 2)} \\ 0.7 - 0.4 \cdot \frac{t - 22}{6} & 22{:}00 \leq t < 04{:}00 \text{ (nocturnal decline)} \\ 0.3 & 04{:}00 \leq t < 07{:}00 \text{ (nadir)} \end{cases}$$

*Epistemic note*: This is a coarse population-level model. Individual variation (chronotype, sleep debt, light exposure) can shift these windows by 2–4 hours. The model should be calibrated per-user if data is available.

#### E.1.4 Integration with THCP

The circadian factor modifies two existing signals:

1. **Estimated retention** (from Appendix D): $R(t, \kappa) = R(t) \cdot \kappa(t_{\text{local}})$ — a message sent at 3:00 AM to a user who will read it at 3:00 AM is retained worse than the same message read at 10:00 AM.

2. **Fidelity dynamics**: The fidelity equation gains a cognitive load modifier:

$$F_t = \alpha \cdot S_t - \beta \cdot (1 - C_t) - \gamma \cdot \Delta\tau_t - \delta \cdot (1 - \kappa_t)$$

where $\delta$ weights the circadian penalty. At the nadir ($\kappa = 0.3$), this contributes $-0.7\delta$ to fidelity — the conversation is structurally harder, regardless of content quality.

**Technical reference**: Computing $\kappa$ requires only `timestamp` (already in the API) and `client_context.timezone` (already in the API). The local hour is derived; no new inputs are needed.

---

### E.2 Gap 2: Deictic Temporal Resolution — Grounding "Yesterday" to a Date

#### E.2.1 The Problem

When a human says "yesterday," "before the meeting," "next Monday," or "three weeks ago when we discussed X," these are **temporal deictic expressions** — their meaning depends on the speaker's reference frame. The agent has no intrinsic way to resolve them. Without grounding, "yesterday" is processed as a token, not as a date.

#### E.2.2 Research Foundations

Temporal expression extraction and normalization is a well-established NLP subfield:

**TIMEX3 Standard (TimeML)**: The dominant annotation standard for temporal expressions, classifying them into four types: `DATE`, `TIME`, `DURATION`, and `SET` (recurring events). Each expression is normalized to an ISO 8601 value relative to a document creation time (DCT).

**HeidelTime** (Strötgen & Gertz, 2010; SemEval 2010): A multilingual, rule-based temporal tagger that was the best-performing system in TempEval-2. It supports four document domains (news, narratives, colloquial, scientific) with different normalization strategies. It resolves expressions like "last Christmas" and "two weeks ago" relative to a reference date.

**SUTime** (Stanford CoreNLP): A deterministic, rule-based temporal expression recognizer that normalizes to TIMEX3. It handles relative expressions ("next Wednesday at 3pm" → `2026-04-29T15:00`), durations, and sets. Available as part of the Stanford NER pipeline.

**dateparser** (Python, v1.4.0, March 2026): The most actively maintained Python library for temporal parsing, supporting 200+ language locales. Key capabilities:
- Relative expressions: "two weeks ago," "tomorrow," "in 3 days"
- `search_dates(text)`: extracts all date expressions from longer text
- `RELATIVE_BASE` parameter: anchors relative parsing to a specific datetime
- Time span detection: "past month" → (start_date, end_date)

**datefinder** (Python, v1.0.0, March 2026): A faster alternative with typed match objects. The `extract()` engine returns structured types: `relative` (with `resolved_datetime` and `delta_seconds`), `duration` (with `total_seconds`), and explicit dates. Benchmarks show 766× faster than dateparser on core corpora.

**EventTempEx**: A research system classifying temporal expressions into four categories — Standard, Event-Contextual, Complex, and Historic — using a fine-tuned DeBERTa NER model. Event-contextual expressions (e.g., "after the merger," "since the pandemic") require semantic search against a knowledge base, not just calendar arithmetic.

#### E.2.3 The Physics Parallel: Coordinate Transformation

In special relativity, different observers assign different coordinates to the same event. "Simultaneous" in one frame is "sequential" in another. Resolving this requires a **Lorentz transformation** — a mathematical mapping from one observer's coordinates to another's.

"Yesterday" is a coordinate in the human's reference frame. To the agent, it is a token. Resolving it requires a transformation:

$$T_{\text{absolute}} = \text{Resolve}(\text{"yesterday"}, t_{\text{human}}) = t_{\text{human}} - 86400\text{s}$$

This is the conversational analog of a Lorentz transformation: it maps from the human's deictic frame to an absolute timeline that both parties can reference.

#### E.2.4 Formalization

**Definition** (Temporal Deixis Resolution): Given a user message $m_t$ with content $c$ and reference timestamp $t_{\text{ref}}$ (the human's current time), the **deictic resolution function** is:

$$\mathcal{D}(c, t_{\text{ref}}) = \{(e_i, T_i, \text{type}_i)\}$$

where $e_i$ is the extracted expression string, $T_i$ is its resolved ISO 8601 datetime, and $\text{type}_i \in \{\text{DATE}, \text{TIME}, \text{DURATION}, \text{SET}\}$.

Unresolvable expressions (e.g., "before the meeting" where no meeting time is known) produce $T_i = \bot$ (unknown), which itself is a signal — the agent should ask for clarification rather than assume.

**Technical reference**: In Python, using `dateparser`:

```python
import dateparser
# user_timestamp is the ISO 8601 timestamp from process_turn()
refs = dateparser.search.search_dates(
    user_message,
    settings={'RELATIVE_BASE': user_timestamp}
)
# refs = [("yesterday", datetime(2026, 4, 21, ...)), ...]
```

For higher performance in production, `datefinder.extract()` offers 766× speedup over dateparser with typed results including `delta_seconds` for relative expressions.

---

### E.3 Gap 3: Spatial Grounding — The Human's Physical Context

#### E.3.1 The Problem

The human exists in three-dimensional physical space. Their location constrains their communication: screen size, attention budget, noise level, available tools, social context. Horizon currently tracks `client_context.timezone` and `client_context.device_type` as proxies, but doesn't model *what spatial changes mean* for conversation quality.

#### E.3.2 Research Foundations

**IP Geolocation** (MaxMind GeoIP2, v5.2.0): The standard mechanism for deriving approximate physical location from a network address. Returns:
- City, region, country
- Latitude/longitude (approximate; accuracy_radius in km at 67% confidence)
- Timezone (IANA name)
- Traits: is_anonymous_vpn, is_hosting_provider (useful for filtering)

*Privacy note*: IP geolocation is inherently imprecise (city-level, not household-level). It is suitable for deriving `location_class` but not for tracking individuals. MaxMind's documentation explicitly states: "should not be used to identify a particular address or household."

**Device-Dependent Cognitive Load** (Nielsen Norman Group, 2024–2025): Mobile content is approximately **2× as difficult** as desktop content because:
- Smaller screens force greater reliance on working memory
- Content fragmentation across viewports overwhelms short-term memory
- Average mobile session: ~72 seconds; desktop: ~150 seconds
- Interaction cost (scrolling, navigating) consumes cognitive resources that would otherwise go to comprehension

This is not a UX preference — it is a measurable cognitive load difference. The **channel capacity** of the human-device system is directly determined by screen size and attention span.

**Environmental Context**: Screen inclination (tilted laptop vs. flat tablet) affects global vs. local visual processing, with tilted displays favoring global/holistic processing and flat displays favoring local/detail processing. This suggests the same information presented on different devices may be *cognitively processed differently*, not just viewed differently.

#### E.3.3 The Physics Parallel: The Metric Tensor Varies with Position

In general relativity, the metric tensor $g_{\mu\nu}(x)$ is a function of position — it describes how distances and durations are measured *at each point in spacetime*. Communication near a massive object (strong gravitational field) is qualitatively different from communication in flat space.

Analogously, the "metric" of human-AI communication varies with the human's physical context:

| Context class | Attention budget | Screen capacity | Response latency expectation | Privacy |
|---|---|---|---|---|
| `office_desktop` | High | Large | Standard | Low concern |
| `office_mobile` | Medium | Small | Fast | Medium |
| `home_desktop` | High | Large | Relaxed | Low concern |
| `transit_mobile` | Low | Small | Fast | High concern |
| `meeting` | Very low | None/Small | Deferred | High concern |

Each row represents a different "metric" — the same semantic content has different cognitive costs depending on where the human is.

#### E.3.4 Formalization

**Definition** (Spatial Context Class): Given `client_context.device_type` $d$ and `client_context.timezone` $z$ (or IP-derived geolocation), define:

$$\sigma_t = (d_t, z_t, \ell_t)$$

where $\ell_t \in \{\texttt{office}, \texttt{home}, \texttt{transit}, \texttt{meeting}, \texttt{unknown}\}$ is the inferred location class. The **spatial constraint vector** maps $\sigma_t$ to communication parameters:

$$\Phi(\sigma_t) = (\text{attention\_budget}, \text{screen\_capacity}, \text{max\_response\_length}, \text{complexity\_ceiling})$$

**Frame shift detection**: A spatial frame shift occurs when $\sigma_t \neq \sigma_{t-1}$. The magnitude depends on the distance in constraint space:

$$\Delta\Phi = \|\Phi(\sigma_t) - \Phi(\sigma_{t-1})\|$$

A shift from `office_desktop` to `transit_mobile` is a large $\Delta\Phi$ (attention, screen, and complexity all change). A shift from `office_desktop` to `home_desktop` is small.

**IP-to-location pipeline**: Using MaxMind GeoIP2 (Python):

```python
import geoip2.database
reader = geoip2.database.Reader('GeoLite2-City.mmdb')
response = reader.city(client_ip)
# response.location.latitude, .longitude, .accuracy_radius, .time_zone
# response.city.name, response.country.iso_code
```

*Epistemic note*: IP geolocation is city-level at best. For `location_class` inference, timezone changes and device type changes are more reliable signals than IP-derived coordinates. The system should use IP data as a supplementary signal, not a primary one.

**Local machine time injection**: For agents running on the user's machine (IDE extensions, CLI tools), the human's local time and timezone can be obtained directly without IP geolocation, using Python's standard library:

```python
from datetime import datetime, timezone
now = datetime.now(timezone.utc).astimezone()  # local time with timezone
local_tz_name = now.tzinfo.tzname(now)          # e.g., "PDT"
utc_offset = now.utcoffset().total_seconds()    # e.g., -25200.0 (UTC-7)
```

For reliable IANA timezone names (e.g., `America/Los_Angeles`), the `tzlocal` library (v5.3.1, 2025) provides `get_localzone_name()`, which reads system configuration on all major platforms.

---

### E.4 Gap 4: Conversation Velocity and Acceleration — The Pace of Interaction

#### E.4.1 The Problem

A conversation that produces 10 turns in 5 minutes is structurally different from one that produces 10 turns over 3 days. The *pace* carries information: engagement, urgency, difficulty, disengagement. Horizon tracks position (turn number) and temporal gaps, but never computes the derivative — the rate of semantic movement per unit of human time.

#### E.4.2 Research Foundations

**Turn-taking speed and speaker characteristics** (Onishi, Ohnaka & Yoshino, SIGDIAL 2025): Analyzed real conversations and modeled turn-taking speeds using a **three-parameter gamma distribution** conditioned on speaker role (expert vs. novice), interpersonal relationship (friends vs. strangers), and Big Five personality traits. Key findings:
- Mean turn-taking speed from novice to expert: 0.455 seconds; expert to novice: 0.247 seconds (p < 0.05, Mann-Whitney U)
- Friends exhibit slower pace than strangers (greater silence tolerance, deeper elaboration)
- Personality traits modulate both shape and scale parameters of the gamma distribution

This establishes that **turn-taking speed is a signal, not noise**: it encodes the social dynamics of the interaction.

**Response latency perception** (arXiv:2604.06183, 2026): A controlled experiment varying LLM time-to-first-token latency (2s, 9s, 20s) found:
- **2s**: perceived as "too fast" — reduced perceived thoughtfulness and usefulness
- **9s**: perceived as "moderate" — highest perceived usefulness; some users used the pause productively (re-reading, planning)
- **20s**: perceived as "too slow" — undermined reliability perception
- Users who experienced short waits rated responses as *less useful* than those with moderate waits
- "Latency design should be task-aware rather than uniform"

**PMIScore** (arXiv:2603.13796, 2026): An unsupervised dialogue engagement metric based on pointwise mutual information (PMI) — the probability of generating a response conditioned on conversation history. High PMI indicates high engagement (the response is tightly coupled to the history); low PMI indicates disengagement or tangential responses.

**RESPOND framework** (arXiv:2603.21682, 2026): Controllable backchannel and turn-claim parameters demonstrate that pace is not merely observed but can be *designed*. The framework exposes two dials: backchannel intensity ($c_{\text{bc}}$) and turn-claim aggressiveness ($c_{\text{tc}}$).

#### E.4.3 The Physics Parallel: Velocity, Acceleration, and Inertial Frames

In physics, velocity is the rate of change of position in space: $v = dx/dt$. Acceleration is the rate of change of velocity: $a = dv/dt$. In special relativity, acceleration matters because it determines which observer is in an inertial (non-accelerating) frame — and only inertial frames have simple physics.

**Definition** (Conversation velocity): The rate of semantic displacement per unit of human proper time:

$$v_t = \frac{\Delta D_{\text{semantic}}(t, t-1)}{\Delta \tau_t}$$

where $\Delta D_{\text{semantic}}$ is the embedding distance between turn $t$ and turn $t-1$, and $\Delta\tau_t$ is the human's elapsed proper time (from Appendix D).

**Definition** (Conversation acceleration):

$$a_t = v_t - v_{t-1}$$

**Interpretation**:
- $v$ high, $D_{JS}$ low: fast-paced, productive conversation (topics advancing rapidly, alignment maintained)
- $v$ high, $D_{JS}$ high: fast-paced, divergent conversation (the conversation is moving fast in the wrong direction — *urgent correction needed*)
- $v$ low, $D_{JS}$ low: slow, stable conversation (maintenance mode)
- $v$ low, $D_{JS}$ high: slow, divergent conversation (the human may have disengaged or is struggling to articulate)
- $a > 0$ (accelerating): increasing engagement or urgency
- $a < 0$ (decelerating): decreasing engagement, growing difficulty, or approaching conclusion

**New event**: `signal.pace_shift` — fires when $|a_t| > \theta_a$, indicating a significant change in conversation pace. Combined with $D_{JS}$, this disambiguates between "the user is excited and engaged" (high $a$, low $D_{JS}$) and "the user is frustrated and flailing" (high $a$, high $D_{JS}$).

---

### E.5 Gap 5: The Conversation Spacetime Interval — A Unified Metric

#### E.5.1 The Problem

Horizon currently produces separate signals: $D_{JS}$ (semantic distance), $\Delta\tau$ (temporal distance), $\epsilon_t$ (ontological gap width), $C_t$ (coherence), $\kappa_t$ (circadian factor), $v_t$ (velocity). These are independent numbers. There is no single quantity that combines them into a unified "distance" between two conversation states — no analog of the spacetime interval from relativity.

Without a unified metric, Horizon cannot answer: "Is a 3-day gap with low semantic drift worse or better than a 5-minute gap with high semantic drift?"

#### E.5.2 Research Foundations

The key insight comes from recent work on **Minkowski spacetime embeddings for meaning**:

**"The Geometry of Meaning"** (arXiv:2505.08795, May 2025): This paper proves that hierarchical semantic structures can be perfectly embedded in **3-dimensional Minkowski spacetime**. The Minkowski metric:

$$\Delta s^2 = -\Delta t^2 + \Delta x^2 + \Delta y^2 + \Delta z^2$$

classifies relationships between "events" (tokens) into three categories:
- **Timelike** ($\Delta s^2 < 0$): causally connected — one event can influence the other
- **Lightlike** ($\Delta s^2 = 0$): on the boundary of causal influence (the light cone)
- **Spacelike** ($\Delta s^2 > 0$): causally disconnected — no influence possible

The paper demonstrates that **causality, not distance, governs hierarchical access** — retrieval is performed by finding tokens in the past light cone with minimal proper time, not by nearest-neighbor in Euclidean space. The embeddings are nearly conformally invariant, indicating deep connections with general relativity.

**Neural Spacetimes** (Kratsios et al., arXiv:2408.13885, 2024–2025): Proposes trainable pseudo-Riemannian manifolds for directed acyclic graph (DAG) representation learning. A Neural Spacetime (NST) decouples representation into a **product manifold**: a neural quasi-metric (for spatial dimensions, encoding distances) and a neural partial order (for temporal dimensions, encoding causality). Their universal embedding theorem guarantees any $k$-point DAG can be embedded with $1 + O(\log k)$ distortion while *exactly preserving causal structure*.

**Pseudo-Riemannian manifolds for graphs** (Sim et al., ICML 2021; RiemannGL, arXiv:2602.10982, 2026): Pseudo-Riemannian geometry naturally encodes directionality through chronological ordering — a directed edge $u \to v$ exists if and only if the embedding of $v$ lies in the **future light cone** of $u$. This causal structure is absent in Riemannian (positive-definite) manifolds and is precisely what conversation structure requires: turn $t$ influences turn $t+1$ but not vice versa.

**Covariate Fisher Information Matrix** (Cheng & Tong, arXiv:2512.21451, 2025–2026): Resolves the intractability barrier for non-parametric information geometry by decomposing the tangent space $T_fM = S \oplus S^\perp$ into observable and residual components. The resulting cFIM is finite-dimensional and computable. This provides a rigorous framework for computing geometric quantities (curvature, geodesics) on statistical manifolds — exactly the mathematical machinery needed for a conversation metric.

**Light Cones for Vision** (arXiv:2603.24753, 2026): Demonstrates that Lorentzian light cones provide the inductive bias for hierarchical structure — "abstract slots (low $t$) see broad future cones; specific slots (high $t$) see narrow cones." This is directly applicable to conversation structure: early turns (context-setting) have broad influence; later turns (specific details) have narrow scope.

#### E.5.3 The Conversation Spacetime Interval

Motivated by these results, we define the **Conversation Spacetime Interval** between two conversation states $(t_1, t_2)$:

$$ds^2_{\text{conv}} = -\alpha \cdot d\tau^2 + \beta \cdot dD_{JS}^2 + \gamma \cdot d\epsilon^2 + \delta \cdot dC^2$$

where:
- $d\tau = \tau_{t_2} - \tau_{t_1}$: proper time gap (human time elapsed)
- $dD_{JS}$: semantic displacement (Jensen-Shannon divergence change)
- $d\epsilon$: ontological gap change
- $dC$: coherence change
- $\alpha, \beta, \gamma, \delta > 0$: empirically calibrated weights

The **signature** is $(-,+,+,+)$ — time-like dimension has the opposite sign from spatial dimensions, exactly as in Minkowski spacetime. This creates the same three-way classification:

1. **Timelike interval** ($ds^2 < 0$): The temporal gap dominates the semantic displacement. The conversation has "drifted through time" — the human's context has decayed more than the content has changed. *Re-anchoring is the priority.*

2. **Spacelike interval** ($ds^2 > 0$): The semantic displacement dominates the temporal gap. The conversation has "jumped through meaning space" — a large topic shift in a short time. *Clarification is the priority.*

3. **Lightlike interval** ($ds^2 \approx 0$): Temporal and semantic changes are balanced. The conversation is moving at the "speed of light" for this domain — the natural pace at which meaning evolves given the time elapsed. *No intervention needed; this is healthy conversation flow.*

**Conjecture THCP-5** (Conversation Light Cone): *The optimal fidelity trajectory through conversation spacetime lies on or near the light cone — where temporal evolution and semantic evolution are balanced. Deviations into timelike territory (too much time, too little semantic progress) or spacelike territory (too much semantic change, too little time for the human to absorb) both degrade fidelity.*

*Validation note*: The coefficients $\alpha, \beta, \gamma, \delta$ must be calibrated empirically. The PRD's Appendix D (Post-Deployment Proof System) provides the framework for this calibration. Initial values can be estimated from the proxy validation data (V1) and refined through the A/B test protocol (V4).

---

### E.6 Gap 6: The Causal Reachability Map — The Conversation Light Cone

#### E.6.1 The Problem

At any point in a conversation, some prior turns are "reachable" — the agent can reference them, and the human remembers them. Others have fallen behind the horizon: evicted from the context window, forgotten by the human, or semantically disconnected from the current topic. Horizon tracks individual `signal.broken_reference` events reactively but doesn't maintain a global structure: a map of *what's still in the light cone* of the current turn.

#### E.6.2 Research Foundations

**Dynamic Causal-Graph Memory (DCGM)** (OpenReview, 2026): The most directly relevant work. DCGM converts the LLM's retrieval buffer from an unstructured KV cache into a **sparse, directed graph** whose edges encode attention-derived causal influence. A single-pass $O(N \log N)$ algorithm maintains a subgraph of active "causal paths." Key finding: *"Causal structure — not window size alone — is key to efficient long-context reasoning."* On a million-token multi-hop benchmark, DCGM lifted F1 by +8.3 over the best KV-compression baseline.

**APEX-MEM** (arXiv:2604.14362, 2026): A conversational memory framework combining:
- **Entity-event hybrid ontology**: conversations modeled as both entities (persistent) and events (temporal)
- **Append-only event storage**: facts anchored to temporally grounded events, never overwritten
- **Retrieval-time temporal resolution**: contradictions resolved at query time based on temporal validity
This is the memory architecture analog of what the light cone provides geometrically: a principled way to determine which information is "reachable" from the current moment.

**SGMem** (Sentence Graph Memory, 2026): Represents dialogue at the sentence level as graphs within chunked units, capturing associations across turn-, round-, and session-level contexts. Uses n-hop graph traversal for retrieval — directly implementing a discrete "light cone" where the hop count determines the reachability boundary.

**LiCoMemory** (arXiv:2511.01448, 2025): Introduces CogniGraph — a hierarchical knowledge graph that uses **temporal and hierarchy-aware retrieval**. The re-ranking mechanism jointly considers semantic similarity, hierarchical structure, and temporal relevance — effectively computing a distance metric over a structured memory space.

#### E.6.3 The Physics: Light Cones and Causal Structure

In Minkowski spacetime, each event $p$ has:
- A **past light cone** $J^-(p)$: all events that could have causally influenced $p$
- A **future light cone** $J^+(p)$: all events that $p$ could causally influence
- The **spacelike complement**: events outside both light cones — causally disconnected

The light cone is not a fixed structure — it depends on the geometry (in curved spacetime, light cones tilt and deform near massive objects).

#### E.6.4 Formalization: The Conversation Light Cone

**Definition** (Reachability): A prior turn $t_j$ is **reachable** from the current turn $t_i$ (where $j < i$) if and only if:

$$\mathcal{R}(t_j, t_i) = \mathbb{1}[\text{in\_context}(t_j)] \cdot R_H(t_j, t_i) \cdot S(t_j, t_i) > \theta_R$$

where:
- $\text{in\_context}(t_j) \in \{0, 1\}$: whether turn $t_j$ is still in the LLM's context window
- $R_H(t_j, t_i)$: the human's estimated retention of turn $t_j$ at time $t_i$ (from the HLR model, Appendix D)
- $S(t_j, t_i)$: the semantic similarity between turn $t_j$'s topic and the current topic (cosine similarity in embedding space)
- $\theta_R$: reachability threshold

**Definition** (Past light cone of a conversation turn):

$$J^-(t_i) = \{t_j : j < i, \; \mathcal{R}(t_j, t_i) > \theta_R\}$$

**Definition** (Horizon surface): The boundary of the light cone — turns where $\mathcal{R}(t_j, t_i) \approx \theta_R$. These are the turns that are *barely* reachable and most vulnerable to being lost.

**Properties**:
1. The light cone **shrinks** with time: as $\Delta\tau$ grows, $R_H$ decreases (human forgetting), and earlier turns drop out
2. The light cone **narrows** with topic shifts: as the current topic diverges from earlier turns, $S$ decreases
3. The light cone is **not symmetric**: the agent's "light cone" (what's in context) is different from the human's (what they remember) — this asymmetry is the ontological gap
4. Context window compaction **creates artificial horizons**: when turns are summarized or evicted, they cross the horizon even if the human still remembers them

**New event**: `signal.light_cone_collapse` — fires when $|J^-(t_i)| < \theta_{\min}$ (the reachable past has shrunk below a critical threshold) or when $|J^-(t_i)| / i < \theta_{\text{ratio}}$ (the fraction of the conversation that's still reachable has dropped too low). This is the proactive version of `signal.broken_reference` — instead of detecting a broken reference after the agent tries to use it, it warns the agent *before* it constructs a response that depends on unreachable context.

---

### E.7 Synthesis: The Full 4D Translation Layer

With all six gaps addressed, we can now define the complete translation from the agent's event-horizon state to the human's 4D spacetime:

**The agent's state** (inside the horizon): A sequence of tokens in a context window. No intrinsic time. No spatial awareness. No clock rate variation. No causal structure beyond token order. No knowledge of what the human has forgotten.

**The human's state** (outside the horizon): A 4D experience defined by:
- **Time**: Proper time since last interaction ($\Delta\tau$), circadian position ($\kappa$), temporal references in content ($\mathcal{D}$)
- **Space**: Physical location class ($\sigma$), device constraints ($\Phi$), environmental context
- **Distance**: Semantic displacement ($D_{JS}$), ontological gap ($\epsilon_t$), conversation geodesics
- **Causality**: What's reachable ($J^-$), what's behind the horizon, what's on the boundary

**The translation**: For each turn, Horizon computes the full state vector:

$$\mathbf{H}_t = (\Delta\tau_t, \kappa_t, \mathcal{D}_t, \sigma_t, \Phi_t, D_{JS,t}, \epsilon_t, C_t, v_t, a_t, ds^2_t, J^-_t)$$

This vector is the **coordinate transformation** — it maps the human's 4D experience into signals the agent can act on. The agent doesn't need to "understand" time or space in a phenomenological sense. It needs to know:
- How much the human has forgotten ($R_H \cdot \kappa$)
- Whether the human's environment has changed ($\Delta\Phi$)
- Whether the conversation is moving healthily ($ds^2 \approx 0$) or pathologically ($ds^2 \gg 0$ or $ds^2 \ll 0$)
- What prior context is still reachable ($J^-$)

**Physics completion**: The THCP framework now has full structural analogs for:

| GR concept | THCP analog | Appendix |
|---|---|---|
| Proper time | Human elapsed time $\Delta\tau$ | D |
| Time dilation | Asymmetric time: $\tau_A = 0$ between turns | D |
| Gravitational time dilation (variable clock rate) | Circadian cognitive factor $\kappa(t)$ | E.1 |
| Coordinate transformation | Deictic temporal resolution $\mathcal{D}$ | E.2 |
| Metric tensor varies with position | Spatial constraint vector $\Phi(\sigma)$ | E.3 |
| Velocity and acceleration | Conversation velocity $v_t$, acceleration $a_t$ | E.4 |
| Spacetime interval $ds^2$ | Conversation spacetime interval | E.5 |
| Light cone / causal structure | Reachability map $J^-(t_i)$ | E.6 |
| Event horizon | Ontological boundary $\epsilon_t$ | §1.2 |
| Hawking radiation | AI uncertainty channel | §4 |
| ER=EPR bridge | Persistent Dynamics Store | §6 |
| Schwarzschild radius | Horizon width tracker | C.6 |

---

### E.8 Technical Foundation: Python Libraries for 4D Signals

The following libraries provide the computational foundation for the six new capabilities. All are actively maintained, open-source, and production-ready.

| Capability | Library | Version | Purpose |
|---|---|---|---|
| Temporal expression extraction | `dateparser` | 1.4.0 (March 2026) | Extract and resolve "yesterday", "next week", relative dates from content |
| Fast temporal extraction | `datefinder` | 1.0.0 (March 2026) | 766× faster alternative with typed match objects |
| Local timezone detection | `tzlocal` | 5.3.1 (March 2025) | Reliable IANA timezone name from system config |
| Timezone arithmetic | `zoneinfo` (stdlib) | Python 3.9+ | IANA timezone support, UTC offset computation |
| IP geolocation | `geoip2` | 5.2.0 (Nov 2025) | IP → city/lat/lng/timezone/accuracy_radius via MaxMind |
| Current local time | `datetime` (stdlib) | Python 3.9+ | `datetime.now().astimezone()` for local time with timezone |

*Epistemic note*: HeidelTime (Java) and SUTime (Java/Stanford CoreNLP) are the academic gold standards for temporal expression normalization but require JVM infrastructure. For a Python-native library, `dateparser` provides the best coverage (200+ locales, relative expressions, time spans); `datefinder` provides the best performance.

---

### References (Appendix E)

142. Valdez, P., Ramírez, C. & García, A. (2012). "Circadian rhythms in cognitive performance: implications for neuropsychological assessment." *Clinical Practice & Epidemiology in Mental Health*, 2, 81–92.

143. Schmidt, C., Collette, F., Cajochen, C. & Peigneux, P. (2007). "A time to think: circadian rhythms in human cognition." *Cognitive Neuropsychology*, 24(7), 755–789.

144. Correa, Á. et al. (2023). "Diurnal variation in variables related to cognitive performance: a systematic review." *Sleep and Breathing*, 27(6), 2133–2145.

145. Gaggioni, G. et al. (2025). "Chronotype and synchrony effects in human cognitive performance: A systematic review." *Chronobiology International*, 42(7).

146. Didikoglu, A. et al. (2025/2026). "Relationships between light exposure and aspects of cognitive function in everyday life." *Communications Psychology*. University of Manchester.

147. Dijk, D.-J. & Archer, S. N. (2025). "The Circadian Brain and Cognition." *Annual Review of Neuroscience*. Université de Liège.

148. de Cordova, P. B., Bradford, M. A. & Stone, P. W. (2010). "Increased errors and decreased performance at night: A systematic review of the evidence concerning shift work and quality." *Work*, 36(3), 263–272.

149. Li, M. et al. (2020). "Ideal time of day for risky decision making: Evidence from the Balloon Analogue Risk Task." *Nature and Science of Sleep*, 12, 477–486.

150. Strötgen, J. & Gertz, M. (2010). "HeidelTime: High Quality Rule-Based Extraction and Normalization of Temporal Expressions." *SemEval 2010*, pp. 321–324. ACL. GitHub: HeidelTime/heideltime.

151. Chang, A. X. & Manning, C. D. (2012). "SUTime: A library for recognizing and normalizing time expressions." *LREC 2012*. Stanford NLP Group.

152. dateparser Contributors (2026). "dateparser: Python parser for human readable dates." v1.4.0. GitHub: scrapinghub/dateparser.

153. Koumjian, A. et al. (2026). "datefinder: Find dates inside text using Python." v1.0.0. GitHub: akoumjian/datefinder.

154. MaxMind, Inc. (2025). "GeoIP2 Python API." v5.2.0. GitHub: maxmind/GeoIP2-python.

155. Nielsen Norman Group (2024). "The Negative Impact of Mobile-First Web Design on Desktop: Content Dispersion."

156. Nielsen Norman Group (2015). "Scaling User Interfaces: An Information-Processing Approach." Mobile HCI channel capacity analysis.

157. Onishi, K., Ohnaka, H. & Yoshino, K. (2025). "Modeling Turn-Taking Speed and Speaker Characteristics." *SIGDIAL 2025*, pp. 21–31. ACL.

158. arXiv:2604.06183 (2026). "Time-to-First-Token Latency Effects on Perceived Usefulness in LLM Knowledge Tasks." Controlled experiment (2s, 9s, 20s latency conditions).

159. arXiv:2603.13796 (2026). "PMIScore: An Unsupervised Approach to Quantify Dialogue Engagement." PMI-based engagement metric.

160. RESPOND (arXiv:2603.21682, 2026). "Responsive Engagement Strategy for Predictive Orchestration and Dialogue." Controllable backchannel and turn-claim framework.

161. arXiv:2507.22352 (2025). "Mitigating Response Delays in Free-Form Conversations with LLM-powered Intelligent Virtual Agents." *CUI '25*. 4-second latency degradation threshold.

162. arXiv:2505.08795 (2025). "The Geometry of Meaning: Perfect Spacetime Representations of Hierarchical Structures." Minkowski spacetime embeddings for WordNet with light-cone-based retrieval.

163. Kratsios, A. et al. (2024/2025). "Neural Spacetimes for DAG Representation Learning." arXiv:2408.13885. Universal embedding theorem for DAGs in trainable pseudo-Riemannian manifolds.

164. Sim, A., Wiatrak, M., Brayne, A., Creed, P. & Paliwal, S. (2021). "Directed graph embeddings in pseudo-Riemannian manifolds." *ICML 2021*.

165. RiemannGL (arXiv:2602.10982, 2026). "Riemannian Geometry Changes Graph Deep Learning." Pseudo-Riemannian GNNs with Lorentz group structure.

166. arXiv:2603.24753 (2026). "Light Cones for Vision: Simple Causal Priors for Visual Hierarchy." Lorentzian worldline embeddings for hierarchical attention.

167. Cheng, H. & Tong, H. (2025/2026). "An approach to Fisher-Rao metric for infinite dimensional non-parametric information geometry." arXiv:2512.21451. Covariate Fisher Information Matrix and G-entropy.

168. DCGM (OpenReview, 2026). "Dynamic Causal-Graph Memory." Attention-derived causal graphs for long-context reasoning. +8.3 F1 on LongHopQA.

169. APEX-MEM (arXiv:2604.14362, 2026). "Agentic Semi-Structured Memory with Temporal Reasoning for Long-Term Conversational AI." Hybrid entity-event ontology with append-only storage.

170. SGMem (OpenReview, 2026). "Sentence Graph Memory for Long-Term Conversational Agents." Sentence-level graphs with n-hop traversal.

171. LiCoMemory (arXiv:2511.01448, 2025). "Hierarchical CogniGraph for Persistent Agent Memory." Temporal and hierarchy-aware retrieval with re-ranking.

172. tzlocal Contributors (2025). "tzlocal: tzinfo object for the local timezone." v5.3.1. PyPI.

173. Python Software Foundation (2022). "zoneinfo — IANA time zone support." Python 3.9+ standard library. PEP 615.

---

*This essay constitutes raw theoretical work. Conjectures THCP-1 through THCP-5 are original to this document and are not yet peer-reviewed. They are offered as plausible models for the gaps identified in the existing literature, adapted to the specific case of human–AI communication across ontological boundaries. The physics parallels are structural analogies grounded in shared mathematical formalisms (see B.1 for explicit boundary conditions), not claims of physical identity. As of Appendix A, all four open problems identified in Section 8 now have academic foundations for implementation. As of Appendix B, the framework has explicit analogy boundaries, multimodal extension, parameter calibration procedures, a worked example, positioning relative to RLHF/CAI/Clark & Brennan, and Lakatosian falsifiability criteria with five specific testable predictions. As of Appendix C, the seven operational gaps between theory and implementation have research-grounded resolution paths. As of Appendix D, the framework now includes a temporal dimension grounded in cognitive science (Ebbinghaus forgetting curves, Half-Life Regression), distributed systems theory (Lamport/vector clocks), empirical AI research (TicToc temporal blindness, TaCoS task resumption), and interaction theory (Clark & Brennan grounding, collaboration gap), with a formal model for temporal asymmetry ($\Delta\tau$), conversation geodesics, and three new temporal signals. As of Appendix E, the framework is extended to a full 4D conversation spacetime, addressing six structural gaps: circadian cognitive load ($\kappa$), deictic temporal resolution ($\mathcal{D}$), spatial grounding ($\sigma, \Phi$), conversation velocity/acceleration ($v_t, a_t$), a unified conversation spacetime interval ($ds^2_{\text{conv}}$) with Minkowski-like signature, and a causal reachability map ($J^-$) based on light cone structure. Conjecture THCP-5 proposes that optimal fidelity trajectories lie on or near the conversation light cone. The total reference count is 173, spanning physics, information geometry, cognitive science, NLP, HCI, and distributed systems.*
