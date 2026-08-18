"""E-7, E-8, E-9 — pure_function_injected_time.

memento_engine_intent.yaml::pure_function_injected_time.
test: tests/unit/memento_mori/test_engine_determinism.py::test_byte_identical_and_no_ambient_clock
"""

from __future__ import annotations

import json
import socket
import subprocess
from datetime import datetime
from unittest.mock import patch

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig

from .conftest import EVAL_INSTANT, build_smallco


class _NoAmbientClockDatetime(datetime):
    """A datetime subclass whose .now()/.utcnow() raise — used to prove
    evaluate() never reads the ambient clock. All other classmethods
    (fromisoformat, constructor, etc.) behave identically."""

    @classmethod
    def now(cls, tz=None):  # noqa: D102
        raise AssertionError("evaluate() must never call datetime.now()")

    @classmethod
    def utcnow(cls):  # noqa: D102
        raise AssertionError("evaluate() must never call datetime.utcnow()")


class _OutboundError(AssertionError):
    pass


def _block(*args, **kwargs):
    raise _OutboundError(f"unexpected outbound call: args={args} kwargs={kwargs}")


def test_byte_identical_and_no_ambient_clock(store, monkeypatch) -> None:
    """E-7: two evaluate() calls, same snapshot+instant -> byte-identical
    serialized report. E-8: evaluate() never reads the system clock. E-9:
    zero network / subprocess calls during evaluation."""
    build_smallco(store)
    snapshot = store.snapshot()
    config = MementoConfig()

    monkeypatch.setattr(engine, "datetime", _NoAmbientClockDatetime)

    with patch.object(socket.socket, "connect", side_effect=_block):
        with patch.object(socket.socket, "connect_ex", side_effect=_block):
            with patch.object(subprocess, "Popen", side_effect=_block):
                report_a = engine.evaluate(snapshot, EVAL_INSTANT, config)
                report_b = engine.evaluate(snapshot, EVAL_INSTANT, config)

    serialized_a = json.dumps(report_a.to_dict(), sort_keys=True, default=str)
    serialized_b = json.dumps(report_b.to_dict(), sort_keys=True, default=str)
    assert serialized_a == serialized_b, "identical (snapshot, instant) must be byte-identical"
    assert report_a.zero_network is True
    assert report_a.zero_llm is True
