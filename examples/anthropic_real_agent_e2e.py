"""End-to-end example: Horizon wrapping a real Anthropic agent.

Mirrors ``openai_real_agent_e2e.py`` but hits Anthropic's cost-controlled
``claude-haiku-4-5`` model. Demonstrates the identical wrapping pattern across
providers.

Cost control:
    - Model: ``claude-haiku-4-5`` (fast, cheapest Claude family)
    - ``max_tokens=120`` per reply
    - 6-turn conversation → typically < 2,000 tokens total → well under a cent

Usage::

    # 1) Ensure ANTHROPIC_API_KEY is set, or fall back to ADA's .env
    python examples/anthropic_real_agent_e2e.py

    # 2) Override the env file location
    ADA_ENV_PATH=/path/to/.env python examples/anthropic_real_agent_e2e.py

What this demonstrates (identical feature set to the OpenAI example, different SDK):
    - ``monitor.wrap(anthropic_client)`` — transparent interception of ``messages.create``
    - Real-time fidelity score computation per turn
    - Event emission in default observe mode (no agent coupling)
    - Handling of Anthropic's content-block response format
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from horizon import FidelityMonitor


CHEAP_MODEL = "claude-haiku-4-5"
MAX_TOKENS_PER_REPLY = 120


def load_anthropic_key() -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key

    env_path = os.environ.get("ADA_ENV_PATH") or str(
        Path.home() / "workspace" / "leocelis" / "ada" / "ada" / ".env"
    )
    if Path(env_path).is_file():
        load_dotenv(env_path)
        key = os.environ.get("ANTHROPIC_API_KEY")
        if key:
            print(f"[setup] loaded ANTHROPIC_API_KEY from {env_path}")
            return key

    print(
        "[setup] ANTHROPIC_API_KEY not found. Export it or set ADA_ENV_PATH to "
        "a .env file that defines it.",
        file=sys.stderr,
    )
    sys.exit(1)


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
    print(
        f"  health={result.health_status}  "
        f"epsilon={result.epsilon_t:.3f}  "
        f"turn_number={result.turn_number}"
    )
    if result.events:
        print("  events:")
        for e in result.events:
            print(f"    • {e.type} (active={e.active}, confidence={e.confidence:.2f})")


def run_conversation() -> None:
    import anthropic

    api_key = load_anthropic_key()
    anthropic_client = anthropic.Anthropic(api_key=api_key, max_retries=1, timeout=60.0)

    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(
        metadata={"domain": "technical", "example": "anthropic_real_agent_e2e"}
    )
    client = monitor.wrap(anthropic_client, session_id)

    system_prompt = (
        "You are a concise technical assistant. Answer in 2-3 short sentences. "
        "Never add disclaimers or filler."
    )

    conversation = [
        "What is the halting problem and why does it matter?",
        "Is Rice's theorem related?",
        "Give a practical consequence for software engineering.",
        "Can static analysers ever be sound AND complete?",
        "Walk through a toy undecidable example.",
        "Summarise in one sentence for my team.",
    ]

    messages: list[dict[str, str]] = []
    for i, human_text in enumerate(conversation, start=1):
        messages.append({"role": "user", "content": human_text})
        response = client.messages.create(
            model=CHEAP_MODEL,
            max_tokens=MAX_TOKENS_PER_REPLY,
            system=system_prompt,
            messages=messages,
        )
        agent_reply = ""
        for block in response.content:
            if hasattr(block, "text"):
                agent_reply += block.text
        messages.append({"role": "assistant", "content": agent_reply})

        result = client.last_result
        if result is not None:
            print_turn_summary(i, human_text, agent_reply, result)

        usage = getattr(response, "usage", None)
        if usage:
            print(
                f"  anthropic-usage: input={usage.input_tokens} "
                f"output={usage.output_tokens}"
            )

    trajectory = monitor.get_trajectory(session_id)
    print("\n═══ Final trajectory ═══")
    print(f"  session_id        = {trajectory.session_id}")
    print(f"  turn_count        = {trajectory.turn_count}")
    print(f"  health_status     = {trajectory.health_status}")
    print(f"  peak_fidelity     = {trajectory.peak_fidelity:.3f}")
    print(f"  current_fidelity  = {trajectory.current_fidelity:.3f}")
    print(f"  igt_trend         = {trajectory.igt_trend:+.4f}")
    print(f"  scores            = {[round(s, 3) for s in trajectory.scores]}")

    print("\n═══ All events (default: observe mode) ═══")
    for e in monitor.get_events(session_id):
        print(f"  • turn {e.turn}: {e.type} active={e.active} conf={e.confidence:.2f}")


if __name__ == "__main__":
    t0 = time.time()
    try:
        run_conversation()
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(130)
    print(f"\ncompleted in {time.time() - t0:.1f}s")
