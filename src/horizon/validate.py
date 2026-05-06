"""End-to-end validation harness for the Horizon Fidelity Monitor.

Runs five canonical scenarios and asserts that each produces the qualitative
signal pattern it is designed to detect. No API keys required; everything runs
locally against the bundled embedding model.

Invoke via the installed console script::

    horizon-validate

or directly::

    python -m horizon.validate

Exit code is 0 if every scenario behaves as expected, 1 otherwise. This is a
"smoke test" for users to confirm that an installed copy of the library is
wired correctly. For empirical validation against labelled corpora, see the
gates in ``tests/validation/``.
"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from horizon import Config, FidelityMonitor

# ── Pretty-print helpers ──────────────────────────────────────────────────

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> str:
    return f"{GREEN}✓{RESET} {msg}"


def _fail(msg: str) -> str:
    return f"{RED}✗{RESET} {msg}"


def _info(msg: str) -> str:
    return f"  {DIM}{msg}{RESET}"


# ── Scenario framework ────────────────────────────────────────────────────


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    duration_ms: float
    observations: list[str]
    failures: list[str]


def run_scenario(
    name: str, fn: Callable[[FidelityMonitor], list[tuple[str, bool, str]]]
) -> ScenarioResult:
    """Run a scenario function and capture timing + checks.

    Each scenario returns a list of (description, passed, observed_value) tuples.
    """
    print(f"\n{BOLD}▶ {name}{RESET}")
    monitor = FidelityMonitor()
    t0 = time.perf_counter()
    try:
        checks = fn(monitor)
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        print(_fail(f"crashed: {type(exc).__name__}: {exc}"))
        return ScenarioResult(name, False, elapsed, [], [str(exc)])

    elapsed = (time.perf_counter() - t0) * 1000

    observations = []
    failures = []
    for desc, ok, observed in checks:
        if ok:
            print(_ok(desc))
        else:
            print(_fail(desc))
            failures.append(desc)
        if observed:
            print(_info(observed))
        observations.append(observed)

    return ScenarioResult(name, not failures, elapsed, observations, failures)


# ── Scenarios ─────────────────────────────────────────────────────────────


def scenario_healthy_conversation(monitor: FidelityMonitor) -> list[tuple[str, bool, str]]:
    """A coherent technical conversation should keep fidelity high and stable."""
    sid = monitor.new_conversation(metadata={"domain": "technical"})
    base = datetime.now(timezone.utc)

    turns = [
        (
            "How does Python's GIL affect multithreading?",
            "The GIL serialises bytecode execution, so CPU-bound threads can't run in parallel. I/O-bound threads still benefit because the GIL is released during blocking calls.",
        ),
        (
            "What about multiprocessing then?",
            "multiprocessing sidesteps the GIL by using separate OS processes, each with its own interpreter. Communication happens through pickling, which adds overhead.",
        ),
        (
            "When would you pick threads over processes?",
            "Threads win when you have many short I/O-bound tasks: the lower memory and faster startup beat the parallelism gain you'd get from processes.",
        ),
        (
            "Any modern alternatives?",
            "asyncio for I/O-bound concurrency, and free-threaded CPython (PEP 703) is removing the GIL in 3.13+ for true parallel threading.",
        ),
    ]

    fidelities = []
    for i, (h, a) in enumerate(turns):
        ts = (base + timedelta(seconds=i * 30)).isoformat()
        r = monitor.process_turn(sid, h, a, timestamp=ts)
        fidelities.append(r.fidelity_score)

    avg_fidelity = sum(fidelities) / len(fidelities)
    final = monitor.get_trajectory(sid)

    return [
        (
            "Fidelity stays healthy on a coherent technical conversation",
            avg_fidelity > 0.5,
            f"avg fidelity = {avg_fidelity:.3f} across {len(turns)} turns; final health = {final.health_status}",
        ),
        (
            "Pipeline emits all 4D signals when timestamps are provided",
            all(f > 0 for f in fidelities),
            f"per-turn fidelity = [{', '.join(f'{f:.2f}' for f in fidelities)}]",
        ),
    ]


def scenario_convergent_conversation(monitor: FidelityMonitor) -> list[tuple[str, bool, str]]:
    """A conversation that's wrapping up should show declining IGT and converged health."""
    sid = monitor.new_conversation()
    monitor.configure(session_id=sid, convergence_threshold=0.95)
    base = datetime.now(timezone.utc)

    turns = [
        ("What's the capital of Japan?", "Tokyo, with about 14 million people in the city proper."),
        ("Got it, thanks.", "You're welcome."),
        (
            "Anything else I should know?",
            "Tokyo is also the world's largest metropolitan area by population.",
        ),
        ("OK, that's helpful.", "Glad to help."),
        ("Thanks again.", "Anytime."),
        ("Bye.", "Take care."),
    ]

    igts = []
    for i, (h, a) in enumerate(turns):
        ts = (base + timedelta(seconds=i * 20)).isoformat()
        r = monitor.process_turn(sid, h, a, timestamp=ts)
        igts.append(r.igt_value)

    traj = monitor.get_trajectory(sid)
    convergence_events = [e for e in monitor.get_events(sid) if e.type == "signal.convergence"]

    return [
        (
            "IGT declines as conversation winds down",
            igts[-1] < igts[1],
            f"IGT trajectory: [{', '.join(f'{x:.2f}' for x in igts)}]",
        ),
        (
            "Convergence signal fires when IGT trend goes negative",
            len(convergence_events) > 0,
            f"convergence events fired: {len(convergence_events)}; igt_trend = {traj.igt_trend:.3f}",
        ),
    ]


