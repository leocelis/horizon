"""Privacy constraint tests.

Verifies that the default configuration sends no data to any external service.
Referenced by horizon_intent.yaml::constraints[no_external_calls_default].
"""

from __future__ import annotations

import socket
from unittest.mock import patch

from horizon import FidelityMonitor


class OutboundNetworkError(AssertionError):
    """Raised when the monitor attempts to open an outbound socket."""


def _block_outbound(*args, **kwargs):
    raise OutboundNetworkError(
        f"Unexpected outbound network call with args={args}, kwargs={kwargs}"
    )


def test_no_external_calls_on_process_turn() -> None:
    """Constraint: no_external_calls_default.

    process_turn() must not open any outbound socket or HTTP request when
    called with defaults (no client_context, no IP geolocation, no export).
    """
    monitor = FidelityMonitor()
    # Trigger lazy embedding load before the network block (model is cached locally)
    monitor._embed_engine.ensure_loaded()

    sid = monitor.new_conversation()

    with patch.object(socket.socket, "connect", side_effect=_block_outbound):
        with patch.object(socket.socket, "connect_ex", side_effect=_block_outbound):
            monitor.process_turn(sid, "Hello", "Hi there")
            monitor.process_turn(
                sid,
                "tell me about websockets",
                "websockets enable full-duplex communication over TCP.",
            )

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == 2


def test_no_external_calls_with_timestamps_only() -> None:
    """With timestamps (no IP geolocation), still no network calls."""
    monitor = FidelityMonitor()
    monitor._embed_engine.ensure_loaded()

    sid = monitor.new_conversation()

    with patch.object(socket.socket, "connect", side_effect=_block_outbound):
        monitor.process_turn(
            sid,
            "hello",
            "hi there",
            timestamp="2026-04-22T10:00:00+00:00",
            client_context={"device_type": "desktop", "timezone": "UTC"},
        )


def test_no_external_calls_on_get_trajectory() -> None:
    """Read-only operations never touch the network."""
    monitor = FidelityMonitor()
    monitor._embed_engine.ensure_loaded()

    sid = monitor.new_conversation()
    monitor.process_turn(sid, "a", "b")

    with patch.object(socket.socket, "connect", side_effect=_block_outbound):
        monitor.get_trajectory(sid)
        monitor.get_events(sid)
