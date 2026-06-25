"""E2E: Horizon as a LangChain callback handler (no network, no langchain install).

We duck-type the LangChain ``BaseCallbackHandler`` contract: Horizon's
``HorizonCallback`` implements ``on_chat_model_start`` / ``on_llm_start`` /
``on_llm_end`` and is designed to work without importing ``langchain`` as a
hard dependency. We exercise it by driving those hooks directly with LangChain-
shaped objects (``ChatGeneration`` + ``AIMessage`` shapes).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from horizon import FidelityMonitor
from horizon.integrations.langchain import HorizonCallback


def _chat_gen(text: str) -> SimpleNamespace:
    """Build a LangChain-shaped ``ChatGeneration``."""
    message = SimpleNamespace(content=text, type="ai")
    return SimpleNamespace(text=text, message=message, generation_info=None)


def _llm_result(text: str) -> SimpleNamespace:
    """Build a LangChain-shaped ``LLMResult``: generations is list[list[Generation]]."""
    return SimpleNamespace(
        generations=[[_chat_gen(text)]],
        llm_output={"token_usage": {"total_tokens": 30}},
    )


@pytest.fixture(name="monitor")
def _monitor() -> FidelityMonitor:
    return FidelityMonitor()


def _drive_turn(callback: HorizonCallback, human: str, agent: str) -> None:
    """Simulate LangChain invoking callbacks around a single LLM call."""
    # ChatModel flow: on_chat_model_start supplies a list[list[BaseMessage]]
    human_msg = SimpleNamespace(type="human", content=human)
    callback.on_chat_model_start({"name": "ChatOpenAI"}, [[human_msg]])
    callback.on_llm_end(_llm_result(agent))


def test_langchain_callback_captures_multi_turn_conversation(monitor: FidelityMonitor) -> None:
    sid = monitor.new_conversation(metadata={"example": "langchain_e2e"})
    cb = HorizonCallback(monitor, sid)

    conversation = [
        ("Explain the Kelly criterion.", "Kelly sizes bets so log-wealth growth is maximised."),
        ("When does it fail?", "It fails when edge estimates are wrong or returns fat-tailed."),
        (
            "Compare with fixed-fractional.",
            "Fixed-fractional is simpler but sub-optimal asymptotically.",
        ),
    ]
    for human, agent in conversation:
        _drive_turn(cb, human, agent)

    assert len(cb.results) == len(conversation)
    trajectory = monitor.get_trajectory(sid)
    assert trajectory.turn_count == 3
    assert cb.last_result is not None
    assert cb.last_result.fidelity_score >= 0.0


def test_langchain_callback_handles_string_prompt_flow(monitor: FidelityMonitor) -> None:
    """Non-chat LLMs call ``on_llm_start(prompts=[...])`` with raw strings."""
    sid = monitor.new_conversation()
    cb = HorizonCallback(monitor, sid)

    cb.on_llm_start({"name": "OpenAI"}, ["What is the Nash equilibrium?"])
    cb.on_llm_end(
        _llm_result(
            "A Nash equilibrium is a strategy profile where no player gains by unilateral deviation."
        )
    )

    assert cb.last_result is not None
    assert cb.last_result.turn_number == 1


def test_langchain_callback_swallows_errors_silently(monitor: FidelityMonitor) -> None:
    """A malformed response must not crash the LangChain chain — the callback
    is fire-and-forget. A response that raises while being parsed should
    leave the callback in a clean state with no crash bubbling up."""
    sid = monitor.new_conversation()
    cb = HorizonCallback(monitor, sid)

    class _ExplodingResponse:
        """An object that raises whenever its attributes are accessed."""

        @property
        def generations(self):
            raise RuntimeError("simulated LangChain response corruption")

    cb.on_llm_start({"name": "OpenAI"}, ["Hello"])
    # Must not raise — callbacks are fire-and-forget.
    cb.on_llm_end(_ExplodingResponse())

    # No TurnResult captured because the attribute access blew up before
    # process_turn could be reached.
    assert cb.last_result is None
    assert cb.results == []


def test_langchain_callback_injects_client_context(monitor: FidelityMonitor) -> None:
    sid = monitor.new_conversation()
    cb = HorizonCallback(
        monitor,
        sid,
        client_context={
            "device_type": "mobile",
            "timezone": "Europe/Berlin",
            "location_class": "transit",
        },
    )

    _drive_turn(
        cb,
        "What's a good Berlin breakfast?",
        "Berlin breakfast usually means rolls with cheese and cold cuts.",
    )

    last = cb.last_result
    assert last is not None
    assert last.location_class is not None
    assert last.spatial_constraint is not None
