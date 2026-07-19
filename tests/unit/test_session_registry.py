"""Unit tests for horizon_monitor.mcp.session_registry.SessionRegistry.

The contract under test: sessions are owned by the key that created them,
capped per key with same-key-only LRU eviction, and a session with no tracked
owner is accessible to anyone (the safe default for callers that bypass the
registry entirely, e.g. direct FidelityMonitor usage or tests).
"""

from __future__ import annotations

import pytest

from horizon_monitor.mcp.session_registry import SessionOwnershipError, SessionRegistry


def test_owner_can_access_their_own_session() -> None:
    reg = SessionRegistry(max_sessions_per_key=10)
    reg.register("sid-1", "key-a")

    reg.check("sid-1", "key-a")  # must not raise


def test_non_owner_is_rejected() -> None:
    reg = SessionRegistry(max_sessions_per_key=10)
    reg.register("sid-1", "key-a")

    with pytest.raises(SessionOwnershipError):
        reg.check("sid-1", "key-b")


def test_untracked_session_is_accessible_to_anyone() -> None:
    """A session never registered (bypassed the MCP tool layer) is not
    ownership-checked — this is the safe default for backward compatibility."""
    reg = SessionRegistry(max_sessions_per_key=10)

    reg.check("never-registered", "key-a")  # must not raise
    reg.check("never-registered", "key-b")  # must not raise


def test_owned_sessions_lists_only_that_keys_sessions() -> None:
    reg = SessionRegistry(max_sessions_per_key=10)
    reg.register("sid-1", "key-a")
    reg.register("sid-2", "key-a")
    reg.register("sid-3", "key-b")

    assert reg.owned_sessions("key-a") == ["sid-1", "sid-2"]
    assert reg.owned_sessions("key-b") == ["sid-3"]
    assert reg.owned_sessions("key-c") == []


def test_eviction_at_cap_removes_only_the_same_keys_oldest_session() -> None:
    reg = SessionRegistry(max_sessions_per_key=2)
    reg.register("sid-1", "key-a")
    reg.register("sid-2", "key-a")

    evicted = reg.register("sid-3", "key-a")  # over cap -> evicts sid-1

    assert evicted == "sid-1"
    assert reg.owned_sessions("key-a") == ["sid-2", "sid-3"]
    # Eviction fully forgets sid-1 (the caller is expected to also end it on
    # the underlying FidelityMonitor, which will then raise its own
    # SessionNotFoundError on any further use) — the registry itself no
    # longer enforces anything for an id it has forgotten.
    reg.check("sid-1", "key-a")  # must not raise: untracked, not "owned by someone else"


def test_one_keys_volume_never_evicts_another_keys_session() -> None:
    reg = SessionRegistry(max_sessions_per_key=1)
    reg.register("sid-a1", "key-a")
    reg.register("sid-b1", "key-b")

    evicted = reg.register("sid-a2", "key-a")  # key-a over its own cap

    assert evicted == "sid-a1"
    assert reg.owned_sessions("key-b") == ["sid-b1"]  # untouched
    reg.check("sid-b1", "key-b")  # still owned, still accessible


def test_release_stops_tracking_a_session() -> None:
    reg = SessionRegistry(max_sessions_per_key=10)
    reg.register("sid-1", "key-a")

    reg.release("sid-1")

    assert reg.owned_sessions("key-a") == []
    reg.check("sid-1", "key-b")  # untracked again -> accessible to anyone


def test_release_of_unknown_session_is_a_safe_noop() -> None:
    reg = SessionRegistry(max_sessions_per_key=10)

    reg.release("never-registered")  # must not raise
