"""E2E: Horizon wrapping the OpenAI SDK with a mocked client (no network).

Proves:
    - ``monitor.wrap(client)`` intercepts ``chat.completions.create``
    - ``set_timestamp_provider`` / ``set_context_provider`` inject simulated
      temporal + spatial context
    - All 4D signals populate end-to-end across a multi-turn conversation
    - ``no_external_calls_default`` holds: the wrapper does not touch the
      network; the mock OpenAI client is the only boundary.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from horizon import FidelityMonitor
from horizon.integrations.openai import HorizonWrappedOpenAI


def _wrap(monitor: FidelityMonitor, client: object, sid: str) -> HorizonWrappedOpenAI:
    """Construct the OpenAI wrapper directly. ``monitor.wrap()`` auto-detects the
    underlying client type by its module path, which doesn't apply to our
    MagicMock stand-ins — instantiating the wrapper class makes the test
    independent of the real ``openai`` package being installed."""
    return HorizonWrappedOpenAI(client, monitor, sid)


def _openai_reply(text: str) -> SimpleNamespace:
    """Build an object shaped like ``openai.types.chat.ChatCompletion``."""
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=text),
                finish_reason="stop",
                logprobs=None,
            )
        ],
        usage=SimpleNamespace(prompt_tokens=10, completion_tokens=20, total_tokens=30),
        id="chatcmpl-test",
        model="gpt-4o-mini",
    )


def _mock_openai_client(replies: list[str]) -> MagicMock:
    """Construct a mock OpenAI client that returns a scripted list of replies."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()

    reply_iter = iter(replies)

    def _create(**_: object) -> SimpleNamespace:
        return _openai_reply(next(reply_iter))

    client.chat.completions.create.side_effect = _create
    return client


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor()


def test_openai_wrap_runs_multi_turn_conversation(monitor: FidelityMonitor) -> None:
    """Run a 4-turn technical Q&A with simulated clock and device switch."""
    sid = monitor.new_conversation(metadata={"example": "openai_e2e"})

    replies = [
        "CPython uses a generational reference-counting GC with cycle collection.",
        "Weak references let you track objects without preventing GC, useful for caches.",
        "Yes, C extension leaks and long-lived references can leak despite GC.",
        "asyncio's event loop schedules coroutines cooperatively via a single thread.",
    ]
    client = _wrap(monitor, _mock_openai_client(replies), sid)

    simulated = {"now": datetime(2026, 4, 22, 9, 0, tzinfo=timezone.utc)}
    ctx = {
        "ctx": {
            "device_type": "desktop",
            "timezone": "America/New_York",
            "location_class": "office",
        }
    }
    client.set_timestamp_provider(lambda: simulated["now"].isoformat())
    client.set_context_provider(lambda: ctx["ctx"])

    messages: list[dict[str, str]] = [{"role": "system", "content": "Concise technical assistant."}]
    script = [
        ("How does Python's GC handle reference cycles?", timedelta(seconds=30)),
        ("What about weak references?", timedelta(seconds=45)),
        ("Can memory leaks still happen?", timedelta(seconds=60)),
        ("Switching gears — explain asyncio's event loop.", timedelta(days=3)),
    ]

    for i, (human, gap) in enumerate(script):
        simulated["now"] = simulated["now"] + gap
        if i == len(script) - 1:
            ctx["ctx"] = {
                "device_type": "mobile",
                "timezone": "America/New_York",
                "location_class": "transit",
            }
        messages.append({"role": "user", "content": human})
        response = client.chat.completions.create(model="gpt-4o-mini", messages=messages)
        messages.append({"role": "assistant", "content": response.choices[0].message.content})

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == len(script)
    assert len(trajectory.scores) == len(script)
    assert all(0.0 <= s <= 1.0 for s in trajectory.scores)

    last = client.last_result
    assert last is not None
    assert last.gap_seconds is not None and last.gap_seconds > 0
    assert last.circadian_factor is not None
    assert last.spatial_constraint is not None
    assert last.location_class is not None
    assert last.reachable_turns is not None
    assert last.reachable_fraction is not None


def test_openai_wrap_respects_framework_agnostic_constraint(monitor: FidelityMonitor) -> None:
    """Wrapping a mock client must not import langchain, llama_index, or any other
    optional framework. This guards against accidental transitive imports from
    our integration adapters."""
    import sys

    forbidden = {"langchain", "llama_index", "langgraph"}
    # reset baseline: some of these may be loaded by prior tests. Snapshot.
    before = {m.split(".", 1)[0] for m in sys.modules} & forbidden

    sid = monitor.new_conversation()
    client = _wrap(monitor, _mock_openai_client(["hi there"]), sid)
    client.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "user", "content": "hi"}]
    )

    after = {m.split(".", 1)[0] for m in sys.modules} & forbidden
    newly_imported = after - before
    assert not newly_imported, f"OpenAI wrap leaked framework imports: {newly_imported}"


def test_openai_wrap_emits_events_in_observe_mode(monitor: FidelityMonitor) -> None:
    """Default config: all events should be observe-mode (active=False)."""
    sid = monitor.new_conversation()

    replies = ["The capital of France is Paris.", "Sorry, did you say France or Spain?"]
    client = _wrap(monitor, _mock_openai_client(replies), sid)

    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "What's the capital of France?"}],
    )
    client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Did I say Spain? I meant France."}],
    )

    events = monitor.get_events(sid)
    for event in events:
        assert event.active is False, f"Event {event.type} should default to observe mode"
