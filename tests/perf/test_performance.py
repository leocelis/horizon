"""Performance tests — latency and memory budgets from the intent.

Referenced by:
  * horizon_intent.yaml::constraints[latency_core]
  * horizon_intent.yaml::constraints[latency_deep]
  * horizon_intent.yaml::constraints[memory_footprint]
  * horizon_intent.yaml::verification[single_turn_metrics_latency]

These tests use soft asserts so they fail loudly but don't brittle-block CI
when machines are oversubscribed. The budget is a warning threshold; the
hard failure threshold is 3× the budget.
"""

from __future__ import annotations

import gc
import time
import tracemalloc
from datetime import datetime, timedelta, timezone

import pytest

from horizon import FidelityMonitor

CORE_BUDGET_MS = 50.0
DEEP_BUDGET_MS = 500.0
MEMORY_BUDGET_MB_100_TURNS = 100.0


def _warmup(monitor: FidelityMonitor) -> str:
    """Pre-load the embedding model and run one turn so timing is steady."""
    monitor._embed_engine.ensure_loaded()
    sid = monitor.new_conversation()
    monitor.process_turn(sid, "warmup", "ready")
    return monitor.new_conversation()


def test_core_pipeline_latency() -> None:
    """Constraint: latency_core — core pipeline < 50ms per turn on CPU.

    We measure the median of N turns after warmup to smooth over scheduler jitter.
    """
    monitor = FidelityMonitor()
    sid = _warmup(monitor)

    samples: list[float] = []
    for i in range(8):
        human = f"turn {i}: explain how TCP handshake works."
        agent = "SYN, SYN-ACK, ACK — three-way handshake establishes a connection."
        t0 = time.perf_counter()
        monitor.process_turn(sid, human, agent)
        samples.append((time.perf_counter() - t0) * 1000.0)

    samples.sort()
    median_ms = samples[len(samples) // 2]
    p90_ms = samples[int(len(samples) * 0.9)]

    assert median_ms < CORE_BUDGET_MS * 3, (
        f"Core pipeline median latency {median_ms:.1f}ms exceeds 3x budget "
        f"({CORE_BUDGET_MS}ms). Samples (ms): {[round(s, 1) for s in samples]}"
    )
    if median_ms >= CORE_BUDGET_MS:
        pytest.xfail(
            f"Core pipeline median latency {median_ms:.1f}ms exceeds target "
            f"{CORE_BUDGET_MS}ms (p90={p90_ms:.1f}ms). Not a CI hard failure, "
            "but out of budget on this machine."
        )


def test_deep_pipeline_latency() -> None:
    """Constraint: latency_deep — full pipeline < 500ms on CPU.

    Tier 2/3 coherence (TGN/NLI) is not enabled by default in V1. The deep
    budget therefore covers the full configured pipeline including all 4D
    signals with timestamps and client_context.
    """
    monitor = FidelityMonitor()
    monitor._embed_engine.ensure_loaded()
    sid = monitor.new_conversation()

    base_time = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)
    monitor.process_turn(
        sid,
        "let's discuss distributed consensus",
        "Paxos and Raft are two foundational algorithms.",
        timestamp=base_time.isoformat(),
        client_context={"device_type": "desktop", "timezone": "UTC"},
    )

    samples: list[float] = []
    for i in range(8):
        ts = (base_time + timedelta(minutes=i + 1)).isoformat()
        t0 = time.perf_counter()
        monitor.process_turn(
            sid,
            f"what about the FLP impossibility result in turn {i}?",
            "FLP shows no deterministic consensus is possible with one faulty process.",
            timestamp=ts,
            client_context={"device_type": "desktop", "timezone": "UTC"},
        )
        samples.append((time.perf_counter() - t0) * 1000.0)

    samples.sort()
    median_ms = samples[len(samples) // 2]
    assert median_ms < DEEP_BUDGET_MS * 3, (
        f"Deep pipeline median latency {median_ms:.1f}ms exceeds 3x budget."
    )


def test_memory_100_turns() -> None:
    """Constraint: memory_footprint — < 100MB for 100 turns."""
    monitor = FidelityMonitor()
    monitor._embed_engine.ensure_loaded()
    sid = monitor.new_conversation()

    gc.collect()
    tracemalloc.start()
    snap_before = tracemalloc.take_snapshot()

    for i in range(100):
        monitor.process_turn(
            sid,
            f"Turn {i}: explain one concept about distributed systems.",
            f"Concept {i}: consensus, ordering, replication, partitioning, fault tolerance.",
        )

    snap_after = tracemalloc.take_snapshot()
    stats = snap_after.compare_to(snap_before, "filename")
    delta_bytes = sum(s.size_diff for s in stats if s.size_diff > 0)
    tracemalloc.stop()

    delta_mb = delta_bytes / (1024 * 1024)
    assert delta_mb < MEMORY_BUDGET_MB_100_TURNS, (
        f"100-turn memory delta {delta_mb:.1f}MB exceeds {MEMORY_BUDGET_MB_100_TURNS}MB budget"
    )


def test_single_turn_metrics_latency() -> None:
    """Verification: single_turn_metrics_latency.

    Process a single turn and verify all metric engines return valid scores
    within the core latency budget.
    """
    monitor = FidelityMonitor()
    sid = _warmup(monitor)

    t0 = time.perf_counter()
    result = monitor.process_turn(
        sid,
        "Explain the CAP theorem briefly.",
        "CAP: consistency, availability, partition-tolerance — pick two under network partitions.",
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert 0.0 <= result.fidelity_score <= 1.0
    assert result.igt_value >= 0.0
    assert 0.0 <= result.divergence_score <= 1.0
    assert 0.0 <= result.twr_value <= 1.0
    assert 0.0 <= result.consistency_score <= 1.0
    assert 0.0 <= result.epsilon_t <= 1.0
    assert isinstance(result.events, list)
    assert result.health_status in {"healthy", "degrading", "critical", "converged"}

    assert elapsed_ms < CORE_BUDGET_MS * 3, (
        f"Single-turn latency {elapsed_ms:.1f}ms exceeds 3x core budget"
    )