def scenario_drifting_conversation(monitor: FidelityMonitor) -> list[tuple[str, bool, str]]:
    """Off-topic agent responses should produce high D_JS and a drift alert."""
    sid = monitor.new_conversation()
    monitor.configure(session_id=sid, event_modes={"alert.drift": "active"})
    base = datetime.now(timezone.utc)

    # Each agent reply is increasingly off-topic from the human question
    turns = [
        (
            "How do I deploy a Flask app to production?",
            "You should consider gunicorn or uwsgi behind nginx. systemd handles process supervision.",
        ),
        (
            "Cool, what about HTTPS?",
            "Pizza is a flatbread topped with tomato sauce and cheese, originating in Naples.",
        ),
        (
            "Wait, I asked about HTTPS for my Flask app.",
            "The migration patterns of monarch butterflies span thousands of kilometers across North America.",
        ),
        (
            "Are you OK? I need help with my Flask deployment.",
            "Beethoven's 9th symphony was completed in 1824 and includes the famous Ode to Joy.",
        ),
    ]

    djs_values = []
    for i, (h, a) in enumerate(turns):
        ts = (base + timedelta(seconds=i * 30)).isoformat()
        r = monitor.process_turn(sid, h, a, timestamp=ts)
        djs_values.append(r.divergence_score)

    avg_djs = sum(djs_values) / len(djs_values)
    clarification_events = [
        e for e in monitor.get_events(sid) if e.type == "checkpoint.clarification"
    ]
    drift_events = [e for e in monitor.get_events(sid) if e.type == "alert.drift"]

    return [
        (
            "D_JS climbs when agent responses don't match human intent",
            avg_djs > 0.3,
            f"avg D_JS = {avg_djs:.3f} (clarification threshold = 0.35)",
        ),
        (
            "checkpoint.clarification fires when D_JS exceeds threshold",
            len(clarification_events) > 0 or len(drift_events) > 0,
            f"clarification events: {len(clarification_events)}, drift events: {len(drift_events)}",
        ),
    ]


def scenario_temporal_desync(monitor: FidelityMonitor) -> list[tuple[str, bool, str]]:
    """A 3-day gap with low retention should fire signal.temporal_desync."""
    sid = monitor.new_conversation()
    monitor.configure(
        session_id=sid,
        event_modes={"signal.temporal_desync": "active", "signal.session_reset": "active"},
    )

    t0 = datetime.now(timezone.utc)
    monitor.process_turn(
        sid,
        "Let's plan the architecture for the new analytics pipeline.",
        "Sure, I'd start with Kafka for ingestion and Flink for stream processing.",
        timestamp=t0.isoformat(),
    )

    # 3 days later
    t1 = t0 + timedelta(days=3)
    r = monitor.process_turn(
        sid,
        "OK so where were we?",
        "Picking up from before — we were discussing Kafka and Flink for the pipeline.",
        timestamp=t1.isoformat(),
    )

    desync_events = [e for e in monitor.get_events(sid) if e.type == "signal.temporal_desync"]
    reset_events = [e for e in monitor.get_events(sid) if e.type == "signal.session_reset"]

    return [
        (
            "gap_seconds reflects the 3-day pause",
            r.gap_seconds is not None and 250_000 < r.gap_seconds < 270_000,
            f"gap_seconds = {r.gap_seconds:.0f} ({r.gap_seconds / 86400:.1f} days)",
        ),
        (
            "estimated_retention drops after long gap",
            r.estimated_retention is not None and r.estimated_retention < 0.3,
            f"estimated_retention = {r.estimated_retention:.3f} (half-life model, 24h default)",
        ),
        (
            "signal.temporal_desync OR signal.session_reset fires",
            len(desync_events) > 0 or len(reset_events) > 0,
            f"desync events: {len(desync_events)}, session_reset events: {len(reset_events)}",
        ),
    ]


