"""Per-key session ownership and capacity limits for the multi-tenant hosted MCP server.

This is a SERVER-layer concern only. The core `FidelityMonitor` class has no
notion of "owner" — correctly so, since it is a single-tenant SDK primitive
used directly by one process/one deployer (the OpenAI/Anthropic/LangChain
wrap() helpers, direct library usage, etc.). Multi-tenancy only exists on the
hosted MCP server, where multiple distinct API keys share one `FidelityMonitor`
instance.

Without this registry, two gaps exist on the hosted server:

  1. Any authenticated key can call `get_trajectory` / `get_events` /
     `process_turn` on ANY session_id, including one created by a different
     key — if that id ever leaks (a log, a shared proxy, a copy-pasted debug
     output), a different tenant can read (or continue) that conversation.

  2. `configure_session(session_id=None)` — the documented "apply globally"
     mode — loops over every live session on the shared `FidelityMonitor` and
     merges the caller's overrides into each one. Any authenticated key can
     silently mutate every OTHER tenant's thresholds/event-modes, with no
     session_id needed at all.

This registry closes both: every session is owned by the key that created it,
capped per key (LRU-evicted — the oldest session of THAT key only is ended,
never another key's), and every subsequent call is checked against ownership
before reaching the monitor. `configure_session`'s "global" mode is
reinterpreted at the server layer as "every session I own", never the
underlying monitor's true global scope.
"""

from __future__ import annotations

import collections
import threading


class SessionOwnershipError(Exception):
    """A session_id exists but is tracked under a different key.

    Deliberately raised with the same shape a caller would treat like "not
    found" — a caller must not be able to distinguish "this belongs to
    someone else" from "this never existed" (that distinction is itself an
    information leak across tenants).
    """


class SessionRegistry:
    """Bounded, thread-safe map of session_id -> owning key_id.

    A session with no tracked owner (created via a path that bypasses this
    registry — e.g. a direct FidelityMonitor call in a test, or a session
    that predates this registry) is treated as accessible to any caller:
    ownership is enforced only once a session has actually been registered
    through the real `new_conversation` MCP entry point.
    """

    def __init__(self, max_sessions_per_key: int) -> None:
        self._max = max_sessions_per_key
        self._owner_of: dict[str, str] = {}
        self._by_key: dict[str, collections.OrderedDict[str, None]] = {}
        self._lock = threading.Lock()

    def register(self, session_id: str, key_id: str) -> str | None:
        """Record `session_id` as owned by `key_id`.

        Returns the session_id evicted to stay within the per-key cap (the
        caller must end that session on the underlying FidelityMonitor), or
        None if nothing was evicted. Eviction only ever removes a session
        belonging to the SAME key — one tenant's volume never costs another
        tenant a session.
        """
        evicted: str | None = None
        with self._lock:
            self._owner_of[session_id] = key_id
            bucket = self._by_key.setdefault(key_id, collections.OrderedDict())
            bucket[session_id] = None
            if len(bucket) > self._max:
                evicted, _ = bucket.popitem(last=False)
                self._owner_of.pop(evicted, None)
        return evicted

    def check(self, session_id: str, key_id: str) -> None:
        """Raise SessionOwnershipError if `session_id` belongs to another key."""
        with self._lock:
            owner = self._owner_of.get(session_id)
        if owner is not None and owner != key_id:
            raise SessionOwnershipError(session_id)

    def owned_sessions(self, key_id: str) -> list[str]:
        """Return all session_ids currently owned by `key_id`, oldest first."""
        with self._lock:
            bucket = self._by_key.get(key_id)
            return list(bucket) if bucket else []

    def release(self, session_id: str) -> None:
        """Stop tracking `session_id` (call when the session itself ends)."""
        with self._lock:
            owner = self._owner_of.pop(session_id, None)
            if owner is not None:
                bucket = self._by_key.get(owner)
                if bucket is not None:
                    bucket.pop(session_id, None)
