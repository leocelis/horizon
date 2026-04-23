"""End-to-end example: Horizon wrapping a real OpenAI agent.

Runs a multi-turn conversation against OpenAI's cheap ``gpt-4o-mini`` model
and shows how Horizon automatically tracks fidelity, events, temporal gaps,
and 4D spacetime signals — with zero changes to agent code.

Cost control:
    - Model: ``gpt-4o-mini`` (~$0.15 / 1M input, $0.60 / 1M output tokens)
    - ``max_tokens=120`` per reply
    - 6-turn conversation → typically < 2,000 tokens total → under $0.002

Usage::

    # 1) Ensure OPENAI_API_KEY is set, or fall back to ADA's .env
    python examples/openai_real_agent_e2e.py

    # 2) Override the env file location
    ADA_ENV_PATH=/path/to/.env python examples/openai_real_agent_e2e.py

What this demonstrates:
    - ``monitor.wrap(client)`` — transparent interception of ``chat.completions.create``
    - Real-time fidelity score computation per turn
    - Temporal signals via an injected simulated clock (3-day gap)
    - Spatial signals via ``client_context`` (desktop → mobile switch)
    - Light-cone / causal reachability tracking across turns
    - Event emission in default observe mode (no agent coupling)
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from horizon import FidelityMonitor


CHEAP_MODEL = "gpt-4o-mini"
"""Cost-controlled model."""

MAX_TOKENS_PER_REPLY = 120
"""Hard cap on tokens per agent reply to keep the example under a few cents."""


def load_openai_key() -> str:
    """Prefer the env var; fall back to ADA's .env. Fail early if neither works."""
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
        "[setup] OPENAI_API_KEY not found. Export it or set ADA_ENV_PATH to "
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
        ds2 = result.spacetime_interval if result.spacetime_interval is not None else 0.0
        cls = result.interval_class or "—"
        kappa = result.circadian_factor if result.circadian_factor is not None else 1.0
        retention = result.estimated_retention if result.estimated_retention is not None else 1.0
        print(
            f"  Δτ={result.gap_seconds:.1f}s ({result.gap_class})  "
            f"retention={retention:.3f}  κ={kappa:.2f}  ds²={ds2:.3f} ({cls})"
        )

    if result.spatial_constraint:
        sc = result.spatial_constraint
        print(
            f"  spatial: attention={sc.attention_budget}  screen={sc.screen_capacity}  "
            f"max_tokens={sc.max_response_length}  complexity={sc.complexity_ceiling}"
        )

    if result.events:
        print("  events:")
        for e in result.events:
            print(f"    • {e.type} (active={e.active}, confidence={e.confidence:.2f})")


def run_conversation() -> None:
    from openai import OpenAI

    api_key = load_openai_key()
    openai_client = OpenAI(api_key=api_key, max_retries=1, timeout=60.0)

    monitor = FidelityMonitor()
    session_id = monitor.new_conversation(
        metadata={"domain": "technical", "example": "openai_real_agent_e2e"}
    )

    desktop_ctx = {
        "device_type": "desktop",
        "timezone": "America/New_York",
        "location_class": "office",
    }
    mobile_ctx = {
        "device_type": "mobile",
        "timezone": "America/New_York",
        "location_class": "transit",
    }

    client = monitor.wrap(openai_client, session_id)

    simulated_clock = {"now": datetime.now(timezone.utc)}
    current_ctx = {"ctx": desktop_ctx}

    client.set_timestamp_provider(lambda: simulated_clock["now"].isoformat())
    client.set_context_provider(lambda: current_ctx["ctx"])

    system_msg = {
        "role": "system",
        "content": (
            "You are a concise technical assistant. Answer in 2-3 short sentences. "
            "Never add disclaimers or filler."
        ),
    }
    messages: list[dict[str, str]] = [system_msg]

    conversation_script = [
        ("How does Python's garbage collector handle reference cycles?", desktop_ctx, timedelta(seconds=30)),
        ("What about weak references — when would I use them?", desktop_ctx, timedelta(seconds=45)),
        ("Can memory leaks still happen despite GC?", desktop_ctx, timedelta(seconds=60)),
        (
            "ok, back to this — where were we again with weak references?",
            mobile_ctx,
            timedelta(days=3),
        ),
        ("actually let me switch topics: explain event loops in asyncio.", mobile_ctx, timedelta(seconds=90)),
        ("what's the difference between create_task and gather?", mobile_ctx, timedelta(seconds=40)),
    ]

    for i, (human_text, ctx, time_jump) in enumerate(conversation_script, start=1):
        simulated_clock["now"] = simulated_clock["now"] + time_jump
        current_ctx["ctx"] = ctx
        messages.append({"role": "user", "content": human_text})

        response = client.chat.completions.create(
            model=CHEAP_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS_PER_REPLY,
            temperature=0.3,
        )
        agent_reply = response.choices[0].message.content or ""
        messages.append({"role": "assistant", "content": agent_reply})

        result = client.last_result
        if result is not None:
            print_turn_summary(i, human_text, agent_reply, result)
        else:
            print(f"  [horizon] no TurnResult captured for turn {i}", file=sys.stderr)

        usage = getattr(response, "usage", None)
        if usage:
            print(
                f"  openai-usage: prompt={usage.prompt_tokens} "
                f"completion={usage.completion_tokens} total={usage.total_tokens}"
            )

    trajectory = monitor.get_trajectory(session_id)
    print("\n═══ Final trajectory ═══")
    print(f"  session_id        = {trajectory.session_id}")
    print(f"  turn_count        = {trajectory.turn_count}")
    print(f"  health_status     = {trajectory.health_status}")
    print(f"  peak_fidelity     = {trajectory.peak_fidelity:.3f}")
    print(f"  current_fidelity  = {trajectory.current_fidelity:.3f}")
    print(f"  igt_trend         = {trajectory.igt_trend:+.4f}")
    if trajectory.estimated_t_star is not None:
        print(f"  estimated_t*      = {trajectory.estimated_t_star}")

    print(f"  scores            = {[round(s, 3) for s in trajectory.scores]}")
    print(
        f"  gaps (seconds)    = "
        f"{[round(g, 1) if g is not None else None for g in trajectory.gap_durations]}"
    )

    print("\n═══ All events (default: observe mode) ═══")
    all_events = monitor.get_events(session_id)
    if not all_events:
        print("  (none)")
    else:
        for e in all_events:
            print(
                f"  • turn {e.turn}: {e.type} "
                f"active={e.active} conf={e.confidence:.2f}"
            )


if __name__ == "__main__":
    t0 = time.time()
    try:
        run_conversation()
    except KeyboardInterrupt:
        print("\naborted.")
        sys.exit(130)
    print(f"\ncompleted in {time.time() - t0:.1f}s")