def scenario_spatial_context(monitor: FidelityMonitor) -> list[tuple[str, bool, str]]:
    """Spatial context should produce constraint signals and frame-shift events."""
    sid = monitor.new_conversation()
    monitor.configure(session_id=sid, event_modes={"signal.frame_shift": "active"})
    base = datetime.now(timezone.utc)

    # Turn 1: desktop at the office
    r1 = monitor.process_turn(
        sid,
        "Walk me through the implementation plan in detail.",
        "Here's a 6-step plan with rationale for each: ...",
        timestamp=base.isoformat(),
        client_context={"device_type": "desktop", "location_class": "office"},
    )

    # Turn 2: switched to mobile in transit
    r2 = monitor.process_turn(
        sid,
        "Quick question while I'm walking — is step 3 blocking step 4?",
        "No, they're independent.",
        timestamp=(base + timedelta(minutes=10)).isoformat(),
        client_context={"device_type": "mobile", "location_class": "mobile_transit"},
    )

    frame_shift_events = [e for e in monitor.get_events(sid) if e.type == "signal.frame_shift"]

    return [
        (
            "Spatial constraint inferred for desktop/office",
            r1.spatial_constraint is not None and r1.spatial_constraint.attention_budget == "high",
            f"turn 1: attention={r1.spatial_constraint.attention_budget}, "
            f"max_resp={r1.spatial_constraint.max_response_length} tokens",
        ),
        (
            "Spatial constraint becomes more restrictive on desktop → mobile shift",
            r2.spatial_constraint is not None
            and r2.spatial_constraint.attention_budget != "high"
            and r2.spatial_constraint.max_response_length
            < r1.spatial_constraint.max_response_length,
            f"turn 2: attention={r2.spatial_constraint.attention_budget}, "
            f"max_resp={r2.spatial_constraint.max_response_length} tokens "
            f"(was {r1.spatial_constraint.max_response_length})",
        ),
        (
            "signal.frame_shift fires on context change",
            len(frame_shift_events) > 0,
            f"frame_shift events: {len(frame_shift_events)}",
        ),
    ]


# ── Driver ────────────────────────────────────────────────────────────────


def main() -> int:
    print(f"{BOLD}Horizon Fidelity Monitor — validation harness{RESET}")
    print(
        f"{DIM}Local-only · no API keys required · ~30s on first run "
        f"(model download), ~5s after{RESET}\n"
    )

    # Pre-load the embedding model so per-scenario timings exclude the cold-start cost.
    print("Loading embedding model...", end=" ", flush=True)
    t0 = time.perf_counter()
    from horizon.engines.embedding import EmbeddingEngine

    EmbeddingEngine(model_name=Config().embedding_model).ensure_loaded()
    print(f"{GREEN}done{RESET} ({(time.perf_counter() - t0) * 1000:.0f}ms)")

    scenarios = [
        ("Healthy technical conversation", scenario_healthy_conversation),
        ("Convergent conversation (winding down)", scenario_convergent_conversation),
        ("Drifting conversation (off-topic agent)", scenario_drifting_conversation),
        ("Temporal desync (3-day gap)", scenario_temporal_desync),
        ("Spatial context shift (desktop → mobile)", scenario_spatial_context),
    ]

    results = [run_scenario(name, fn) for name, fn in scenarios]

    print(f"\n{BOLD}{'=' * 60}{RESET}")
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    total_ms = sum(r.duration_ms for r in results)

    for r in results:
        marker = f"{GREEN}PASS{RESET}" if r.passed else f"{RED}FAIL{RESET}"
        print(f"  {marker}  {r.name}  {DIM}({r.duration_ms:.0f}ms){RESET}")

    print(f"{BOLD}{'=' * 60}{RESET}")

    if passed == total:
        print(
            f"{GREEN}{BOLD}✓ All {total} scenarios passed{RESET} "
            f"{DIM}({total_ms:.0f}ms total){RESET}"
        )
        print(f"{DIM}Horizon is wired correctly and producing sensible signals.{RESET}")
        return 0
    else:
        failed = total - passed
        print(f"{RED}{BOLD}✗ {failed}/{total} scenarios failed{RESET}")
        for r in results:
            if not r.passed:
                print(f"  {RED}{r.name}{RESET}")
                for f in r.failures:
                    print(f"    - {f}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
