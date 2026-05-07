# Horizon Fidelity Monitor — Technical Specification

*Leo Celis · April 2026*

**Based on**: [PRD](./THCP_FIDELITY_MONITOR_PRD.md) · [Research](./TRANS_HORIZON_COMMUNICATION_HUMAN_AI_THEORETICAL_FRAMEWORK.md) · [Intent](./horizon_intent.yaml)

---

## 1. Overview

This document translates the PRD's *what* into the engineer's *how*. Every field is typed, every algorithm is pseudocoded with edge cases, and every decision that the PRD left open is resolved. An engineer reading this document should be able to implement Horizon without consulting any other source.

**Scope**: The core library (`horizon` Python package). Integration adapters, the calibration engine, and the shared fidelity dashboard are out of scope for this spec and will have their own specs.

**Python version**: 3.10+ (for `match` statements, `|` union types, `dataclasses` with `slots=True`).

---

## 2. Data Models

All public types are frozen dataclasses. Internal mutation happens on `Session` state objects, never on return types. All float fields use `float` (IEEE 754 double precision).

### 2.1 Configuration

```python
from dataclasses import dataclass, field
from typing import Literal

@dataclass(frozen=True)
class Config:
    # Core thresholds
    clarification_threshold: float = 0.35       # D_JS above this → checkpoint.clarification
    convergence_window: int = 3                  # consecutive low-IGT turns
    convergence_threshold: float = 0.1           # IGT trend below this = converging
    drift_window: int = 4                        # consecutive fidelity-declining turns
    verbosity_threshold: float = 0.5             # TWR above this → alert.verbosity
    consistency_threshold: float = 0.6           # consistency below this → alert.contradiction
    consistency_method: Literal["fast", "nli"] = "fast"

    # Fidelity dynamics weights
    alpha: float = 0.3                           # semantic information absorption
    lambda_r: float = 0.1                        # recoverable drift penalty
    lambda_i: float = 0.3                        # irreversible loss penalty
    beta: float = 0.2                            # D_JS penalty
    gamma: float = 0.1                           # temporal asymmetry penalty (Δτ)
    delta: float = 0.05                          # circadian penalty (1 - κ)

    # Composite score weights
    w_igt: float = 0.3
    w_djs: float = 0.3
    w_twr: float = 0.15
    w_consistency: float = 0.25

    # Temporal
    context_half_life_hours: float = 24.0        # h_c for HLR model
    temporal_desync_threshold_seconds: float = 3600.0
    chronotype_offset: float = 0.0               # hours to shift κ curve

    # 4D spacetime
    pace_shift_threshold: float = 0.3            # |a_t| threshold
    light_cone_ratio_threshold: float = 0.3      # |J⁻|/i threshold
    light_cone_min_threshold: int = 3            # minimum |J⁻| absolute
    reachability_threshold: float = 0.1          # θ_R for reachability
    broken_reference_threshold: float = 0.3      # reachable_fraction below this → signal.broken_reference (if turn_count > 5)
    spacetime_alpha: float = 1.0                 # ds² time coefficient
    spacetime_beta: float = 1.0                  # ds² D_JS coefficient
    spacetime_gamma: float = 1.0                 # ds² ε coefficient
    spacetime_delta: float = 1.0                 # ds² coherence coefficient

    # Conversation mode
    conversation_mode: Literal["auto", "execute", "explore", "refine", "learn"] = "auto"
    domain: str = "general"

    # Embedding
    embedding_model: str = "all-MiniLM-L6-v2"
    model_path: str | None = None                # local filesystem path to pre-downloaded model (overrides embedding_model when set)

    # Event modes: event_type → "active" | "observe"
    event_modes: dict[str, Literal["active", "observe"]] = field(default_factory=dict)
    # Default: all observe. Any event not in this dict defaults to "observe".
```

**Mapping to `configure()` object parameters (from `horizon_intent.yaml::interface.tools.configure`):**

The intent's `configure()` exposes three compound parameters that are flattened into the individual `Config` fields above:

| `configure()` parameter | `Config` fields it writes |
|---|---|
| `fidelity_weights={alpha,lambda_r,lambda_i,beta}` | `alpha`, `lambda_r`, `lambda_i`, `beta` |
| `temporal_weights={gamma,delta}` | `gamma`, `delta` |
| `spacetime_coefficients={alpha,beta,gamma,delta_st}` | `spacetime_alpha`, `spacetime_beta`, `spacetime_gamma`, `spacetime_delta` |

The `embedding_model` parameter accepts the logical values from the intent (`local-sentence-transformer | openai-text-embedding-3-small | custom`) and the implementation resolves them to a concrete identifier (`all-MiniLM-L6-v2` for `local-sentence-transformer`, the HuggingFace / OpenAI model slug for the others). The `model_path` field is an opt-in escape hatch for air-gapped installs and local weights; when set, it takes precedence over `embedding_model`.

### 2.2 Turn Result

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class TemporalReference:
    expression: str                              # "yesterday", "next Monday"
    resolved: Optional[str]                      # ISO 8601 or None if unresolvable
    type: Literal["DATE", "TIME", "DURATION", "SET", "UNKNOWN"]

@dataclass(frozen=True)
class SpatialConstraint:
    attention_budget: Literal["high", "medium", "low"]
    screen_capacity: Literal["large", "medium", "small"]
    max_response_length: int                     # suggested max tokens
    complexity_ceiling: Literal["high", "medium", "low"]

@dataclass(frozen=True)
class Event:
    type: str                                    # e.g. "checkpoint.clarification"
    active: bool                                 # from config event_modes
    confidence: float                            # [0, 1]
    turn: int
    suggested_behavior: str
    mode: Optional[str]                          # conversation mode when event fired
    metadata: dict = field(default_factory=dict) # signal-specific data

@dataclass(frozen=True)
class TurnResult:
    # Core (always present)
    turn_number: int
    igt_value: float                             # [0, ∞) in bits
    igt_trend: float                             # slope over last N turns
    divergence_score: float                      # [0, 1]
    twr_value: float                             # [0, 1]
    consistency_score: float                     # [0, 1]
    fidelity_score: float                        # [0, 1] (clamped)
    health_status: Literal["healthy", "degrading", "critical", "converged"]
    degradation_type: Literal["none", "recoverable_drift", "irreversible_loss", "both"]
    events: list[Event]
    epsilon_t: float                             # estimated ontological gap
    conversation_mode: str                       # detected or configured

    # Temporal (None when timestamp not provided)
    gap_seconds: Optional[float] = None
    gap_class: Optional[Literal["realtime", "seconds", "minutes", "hours", "days"]] = None
    estimated_retention: Optional[float] = None  # [0, 1]
    temporal_asymmetry: Optional[float] = None   # >= 0
    resumption_cost: Optional[Literal["none", "low", "medium", "high", "extreme"]] = None
    circadian_factor: Optional[float] = None     # [0, 1]
    temporal_references: Optional[list[TemporalReference]] = None

    # Pace (None when timestamp not provided or turn < 2)
    conversation_velocity: Optional[float] = None
    conversation_acceleration: Optional[float] = None

    # Spacetime (None when timestamp not provided or turn < 2)
    spacetime_interval: Optional[float] = None   # ds² value
    interval_class: Optional[Literal["timelike", "spacelike", "lightlike"]] = None

    # Causal (None when timestamp not provided — see `temporal_signals_optional` constraint).
    # Reachability composes a temporal-decay term (half-life regression × κ) with context
    # eviction and semantic dissimilarity, so we cannot compute it without a wall-clock time.
    reachable_turns: Optional[int] = None
    reachable_fraction: Optional[float] = None

    # Spatial (None when client_context not provided)
    location_class: Optional[str] = None
    spatial_constraint: Optional[SpatialConstraint] = None
    spatial_frame_shift: Optional[float] = None  # |ΔΦ|, None on first turn with context
