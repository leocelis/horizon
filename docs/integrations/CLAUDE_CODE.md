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
claude mcp add horizon -- python -m horizon_monitor.mcp.server --scope user
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
| `command not found` when using `horizon serve` | Script not installed | Use `python -m horizon_monitor.mcp.server` instead, or `pip install 'horizon-monitor[mcp]'` |
| Tools don't appear | MCP server not registered or wrong scope | Run `claude mcp list` to check; re-add with correct `--scope` |
| Per-call approval dialogs every turn | No allowlist in `settings.json` | Add the `permissions.allow` snippet from §3 |
| `new_conversation` never fires | Instructions not in `~/.claude/CLAUDE.md` | Append the monitoring block from §2 |
| First `process_turn` takes a few seconds | Model warming up after server start | Normal — subsequent calls are ≈100 ms |
| Resource URIs not resolving | Session not yet created | Call `new_conversation` first; resources require a valid `session_id` |

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
