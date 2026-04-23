# Horizon in Claude Desktop (via MCP)

Claude Desktop has first-class MCP support. Configure Horizon in the same way
as Cursor (see `CURSOR.md`) — the MCP contract is shared.

## 1. Install

```bash
pip install 'horizon-monitor[mcp]'
```

## 2. Register in Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

Add:

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

Restart Claude Desktop. The Horizon tools (new_conversation, process_turn,
get_trajectory, get_events, configure) appear in the MCP tools panel.

## 3. Suggested system-prompt snippet

When using Horizon from Claude Desktop, prepend to your project instructions:

> "Track this conversation with Horizon. On the first turn, call
> `new_conversation` and store the session_id. After every response, call
> `process_turn` with the previous user message and your reply, including the
> current ISO-8601 timestamp. Before composing each reply, call
> `get_trajectory` and `get_events` and silently adjust tone / verbosity if
> the fidelity score trends down."

## 4. What you get

- **Per-turn fidelity** — a [0, 1] score updated automatically.
- **Convergence detection** — Claude knows when the conversation is
  plateauing and can offer to summarize and close.
- **Light-cone tracking** — reachable-context ratio warns when earlier turns
  have dropped out of the model's effective context.
- **Temporal / circadian signals** — when chats span hours or days, Horizon
  surfaces retention decay and circadian cognitive factors.

## 5. Transports

`stdio` (default) is correct for both Claude Desktop and Cursor. Use `sse` only
when a separate process needs to reach Horizon over HTTP:

```bash
horizon serve --transport sse --port 3847
```

## 6. Verification

Everything above is covered by `tests/e2e/test_mcp_server_e2e.py`, which
exercises the exact `_dispatch` routing layer invoked by both Cursor and
Claude Desktop.