```

### 2.3 API Return Types

```python
@dataclass(frozen=True)
class FidelityTrajectory:
    session_id: str
    turn_count: int
    scores: list[float]                          # fidelity score per turn, index 0 = turn 1
    timestamps: list[Optional[str]]              # ISO 8601 per turn (None when not provided)
    gap_durations: list[Optional[float]]         # seconds between turns (None for turn 1)
    igt_trend: float                             # slope over entire trajectory
    health_status: Literal["healthy", "degrading", "critical", "converged"]
    estimated_t_star: Optional[int]              # estimated optimal length (None if not yet detectable)
    peak_fidelity: float
    current_fidelity: float

@dataclass(frozen=True)
class ConfigWarning:
    parameter: str
    message: str

@dataclass(frozen=True)
class ConfigResult:
    applied: dict                                # parameter name → applied value
    warnings: list[ConfigWarning]               # e.g. invalid IANA timezone, unknown event type

@dataclass(frozen=True)
class ExportResult:
    status: Literal["success", "partial", "failed"]
    records_exported: int
    target: str                                  # e.g. "langsmith", "json"
    target_url: Optional[str]                    # URL of exported artifact if available
    errors: list[str]                            # empty on success
```

### 2.4 Session State (Internal, Mutable)

```python
from dataclasses import dataclass, field
import numpy as np
from numpy import ndarray

@dataclass
class TurnState:
    turn_number: int
    human_embedding: ndarray                     # shape: (embed_dim,)
    agent_embedding: ndarray                     # shape: (embed_dim,)
    combined_embedding: ndarray                  # mean(human, agent)
    timestamp: Optional[str] = None              # ISO 8601 or None
    timestamp_epoch: Optional[float] = None      # seconds since Unix epoch
    client_context: Optional[dict] = None
    igt_value: float = 0.0
    divergence_score: float = 0.0
    twr_value: float = 0.0
    consistency_score: float = 1.0
    fidelity_score: float = 0.0
    epsilon_t: float = 0.0
    velocity: Optional[float] = None
    in_context: bool = True                      # tracked by context window model

@dataclass
class Session:
    session_id: str
    config: Config
    turns: list[TurnState] = field(default_factory=list)
    fidelity_trajectory: list[float] = field(default_factory=list)
    event_log: list[Event] = field(default_factory=list)
    history_embedding: Optional[ndarray] = None  # running compressed history
    detected_mode: Optional[str] = None
    context_window_tokens: int = 0               # estimated token usage
    max_context_tokens: int = 128_000            # from model config or default

    @property
    def turn_count(self) -> int:
        return len(self.turns)
```

---

## 3. Session Lifecycle

```
new_conversation(metadata) → session_id
    │
    ├── Creates Session with empty state, applies Config
    │
    ▼
process_turn(session_id, human_msg, agent_resp, ...) → TurnResult
    │
    ├── Validates session_id exists → SessionNotFoundError if not
    ├── Embeds human_msg and agent_resp
    ├── Runs signal pipeline (§4–§7)
    ├── Appends TurnState to session
    ├── Returns frozen TurnResult
    │
    ▼  (repeats)
    │
get_trajectory(session_id) → FidelityTrajectory
get_events(session_id, active_only) → list[Event]
configure(session_id, ...) → ConfigResult
export_to(session_id, target, connection) → ExportResult
```

**Session isolation**: Each `Session` is an independent object. No shared mutable state between sessions. Concurrent `process_turn` calls on *different* sessions are safe. Concurrent `process_turn` calls on the *same* session are serialized via a per-session lock.

**Session storage**: In-memory by default (`dict[str, Session]`). No persistence. The Persistent Dynamics Store (cross-session) is a separate component.

**Error cases**:

| Condition | Behavior |
|---|---|
| `process_turn` with unknown `session_id` | Raise `SessionNotFoundError` |
| `process_turn` with `turn_number` out of order | Turn number is auto-incremented, not user-provided |
| Timestamps out of chronological order | Emit warning; compute `gap_seconds` as negative; skip temporal signals for that turn |
| Embedding model fails to load | Raise `EmbeddingModelError` on first `process_turn`, not on `new_conversation` (lazy init) |
| `client_context.ip_address` is RFC1918 / private | Set `location_class = "unknown"`; proceed without geolocation |
| `client_context.timezone` is invalid IANA name | Fall back to UTC; emit warning in `ConfigResult` |

---

## 4. Embedding Layer

The embedding layer is the only ML component in the core pipeline. It converts text to dense vectors.

### 4.1 Initialization (Lazy)

```python
# Called once on first process_turn, not on import or new_conversation.
from sentence_transformers import SentenceTransformer

class EmbeddingEngine:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2",
                 model_path: Optional[str] = None):
        self._model: Optional[SentenceTransformer] = None
        self._model_name = model_name
        self._model_path = model_path
        self._dim: Optional[int] = None

    def _ensure_loaded(self):
        if self._model is None:
            source = self._model_path or self._model_name
            self._model = SentenceTransformer(source)
            self._dim = self._model.get_sentence_embedding_dimension()

    # Public alias so tests / integration code can eagerly warm the model
    # before patching the network (e.g. privacy tests block socket.connect
    # after the weights have been cached).
    def ensure_loaded(self) -> None:
        self._ensure_loaded()

    def embed(self, text: str) -> ndarray:
        self._ensure_loaded()
        return self._model.encode(text, normalize_embeddings=True)

    @property
    def dim(self) -> int:
        self._ensure_loaded()
        return self._dim
```

**Normalization**: All embeddings are L2-normalized at encode time (`normalize_embeddings=True`). This means cosine similarity == dot product, saving one operation per comparison.

### 4.3 Model Download and Caching

The default model (`all-MiniLM-L6-v2`) is ~80MB (22M parameters, 384-dim output). On first invocation, `sentence-transformers` downloads from HuggingFace Hub to `~/.cache/huggingface/hub/`. Subsequent runs load from cache with no network call.

**Cold-start budget:**

| Step | Duration (typical) | Notes |
|---|---|---|
| `pip install horizon-monitor` | 30–60s | Installs sentence-transformers + torch (~500MB total) |
| First `process_turn` — model download | 15–45s | ~80MB on 10+ Mbps connection |
| First `process_turn` — model load | 2–5s | CPU; faster on SSD |
| **Total cold start** | **~1–2 min** | Within 3-minute TTFV target on standard connections |

**Offline / air-gapped installs:** set `Config.model_path` to a local directory containing the pre-downloaded sentence-transformer weights; `EmbeddingEngine._ensure_loaded` (see §4.1) selects that path over `embedding_model` and performs zero network I/O. The `[bundled]` pip extra pre-packages weights inside the wheel, and the Docker image (§16.3) bakes them at build time. Together these satisfy the `no_external_calls_default` constraint under every install mode.

### 4.2 History Embedding

The conversation history is compressed into a single vector that represents "what the conversation has covered so far." This is used by IGT and TWR.

**Algorithm**: Exponentially weighted running mean.

```python
def update_history(session: Session, new_combined: ndarray, decay: float = 0.9):
    if session.history_embedding is None:
        session.history_embedding = new_combined.copy()
    else:
        session.history_embedding = (
            decay * session.history_embedding + (1 - decay) * new_combined
        )
        # Re-normalize to unit sphere
        norm = np.linalg.norm(session.history_embedding)
        if norm > 0:
            session.history_embedding /= norm
