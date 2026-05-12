# Horizon integration index

Horizon ships with production-ready adapters for every major agent runtime.
Pick the shortest path for your stack.

| Stack | How to plug in | Runnable example | CI-safe test |
|---|---|---|---|
| OpenAI SDK (`openai`) | `monitor.wrap(client, sid)` | [`examples/openai_real_agent_e2e.py`](../../examples/openai_real_agent_e2e.py) | [`tests/e2e/test_openai_wrap_e2e.py`](../../tests/e2e/test_openai_wrap_e2e.py) |
| Anthropic SDK (`anthropic`) | `monitor.wrap(client, sid)` | [`examples/anthropic_real_agent_e2e.py`](../../examples/anthropic_real_agent_e2e.py) | [`tests/e2e/test_anthropic_wrap_e2e.py`](../../tests/e2e/test_anthropic_wrap_e2e.py) |
| LangChain / LangGraph | `HorizonCallback(monitor, sid)` | [`examples/langchain_real_agent_e2e.py`](../../examples/langchain_real_agent_e2e.py) | [`tests/e2e/test_langchain_callback_e2e.py`](../../tests/e2e/test_langchain_callback_e2e.py) |
| OpenAI Agents SDK (`openai-agents`) | `horizon_instrument_agent_run(...)` | [`examples/openai_agents_sdk_e2e.py`](../../examples/openai_agents_sdk_e2e.py) | [`tests/e2e/test_openai_agents_sdk_e2e.py`](../../tests/e2e/test_openai_agents_sdk_e2e.py) |
| Any custom / local LLM | `monitor.process_turn(sid, human, agent, ...)` | [`examples/raw_framework_agnostic_e2e.py`](../../examples/raw_framework_agnostic_e2e.py) | [`tests/e2e/test_raw_strings_e2e.py`](../../tests/e2e/test_raw_strings_e2e.py) |
| Cursor (IDE agent) | MCP server — [CURSOR.md](./CURSOR.md) | MCP config snippet in `CURSOR.md` | [`tests/e2e/test_mcp_server_e2e.py`](../../tests/e2e/test_mcp_server_e2e.py) |
| Claude Desktop | MCP server — [CLAUDE_DESKTOP.md](./CLAUDE_DESKTOP.md) | MCP config snippet in `CLAUDE_DESKTOP.md` | [`tests/e2e/test_mcp_server_e2e.py`](../../tests/e2e/test_mcp_server_e2e.py) |
| Claude Code (CLI) | MCP server — [CLAUDE_CODE.md](./CLAUDE_CODE.md) | `claude mcp add` + `~/.claude/CLAUDE.md` block | [`tests/e2e/test_mcp_server_e2e.py`](../../tests/e2e/test_mcp_server_e2e.py) |
| GitHub Copilot | VS Code extension / gateway middleware / log replay — [COPILOT.md](./COPILOT.md) | see `COPILOT.md` | covered by raw + MCP e2e tests |

## The common contract

Every adapter ultimately funnels into the same four calls:

```python
monitor = FidelityMonitor()
sid = monitor.new_conversation(metadata=...)
monitor.process_turn(
    session_id=sid,
    human_message=...,   # str
    agent_response=...,  # str
    timestamp=...,       # optional ISO 8601 — unlocks 4D signals
    client_context=...,  # optional {"device_type", "timezone", "location_class", "ip_address"}
    logprobs=...,        # optional
    human_latency_ms=..., # optional
)
monitor.get_trajectory(sid)
monitor.get_events(sid, active_only=...)
```

Adapters only differ in *how* they feed the first two string arguments. The
signal math, the event system, the fidelity score — all identical.

## Proven end to end

All seven integration surfaces above are exercised by automated tests that
run without network access or API keys. See
[`../../tests/e2e/`](../../tests/e2e/) for the full suite.
