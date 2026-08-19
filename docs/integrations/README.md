# Horizon integration index

Horizon ships with production-ready adapters for OpenAI, Anthropic,
LangChain/LangGraph, the OpenAI Agents SDK, and MCP clients (Cursor, Claude
Desktop, Claude Code). GitHub Copilot is not yet a working integration — see
the note below. Pick the shortest path for your stack.

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
| Mission plane (Memento Mori) — optional, any MCP host | Configure a local store, then paste the rules block — [MEMENTO_MORI_AGENTS.md](./MEMENTO_MORI_AGENTS.md) | rules block in `MEMENTO_MORI_AGENTS.md` §3 | [`tests/unit/memento_mori/test_mcp_tools.py`](../../tests/unit/memento_mori/test_mcp_tools.py) |
| GitHub Copilot — **experimental, not yet working** | VS Code extension / gateway middleware / log replay — [COPILOT.md](./COPILOT.md) | see `COPILOT.md` | no Copilot-specific test; Patterns 2–3 reuse the raw-strings/MCP e2e paths, Pattern 1 (VS Code extension) is untested pseudocode |

## Two planes, two contracts

Everything in the table above is the **conversation** plane: it measures the health of
a dialogue and its signals are applied *silently*. Horizon also ships an optional
**mission** plane (Memento Mori) that measures elapsed calendar time against goals —
ages, deadlines, stalls, entity latency. It is **inert unless a mission store is
configured**, and its contract is deliberately inverted: mission signals are
**surfaced to the operator with their numbers**, never absorbed silently. Events carry
a `plane` field (`"conversation"` | `"mission"`) so hosts route the two correctly.
See [MEMENTO_MORI_AGENTS.md](./MEMENTO_MORI_AGENTS.md).

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

Six of the seven integration surfaces above are exercised by automated tests
that run without network access or API keys. GitHub Copilot is the
exception — it is an experimental recipe (see the note in the table above),
not a tested integration. See [`../../tests/e2e/`](../../tests/e2e/) for the
full suite.
