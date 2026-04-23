# Horizon in Cursor (via MCP)

Horizon ships an MCP server that turns every Horizon API into an MCP tool. Once
registered, Cursor's agent (and Background Agents / Bugbot) can call
`new_conversation`, `process_turn`, `get_trajectory`, `get_events`, and
`configure` directly — no code changes to your project, no SDK coupling.

## 1. Install

```bash
pip install 'horizon-monitor[mcp]'
```

This adds the `horizon` CLI entry point (see `src/horizon/mcp/cli.py`) and
the `mcp` + `click` extras.

Verify:

```bash
horizon --help
horizon serve --help
```

## 2. Register in Cursor

Cursor reads MCP servers from `.cursor/mcp.json` (workspace-level) or
`~/.cursor/mcp.json` (user-level). Add:

```json
{
  "mcpServers": {
    "horizon": {
      "command": "horizon",
      "args": ["serve"],
      "env": {}
    }
  }
}
```

Reload Cursor. The Horizon tools appear in the agent's tool list.

## 3. How to use from inside Cursor

Typical flow the agent should follow:

1. Call `new_conversation` once per distinct task or chat thread. Store the
   returned `session_id`.
2. After every LLM turn (or every meaningful user ↔ agent round), call
   `process_turn` with the human message and the agent's response. Supply
   `timestamp` (ISO 8601) to enable 4D spacetime signals.
3. When the user asks "how is this going?", call `get_trajectory` — fidelity,
   T*, health status, gap durations.
4. When something looks off, call `get_events` (optionally `active_only=true`)
   and feed the suggested behaviours back into your system prompt.
5. To flip an event from `observe` to `active` mode for a specific session,
   call `configure` with an `event_modes` override.

### Example prompt for a Cursor agent

> "For this project, treat every user message + response pair as a new Horizon
> turn. Before composing the next response, fetch `get_trajectory` and
> `get_events`. If `health_status == 'degrading'` or any `alert.drift` event
> fires, warn the user and offer to re-anchor the conversation."

## 4. Privacy guarantee

Horizon's default config is 100% local: `no_external_calls_default` is a
priority-2 constraint backed by `tests/unit/test_privacy.py`. The MCP server
adds no network behaviour — it only speaks MCP over stdio (or local SSE).

## 5. Troubleshooting

| Symptom | Likely cause |
|---|---|
| `horizon: command not found` | Extra not installed; run `pip install 'horizon-monitor[mcp]'`. |
| `ImportError: MCP support requires ...` | The `[mcp]` extra is missing. |
| Tools don't show up in Cursor | Check `.cursor/mcp.json` JSON syntax; reload the MCP panel. |
| Cold start takes 30–60s on first call | Sentence-transformer download; subsequent calls are instant (cached). |
