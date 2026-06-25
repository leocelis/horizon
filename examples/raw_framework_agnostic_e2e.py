"""End-to-end example: Horizon with no agent framework at all.

Proves ``framework_agnostic`` the hard way: you supply strings, Horizon gives
you fidelity. No OpenAI, no Anthropic, no LangChain, no MCP — just the stdlib
plus ``horizon-monitor``.

Use this when:
    - You run your own LLM (local, self-hosted, custom endpoint).
    - You want to monitor archived conversations from logs.
    - You're embedding Horizon inside a larger data pipeline where the SDK
      doesn't matter.

Usage::

    python examples/raw_framework_agnostic_e2e.py
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from horizon import FidelityMonitor


def print_turn_summary(turn_idx: int, human: str, agent: str, result: Any) -> None:
    print(f"\n── Turn {turn_idx} ──────────────────────────────────────────────")
    print(f"  human : {human[:90]}{'…' if len(human) > 90 else ''}")
    print(f"  agent : {agent[:90]}{'…' if len(agent) > 90 else ''}")
    print(
        f"  fidelity={result.fidelity_score:.3f}  "
        f"igt={result.igt_value:.3f}  "
        f"djs={result.divergence_score:.3f}  "
        f"twr={result.twr_value:.3f}  "
        f"consistency={result.consistency_score:.3f}"
    )
    reachable_str = (
        f"{result.reachable_turns}/{result.reachable_fraction:.2f}"
        if result.reachable_turns is not None and result.reachable_fraction is not None
        else "n/a"
    )
    print(
        f"  health={result.health_status}  "
        f"epsilon={result.epsilon_t:.3f}  "
        f"reachable={reachable_str}"
    )
    if result.gap_seconds is not None:
        print(f"  Δτ={result.gap_seconds:.1f}s ({result.gap_class})  κ={result.circadian_factor:.2f}")
    if result.events:
        print("  events:")
        for e in result.events:
            print(f"    • {e.type} active={e.active} conf={e.confidence:.2f}")


def run_conversation() -> None:
    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(
        metadata={"domain": "support", "example": "raw_framework_agnostic"}
    )

    clock = datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)
    transcript = [
        ("Hi — I can't log in to my account.",
         "Sorry to hear that. Can you tell me what error message you see?",
         timedelta(seconds=0)),
        ("It says 'invalid credentials' even though I know my password is right.",
         "Thanks. Have you changed your password in the last 24 hours?",
         timedelta(seconds=35)),
        ("No, I haven't touched it in months.",
         "Got it. Let's try a password reset — I'll send a link to your email.",
         timedelta(seconds=40)),
        ("Actually wait — I just remembered, I might have enabled 2FA yesterday.",
         "That explains it. Let's verify your 2FA device first before resetting.",
         timedelta(seconds=55)),
        ("Ok, I have my authenticator app open.",
         "Perfect. What's the 6-digit code currently displayed?",
         timedelta(seconds=25)),
        ("482103.",
         "Looks valid. Try logging in again and use that code when prompted.",
         timedelta(seconds=20)),
        ("It worked! Thanks.",
         "Glad it's resolved. Anything else I can help with today?",
         timedelta(seconds=15)),
    ]

    for i, (human, agent, delta) in enumerate(transcript, start=1):
        clock = clock + delta
        result = monitor.process_turn(
            session_id=session_id,
            human_message=human,
            agent_response=agent,
            timestamp=clock.isoformat(),
            client_context={"device_type": "mobile", "timezone": "America/Los_Angeles",
                             "location_class": "home"},
        )
        print_turn_summary(i, human, agent, result)

    trajectory = monitor.get_trajectory(session_id)
    print("\n═══ Final trajectory ═══")
    print(f"  session_id        = {trajectory.session_id}")
    print(f"  turn_count        = {trajectory.turn_count}")
    print(f"  health_status     = {trajectory.health_status}")
    print(f"  peak_fidelity     = {trajectory.peak_fidelity:.3f}")
    print(f"  current_fidelity  = {trajectory.current_fidelity:.3f}")
    print(f"  igt_trend         = {trajectory.igt_trend:+.4f}")
    print(f"  scores            = {[round(s, 3) for s in trajectory.scores]}")


if __name__ == "__main__":
    t0 = time.time()
    try:
        run_conversation()
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(130)
    print(f"\ncompleted in {time.time() - t0:.1f}s")
