"""Internal mutable session state — never exposed directly in the public API."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from numpy import ndarray

from horizon.config import Config
from horizon.engines.claim_consistency import ClaimTracker
from horizon.models import Event
from horizon.spacetime.pacing import PacingHint


@dataclass
class TurnState:
    """Mutable per-turn state stored inside Session."""

    turn_number: int
    human_embedding: ndarray
    agent_embedding: ndarray
    combined_embedding: ndarray

    # Per-sentence agent embeddings — lets TWR catch verbatim sentence
    # repeats that a turn-level cosine misses. None means "not computed".
    # This is embeddings only (no raw text), preserving the privacy
    # invariant that no user/agent strings live in TurnState.
    agent_sentence_embeddings: list[ndarray] | None = None

    timestamp: str | None = None
    timestamp_epoch: float | None = None
    client_context: dict | None = None

    igt_value: float = 0.0
    divergence_score: float = 0.0
    twr_value: float = 0.0
    consistency_score: float = 1.0
    fidelity_score: float = 0.0
    epsilon_t: float = 0.0
    velocity: float | None = None
    in_context: bool = True

    # Pacing — pre-computed at end of pipeline for use by the NEXT turn's
    # event evaluator. Stored here (not raw text) so privacy invariants hold.
    agent_pacing_hint: PacingHint | None = None
    """Was THIS turn's agent_response a "do X and report back" instruction?"""

    human_completion_marker: bool = False
    """Did THIS turn's human_message explicitly signal completion of a prior
    deferred action? (Suppresses pace_premature_report on the same turn.)"""


@dataclass
class Session:
    """All mutable state for a single conversation session."""

    session_id: str
    config: Config

    turns: list[TurnState] = field(default_factory=list)
    fidelity_trajectory: list[float] = field(default_factory=list)
    event_log: list[Event] = field(default_factory=list)
    history_embedding: ndarray | None = None
    """Exponentially weighted running mean of all turn embeddings."""

    detected_mode: str | None = None
    context_window_tokens: int = 0
    max_context_tokens: int = 128_000

    claim_tracker: ClaimTracker = field(default_factory=ClaimTracker)
    """Per-session memory of agent-asserted numeric/named facts —
    used by the claim-tracker contradiction detector (v0.2)."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def turn_count(self) -> int:
        return len(self.turns)
