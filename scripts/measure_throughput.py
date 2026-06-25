"""Single-process throughput benchmark for ``FidelityMonitor.process_turn``.

Closes the v0.2.0 audit gap "high-QPS scaling unvalidated" with measured
numbers for the deployment shape Horizon's library actually runs in:
**one monitor per process, many concurrent sessions, calls serialised
inside the process by the GIL + per-session lock**.

We report:
  - Steady-state turns/second (after warmup).
  - p50 / p95 / p99 latency per ``process_turn`` call (ms).
  - Peak RSS (MB).
  - A "rotating sessions" scenario where N sessions are advanced
    round-robin to surface any per-session-history scaling effects.

Multi-process scale-out is straightforward (one ``FidelityMonitor``
instance per worker process, sticky-routed by ``session_id``); the
single-process number is the relevant unit because that's what one
worker sustains.

Usage:
  python scripts/measure_throughput.py --sessions 16 --turns 25 \
      --output docs/reviews/throughput.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import resource
except ImportError:
    resource = None

from horizon import FidelityMonitor

TEMPLATES: list[tuple[str, str]] = [
    (
        "How do I deploy a FastAPI service behind nginx with TLS termination?",
        "Use a systemd unit for FastAPI on a UNIX socket and an nginx server block "
        "that proxies to that socket; let certbot handle the cert renewal.",
    ),
    (
        "What's the right way to model soft deletes in Postgres?",
        "Add a deleted_at TIMESTAMP column, default NULL, and filter every read "
        "via a partial index WHERE deleted_at IS NULL.",
    ),
    (
        "I'm seeing intermittent 502s from my Kubernetes ingress — where do I look first?",
        "Check the ingress controller logs for upstream connect failures, then the "
        "pod readiness gates and the Service endpoint slices.",
    ),
    (
        "Can you walk me through async/await in Python in plain English?",
        "An async function returns a coroutine; awaiting one yields control back to "
        "the event loop until the awaited coroutine completes.",
    ),
    (
        "My Stripe webhooks keep duplicating — best practice for idempotency?",
        "Persist the event ID on first receipt; on every subsequent delivery, look "
        "it up and short-circuit with a 200 if already processed.",
    ),
    (
        "How do I set up structured logging with tracing context in Go?",
        "Use slog with a context-aware handler that pulls trace and span IDs from "
        "the incoming context and appends them as attributes on every record.",
    ),
    (
        "I keep hitting rate limits on the OpenAI API — what's the right backoff?",
        "Read the Retry-After header, sleep that many seconds, and apply jittered "
        "exponential backoff on top with a cap of about 60 s.",
    ),
    (
        "What's the cleanest way to test code that depends on the system clock?",
        "Inject a `now()` callable; in production it returns datetime.now, in "
        "tests it returns whatever you advance it to.",
    ),
]


def _peak_rss_mb() -> float | None:
    if resource is None:
        return None
    raw = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return raw / 1024.0 / 1024.0 if sys.platform == "darwin" else raw / 1024.0


def _percentile(sorted_vals: list[float], p: float) -> float:
    if not sorted_vals:
        return float("nan")
    idx = max(0, min(len(sorted_vals) - 1, int(round(p * (len(sorted_vals) - 1)))))
    return sorted_vals[idx]


def _scenario_single_session(monitor: FidelityMonitor, n_turns: int) -> tuple[float, list[float]]:
    """Pure single-session: same conv, n_turns of growing history."""
    sid = monitor.new_conversation()
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
    latencies: list[float] = []
    t0 = time.perf_counter()
    for i in range(n_turns):
        h, a = TEMPLATES[i % len(TEMPLATES)]
        ts = (base + timedelta(minutes=i + 1)).isoformat()
        s = time.perf_counter()
        monitor.process_turn(sid, h, a, timestamp=ts)
        latencies.append((time.perf_counter() - s) * 1000.0)
    return time.perf_counter() - t0, latencies


def _scenario_rotating_sessions(
    monitor: FidelityMonitor, n_sessions: int, n_turns: int
) -> tuple[float, list[float]]:
    """N independent sessions advanced round-robin, mimicking a worker
    that fans out across many active conversations from a queue."""
    sids = [monitor.new_conversation() for _ in range(n_sessions)]
    base_per_sid = [
        datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc) + timedelta(hours=i)
        for i in range(n_sessions)
    ]
    counters = [0] * n_sessions
    latencies: list[float] = []
    t0 = time.perf_counter()
    for round_idx in range(n_turns):
        for s_idx in range(n_sessions):
            i = counters[s_idx]
            h, a = TEMPLATES[i % len(TEMPLATES)]
            ts = (base_per_sid[s_idx] + timedelta(minutes=i + 1)).isoformat()
            t = time.perf_counter()
            monitor.process_turn(sids[s_idx], h, a, timestamp=ts)
            latencies.append((time.perf_counter() - t) * 1000.0)
            counters[s_idx] += 1
    return time.perf_counter() - t0, latencies


def _summary(name: str, wall: float, latencies: list[float]) -> dict:
    sorted_lat = sorted(latencies)
    return {
        "scenario": name,
        "turns": len(latencies),
        "wall_seconds": wall,
        "throughput_per_second": len(latencies) / wall if wall > 0 else float("nan"),
        "latency_ms": {
            "mean": statistics.fmean(latencies) if latencies else 0.0,
            "p50": _percentile(sorted_lat, 0.50),
            "p95": _percentile(sorted_lat, 0.95),
            "p99": _percentile(sorted_lat, 0.99),
            "max": sorted_lat[-1] if sorted_lat else float("nan"),
        },
    }


def _print_row(s: dict) -> None:
    lat = s["latency_ms"]
    print(
        f"  {s['scenario']:<26}  {s['turns']:>4} turns  "
        f"{s['throughput_per_second']:>6.1f} t/s   "
        f"p50={lat['p50']:>5.1f}  p95={lat['p95']:>5.1f}  "
        f"p99={lat['p99']:>5.1f}  max={lat['max']:>6.1f} ms"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=16, help="Concurrent sessions for the rotating scenario")
    parser.add_argument("--turns", type=int, default=25, help="Turns per session in the rotating scenario")
    parser.add_argument("--single-turns", type=int, default=50, help="Turns for the single-session scenario")
    parser.add_argument("--warmup-turns", type=int, default=3, help="Warmup turns excluded from stats")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    print("Single-process throughput benchmark")
    print(f"  Single-session    : {args.single_turns} turns")
    print(f"  Rotating-sessions : {args.sessions} sessions × {args.turns} turns "
          f"({args.sessions * args.turns} total)")
    print(f"  Warmup            : {args.warmup_turns} turns (excluded from stats)")
    print()

    monitor = FidelityMonitor()

    print("Warming up (model load + JIT) …", flush=True)
    warmup_sid = monitor.new_conversation()
    base = datetime(2026, 1, 1, 8, 0, 0, tzinfo=timezone.utc)
    for i in range(max(1, args.warmup_turns)):
        h, a = TEMPLATES[i % len(TEMPLATES)]
        monitor.process_turn(warmup_sid, h, a, timestamp=(base + timedelta(minutes=i)).isoformat())
    print("Warmup done.")
    print()

    print("Scenario 1: single session, growing history …", flush=True)
    wall1, lat1 = _scenario_single_session(monitor, args.single_turns)
    s1 = _summary("single_session", wall1, lat1)
    _print_row(s1)

    print()
    print("Scenario 2: rotating sessions (round-robin) …", flush=True)
    wall2, lat2 = _scenario_rotating_sessions(monitor, args.sessions, args.turns)
    s2 = _summary("rotating_sessions", wall2, lat2)
    _print_row(s2)

    rss = _peak_rss_mb()
    print()
    if rss is not None:
        print(f"Peak resident memory: {rss:.0f} MB")

    out = {
        "scenarios": [s1, s2],
        "peak_rss_mb": rss,
        "params": {
            "single_turns": args.single_turns,
            "rotating_sessions": args.sessions,
            "rotating_turns_per_session": args.turns,
            "warmup_turns": args.warmup_turns,
        },
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(out, indent=2))
        print(f"\nWrote {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
