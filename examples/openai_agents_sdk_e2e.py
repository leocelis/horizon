"""End-to-end example: Horizon instrumenting the OpenAI Agents SDK.

The Agents SDK (``openai-agents``) runs a multi-step loop (tool calls + final
answer). Horizon plugs in via one helper function that's called after each
``Runner.run()`` completes — identical ``process_turn`` contract across SDKs.

Requires::

    pip install horizon-monitor openai openai-agents python-dotenv

Cost control:
    - Model: ``gpt-4o-mini``
    - Single Agent with one toy tool
    - 3 agent runs → typically under a cent

Usage::

    python examples/openai_agents_sdk_e2e.py
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from horizon import FidelityMonitor


CHEAP_MODEL = "gpt-4o-mini"


def load_openai_key() -> str:
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    env_path = os.environ.get("ADA_ENV_PATH") or str(
        Path.home() / "workspace" / "leocelis" / "ada" / "ada" / ".env"
    )
    if Path(env_path).is_file():
        load_dotenv(env_path)
        key = os.environ.get("OPENAI_API_KEY")
        if key:
            print(f"[setup] loaded OPENAI_API_KEY from {env_path}")
            return key

    print("[setup] OPENAI_API_KEY not found.", file=sys.stderr)
    sys.exit(1)


def horizon_instrument_agent_run(
    monitor: FidelityMonitor,
    session_id: str,
    run_result: Any,
    human_prompt: str,
) -> None:
    """Adapter: call once per ``Runner.run()``. Extracts final output + timestamp."""
    final_output = getattr(run_result, "final_output", None) or str(run_result)
    ts = datetime.now(timezone.utc).isoformat()
    result = monitor.process_turn(
        session_id=session_id,
        human_message=human_prompt,
        agent_response=str(final_output),
        timestamp=ts,
    )
    print(
        f"  [horizon] fidelity={result.fidelity_score:.3f}  "
        f"igt={result.igt_value:.3f}  djs={result.divergence_score:.3f}  "
        f"health={result.health_status}"
    )


def run_conversation() -> None:
    load_openai_key()
    try:
        from agents import Agent, Runner, function_tool  # openai-agents
    except ImportError:
        print(
            "[setup] openai-agents is not installed. Install with: pip install openai-agents",
            file=sys.stderr,
        )
        sys.exit(1)

    @function_tool
    def lookup_market_cap(ticker: str) -> str:
        """Toy tool: returns a fake market cap for a stock ticker."""
        return f"Market cap for {ticker.upper()}: ~$1.2T (approximate)."

    agent = Agent(
        name="finance_research_agent",
        instructions=(
            "You are a concise financial research assistant. "
            "Answer in 1-2 sentences. Use the lookup_market_cap tool when asked."
        ),
        tools=[lookup_market_cap],
        model=CHEAP_MODEL,
    )

    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(
        metadata={"domain": "technical", "example": "openai_agents_sdk_e2e"}
    )

    prompts = [
        "Look up the market cap of NVDA.",
        "Now compare that with AAPL — which is larger?",
        "Summarise in one sentence for a newsletter.",
    ]

    for i, prompt in enumerate(prompts, start=1):
        print(f"\n── Run {i} ──────────────────────────────────────────────")
        print(f"  user  : {prompt}")
        run_result = Runner.run_sync(agent, input=prompt)
        print(f"  agent : {str(run_result.final_output)[:90]}")
        horizon_instrument_agent_run(monitor, session_id, run_result, prompt)

    trajectory = monitor.get_trajectory(session_id)
    print("\n═══ Final trajectory ═══")
    print(f"  session_id        = {trajectory.session_id}")
    print(f"  turn_count        = {trajectory.turn_count}")
    print(f"  health_status     = {trajectory.health_status}")
    print(f"  peak_fidelity     = {trajectory.peak_fidelity:.3f}")
    print(f"  current_fidelity  = {trajectory.current_fidelity:.3f}")

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
