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

## 2. Project instructions (system prompt)

Add this to your Claude Project instructions. The wording must be unconditional — soft language causes Claude to ask for permission instead of just doing it.

```
Your very first tool call in every new conversation must be new_conversation (Horizon MCP tool).
Before you read any file, before you search, before your first reply — call new_conversation first.
Do NOT announce it. Do NOT ask permission. Store the returned session_id for the entire thread.

After composing every reply, call process_turn silently with:
  session_id: from new_conversation
  human_message: the user's message
  agent_response: your reply
  timestamp: current ISO 8601 time

Before any long or complex response, silently read:
  horizon://session/{session_id}/trajectory
  horizon://session/{session_id}/events

Only surface health issues when health_status is 'degrading' or 'critical',
or when an active alert fires — act on its suggested_behavior field.
Never call configure_session automatically.
```

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