```

**Why exponentially weighted**: A simple mean gives equal weight to turn 1 and turn 50. The exponential decay weights recent turns more heavily, matching the agent's attention pattern (more recent context is more relevant). `decay=0.9` means a turn's influence halves after ~7 subsequent turns.

**Edge case — turn 1**: History is initialized to the first turn's combined embedding. IGT for turn 1 is computed differently (see §5.1).

---

## 5. Core Signal Algorithms

### 5.1 Information Gain per Turn (IGT)

**What it measures**: How much new semantic content this turn adds beyond what the conversation already covered.

```python
def compute_igt(combined_embedding: ndarray, history_embedding: ndarray,
                turn_number: int) -> float:
    if turn_number == 1:
        # First turn: all information is new. Return a baseline high value.
        return 1.0

    # Cosine similarity between this turn and compressed history
    # (both L2-normalized, so dot product = cosine similarity)
    similarity = float(np.dot(combined_embedding, history_embedding))

    # Clamp to valid range (floating point can exceed [-1, 1] slightly)
    similarity = max(-1.0, min(1.0, similarity))

    # Information gain = the orthogonal component
    # If similarity = 1.0 (identical to history), gain = 0
    # If similarity = 0.0 (fully orthogonal), gain = 1.0
    # Negative similarity (contradiction) counts as high gain
    igt = 1.0 - similarity

    return max(0.0, igt)
```

**IGT trend**: Slope of IGT over the last `convergence_window` turns, computed via linear regression.

```python
def compute_igt_trend(session: Session, window: int) -> float:
    if session.turn_count < 2:
        return 0.0

    recent = [t.igt_value for t in session.turns[-window:]]
    if len(recent) < 2:
        return 0.0

    # Simple linear regression: slope of IGT values over index
    x = np.arange(len(recent), dtype=float)
    slope = np.polyfit(x, recent, 1)[0]
    return float(slope)
```

### 5.2 Intent–Response Divergence (D_JS Proxy)

**What it measures**: How well the agent's response aligns with the human's stated intent.

```python
def compute_divergence(human_embedding: ndarray, agent_embedding: ndarray) -> float:
    # Both L2-normalized. Cosine similarity = dot product.
    similarity = float(np.dot(human_embedding, agent_embedding))
    similarity = max(-1.0, min(1.0, similarity))

    # D_JS proxy: 0 = perfectly aligned, 1 = maximally divergent
    divergence = (1.0 - similarity) / 2.0  # map [-1, 1] → [0, 1]

    return divergence
```

**Why `/2.0`**: Cosine similarity ranges from -1 to 1. The mapping `(1 - sim) / 2` maps this to [0, 1] where 0 = identical and 1 = opposite directions. This is a monotonic proxy for Jensen-Shannon divergence (the true JSD would require probability distributions, not vectors).

### 5.3 Token Waste Ratio (TWR)

**What it measures**: Fraction of the agent's response that is semantically redundant with prior conversation.

```python
def compute_twr(agent_response: str, session: Session,
                embed_fn, threshold: float = 0.85) -> float:
    if session.turn_count == 0:
        return 0.0  # First turn: nothing to be redundant with

    # Split agent response into sentences
    sentences = split_sentences(agent_response)
    if not sentences:
        return 0.0

    # Embed all sentences in batch
    sent_embeddings = [embed_fn(s) for s in sentences]

    # Compare each sentence against all prior turn embeddings
    waste_count = 0
    for sent_emb in sent_embeddings:
        for prior_turn in session.turns:
            sim = float(np.dot(sent_emb, prior_turn.agent_embedding))
            if sim > threshold:
                waste_count += 1
                break  # counted as waste; no need to check further

    return waste_count / len(sentences)


def split_sentences(text: str) -> list[str]:
    """Split text into sentences. Simple heuristic: split on .!? followed by space or end."""
    import re
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s for s in sentences if len(s.split()) >= 3]  # filter out trivial fragments
```

**Threshold 0.85**: A sentence with > 0.85 cosine similarity to a prior turn's agent response is considered a paraphrase/repetition. This threshold is calibrated during V1 validation.

### 5.4 Conversation Coherence — Tier 1 (Bipredictability)

**What it measures**: Structural consistency between the context, response, and expected next prompt.

```python
def compute_bipredictability(human_embedding: ndarray, agent_embedding: ndarray,
                             history_embedding: ndarray) -> float:
    if history_embedding is None:
        return 1.0  # First turn: coherent by definition

    # Shared predictability: how well the agent response bridges
    # the history and the human's new input
    # Triangle of similarities:
    h_a = float(np.dot(history_embedding, agent_embedding))  # history → agent
    h_h = float(np.dot(history_embedding, human_embedding))  # history → human
    a_h = float(np.dot(agent_embedding, human_embedding))    # agent → human

    # Bipredictability: high when all three are mutually consistent
    # Low when any pair is divergent while others are similar
    P = (h_a + h_h + a_h) / 3.0

    # Normalize to [0, 1] from [-1, 1] mean range
    score = (P + 1.0) / 2.0
    return max(0.0, min(1.0, score))
```

**Latency**: Three dot products = < 1ms. No model call.

### 5.5 Composite Fidelity Score

The snapshot fidelity score (current turn quality):

```python
def compute_snapshot_fidelity(igt: float, djs: float, twr: float,
                               consistency: float, config: Config) -> float:
    score = (
        config.w_igt * min(igt, 1.0) +            # cap IGT contribution at 1.0
        config.w_djs * (1.0 - djs) +
        config.w_twr * (1.0 - twr) +
        config.w_consistency * consistency
    )
    return max(0.0, min(1.0, score))
```

The dynamic fidelity score (trajectory-aware, with temporal and circadian penalties):

```python
def compute_dynamic_fidelity(
    prev_fidelity: float,
    igt: float,
    djs: float,
    delta_recoverable: float,     # estimated from TWR increase
    delta_irreversible: float,    # estimated from context window eviction
    delta_tau: float,             # temporal asymmetry penalty
    kappa: float,                 # circadian factor (1.0 if no timestamp)
    config: Config,
) -> float:
    f = (
        prev_fidelity
        + config.alpha * min(igt, 1.0)
        - config.lambda_r * delta_recoverable
        - config.lambda_i * delta_irreversible
        - config.beta * djs
        - config.gamma * delta_tau
        - config.delta * (1.0 - kappa)
    )
    return max(0.0, min(1.0, f))
```

**Edge case — turn 1**: `prev_fidelity` is initialized to the snapshot fidelity of turn 1. All delta terms are 0 for the first turn.

**Determining `delta_recoverable` vs `delta_irreversible`**: If fidelity decreased and context window has not been compacted since the last turn, the loss is classified as recoverable. If context tokens were evicted between turns (see §8), the loss is irreversible.

### 5.6 Health Status

```python
def compute_health(session: Session, fidelity: float,
                   igt_trend: float, config: Config) -> str:
    if igt_trend < config.convergence_threshold and session.turn_count >= config.convergence_window:
        recent_igt = [t.igt_value for t in session.turns[-config.convergence_window:]]
        if all(v < config.convergence_threshold for v in recent_igt):
            return "converged"

    trajectory = session.fidelity_trajectory
    if len(trajectory) >= config.drift_window:
        recent = trajectory[-config.drift_window:]
        if all(recent[i] > recent[i + 1] for i in range(len(recent) - 1)):
            if fidelity < 0.3:
                return "critical"
            return "degrading"

    return "healthy"
```

---

## 6. 4D Spacetime Layer

All signals in this section return `None` when `timestamp` is not provided (constraint: `temporal_signals_optional`). The spatial signals return `None` when `client_context` is not provided (constraint: `spatial_signals_optional`).

### 6.1 Temporal Gap and Classification

```python
from datetime import datetime, timezone as tz

def compute_temporal_gap(current_ts: str, prev_ts: Optional[str]) -> tuple[float, str]:
    if prev_ts is None:
        return 0.0, "realtime"

    current = datetime.fromisoformat(current_ts)
    prev = datetime.fromisoformat(prev_ts)
    gap = (current - prev).total_seconds()

    gap_class = classify_gap(gap)
    return gap, gap_class

def classify_gap(seconds: float) -> str:
    if seconds < 1:
        return "realtime"
    elif seconds < 60:
        return "seconds"
    elif seconds < 3600:
        return "minutes"
    elif seconds < 86400:
        return "hours"
    else:
        return "days"
