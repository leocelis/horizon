"""Horizon Fidelity Monitor — 4D conversation dynamics for AI agents.

Public API::

    from horizon_monitor import FidelityMonitor, Config

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

from importlib.metadata import PackageNotFoundError, version

from horizon_monitor.config import Config
from horizon_monitor.engines.embedding import EmbeddingModelError
from horizon_monitor.grounding import (
    GroundingHookError,
    GroundingResult,
    ToolHook,
)
from horizon_monitor.models import (
    ConfigResult,
    ConfigWarning,
    Event,
    ExportResult,
    FidelityTrajectory,
    SpatialConstraint,
    TemporalReference,
    TurnResult,
)
from horizon_monitor.monitor import FidelityMonitor, SessionNotFoundError

try:
    __version__ = version("horizon-monitor")
except PackageNotFoundError:
    # Not installed as a package (e.g. running from a source checkout
    # without `pip install -e .`) — avoid hand-duplicating the version
    # that lives in pyproject.toml.
    __version__ = "0.0.0+unknown"

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
    "ToolHook",
    "GroundingResult",
    "GroundingHookError",
]
