"""Shared pytest fixtures for all Horizon tests."""

from __future__ import annotations

import pytest

from horizon import Config, FidelityMonitor


@pytest.fixture
def config() -> Config:
    """Default Config for tests."""
    return Config()


@pytest.fixture
def monitor(config: Config) -> FidelityMonitor:
    """FidelityMonitor with default config, no persistence."""
    return FidelityMonitor(config=config)


@pytest.fixture
def session_id(monitor: FidelityMonitor) -> str:
    """Pre-created session for tests that need an existing session."""
    return monitor.new_conversation(metadata={"domain": "test"})


# Sample conversation turns for reuse across tests
TURN_1_HUMAN = "How does Python handle memory management?"
TURN_1_AGENT = (
    "Python uses automatic memory management through reference counting "
    "and a cyclic garbage collector. When an object's reference count drops "
    "to zero, it is immediately deallocated. The gc module handles reference cycles."
)
TURN_2_HUMAN = "Can you explain the garbage collector in more detail?"
TURN_2_AGENT = (
    "Python's cyclic garbage collector detects reference cycles — groups of objects "
    "that reference each other but are not reachable from any root. It runs in three "
    "generations, collecting short-lived objects frequently and long-lived ones rarely."
)
TURN_3_HUMAN = "What about memory leaks — can they happen in Python?"
TURN_3_AGENT = (
    "Yes, memory leaks can still happen in Python. Common causes include global "
    "containers that grow unboundedly, event handler references that prevent "
    "garbage collection, and extension modules with manual memory management."
)

TIMESTAMP_1 = "2026-04-22T10:00:00+00:00"
TIMESTAMP_2 = "2026-04-22T10:01:30+00:00"  # 90 seconds later
TIMESTAMP_3 = "2026-04-22T10:05:00+00:00"  # 3.5 minutes after T1

TIMESTAMP_DAYS_LATER = "2026-04-25T10:00:00+00:00"  # 3 days later