```

### 6.2 Circadian Cognitive Factor κ(t)

```python
def compute_circadian_factor(timestamp: str, timezone_str: Optional[str],
                              chronotype_offset: float = 0.0) -> float:
    from zoneinfo import ZoneInfo

    dt = datetime.fromisoformat(timestamp)

    if timezone_str:
        try:
            local_tz = ZoneInfo(timezone_str)
            dt = dt.astimezone(local_tz)
        except (KeyError, ValueError):
            pass  # fall back to timestamp's own timezone

    hour = dt.hour + dt.minute / 60.0 - chronotype_offset
    hour = hour % 24  # wrap around

    if 7.0 <= hour < 10.0:
        return 0.5 + 0.5 * (hour - 7.0) / 3.0       # morning ramp: 0.5 → 1.0
    elif 10.0 <= hour < 14.0:
        return 1.0                                      # peak 1
    elif 14.0 <= hour < 16.0:
        return 0.7                                      # post-lunch dip
    elif 16.0 <= hour < 22.0:
        return 1.0                                      # peak 2
    elif 22.0 <= hour or hour < 4.0:
        # nocturnal decline: 0.7 → 0.3
        if hour >= 22.0:
            t = hour - 22.0
        else:
            t = hour + 2.0  # hours past 22:00
        return max(0.3, 0.7 - 0.4 * t / 6.0)
    else:  # 4.0 <= hour < 7.0
        return 0.3                                      # nadir
```

### 6.3 Estimated Human Retention

```python
def compute_retention(gap_seconds: float, h_c_hours: float,
                       kappa: float) -> float:
    if gap_seconds <= 0:
        return 1.0

    h_c_seconds = h_c_hours * 3600.0
    R = 2.0 ** (-gap_seconds / h_c_seconds)

    # Adjust for circadian position
    R_adjusted = R * kappa

    return max(0.0, min(1.0, R_adjusted))
```

### 6.4 Temporal Asymmetry Penalty (Δτ)

```python
def compute_temporal_asymmetry_penalty(gap_seconds: float, h_c_hours: float,
                                        kappa: float,
                                        w_memory: float = 1.0) -> float:
    if gap_seconds < 60:  # less than 1 minute: penalty ≈ 0
        return 0.0

    retention = compute_retention(gap_seconds, h_c_hours, kappa)
    delta_tau = (1.0 - retention) * w_memory

    return delta_tau
```

### 6.5 Resumption Cost

```python
def compute_resumption_cost(gap_seconds: float, retention: float) -> str:
    if gap_seconds < 60:
        return "none"
    elif gap_seconds < 300 and retention > 0.8:
        return "low"
    elif gap_seconds < 3600 and retention > 0.5:
        return "medium"
    elif gap_seconds < 86400:
        return "high"
    else:
        return "extreme"
```

### 6.6 Deictic Temporal Resolution

```python
def resolve_deictic_expressions(text: str, reference_timestamp: str
                                 ) -> list[TemporalReference]:
    import dateparser

    base_dt = datetime.fromisoformat(reference_timestamp)

    results = dateparser.search.search_dates(
        text,
        settings={
            'RELATIVE_BASE': base_dt,
            'RETURN_AS_TIMEZONE_AWARE': True,
        }
    )

    if not results:
        return []

    refs = []
    for expression, resolved_dt in results:
        # Classify type
        expr_lower = expression.lower()
        if any(w in expr_lower for w in ["hour", "minute", "second", "am", "pm", ":"]):
            ref_type = "TIME"
        elif any(w in expr_lower for w in ["week", "month", "year", "day"]):
            ref_type = "DURATION" if any(w in expr_lower for w in ["for", "during", "past"]) else "DATE"
        else:
            ref_type = "DATE"

        refs.append(TemporalReference(
            expression=expression,
            resolved=resolved_dt.isoformat() if resolved_dt else None,
            type=ref_type,
        ))

    return refs
```

**Edge case**: `dateparser` can return false positives (e.g., "May" as a name, not a month). The consumer should treat `temporal_references` as suggestions, not ground truth. Unresolvable expressions produce `resolved=None`.

### 6.7 Conversation Velocity and Acceleration

```python
def compute_velocity(current_embedding: ndarray, prev_embedding: ndarray,
                      gap_seconds: float) -> Optional[float]:
    if gap_seconds <= 0:
        return None  # no proper time elapsed

    semantic_displacement = 1.0 - float(np.dot(current_embedding, prev_embedding))
    semantic_displacement = max(0.0, semantic_displacement)

    velocity = semantic_displacement / gap_seconds
    return velocity

def compute_acceleration(current_velocity: Optional[float],
                          prev_velocity: Optional[float]) -> Optional[float]:
    if current_velocity is None or prev_velocity is None:
        return None
    return current_velocity - prev_velocity
```

**Units**: Velocity is in "semantic displacement per second." Acceleration is in "semantic displacement per second per turn." These are abstract units — the absolute values are less important than the relative change (acceleration is the actionable signal).

### 6.8 Spacetime Interval

```python
def compute_spacetime_interval(
    d_tau: float,           # proper time gap (seconds)
    d_djs: float,           # change in D_JS between turns
    d_epsilon: float,       # change in ε_t between turns
    d_coherence: float,     # change in consistency score between turns
    config: Config,
) -> tuple[float, str]:
    ds2 = (
        -config.spacetime_alpha * d_tau ** 2
        + config.spacetime_beta * d_djs ** 2
        + config.spacetime_gamma * d_epsilon ** 2
        + config.spacetime_delta * d_coherence ** 2
    )

    # Normalize d_tau to avoid dominating by raw seconds
    # Use log-scale for time: log(1 + gap_seconds) to compress large gaps
    import math
    d_tau_normalized = math.log1p(abs(d_tau))

    ds2 = (
        -config.spacetime_alpha * d_tau_normalized ** 2
        + config.spacetime_beta * d_djs ** 2
        + config.spacetime_gamma * d_epsilon ** 2
        + config.spacetime_delta * d_coherence ** 2
    )

    # Classification
    LIGHTLIKE_EPSILON = 0.01
    if ds2 < -LIGHTLIKE_EPSILON:
        interval_class = "timelike"
    elif ds2 > LIGHTLIKE_EPSILON:
        interval_class = "spacelike"
    else:
        interval_class = "lightlike"

    return ds2, interval_class
```

**Critical design decision**: Raw `d_tau` in seconds (e.g., 259200 for 3 days) would always dominate the spatial terms (which are in [0, 1]). We use `log(1 + gap_seconds)` to compress the time axis. This makes "3 days vs 1 hour" a significant but not overwhelming difference, comparable in scale to semantic shifts. The coefficients are calibrated empirically via V4 A/B testing.

---

## 7. Causal Reachability (Light Cone)

### 7.1 Context Window Model

Horizon does not sit inside the LLM. It tracks context window state through estimation:

```python
def estimate_tokens(text: str) -> int:
    """Rough token count estimate. 1 token ≈ 4 characters for English."""
    return len(text) // 4

def update_context_window(session: Session, human_msg: str, agent_resp: str):
    new_tokens = estimate_tokens(human_msg) + estimate_tokens(agent_resp)
    session.context_window_tokens += new_tokens

    # If estimated tokens exceed max, mark oldest turns as out-of-context
    while session.context_window_tokens > session.max_context_tokens:
        for turn in session.turns:
            if turn.in_context:
                evicted_tokens = estimate_tokens("placeholder") * 2
                # Rough: assume each turn contributed equally
                evicted_tokens = session.context_window_tokens // len(
                    [t for t in session.turns if t.in_context]
                )
                turn.in_context = False
                session.context_window_tokens -= evicted_tokens
                break
        else:
            break  # all turns already out of context
