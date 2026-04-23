"""Internal mutable session state — never exposed directly in the public API."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional

import numpy as np
from numpy import ndarray

from horizon.config import Config
from horizon.models import Event

if TYPE_CHECKING:
    pass


@dataclass
class TurnState:
    """Mutable per-turn state stored inside Session."""

    turn_number: int
    human_embedding: ndarray
    agent_embedding: ndarray
    combined_embedding: ndarray

    timestamp: Optional[str] = None
    timestamp_epoch: Optional[float] = None
    client_context: Optional[dict] = None

    igt_value: float = 0.0
    divergence_score: float = 0.0
    twr_value: float = 0.0
    consistency_score: float = 1.0
    fidelity_score: float = 0.0
    epsilon_t: float = 0.0
    velocity: Optional[float] = None
    in_context: bool = True


@dataclass
class Session:
    """All mutable state for a single conversation session."""

    session_id: str
    config: Config

    turns: list[TurnState] = field(default_factory=list)
    fidelity_trajectory: list[float] = field(default_factory=list)
    event_log: list[Event] = field(default_factory=list)
    history_embedding: Optional[ndarray] = None
    """Exponentially weighted running mean of all turn embeddings."""

    detected_mode: Optional[str] = None
    context_window_tokens: int = 0
    max_context_tokens: int = 128_000

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    @property
    def turn_count(self) -> int:
        return len(self.turns)
