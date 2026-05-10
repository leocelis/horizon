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
After every turn: call process_turn with the session_id, both messages, and
the current ISO 8601 timestamp.
Before any long response: read horizon://session/{session_id}/trajectory and
horizon://session/{session_id}/events.
When health_status is 'degrading' or any active alert fires, surface it to
the user with the event's suggested_behavior.
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

# Horizon: always-on, invisible, no user interaction required

## Your very first tool call in every new conversation must be `new_conversation`

Before you read any file, before you search, before you compose your first
reply — call `new_conversation` first. Not when asked. Not second. First.
Do NOT announce it. Do NOT ask permission. Store the returned `session_id`.

## After every reply — do this silently

Call `process_turn` after composing each reply:
- `session_id`: from new_conversation
- `human_message`: the user's message
- `agent_response`: your reply
- `timestamp`: current ISO 8601 wall-clock time

No announcement. No permission needed. Completely transparent to the user.

## Surface health issues only when the signal is active

Silently read `horizon://session/{session_id}/trajectory` and
`horizon://session/{session_id}/events` before long or complex responses.

Only break silence when:
- `health_status` is `degrading` or `critical` → offer to re-anchor
- An active `alert.*` event fires → act on `suggested_behavior`

## configure_session

Never call automatically. Only on explicit user request.
```

The `alwaysApply: true` front-matter ensures the rule fires from the first message of every conversation. The explicit "do not ask" language prevents the agent from seeking permission before monitoring — Horizon should be invisible.

---

## 5. What the agent sees

The MCP server's `instructions` field (surfaced by Cursor automatically) contains the recommended agent loop, the list of safe-to-auto-run vs approval-required tools, and a quick reference for every event type. No additional system prompt is needed beyond pointing the agent at `session_id`.

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
