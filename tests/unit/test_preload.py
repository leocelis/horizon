"""Tests for FidelityMonitor.preload_models() — eliminates first-call latency.

Covers v0.2.0 cold-start API. The intent is that a production caller can
invoke ``preload_models()`` at process startup and get a ~3–5s blocking
load *once*, after which every ``process_turn`` call meets the <50ms core
budget.
"""

from __future__ import annotations

import time

from horizon import FidelityMonitor


def test_preload_models_returns_timing_report() -> None:
    monitor = FidelityMonitor()
    report = monitor.preload_models()

    assert isinstance(report, dict)
    assert "embedding_model_ms" in report
    assert report["embedding_model_ms"] >= 0.0


def test_preload_makes_first_turn_fast() -> None:
    """After preload, the first process_turn call should not pay the load cost."""
    monitor = FidelityMonitor()
    monitor.preload_models()  # ← absorb the cold-start cost here

    sid = monitor.new_conversation()
    t0 = time.perf_counter()
    monitor.process_turn(sid, "What is async/await?", "Concurrency primitives in Python.")
    first_call_ms = (time.perf_counter() - t0) * 1000.0

    # First call should be well under the 500ms deep-pipeline budget after
    # preload. Without preload this would be ~3-5 seconds (model download/load).
    assert first_call_ms < 500.0, (
        f"First process_turn after preload took {first_call_ms:.1f}ms — "
        "preload_models() did not pre-warm correctly."
    )


def test_preload_is_idempotent() -> None:
    """Calling preload_models() twice should not re-load and should be cheap."""
    monitor = FidelityMonitor()
    monitor.preload_models()

    t0 = time.perf_counter()
    report = monitor.preload_models()
    second_call_ms = (time.perf_counter() - t0) * 1000.0

    assert report["embedding_model_ms"] < 50.0, (
        f"Second preload_models() took {report['embedding_model_ms']:.1f}ms "
        "internally and {second_call_ms:.1f}ms wall — should be a no-op"
    )
    assert second_call_ms < 50.0