```

**Alternative**: The developer can call `configure(session_id, context_evicted_turns=[1, 2, 3])` to explicitly signal which turns were compacted. This is more accurate but requires integration work. When not provided, Horizon estimates.

### 7.2 Reachability Computation

Reachability is a timestamp-gated signal (see `temporal_signals_optional` constraint in `horizon_intent.yaml`). `process_turn` only invokes this function when `timestamp is not None`; otherwise the `reachable_turns` / `reachable_fraction` fields on `TurnResult` stay as `None`.

```python
def compute_reachability(session: Session, current_turn: int,
                          current_embedding: ndarray,
                          gap_seconds: float,
                          kappa: float,
                          config: Config) -> tuple[int, float]:
    reachable = []

    for turn_state in session.turns:
        if turn_state.turn_number >= current_turn:
            continue

        # Factor 1: Is it in the context window?
        in_context = 1.0 if turn_state.in_context else 0.0

        # Factor 2: Human retention of that turn
        if turn_state.timestamp_epoch is not None and gap_seconds > 0:
            turn_gap = gap_seconds  # simplified: gap from turn to now
            R_H = compute_retention(turn_gap, config.context_half_life_hours, kappa)
        else:
            R_H = 1.0  # no timestamp: assume full retention

        # Factor 3: Semantic relevance
        S = float(np.dot(turn_state.combined_embedding, current_embedding))
        S = max(0.0, (S + 1.0) / 2.0)  # normalize to [0, 1]

        # Combined reachability
        R = in_context * R_H * S

        if R > config.reachability_threshold:
            reachable.append(turn_state.turn_number)

    count = len(reachable)
    fraction = count / max(1, current_turn - 1)

    return count, fraction
```

---

## 8. Event System

### 8.1 Event Evaluation

After all signals are computed, the event engine evaluates all 14 conditions:

```python
def evaluate_events(session: Session, turn: TurnState, result: TurnResult,
                     config: Config) -> list[Event]:
    events = []

    def emit(event_type: str, confidence: float, behavior: str, **meta):
        active = config.event_modes.get(event_type, "observe") == "active"
        events.append(Event(
            type=event_type,
            active=active,
            confidence=confidence,
            turn=turn.turn_number,
            suggested_behavior=behavior,
            mode=result.conversation_mode,
            metadata=meta,
        ))

    # 1. checkpoint.clarification
    if result.divergence_score > config.clarification_threshold:
        emit("checkpoint.clarification", result.divergence_score,
             "Pause and ask a targeted question before responding")

    # 2. checkpoint.comprehension
    if result.igt_trend < -0.05 and session.turn_count >= config.convergence_window:
        emit("checkpoint.comprehension", abs(result.igt_trend),
             "Summarize understanding and ask for confirmation")

    # 3. alert.drift
    if result.health_status in ("degrading", "critical"):
        emit("alert.drift", 1.0 - result.fidelity_score,
             "Reset context or re-anchor to original intent")

    # 4. alert.contradiction
    if result.consistency_score < config.consistency_threshold:
        emit("alert.contradiction", 1.0 - result.consistency_score,
             "Flag specific contradicting turns for resolution")

    # 5. alert.verbosity
    if result.twr_value > config.verbosity_threshold:
        emit("alert.verbosity", result.twr_value,
             "Reduce response length; prioritize information density")

    # 6. signal.convergence
    if result.health_status == "converged":
        emit("signal.convergence", 0.9,
             "Conversation reached its natural endpoint; summarize and close")

    # 7. signal.optimal_length
    # T* estimation: where expected fidelity gain turns negative
    if session.turn_count >= 5 and result.igt_trend < 0:
        # Simple heuristic: if we're past 80% of estimated T*
        estimated_t_star = max(5, int(session.turn_count / max(0.01, -result.igt_trend)))
        if session.turn_count > estimated_t_star * 0.8:
            emit("signal.optimal_length", 0.7,
                 "Proactively summarize and check if more is needed",
                 estimated_t_star=estimated_t_star)

    # 8. signal.horizon_widening
    if session.turn_count >= 2:
        prev_eps = session.turns[-2].epsilon_t
        if result.epsilon_t > prev_eps * 1.5 and result.epsilon_t > 0.3:
            emit("signal.horizon_widening", result.epsilon_t,
                 "Increase humility, reduce confidence, ask for more context")

    # 9. signal.session_reset
    if result.degradation_type == "irreversible_loss":
        emit("signal.session_reset", 0.9,
             "Start fresh session with structured handoff summary")

    # 10. signal.temporal_desync
    if (result.gap_seconds is not None
            and result.gap_seconds > config.temporal_desync_threshold_seconds
            and result.estimated_retention is not None
            and result.estimated_retention < 0.5):
        emit("signal.temporal_desync", 1.0 - result.estimated_retention,
             "Re-anchor: summarize where conversation left off, check if intent changed",
             gap_seconds=result.gap_seconds, estimated_retention=result.estimated_retention)

    # 11. signal.broken_reference
    # Detected via deictic or explicit reference to a non-reachable turn
    # (requires NLP reference detection — simplified: check if reachable fraction dropped).
    # Threshold is config-driven per-domain; gate also requires timestamp-derived
    # reachability (reachable_fraction is None when no timestamp was provided).
    if (result.reachable_fraction is not None
            and result.reachable_fraction < config.broken_reference_threshold
            and session.turn_count > 5):
        emit("signal.broken_reference", 1.0 - result.reachable_fraction,
             "Alert: user may reference content the agent no longer has access to",
             reachable_fraction=result.reachable_fraction)

    # 12. signal.frame_shift
    if (turn.client_context is not None and session.turn_count >= 2
            and session.turns[-2].client_context is not None):
        prev_ctx = session.turns[-2].client_context
        curr_ctx = turn.client_context
        if (prev_ctx.get("device_type") != curr_ctx.get("device_type")
                or prev_ctx.get("timezone") != curr_ctx.get("timezone")):
            emit("signal.frame_shift", 0.8,
                 "Adjust assumptions about available attention and cognitive bandwidth")

    # 13. signal.pace_shift
    if (result.conversation_acceleration is not None
            and abs(result.conversation_acceleration) > config.pace_shift_threshold):
        accel = result.conversation_acceleration
        if accel > 0 and result.divergence_score < config.clarification_threshold:
            behavior = "Engagement surge detected — match energy, maintain alignment"
        elif accel > 0 and result.divergence_score > config.clarification_threshold:
            behavior = "Frustration detected — slow down, ask what's most important"
        else:
            behavior = "Disengagement detected — check if user needs something different"
        emit("signal.pace_shift", abs(accel),
             behavior, acceleration=accel)

    # 14. signal.light_cone_collapse
    # Requires enough history to have a meaningful light cone (>= 3 turns) and a
    # timestamp to have computed reachability in the first place. Fires when
    # either the absolute count or the fraction of reachable prior turns falls
    # below its configured threshold.
    if (session.turn_count >= 3
            and result.reachable_turns is not None
            and result.reachable_fraction is not None
            and (result.reachable_turns < config.light_cone_min_threshold
                 or result.reachable_fraction < config.light_cone_ratio_threshold)):
        emit("signal.light_cone_collapse", 1.0 - result.reachable_fraction,
             "Proactively summarize key context before it becomes unreachable; "
             "warn agent not to reference lost turns",
             reachable_turns=result.reachable_turns,
             reachable_fraction=result.reachable_fraction)

    return events
```

---

## 9. Spatial Grounding

### 9.1 Location Class Inference

```python
def infer_location_class(client_context: dict) -> str:
    explicit = client_context.get("location_class")
    if explicit and explicit != "unknown":
        return explicit

    ip = client_context.get("ip_address")
    if ip:
        try:
            import geoip2.database
            reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')
            response = reader.city(ip)
            if response.traits.is_anonymous_vpn or response.traits.is_hosting_provider:
                return "unknown"
            if response.location.accuracy_radius and response.location.accuracy_radius > 100:
                return "unknown"
            return "inferred"
        except Exception:
            return "unknown"

    return "unknown"
