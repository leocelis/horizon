# Horizon in Claude Desktop (via MCP)

Claude Desktop has first-class MCP support. The MCP contract is identical to Cursor — the same tools, resources, and prompt work in both clients.

---

## 1. Register in Claude Desktop

Edit `claude_desktop_config.json`:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

### Option A — Hosted endpoint (zero install, recommended for alpha users)

No Python install required. Request an alpha key via [GitHub Discussions](https://github.com/leocelis/horizon/discussions), then add:

```json
{
  "mcpServers": {
    "horizon": {
      "url": "https://horizon.leocelis.com/sse",
      "headers": { "Authorization": "Bearer YOUR_KEY_HERE" }
    }
  }
}
```

Restart Claude Desktop. The tools appear in the MCP panel immediately.

### Option B — pip install

```bash
pip install 'horizon-monitor[mcp]'
```

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

Restart Claude Desktop. The three tools (`new_conversation`, `process_turn`, `configure_session`), two resources, and one prompt appear in the MCP tools panel.

---

## 2. Suggested system-prompt snippet

Prepend to your Claude project instructions:

> "Track this conversation with Horizon. On the first turn, call `new_conversation` and store the session_id. After every response, call `process_turn` with the previous user message and your reply, including the current ISO-8601 timestamp. Before composing each reply, read `horizon://session/{session_id}/trajectory` and silently adjust tone / verbosity if fidelity trends down. When `health_status` is `degrading` or any alert fires, surface it to the user with the event's suggested_behavior."

---

## 3. What you get

- **Per-turn fidelity** — a [0, 1] score updated automatically.
- **Convergence detection** — Claude knows when the conversation is plateauing and can offer to summarize and close.
- **Light-cone tracking** — reachable-context ratio warns when earlier turns have dropped out of effective context.
- **Temporal / circadian signals** — when chats span hours or days, Horizon surfaces retention decay and circadian cognitive factors.

---

## 4. Transports

`stdio` is correct for local Claude Desktop. Use SSE only when a separate process needs to reach Horizon over HTTP:

```bash
horizon serve --transport sse --port 3847
```

For the hosted endpoint, SSE is used automatically via the `url` field in the config.

---

## 5. Verification

The MCP server is tested in `tests/e2e/test_mcp_server_e2e.py`, which exercises the exact dispatch layer invoked by both Cursor and Claude Desktop.
