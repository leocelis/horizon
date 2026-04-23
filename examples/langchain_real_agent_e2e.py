"""End-to-end example: Horizon as a LangChain callback.

Runs a real LangChain ``ChatOpenAI`` conversation and attaches ``HorizonCallback``
so every ``.invoke()`` call is tracked automatically — no code changes to any
chain or agent.

Requires::

    pip install horizon-monitor langchain langchain-openai python-dotenv

Cost control:
    - Model: ``gpt-4o-mini``
    - ``max_tokens=120`` per reply
    - 5-turn conversation under $0.002

Usage::

    python examples/langchain_real_agent_e2e.py
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from horizon import FidelityMonitor
from horizon.integrations.langchain import HorizonCallback


CHEAP_MODEL = "gpt-4o-mini"
MAX_TOKENS_PER_REPLY = 120


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

    print(
        "[setup] OPENAI_API_KEY not found. Export it or set ADA_ENV_PATH.",
        file=sys.stderr,
    )
    sys.exit(1)


def print_turn_summary(turn_idx: int, human: str, result: Any) -> None:
    print(f"\n── Turn {turn_idx} ──────────────────────────────────────────────")
    print(f"  human : {human[:90]}{'…' if len(human) > 90 else ''}")
    print(
        f"  fidelity={result.fidelity_score:.3f}  "
        f"igt={result.igt_value:.3f}  "
        f"djs={result.divergence_score:.3f}  "
        f"twr={result.twr_value:.3f}"
    )
    print(f"  health={result.health_status}  epsilon={result.epsilon_t:.3f}")


def run_conversation() -> None:
    load_openai_key()  # populate OPENAI_API_KEY for langchain_openai

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_openai import ChatOpenAI
    except ImportError:
        print(
            "[setup] missing langchain. Install with: "
            "pip install langchain langchain-openai",
            file=sys.stderr,
        )
        sys.exit(1)

    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(
        metadata={"domain": "technical", "example": "langchain_real_agent_e2e"}
    )
    callback = HorizonCallback(monitor, session_id)

    llm = ChatOpenAI(
        model=CHEAP_MODEL,
        max_tokens=MAX_TOKENS_PER_REPLY,
        temperature=0.3,
        callbacks=[callback],
    )

    conversation = [
        "What is the Peter principle in organisations?",
        "Does it apply to flat engineering orgs?",
        "How would you counteract it in hiring?",
        "Give one concrete metric to watch.",
        "Summarise for a hiring-manager handbook.",
    ]

    history = [SystemMessage(content="Be concise: 2-3 sentences per reply.")]
    for i, human_text in enumerate(conversation, start=1):
        history.append(HumanMessage(content=human_text))
        response = llm.invoke(history)
        history.append(response)  # AIMessage

        result = callback.last_result
        if result is not None:
            print_turn_summary(i, human_text, result)

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