```

### 9.2 Spatial Constraint Vector

```python
SPATIAL_PROFILES = {
    ("desktop", "office"):  SpatialConstraint("high", "large", 2000, "high"),
    ("desktop", "home"):    SpatialConstraint("high", "large", 2000, "high"),
    ("mobile", "office"):   SpatialConstraint("medium", "small", 600, "medium"),
    ("mobile", "home"):     SpatialConstraint("medium", "small", 800, "medium"),
    ("mobile", "transit"):  SpatialConstraint("low", "small", 400, "low"),
    ("tablet", "office"):   SpatialConstraint("medium", "medium", 1200, "medium"),
}
DEFAULT_CONSTRAINT = SpatialConstraint("medium", "medium", 1000, "medium")

def compute_spatial_constraint(client_context: dict) -> SpatialConstraint:
    device = client_context.get("device_type", "desktop")
    location = client_context.get("location_class", "unknown")

    key = (device, location)
    return SPATIAL_PROFILES.get(key, DEFAULT_CONSTRAINT)
```

---

## 10. Epsilon Tracker (ε_t)

Estimates the ontological gap width for the current topic. Higher ε means harder domain for human-AI communication.

```python
def estimate_epsilon(session: Session, current_embedding: ndarray,
                      divergence_score: float) -> float:
    if session.turn_count < 3:
        return divergence_score  # bootstrap: use D_JS as initial estimate

    # Compute topic shift magnitude
    if session.turn_count >= 2:
        prev = session.turns[-2].combined_embedding
        topic_shift = 1.0 - float(np.dot(current_embedding, prev))
        topic_shift = max(0.0, topic_shift)
    else:
        topic_shift = 0.0

    # Running average of D_JS as baseline ε
    recent_djs = [t.divergence_score for t in session.turns[-5:]]
    baseline_eps = sum(recent_djs) / len(recent_djs)

    # ε spikes when topic shifts into unfamiliar territory
    epsilon = baseline_eps + 0.5 * topic_shift

    return min(1.0, epsilon)
```

---

## 11. The process_turn Pipeline

The full orchestration, in execution order:

```python
def process_turn(session: Session, human_message: str, agent_response: str,
                  timestamp: Optional[str], client_context: Optional[dict],
                  logprobs: Optional[list], human_latency_ms: Optional[float],
                  embed_engine: EmbeddingEngine, config: Config) -> TurnResult:

    turn_number = session.turn_count + 1

    # ── Step 1: Embed ──
    h_emb = embed_engine.embed(human_message)
    a_emb = embed_engine.embed(agent_response)
    c_emb = (h_emb + a_emb) / 2.0
    c_emb /= np.linalg.norm(c_emb)  # re-normalize

    # ── Step 2: Core signals ──
    igt = compute_igt(c_emb, session.history_embedding, turn_number)
    igt_trend = compute_igt_trend(session, config.convergence_window)
    djs = compute_divergence(h_emb, a_emb)
    twr = compute_twr(agent_response, session, embed_engine.embed)
    consistency = compute_bipredictability(h_emb, a_emb, session.history_embedding)
    epsilon = estimate_epsilon(session, c_emb, djs)

    # ── Step 3: Temporal signals ──
    gap_seconds = gap_class = retention = delta_tau_penalty = None
    kappa = 1.0  # default: peak cognition (no circadian penalty)
    circadian = None
    temporal_refs = None
    resumption = None
    ts_epoch = None

    if timestamp:
        ts_epoch = datetime.fromisoformat(timestamp).timestamp()
        prev_ts = session.turns[-1].timestamp if session.turns else None
        gap_seconds, gap_class = compute_temporal_gap(timestamp, prev_ts)

        tz_str = client_context.get("timezone") if client_context else None
        kappa = compute_circadian_factor(timestamp, tz_str, config.chronotype_offset)
        circadian = kappa

        retention = compute_retention(gap_seconds, config.context_half_life_hours, kappa)
        delta_tau_penalty = compute_temporal_asymmetry_penalty(
            gap_seconds, config.context_half_life_hours, kappa
        )
        resumption = compute_resumption_cost(gap_seconds, retention)
        temporal_refs = resolve_deictic_expressions(human_message, timestamp)

    # ── Step 4: Fidelity dynamics ──
    update_context_window(session, human_message, agent_response)
    delta_recoverable = max(0.0, twr - 0.3)  # recoverable: excess redundancy
    delta_irreversible = 0.0
    newly_evicted = sum(1 for t in session.turns if not t.in_context) - sum(
        1 for t in session.turns[:-1] if not t.in_context
    ) if session.turns else 0
    if newly_evicted > 0:
        delta_irreversible = newly_evicted * 0.1

    prev_fidelity = session.fidelity_trajectory[-1] if session.fidelity_trajectory else 0.5
    fidelity = compute_dynamic_fidelity(
        prev_fidelity, igt, djs, delta_recoverable, delta_irreversible,
        delta_tau_penalty or 0.0, kappa, config,
    )

    # ── Step 5: Health ──
    session.fidelity_trajectory.append(fidelity)
    health = compute_health(session, fidelity, igt_trend, config)

    degradation = "none"
    if delta_irreversible > 0:
        degradation = "both" if delta_recoverable > 0.1 else "irreversible_loss"
    elif delta_recoverable > 0.1:
        degradation = "recoverable_drift"

    # ── Step 6: Pace (requires turn >= 2 and timestamps) ──
    velocity = acceleration = None
    if timestamp and session.turns and session.turns[-1].velocity is not None:
        velocity = compute_velocity(c_emb, session.turns[-1].combined_embedding, gap_seconds)
        acceleration = compute_acceleration(velocity, session.turns[-1].velocity)
    elif timestamp and session.turns and gap_seconds and gap_seconds > 0:
        velocity = compute_velocity(c_emb, session.turns[-1].combined_embedding, gap_seconds)

    # ── Step 7: Spacetime interval ──
    ds2 = interval_class = None
    if timestamp and session.turns and gap_seconds:
        prev_turn = session.turns[-1]
        d_djs = abs(djs - prev_turn.divergence_score)
        d_eps = abs(epsilon - prev_turn.epsilon_t)
        d_coh = abs(consistency - prev_turn.consistency_score)
        ds2, interval_class = compute_spacetime_interval(
            gap_seconds, d_djs, d_eps, d_coh, config
        )

    # ── Step 8: Causal reachability ──
    # Timestamp-gated (see `temporal_signals_optional`): without a wall-clock time
    # the human-retention term is undefined, so we leave both fields as None and
    # downstream event checks treat that as "unknown" rather than firing false
    # positives on signal.broken_reference / signal.light_cone_collapse.
    if timestamp is not None:
        reachable_count, reachable_frac = compute_reachability(
            session, turn_number, c_emb, gap_seconds or 0.0, kappa, config
        )
    else:
        reachable_count, reachable_frac = None, None

    # ── Step 9: Spatial ──
    loc_class = spatial = spatial_shift = None
    if client_context:
        loc_class = infer_location_class(client_context)
        spatial = compute_spatial_constraint(client_context)
        if session.turns and session.turns[-1].client_context:
            # compute frame shift magnitude (simplified: 0 or 1)
            prev_spatial = compute_spatial_constraint(session.turns[-1].client_context)
            shift = (0 if spatial == prev_spatial else 1.0)
            spatial_shift = shift

    # ── Step 10: Mode detection ──
    mode = config.conversation_mode
    if mode == "auto":
        mode = detect_conversation_mode(session, h_emb, turn_number)
    session.detected_mode = mode

    # ── Step 11: Build TurnState and append ──
    turn_state = TurnState(
        turn_number=turn_number, human_embedding=h_emb, agent_embedding=a_emb,
        combined_embedding=c_emb, timestamp=timestamp, timestamp_epoch=ts_epoch,
        client_context=client_context, igt_value=igt, divergence_score=djs,
        twr_value=twr, consistency_score=consistency, fidelity_score=fidelity,
        epsilon_t=epsilon, velocity=velocity, in_context=True,
    )
    session.turns.append(turn_state)
    update_history(session, c_emb)

    # ── Step 12: Build preliminary result (needed by event engine) ──
    result = TurnResult(
        turn_number=turn_number, igt_value=igt, igt_trend=igt_trend,
        divergence_score=djs, twr_value=twr, consistency_score=consistency,
        fidelity_score=fidelity, health_status=health, degradation_type=degradation,
        events=[],  # placeholder
        epsilon_t=epsilon, conversation_mode=mode,
        gap_seconds=gap_seconds, gap_class=gap_class,
        estimated_retention=retention,
        temporal_asymmetry=gap_seconds if gap_seconds else None,
        resumption_cost=resumption, circadian_factor=circadian,
        temporal_references=temporal_refs,
        conversation_velocity=velocity, conversation_acceleration=acceleration,
        spacetime_interval=ds2, interval_class=interval_class,
        reachable_turns=reachable_count, reachable_fraction=reachable_frac,
        location_class=loc_class, spatial_constraint=spatial,
        spatial_frame_shift=spatial_shift,
    )

    # ── Step 13: Events ──
    events = evaluate_events(session, turn_state, result, config)
    session.event_log.extend(events)

    # Return final result with events filled in
    return TurnResult(
        **{k: v for k, v in result.__dict__.items() if k != 'events'},
        events=events,
    )
