"""LangChain callback handler for automatic Horizon turn monitoring."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from horizon.models import TurnResult
from horizon.monitor import FidelityMonitor


class HorizonCallback:
    """LangChain BaseCallbackHandler that auto-calls process_turn after each LLM invocation.

    Usage with LangChain::

        from langchain_openai import ChatOpenAI
        from horizon import FidelityMonitor
        from horizon.integrations.langchain import HorizonCallback

        monitor = FidelityMonitor()
        session_id = monitor.new_conversation()
        callback = HorizonCallback(monitor, session_id)

        llm = ChatOpenAI(callbacks=[callback])
        llm.invoke("Tell me about Python asyncio")

    The callback stores the last human message and result for access after invocation.
    """

    def __init__(
        self,
        monitor: FidelityMonitor,
        session_id: str,
        include_timestamps: bool = True,
        client_context: dict | None = None,
    ) -> None:
        self._monitor = monitor
        self._session_id = session_id
        self._include_timestamps = include_timestamps
        self._client_context = client_context
        self._pending_human_message: str | None = None
        self.last_result: TurnResult | None = None
        self.results: list[TurnResult] = []

    def on_llm_start(
        self, serialized: dict, prompts: list[str], **kwargs: Any
    ) -> None:
        """Capture the last human prompt."""
        if prompts:
            self._pending_human_message = prompts[-1]

    def on_chat_model_start(
        self, serialized: dict, messages: list, **kwargs: Any
    ) -> None:
        """Capture the last human message from a chat prompt."""
        try:
            flat_messages = messages[0] if messages else []
            for msg in reversed(flat_messages):
                content = getattr(msg, "content", None) or (
                    msg.get("content") if isinstance(msg, dict) else None
                )
                if content:
                    self._pending_human_message = str(content)
                    break
        except Exception:
            pass

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Process the completed turn after the LLM response is available."""
        if self._pending_human_message is None:
            return

        try:
            agent_response = ""
            generations = getattr(response, "generations", None)
            if generations:
                first_gen = generations[0]
                if first_gen:
                    gen = first_gen[0]
                    agent_response = (
                        getattr(gen, "text", None)
                        or getattr(getattr(gen, "message", None), "content", None)
                        or str(gen)
                    )

            ts = datetime.now(timezone.utc).isoformat() if self._include_timestamps else None

            result = self._monitor.process_turn(
                self._session_id,
                human_message=self._pending_human_message,
                agent_response=agent_response,
                timestamp=ts,
                client_context=self._client_context,
            )
            self.last_result = result
            self.results.append(result)
        except Exception:
            pass
        finally:
            self._pending_human_message = None

    # Make the class usable as a LangChain callback by duck-typing the protocol
    # (avoids requiring langchain as a hard dependency)
    def __call__(self, *args: Any, **kwargs: Any) -> None:
        pass
