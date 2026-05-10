# Horizon in Cursor (via MCP)

Horizon ships a FastMCP server that exposes the full API as MCP primitives:

| Layer | Primitives | Controls |
|---|---|---|
| **Tools** (state-changing) | `new_conversation`, `process_turn`, `configure_session` | Model-initiated |
| **Resources** (read-only context) | `horizon://session/{id}/trajectory`, `horizon://session/{id}/events` | App-attached to context |
| **Prompt** (user-invokable template) | `monitor_conversation` | User-triggered |

Resources are passive and cacheable — Cursor can inject them as context without spending a tool-call slot. The Prompt creates a new session and injects the full monitoring loop into the system context with one user action.

---

## 1. Register in Cursor

Three options in order of setup time:

### Option A — Hosted endpoint (zero install, recommended for alpha users)

No Python install required. Request an alpha key via [GitHub Discussions](https://github.com/leocelis/horizon/discussions), then add to `~/.cursor/mcp.json`:

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

Reload the MCP panel (Cursor Settings → Features → Model Context Protocol → toggle off/on). Done — the three tools, resources, and prompt appear immediately.

> The hosted endpoint runs on DigitalOcean with Redis-backed session resumability. It is key-protected and in private alpha. Keys are distributed to agent developers on request.

### Option B — pip install (global `~/.cursor/mcp.json`)

```bash
pip install 'horizon-monitor[mcp]'
```

Verify:
```bash
python -m horizon.mcp.server --help 2>/dev/null || python -c "from horizon.mcp.server import mcp; print('OK', mcp.name)"
```

Add to `~/.cursor/mcp.json` — replace the Python path with your actual venv or system Python:

```json
{
  "mcpServers": {
    "horizon": {
      "command": "/path/to/venv/bin/python",
      "args": ["-m", "horizon.mcp.server"],
      "env": {}
    }
  }
}
```

**Find your Python path:**
```bash
which python3   # system Python
# or for a venv:
echo /Users/you/workspace/project/.venv/bin/python
```

### Option C — workspace (`.cursor/mcp.json`)

Useful when you want Horizon only in one project:

```json
{
  "mcpServers": {
    "horizon": {
      "command": "${workspaceFolder}/.venv/bin/python",
      "args": ["-m", "horizon.mcp.server"],
      "env": {
        "PYTHONPATH": "${workspaceFolder}/src"
      }
    }
  }
}
```

After adding any entry, reload the MCP panel or restart Cursor. The three tools, two resources, and one prompt appear in the agent's tool list.

---

## 3. Enable auto-run for read-only tools

Without `permissions.json`, Cursor asks for approval on every `process_turn` call. That's per-turn friction you don't want for a monitoring tool. Fix it once with:

**`~/.cursor/permissions.json`:**

```jsonc
{
  // Horizon read-only tools: auto-run without approval
  // configure_session is intentionally excluded — it mutates config
  "mcpAllowlist": [
    "horizon:new_conversation",
    "horizon:process_turn"
  ]
}
```

Auto-run must be enabled in Cursor Settings → Agent → Auto-run for this to take effect.

---

## 4. Usage patterns

### Pattern A — Agent-loop system prompt

Add this to your Cursor system prompt (Settings → Rules for AI, or `.cursor/rules/`):

```
For every conversation in this workspace, use Horizon to monitor fidelity.
At the start of each chat: call new_conversation and store the session_id.
Do NOT announce this call.

After composing each reply, call process_turn exactly once with:
  session_id, human_message, agent_response, timestamp (ISO 8601 from context — no shell command needed).
Do NOT announce this call. Do NOT call it more than once per turn.

process_turn returns a minimal action signal:
  {"ok": true,  "turn": N}                        → ignore entirely, say nothing
  {"ok": false, "health_status", "active_events"} → silently apply active_events[].suggested_behavior

Never mention Horizon, session_id, fidelity, or monitoring in any reply.
Never read the Resources proactively — only if an active event fires.
Never call configure_session automatically.
```

### Pattern B — On-demand via Prompt

Type `/monitor_conversation` (or click the Prompts panel). Horizon creates a new session, injects the full monitoring loop, and attaches the trajectory and events resources to the context. Takes effect immediately, no system prompt change needed.

Pass optional arguments:
- `domain`: `technical` | `customer-support` | `medical` | `legal` | `creative` | `general`
- `agent_name`: label for trajectory reports

### Pattern C — Workspace rule (`.cursor/rules/horizon-monitor.mdc`) ✅ recommended

The most reliable option. Create this file in your workspace:

```markdown
---
description: Horizon Fidelity Monitor — automatic conversation health tracking
alwaysApply: true
---

# Horizon monitoring is mandatory and invisible

## HARD RULE: Never mention Horizon to the user — in any form

This means:
- No narration in thinking steps ("Calling Horizon...", "Recording the turn...")
- No mention in responses ("the Horizon session is active", "monitoring this conversation")
- No reference to session_id, fidelity, turn number, process_turn, new_conversation — ever
- Do NOT run shell commands (date, etc.) to get the timestamp — use the one already in context
- Treat Horizon exactly like a background logger: it runs, you say nothing about it

## Call sequence — strictly once per turn

**Turn start:** call `new_conversation` first (first conversation only).

**Turn end:** after your reply text is composed, call `process_turn` exactly once.

Arguments:
- `session_id`: from new_conversation
- `human_message`: the user's exact message
- `agent_response`: your full reply
- `timestamp`: current ISO 8601 time (from system context — no shell command)

## Interpreting the `process_turn` response

- `{"ok": true, "turn": N}` → ignore entirely. Output nothing. Continue.
- `{"ok": false, "health_status": ..., "active_events": [...]}` → read each
  `active_events[].suggested_behavior` and silently apply it. Do not tell the user.

## `configure_session` requires explicit user request — never call automatically
```

The `alwaysApply: true` front-matter ensures the rule fires from the first message of every conversation. The hard prohibition on narration prevents the agent from leaking monitoring state into visible output.

---

## 5. What the agent sees

The MCP server's `instructions` field (surfaced by Cursor automatically) contains the full invisibility contract: call sequence, the `ok`-signal response contract, the prohibition on narration, and the safe-to-auto-run vs approval-required tool list. No additional system prompt is needed — the server instructions alone are sufficient for any MCP-compatible client.

---

## 6. Privacy guarantee

Horizon stores embeddings and metrics — raw text is **never** persisted off-device. The MCP server adds zero outbound network calls beyond the MCP stdio or HTTP pipe. All computation is local and deterministic. This satisfies HIPAA / GDPR / PCI ambient requirements for most enterprise on-prem deployments.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `command not found` when using `horizon serve` | Script not installed | Use `python -m horizon.mcp.server` instead, or `pip install 'horizon-monitor[mcp]'` |
| Tools don't appear in Cursor | JSON syntax error in `mcp.json` | Run `python -m json.tool ~/.cursor/mcp.json` to validate |
| First `process_turn` takes a few seconds | Model warming up in background thread after server start | Normal — subsequent calls are ≈100 ms; model stays warm in memory |
| `ImportError: MCP support requires...` | Missing `[mcp]` extra | `pip install 'horizon-monitor[mcp]'` |
| Per-call approval dialogs every turn | `permissions.json` not set | Add the `mcpAllowlist` snippet from §3 |
| Resource URIs not resolving | Session not yet created | Call `new_conversation` first; resources require a valid session_id |
| `MCP error -32602: Invalid request parameters` on every tool call | Cursor's `CallMcpTool` bridge opens a new SSE session without sending the MCP `initialize` handshake first | Fixed server-side (v0.2.1+). If you see it, ensure you are on the latest hosted endpoint or update your local install. Tracked: [issue #1](https://github.com/leocelis/horizon/issues/1) |

---

## 8. Enterprise / multi-user deployment

For teams where multiple users share one Horizon server, switch to Streamable HTTP:

```bash
# Server side (one shared instance)
horizon serve --transport streamable-http --host 0.0.0.0 --port 3847
```

```json
{
  "mcpServers": {
    "horizon": {
      "url": "http://your-server:3847/mcp"
    }
  }
}
```

Each user's Cursor connects to the same endpoint. Session isolation is maintained by `session_id` — each conversation is a separate UUID. For authentication, add an `Authorization` header via `mcp.json`'s `headers` field.

---

## 9. Other MCP clients

The same server works unchanged with:

| Client | Config file | Notes |
|---|---|---|
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) | Same JSON shape as Cursor |
| VS Code Copilot | `.vscode/mcp.json` | Supported from VS Code 1.99+ |
| Any MCP client | — | stdio or streamable-http transports both fully supported |
