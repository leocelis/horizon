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
  {"ok": false, "health_status", "active_events"} → apply by PLANE:
    plane "conversation" → silently apply suggested_behavior to the current reply
    plane "mission"      → SURFACE it to the operator with its numbers, then
                           propose one concrete next action (see the mission-plane
                           section below). Never absorb a mission signal silently.

Never mention Horizon, session_id, fidelity, or monitoring in any reply or thinking
step. That silence covers the CONVERSATION plane only — mission-plane signals
(plane: "mission") are meant to be said out loud, with their numbers.
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

---

## Mission plane (Memento Mori) — optional, and LOUD

Horizon has a second, optional plane that clocks **missions** (goals with
deadlines) rather than conversations. It is **off unless a mission store is
configured**: with no store, its six tools (`clock_register`, `clock_progress`,
`clock_status`, `clock_propose`, `clock_ack`, `associate_mission`) do not appear
at all and nothing changes.

If you enable it, note the contract is the **opposite** of the fidelity plane's:

| | Conversation plane | Mission plane |
|---|---|---|
| Event payload | `plane: "conversation"` | `plane: "mission"` |
| What the agent does | applies `suggested_behavior` silently | **states it to the operator with its numbers**, then proposes one next action |
| Why | naming the monitor distorts the conversation | a deadline nobody hears about is the failure the plane exists to prevent |

Enable it by pointing the server at a local store:

```bash
HORIZON_MEMENTO_STORE_PATH=~/.horizon/missions.db
```

Keep the store **local**. The hosted endpoint deliberately runs without one:
mission data is single-operator and personal, and does not belong on shared
infrastructure.

The canonical agent-rules block for the mission plane — session start, the
side-effect write rule, parks needing dates, ack discipline, and the reply
prohibitions — lives in
[MEMENTO_MORI_AGENTS.md](./MEMENTO_MORI_AGENTS.md). Paste that block alongside
the one above when you turn the plane on.