```

---

## 12. Package Structure

The repository follows the PyPA ``src/`` layout. Importable Python code lives
under ``src/horizon/``; deployment assets, docs, tests, and examples sit at
the repository root.

```
horizon/                             # repository root
├── pyproject.toml
├── README.md · LICENSE · CHANGELOG.md · CONTRIBUTING.md
├── .gitignore                       # ignores docs-private/
├── src/
│   └── horizon/                     # importable package
│       ├── __init__.py              # public API: FidelityMonitor, Config, TurnResult
│       ├── monitor.py               # FidelityMonitor class (session management, process_turn orchestration)
│       ├── config.py                # Config dataclass
│       ├── models.py                # TurnResult, Event, TemporalReference, SpatialConstraint, etc.
│       ├── session.py               # Session, TurnState (internal state)
│       ├── py.typed                 # PEP 561 marker
│       ├── engines/
│       │   ├── __init__.py
│       │   ├── embedding.py         # EmbeddingEngine (lazy-loaded sentence-transformers, `ensure_loaded()` public)
│       │   ├── igt.py               # compute_igt, compute_igt_trend
│       │   ├── divergence.py        # compute_divergence
│       │   ├── twr.py               # compute_twr, split_sentences
│       │   ├── coherence.py         # compute_bipredictability (Tier 1)
│       │   ├── fidelity.py          # compute_snapshot_fidelity, compute_dynamic_fidelity, compute_health
│       │   ├── epsilon.py           # estimate_epsilon
│       │   └── mode.py              # detect_conversation_mode (see §15)
│       ├── spacetime/
│       │   ├── __init__.py
│       │   ├── temporal.py          # compute_temporal_gap, classify_gap, compute_retention, compute_delta_tau
│       │   ├── circadian.py         # compute_circadian_factor
│       │   ├── deictic.py           # resolve_deictic_expressions
│       │   ├── velocity.py          # compute_velocity, compute_acceleration
│       │   ├── interval.py          # compute_spacetime_interval
│       │   ├── light_cone.py        # compute_reachability
│       │   └── spatial.py           # infer_location_class, compute_spatial_constraint
│       ├── events/
│       │   ├── __init__.py
│       │   └── evaluator.py         # evaluate_events (all 14 conditions)
│       ├── context/
│       │   ├── __init__.py
│       │   └── window.py            # update_context_window, context tracking
│       ├── storage/
│       │   ├── __init__.py
│       │   └── sqlite.py            # PersistentDynamicsStore — optional SQLite dynamics store
│       │                            #   for cross-session learning (off by default; in-memory first)
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── langchain.py         # HorizonCallback for LangChain/LangGraph
│       │   ├── openai.py            # monitor.wrap(OpenAI()) — intercepts create() calls
│       │   ├── anthropic.py         # monitor.wrap(Anthropic()) — intercepts create() calls
│       │   └── export.py            # export_to (JSON, LangSmith, Langfuse, OpenTelemetry, Arize)
│       └── mcp/
│           ├── __init__.py
│           ├── server.py            # MCP server: exposes new_conversation, process_turn, get_trajectory, get_events, configure
│           └── cli.py               # `horizon serve --port 3847` entry point
├── tests/                           # unit, integration, e2e, perf, validation
├── examples/                        # runnable demos (OpenAI, Anthropic, LangChain, Agents SDK, raw strings)
├── deploy/
│   └── docker/
│       ├── Dockerfile               # Minimal Python image with horizon-monitor + sentence-transformers cached
│       └── docker-compose.yml       # Self-hosted deployment with optional persistent volume
├── docs/
│   ├── research/                    # THCP theoretical framework
│   ├── product/                     # PRD
│   ├── spec/                        # horizon_intent.yaml + HORIZON_TECH_SPEC.md (this file)
│   ├── integrations/                # Cursor / Claude Desktop / Copilot guides
│   └── reviews/                     # audits and E2E reviews
└── docs-private/                    # git-ignored — market research, go-to-market
```

---

## 13. Dependency Manifest

### Required (core pipeline)

```
sentence-transformers>=2.2.0    # embedding model
numpy>=1.24                      # vector operations
dateparser>=1.2.0                # deictic temporal resolution
tzlocal>=5.0                     # local timezone detection
```

### Optional

```
geoip2>=4.0                      # IP geolocation (spatial grounding)
torch>=2.0                       # Tier 2/3 coherence models
transformers>=4.30               # NLI cross-encoder (Tier 3)
```

### MCP server (extra: `pip install horizon-monitor[mcp]`)

```
mcp>=1.0                         # Model Context Protocol SDK
uvicorn>=0.27                    # ASGI server for horizon serve
click>=8.0                       # CLI framework for horizon serve
```

### Export adapters (extras per target)

Each observability target is installable à la carte so users only pull in the SDK they need. `export_to` raises a clear `ExportResult(status="failed")` with `errors=["missing dependency: <pkg>"]` when the extra is absent.

```
# pip install horizon-monitor[langsmith]
langsmith>=0.1                   # LangSmith tracer client

# pip install horizon-monitor[langfuse]
langfuse>=2.0                    # Langfuse observability SDK

# pip install horizon-monitor[otel]
opentelemetry-api>=1.20          # OpenTelemetry core API
opentelemetry-sdk>=1.20          # OpenTelemetry SDK (exporters pluggable)

# pip install horizon-monitor[arize]
arize>=7.0                       # Arize AX client (optional; roadmap)
```

JSON export uses only the Python standard library and therefore does not require any extra.

### Docker

The `docker/Dockerfile` pre-caches the default embedding model at build time (`RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"`) so containers start with zero cold-start delay.

---

## 14. Performance Budget

Per-turn latency breakdown for the core pipeline (CPU, no GPU, 100-turn conversation):

| Step | Operation | Budget |
|---|---|---|
| Embedding (2 texts) | sentence-transformers encode | 20ms |
| IGT + D_JS + TWR | vector ops + sentence split | 5ms |
| Coherence Tier 1 | 3 dot products | < 1ms |
| Temporal signals (all) | arithmetic + dateparser | 3ms |
| Spacetime interval | arithmetic | < 1ms |
| Causal reachability | 100 dot products (per prior turn) | 2ms |
| Spatial inference | lookup | < 1ms |
| Event evaluation | 14 conditionals | < 1ms |
| State update | history embedding, session append | < 1ms |
| **Total** | | **~33ms** |

