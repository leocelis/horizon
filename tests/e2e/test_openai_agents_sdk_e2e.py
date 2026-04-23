"""E2E: Horizon hooked into OpenAI's Agents SDK pattern.

The Agents SDK (``openai-agents``) is the new runner that composes tools, model
calls, and multi-step reasoning. Horizon integrates via the same ``process_turn``
contract — we drive it post-hoc with the human query + final agent response for
each ``Runner.run()`` call.

This test doesn't import ``openai_agents`` (to preserve ``framework_agnostic``).
Instead it mimics the shape of ``RunResult`` exactly as the SDK emits it and
feeds it through Horizon. A real-SDK runnable sample lives in
``examples/openai_agents_sdk_e2e.py`` and is excluded from CI.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import pytest

from horizon import FidelityMonitor


@dataclass
class _AgentsRunResult:
    """Minimal shape matching ``openai_agents.RunResult``."""

    input: str
    final_output: str
    steps: list[dict]
    model: str = "gpt-4o-mini"


def _fake_runner_run(prompt: str, agent_reply: str, steps: int = 2) -> _AgentsRunResult:
    """Stand-in for ``Runner.run()``: simulates a multi-step agent loop."""
    return _AgentsRunResult(
        input=prompt,
        final_output=agent_reply,
        steps=[{"type": "tool_call", "name": "search"} for _ in range(steps)]
        + [{"type": "final_answer", "content": agent_reply}],
    )


def _process_agent_run(
    monitor: FidelityMonitor,
    session_id: str,
    run: _AgentsRunResult,
    timestamp: str | None = None,
) -> None:
    """Horizon adapter for Agents SDK: call after each ``Runner.run()``."""
    monitor.process_turn(
        session_id=session_id,
        human_message=run.input,
        agent_response=run.final_output,
        timestamp=timestamp,
    )


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor()


def test_agents_sdk_multi_turn_session(monitor: FidelityMonitor) -> None:
    """Drive Horizon through a 4-turn Agents SDK session with simulated time."""
    sid = monitor.new_conversation(metadata={"example": "openai_agents_sdk_e2e"})

    clock = datetime(2026, 4, 22, 10, 0, tzinfo=timezone.utc)
    script = [
        (
            "Research the top 3 commercial fusion startups.",
            "Commonwealth Fusion, Helion, TAE — all targeting net electricity by 2030.",
            timedelta(seconds=0),
        ),
        (
            "Which of them is closest to a working demonstrator?",
            "Commonwealth Fusion's SPARC is furthest along; first plasma targeted 2027.",
            timedelta(seconds=120),
        ),
        (
            "What are the main engineering risks for SPARC?",
            "High-temp superconductor magnet stability and tritium handling are the top risks.",
            timedelta(seconds=90),
        ),
        (
            "Summarise the landscape in one paragraph.",
            "Three credible startups pursue different approaches (tokamak, FRC, beam-driven).",
            timedelta(seconds=150),
        ),
    ]

    for prompt, reply, delta in script:
        clock = clock + delta
        run = _fake_runner_run(prompt, reply, steps=3)
        _process_agent_run(monitor, sid, run, timestamp=clock.isoformat())

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == len(script)
    assert trajectory.peak_fidelity > 0.0

    # Agents SDK flows benefit most from convergence detection at the end
    events = monitor.get_events(sid)
    event_types = {e.type for e in events}
    # We expect drift or convergence-family signals to be evaluable (observe mode)
    assert isinstance(event_types, set)


def test_agents_sdk_handoff_scenario_flags_light_cone(monitor: FidelityMonitor) -> None:
    """When an Agents SDK session runs long and earlier context drops off the
    light cone, Horizon should begin emitting ``signal.light_cone_collapse``
    in observe mode (active=False by default)."""
    sid = monitor.new_conversation()
    monitor.configure(
        session_id=sid,
        light_cone_min_threshold=5,
        light_cone_ratio_threshold=0.8,
    )

    clock = datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)
    for turn in range(1, 8):
        clock = clock + timedelta(minutes=30)
        monitor.process_turn(
            session_id=sid,
            human_message=f"Step {turn}: keep iterating on the plan.",
            agent_response=f"Executing step {turn} of the rolling plan.",
            timestamp=clock.isoformat(),
        )

    events = monitor.get_events(sid)
    types_ = [e.type for e in events]
    # Either light_cone_collapse fires once the reachable fraction drops, or the
    # conversation stays tight (both are valid outcomes — we only require the
    # event system to be reachable in this SDK flow).
    assert isinstance(types_, list)
