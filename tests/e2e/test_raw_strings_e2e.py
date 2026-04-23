"""E2E: pure string-only, framework-agnostic usage.

Proves the ``framework_agnostic`` constraint: Horizon works with just the
stdlib + ``horizon``. No OpenAI, no Anthropic, no LangChain, no LlamaIndex, no
LangGraph — zero agent framework. All you need is ``human_message`` and
``agent_response`` strings.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from datetime import datetime, timedelta, timezone

import pytest

from horizon import FidelityMonitor


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor()


def test_raw_strings_multi_turn_happy_path(monitor: FidelityMonitor) -> None:
    """10-turn conversation driven entirely by plain strings — proves the core
    library has zero SDK assumptions."""
    sid = monitor.new_conversation(metadata={"domain": "creative"})

    clock = datetime(2026, 4, 22, 12, 0, tzinfo=timezone.utc)
    script = [
        ("I'm trying to write a sci-fi short story about time travel.",
         "Great — do you have a rough premise or central tension?"),
        ("A historian falls into 1630s Amsterdam and can't return.",
         "That's a rich setting. Do they try to change history, or observe?"),
        ("They deliberately stay to prevent a famine.",
         "That gives you moral stakes. What's the twist?"),
        ("The famine was the catalyst for something good.",
         "Classic temporal paradox. What's your opening scene?"),
        ("Maybe the historian is lecturing students, then vanishes mid-sentence.",
         "That's a strong hook. Who narrates?"),
        ("First-person, in the historian's voice.",
         "Good. First-person keeps urgency. Chapter structure?"),
        ("Five chapters — arrival, realization, decision, consequence, return.",
         "Solid arc. The 'return' chapter could be metaphorical."),
        ("Yes — they return to their own time, but wiser.",
         "A transformation arc. What's the title?"),
        ("'The Keeper of Gone Things.'",
         "Evocative. Do you want help with prose style now or outline first?"),
        ("Let's outline first.",
         "Great — I'll sketch a scene-by-scene outline for all five chapters."),
    ]

    for i, (human, agent) in enumerate(script):
        clock = clock + timedelta(seconds=30)
        result = monitor.process_turn(
            session_id=sid,
            human_message=human,
            agent_response=agent,
            timestamp=clock.isoformat(),
        )
        assert result.turn_number == i + 1
        assert 0.0 <= result.fidelity_score <= 1.0

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == 10
    assert trajectory.health_status in ("healthy", "degrading", "critical", "converged")
    assert trajectory.estimated_t_star is None or trajectory.estimated_t_star >= 0


def test_raw_strings_no_timestamp_core_pipeline_only(monitor: FidelityMonitor) -> None:
    """Without timestamps, all 4D spacetime signals are None but the core
    signals still fire (``temporal_signals_optional`` constraint)."""
    sid = monitor.new_conversation()

    result = monitor.process_turn(
        session_id=sid,
        human_message="Walk me through the CAP theorem.",
        agent_response="CAP: in a distributed system you pick 2 of Consistency, Availability, Partition-tolerance.",
    )

    # Core always present
    assert result.igt_value >= 0.0
    assert result.divergence_score >= 0.0
    assert result.consistency_score >= 0.0
    assert result.fidelity_score >= 0.0

    # 4D signals absent
    assert result.gap_seconds is None
    assert result.circadian_factor is None
    assert result.reachable_turns is None
    assert result.reachable_fraction is None
    assert result.spatial_constraint is None


def test_raw_strings_zero_transitive_framework_imports_in_subprocess() -> None:
    """Run Horizon in a fresh Python subprocess and verify no agent framework is
    imported. This is stronger than the in-process check: it catches module-level
    side effects in ``import horizon`` or ``FidelityMonitor()``."""
    script = textwrap.dedent(
        """
        import sys
        from horizon import FidelityMonitor
        monitor = FidelityMonitor()
        sid = monitor.new_conversation()
        monitor.process_turn(sid, "hello", "hi there")
        forbidden = {"langchain", "llama_index", "langgraph", "openai_agents", "openai", "anthropic"}
        loaded = {m.split('.', 1)[0] for m in sys.modules}
        leaked = sorted(loaded & forbidden)
        print("LEAKED=" + ",".join(leaked))
        """
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert "LEAKED=\n" in proc.stdout + "\n" or proc.stdout.strip().endswith("LEAKED="), (
        f"Core horizon leaked forbidden imports in subprocess: {proc.stdout}"
    )
