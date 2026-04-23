"""Anthropic SDK client wrapper for transparent Horizon monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from horizon.monitor import FidelityMonitor
from horizon.models import TurnResult


class HorizonWrappedAnthropic:
    """Wraps an anthropic.Anthropic client to auto-call process_turn after each message.

    Usage::

        import anthropic
        from horizon import FidelityMonitor

        monitor = FidelityMonitor()
        session_id = monitor.new_conversation()
        client = monitor.wrap(anthropic.Anthropic(), session_id)

        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello!"}]
        )
    """

    def __init__(
        self,
        client: Any,
        monitor: FidelityMonitor,
        session_id: str,
        include_timestamps: bool = True,
        client_context: Optional[dict] = None,
    ) -> None:
        self._client = client
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._client_context = client_context
        self.last_result: Optional[TurnResult] = None

    @property
    def messages(self) -> "_WrappedMessages":
        return _WrappedMessages(
            self._client.messages, self._monitor, self._session_id,
            self._include_timestamps, self._client_context, self,
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)


class _WrappedMessages:
    def __init__(self, messages: Any, monitor: FidelityMonitor, session_id: str,
                 include_timestamps: bool, client_context: Optional[dict],
                 wrapper: HorizonWrappedAnthropic) -> None:
        self._messages = messages
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._client_context = client_context
        self._wrapper = wrapper

    def create(self, **kwargs: Any) -> Any:
        """Intercept Anthropic message creation and call process_turn after response."""
        response = self._messages.create(**kwargs)
        self._post_turn(kwargs.get("messages", []), response)
        return response

    def _extract_human_message(self, messages: list) -> str:
        for msg in reversed(messages):
            if isinstance(msg, dict) and msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    # content blocks
                    return " ".join(
                        block.get("text", "") for block in content
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                return str(content)
        return ""

    def _post_turn(self, messages: list, response: Any) -> None:
        try:
            human_msg = self._extract_human_message(messages)
            # Anthropic response: response.content is a list of ContentBlock
            agent_resp = ""
            if hasattr(response, "content"):
                for block in response.content:
                    if hasattr(block, "text"):
                        agent_resp += block.text

            ts = datetime.now(timezone.utc).isoformat() if self._include_timestamps else None
            result = self._monitor.process_turn(
                self._session_id,
                human_message=human_msg,
                agent_response=agent_resp,
                timestamp=ts,
                client_context=self._client_context,
            )
            self._wrapper.last_result = result
        except Exception:
            pass

    def __getattr__(self, name: str) -> Any:
        return getattr(self._messages, name)