Headroom: 17ms within the 50ms budget.

**Memory**: Each `TurnState` stores 3 embeddings (384-dim for MiniLM) = 3 × 384 × 8 bytes = ~9.2KB per turn. For 100 turns: ~920KB for embeddings + overhead ≈ 2–5MB. Well within the 100MB budget.

---

## 15. Conversation Mode Detection

The mode detector classifies the current conversation into one of four modes. Used by the event system to contextualize suggested behaviors.

```python
def detect_conversation_mode(session: Session, human_embedding: ndarray,
                              turn_number: int) -> str:
    if turn_number <= 2:
        return "explore"

    recent = session.turns[-3:]
    avg_igt = sum(t.igt_value for t in recent) / len(recent)
    avg_djs = sum(t.divergence_score for t in recent) / len(recent)

    # Question density heuristic: explore mode when IGT is high and D_JS is low
    if avg_igt > 0.5 and avg_djs < 0.2:
        return "explore"

    # Execute mode: low IGT (repeating patterns), low D_JS (aligned)
    if avg_igt < 0.3 and avg_djs < 0.2:
        return "execute"

    # Refine mode: moderate IGT, moderate D_JS (iterating toward precision)
    if 0.2 < avg_igt < 0.6 and 0.15 < avg_djs < 0.4:
        return "refine"

    # Learn mode: high IGT, high D_JS (new territory, misalignment expected)
    if avg_igt > 0.4 and avg_djs > 0.3:
        return "learn"

    return "explore"  # default
```

---

## 16. Integration Adapters

### 16.1 OpenAI / Anthropic SDK Wrap

The `wrap` pattern intercepts `chat.completions.create()` calls, extracts human message and agent response, and calls `process_turn` automatically.

```python
# integrations/openai.py (same pattern for anthropic.py)

class HorizonWrappedClient:
    def __init__(self, client, monitor, session_id: str):
        self._client = client
        self._monitor = monitor
        self._session_id = session_id

    @property
    def chat(self):
        return HorizonWrappedChat(self._client.chat, self._monitor, self._session_id)

class HorizonWrappedChat:
    @property
    def completions(self):
        return HorizonWrappedCompletions(...)

class HorizonWrappedCompletions:
    def create(self, **kwargs):
        human_msg = self._extract_last_user_message(kwargs.get("messages", []))
        response = self._original.create(**kwargs)
        agent_msg = response.choices[0].message.content
        logprobs = getattr(response.choices[0], "logprobs", None)

        self._monitor.process_turn(
            session_id=self._session_id,
            human_message=human_msg,
            agent_response=agent_msg,
            logprobs=logprobs,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        return response  # unchanged — monitor is transparent
```

Usage: `client = monitor.wrap(OpenAI(), session_id="abc")` — returns a `HorizonWrappedClient` that behaves identically to the original client.

**Override hooks** (for replay, simulation, synthetic contexts):

```python
# Deterministic timestamps (e.g. replaying a logged conversation)
wrapped.set_timestamp_provider(lambda: "2026-04-22T14:30:00+00:00")

# Dynamic per-turn context
wrapped.set_context_provider(lambda: {"device_type": "mobile", "timezone": "America/Los_Angeles"})

# Or a static context for every subsequent turn
wrapped.set_client_context({"device_type": "desktop", "timezone": "UTC"})

# Restore real-wall-clock / unset overrides
wrapped.set_timestamp_provider(None)
wrapped.set_context_provider(None)
```

Both providers are optional. When neither is set, the wrapper uses `datetime.now(timezone.utc).isoformat()` and whatever static `client_context` was supplied at construction time (or `None`). The same three hooks are mirrored on the Anthropic wrap for API symmetry.

### 16.2 MCP Server

The MCP server exposes Horizon's core API as MCP tools, enabling IDE integrations (Cursor, Claude Desktop) without code changes.

```python
# mcp/server.py

from mcp.server import Server
from horizon import FidelityMonitor, Config

app = Server("horizon")
monitor = FidelityMonitor(Config())

@app.tool()
def new_conversation() -> dict:
    session_id = monitor.new_conversation()
    return {"session_id": session_id}

@app.tool()
def process_turn(session_id: str, human_message: str, agent_response: str,
                 timestamp: str = None, client_context: dict = None) -> dict:
    result = monitor.process_turn(
        session_id=session_id,
        human_message=human_message,
        agent_response=agent_response,
        timestamp=timestamp,
        client_context=client_context,
    )
    return dataclasses.asdict(result)

@app.tool()
def get_trajectory(session_id: str) -> dict:
    trajectory = monitor.get_trajectory(session_id)
    return dataclasses.asdict(trajectory)

@app.tool()
def configure(**kwargs) -> dict:
    result = monitor.configure(**kwargs)
    return dataclasses.asdict(result)
```

**CLI entry point** (`mcp/cli.py`):

```python
# horizon serve --port 3847 --transport stdio|sse
import click

@click.command()
@click.option("--port", default=3847, help="Port for SSE transport")
@click.option("--transport", default="stdio", type=click.Choice(["stdio", "sse"]))
def serve(port: int, transport: str):
    from mcp.server import run
    from horizon.mcp.server import app

    if transport == "stdio":
        run(app, transport="stdio")
    else:
        run(app, transport="sse", port=port)
```

**Cursor integration**: Users add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "horizon": {
      "command": "horizon",
      "args": ["serve"],
      "env": {}
    }
  }
}
```

**Claude Desktop integration**: Users add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "horizon": {
      "command": "horizon",
      "args": ["serve"],
      "env": {}
    }
  }
}
```

### 16.3 Docker Deployment

```dockerfile
# docker/Dockerfile
FROM python:3.12-slim

RUN pip install --no-cache-dir horizon-monitor[mcp]

# Pre-cache embedding model at build time (zero cold-start)
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

EXPOSE 3847
CMD ["horizon", "serve", "--transport", "sse", "--port", "3847"]
```

```yaml
# docker/docker-compose.yml
version: "3.8"
services:
  horizon:
    build: .
    ports:
      - "3847:3847"
    volumes:
      - horizon-data:/data   # persistent dynamics store
    environment:
      - HORIZON_GEOIP_DB=/data/GeoLite2-City.mmdb  # optional
volumes:
  horizon-data:
```

---

## 17. Open Implementation Decisions

These are decisions deferred to implementation time, not spec time:

| Decision | Options | Recommendation |
|---|---|---|
| Sentence splitter | regex (current) vs. spaCy sentencizer vs. nltk punkt | Start with regex; replace if V1 shows TWR accuracy issues |
| Thread safety for Session | per-session `threading.Lock` vs. `asyncio.Lock` | `threading.Lock` for sync API; add `async` variant later |
| GeoIP2 database path | bundled vs. config vs. env var | Config parameter with env var fallback (`HORIZON_GEOIP_DB`) |
| History decay factor | 0.9 (current) vs. tunable | Start fixed; add to `Config` if V1 shows sensitivity |
| Conversation mode detector | embedding classifier vs. rule-based | Rule-based first (question density + specificity heuristics); swap to classifier if accuracy < 70% |
| MCP session persistence | in-memory vs. file-backed between IDE restarts | In-memory first; enable the SQLite `PersistentDynamicsStore` (already implemented under `horizon.storage.sqlite`) when cross-session dynamics learning is turned on |
| SDK wrap: async support | sync-only vs. sync + async | Sync wrappers first; add async variants if demand warrants |

---

*This document is the implementation contract for the Horizon Fidelity Monitor. It translates the PRD's product requirements and the research essay's mathematical formulations into typed data models, deterministic algorithms, and explicit edge-case handling. An engineer can implement from this spec without consulting any other source. Changes to algorithms or data models require updating this spec first — code follows the spec, not the other way around.*
