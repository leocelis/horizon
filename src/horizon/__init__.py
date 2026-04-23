"""Horizon Fidelity Monitor — 4D conversation dynamics for AI agents.

Public API::

    from horizon import FidelityMonitor, Config

    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(metadata={"domain": "technical"})
    result = monitor.process_turn(
        session_id,
        human_message="How do I use asyncio in Python?",
        agent_response="asyncio is Python's standard library for async I/O...",
        timestamp="2026-04-22T10:30:00+00:00",
    )
    print(result.fidelity_score)
    print(result.events)
"""

from horizon.config import Config
from horizon.engines.embedding import EmbeddingModelError
from horizon.models import (
    ConfigResult,
    ConfigWarning,
    Event,
    ExportResult,
    FidelityTrajectory,
    SpatialConstraint,
    TemporalReference,
    TurnResult,
)
from horizon.monitor import FidelityMonitor, SessionNotFoundError

__version__ = "0.1.0"

__all__ = [
    "FidelityMonitor",
    "Config",
    "TurnResult",
    "Event",
    "FidelityTrajectory",
    "ConfigResult",
    "ConfigWarning",
    "ExportResult",
    "SpatialConstraint",
    "TemporalReference",
    "SessionNotFoundError",
    "EmbeddingModelError",
]
