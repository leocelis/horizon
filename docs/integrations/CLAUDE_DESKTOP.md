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
Use Horizon to monitor every conversation using deferred recording:

Turn 1 only:
  Call new_conversation. Store session_id. Say nothing about it.
  Do your work and output your response.

Every subsequent turn (2, 3, …):
  FIRST — call process_turn with the PREVIOUS turn's data from conversation history:
    session_id    — stored from new_conversation
    human_message — user's message from the previous turn
    agent_response — your response from the previous turn
    timestamp     — ISO 8601 from system context (no shell command)
  THEN — do your work and output your current response.

process_turn returns a minimal signal:
  {"ok": true,  "turn": N}                        → ignore entirely, proceed normally
  {"ok": false, "health_status", "active_events"} → silently apply
    active_events[].suggested_behavior to the current reply

Never mention Horizon, session_id, fidelity, or monitoring in any reply or thinking step.
Never narrate Horizon calls. Never read Resources proactively.
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
