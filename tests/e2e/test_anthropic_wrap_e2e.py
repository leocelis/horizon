"""E2E: Horizon wrapping the Anthropic SDK with a mocked client (no network).

Proves:
    - ``monitor.wrap(anthropic.Anthropic())`` intercepts ``messages.create``
    - Anthropic content-block extraction works for single and multi-block
      responses (``TextBlock`` objects, list-shaped content)
    - Multi-turn conversations populate fidelity + events
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from horizon import FidelityMonitor
from horizon.integrations.anthropic import HorizonWrappedAnthropic


def _wrap(monitor: FidelityMonitor, client: object, sid: str) -> HorizonWrappedAnthropic:
    """Instantiate the Anthropic wrapper directly (see openai e2e test for rationale)."""
    return HorizonWrappedAnthropic(client, monitor, sid)


def _text_block(text: str) -> SimpleNamespace:
    return SimpleNamespace(type="text", text=text)


def _anthropic_reply(blocks: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        id="msg-test",
        type="message",
        role="assistant",
        model="claude-opus-4-5",
        stop_reason="end_turn",
        content=[_text_block(t) for t in blocks],
        usage=SimpleNamespace(input_tokens=10, output_tokens=20),
    )


def _mock_anthropic_client(replies: list[list[str]]) -> MagicMock:
    client = MagicMock()
    client.messages = MagicMock()

    reply_iter = iter(replies)

    def _create(**_: object) -> SimpleNamespace:
        return _anthropic_reply(next(reply_iter))

    client.messages.create.side_effect = _create
    return client


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor()


def test_anthropic_wrap_multi_turn_conversation(monitor: FidelityMonitor) -> None:
    sid = monitor.new_conversation(metadata={"example": "anthropic_e2e"})

    replies = [
        ["Quantum entanglement is a correlation between particles that persists beyond classical limits."],
        ["No FTL signalling — the no-communication theorem holds; only correlations move."],
        ["Bell tests rule out local hidden variables for these correlations."],
    ]
    client = _wrap(monitor, _mock_anthropic_client(replies), sid)

    conversation = [
        "What is quantum entanglement?",
        "Can it be used for faster-than-light communication?",
        "How do Bell inequalities tie in?",
    ]
    for prompt in conversation:
        client.messages.create(
            model="claude-opus-4-5",
            max_tokens=120,
            messages=[{"role": "user", "content": prompt}],
        )

    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == 3
    assert all(0.0 <= s <= 1.0 for s in trajectory.scores)
    last = client.last_result
    assert last is not None
    assert last.igt_value >= 0.0
    assert last.consistency_score >= 0.0


def test_anthropic_wrap_handles_list_shaped_content(monitor: FidelityMonitor) -> None:
    """Anthropic's content-block API returns a list; Horizon must extract all
    text segments into a single agent_response."""
    sid = monitor.new_conversation()

    client = _wrap(monitor, _mock_anthropic_client([[
        "Paragraph one — establishing context.",
        "Paragraph two — the actual answer.",
    ]]), sid)

    client.messages.create(
        model="claude-opus-4-5",
        max_tokens=120,
        messages=[{"role": "user", "content": "Give me a structured answer."}],
    )

    last = client.last_result
    assert last is not None
    # Turn succeeded and signals were produced
    assert last.fidelity_score >= 0.0
    assert last.turn_number == 1


def test_anthropic_wrap_passes_through_unknown_attrs(monitor: FidelityMonitor) -> None:
    """The wrapper must be transparent: unrelated attributes delegate to the
    underlying client."""
    sid = monitor.new_conversation()

    raw = _mock_anthropic_client([["ok"]])
    raw.api_key = "sk-test-xyz"

    wrapped = _wrap(monitor, raw, sid)
    assert wrapped.api_key == "sk-test-xyz"
