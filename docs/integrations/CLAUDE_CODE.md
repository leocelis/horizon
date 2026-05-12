# Horizon in Claude Code (via MCP)

Horizon ships a FastMCP server that exposes the full API as MCP primitives:

| Layer | Primitives | Controls |
|---|---|---|
| **Tools** (state-changing) | `new_conversation`, `process_turn`, `configure_session` | Model-initiated |
| **Resources** (read-only context) | `horizon://session/{id}/trajectory`, `horizon://session/{id}/events` | App-attached to context |
| **Prompt** (user-invokable template) | `monitor_conversation` | User-triggered |

The MCP contract is identical to Cursor — the same tools, resources, and prompt work in both clients.

---

## 1. Register in Claude Code

Three options in order of setup time:

### Option A — Hosted endpoint (zero install, recommended)

No Python install required. Request an alpha key via [GitHub Discussions](https://github.com/leocelis/horizon/discussions), then run:

```bash
# User scope — available in every project
claude mcp add --transport http horizon https://horizon.leocelis.com/sse \
  --header "Authorization: Bearer YOUR_KEY_HERE" \
  --scope user
```

Verify:
```bash
claude mcp get horizon
```

The three tools, two resources, and one prompt appear in every Claude Code session.

### Option B — pip install (stdio)

```bash
pip install 'horizon-monitor[mcp]'
```

```bash
# User scope — available in every project
claude mcp add horizon -- python -m horizon.mcp.server --scope user
```

### Option C — Project scope (`.mcp.json`)

Useful when you want Horizon only in one repo. Create `.mcp.json` at the project root:

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

Claude Code picks up `.mcp.json` automatically and prompts for trust approval on first use.

---

## 2. Add instructions to `~/.claude/CLAUDE.md`

Claude Code reads `~/.claude/CLAUDE.md` as global instructions for every session across all projects. Add the Horizon monitoring block there so the agent follows the call sequence without being asked.

The wording must be unconditional — soft language causes Claude to ask for permission instead of just acting.

**`~/.claude/CLAUDE.md`** (append):

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

For project-scoped instructions, add the same block to the project's `CLAUDE.md` instead.

---

## 3. Allow Horizon tools without per-call approval

Without an allowlist entry, Claude Code prompts for approval on every `process_turn` call. Add a rule to your settings to auto-allow the monitoring tools:

**`~/.claude/settings.json`** (or project `.claude/settings.json`):

```json
{
  "permissions": {
    "allow": [
      "mcp__horizon__new_conversation",
      "mcp__horizon__process_turn"
    ]
  }
}
```

`configure_session` is intentionally excluded — it mutates session config and should require explicit approval.

---

## 4. What you get

- **Per-turn fidelity** — a [0, 1] score updated automatically.
- **Convergence detection** — Claude knows when the conversation is plateauing and can offer to summarize and close.
- **Light-cone tracking** — reachable-context ratio warns when earlier turns have dropped out of effective context.
- **Temporal / circadian signals** — when sessions span hours or days, Horizon surfaces retention decay and circadian cognitive factors.

---

## 5. Verification

```bash
# Confirm the server is registered
claude mcp list

# Confirm the tools are available (inside a session)
# /mcp  — shows all connected servers and tool counts
```

The MCP server is tested in `tests/e2e/test_mcp_server_e2e.py`, which exercises the exact dispatch layer invoked by Claude Code, Cursor, and Claude Desktop.

---

## 6. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `command not found` when using `horizon serve` | Script not installed | Use `python -m horizon.mcp.server` instead, or `pip install 'horizon-monitor[mcp]'` |
| Tools don't appear | MCP server not registered or wrong scope | Run `claude mcp list` to check; re-add with correct `--scope` |
| Per-call approval dialogs every turn | No allowlist in `settings.json` | Add the `permissions.allow` snippet from §3 |
| `new_conversation` never fires | Instructions not in `~/.claude/CLAUDE.md` | Append the monitoring block from §2 |
| First `process_turn` takes a few seconds | Model warming up after server start | Normal — subsequent calls are ≈100 ms |
| Resource URIs not resolving | Session not yet created | Call `new_conversation` first; resources require a valid `session_id` |
