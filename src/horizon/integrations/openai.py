"""OpenAI SDK client wrapper for transparent Horizon monitoring."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from horizon.models import TurnResult
from horizon.monitor import FidelityMonitor

TimestampProvider = Callable[[], str | None]
"""Callable returning an ISO 8601 timestamp (or None to disable temporal signals)."""

ContextProvider = Callable[[], dict | None]
"""Callable returning a client_context dict (or None) for the next turn."""


class HorizonWrappedOpenAI:
    """Wraps an openai.OpenAI client to auto-call process_turn after each chat completion.

    The wrapper is transparent — all attributes delegate to the original client.
    Only chat.completions.create() is intercepted.

    Usage::

        from openai import OpenAI
        from horizon import FidelityMonitor

        monitor = FidelityMonitor()
        session_id = monitor.new_conversation()
        client = monitor.wrap(OpenAI(), session_id)

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        # process_turn was called automatically
        print(monitor.get_trajectory(session_id).current_fidelity)

    Testing / simulation::

        # Inject custom timestamps and per-turn client context
        client = monitor.wrap(OpenAI(), session_id)
        client.set_timestamp_provider(lambda: simulated_clock.isoformat())
        client.set_context_provider(lambda: current_device_context)
    """

    def __init__(
        self,
        client: Any,
        monitor: FidelityMonitor,
        session_id: str,
        include_timestamps: bool = True,
        client_context: dict | None = None,
    ) -> None:
        self._client = client
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._client_context = client_context
        self._timestamp_provider: TimestampProvider | None = None
        self._context_provider: ContextProvider | None = None
        self.last_result: TurnResult | None = None

    def set_timestamp_provider(self, provider: TimestampProvider | None) -> None:
        """Override the wall-clock timestamp used for each turn.

        Useful for replaying historical conversations or simulating temporal
        gaps in tests and examples. Pass None to restore `datetime.now(UTC)`.
        """
        self._timestamp_provider = provider

    def set_context_provider(self, provider: ContextProvider | None) -> None:
        """Supply a fresh client_context dict for each turn."""
        self._context_provider = provider

    def set_client_context(self, ctx: dict | None) -> None:
        """Set a static client_context applied to every subsequent turn."""
        self._client_context = ctx

    @property
    def chat(self) -> _WrappedChat:
        return _WrappedChat(
            self._client.chat, self._monitor, self._session_id, self._include_timestamps, self
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _WrappedChat:
    def __init__(
        self,
        chat: Any,
        monitor: FidelityMonitor,
        session_id: str,
        include_timestamps: bool,
        wrapper: HorizonWrappedOpenAI,
    ) -> None:
        self._chat = chat
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._wrapper = wrapper

    @property
    def completions(self) -> _WrappedCompletions:
        return _WrappedCompletions(
            self._chat.completions,
            self._monitor,
            self._session_id,
            self._include_timestamps,
            self._wrapper,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._chat, name)


class _WrappedCompletions:
    def __init__(
        self,
        completions: Any,
        monitor: FidelityMonitor,
        session_id: str,
        include_timestamps: bool,
        wrapper: HorizonWrappedOpenAI,
    ) -> None:
        self._completions = completions
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._wrapper = wrapper

    def create(self, **kwargs: Any) -> Any:
        """Intercept chat completion and call process_turn after response."""
        response = self._completions.create(**kwargs)
        self._post_turn(kwargs.get("messages", []), response)
        return response

    def _extract_human_message(self, messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                return str(msg.get("content", ""))
        return ""

    def _resolve_timestamp(self) -> str | None:
        if not self._include_timestamps:
            return None
        provider = self._wrapper._timestamp_provider
        if provider is not None:
            return provider()
        return datetime.now(timezone.utc).isoformat()

    def _resolve_client_context(self) -> dict | None:
        provider = self._wrapper._context_provider
        if provider is not None:
            return provider()
        return self._wrapper._client_context

    def _post_turn(self, messages: list, response: Any) -> None:
        try:
            human_msg = self._extract_human_message(messages)
            agent_resp = response.choices[0].message.content or ""

            logprobs = None
            try:
                logprobs_data = response.choices[0].logprobs
                if logprobs_data and hasattr(logprobs_data, "content"):
                    logprobs = [
                        {"token": t.token, "logprob": t.logprob}
                        for t in (logprobs_data.content or [])
                    ]
            except Exception:
                pass

            ts = self._resolve_timestamp()
            ctx = self._resolve_client_context()
            result = self._monitor.process_turn(
                self._session_id,
                human_message=human_msg,
                agent_response=agent_resp,
                timestamp=ts,
                client_context=ctx,
                logprobs=logprobs,
            )
            self._wrapper.last_result = result
        except Exception:
            pass

    def __getattr__(self, name: str) -> Any:
        return getattr(self._completions, name)
