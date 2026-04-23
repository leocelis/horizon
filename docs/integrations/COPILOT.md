# Horizon with GitHub Copilot

Copilot itself doesn't call external tools during chat, but you can still
monitor Copilot-driven conversations through three patterns.

## Pattern 1 — VS Code extension (wrap the Copilot Chat sidebar)

The simplest integration: write a thin VS Code extension that listens for
Copilot Chat turns via the `vscode.chat` API and forwards each `(prompt,
response)` pair to a locally running Horizon MCP server.

```ts
import * as vscode from "vscode";

// Pseudocode — the exact Copilot Chat API surface is evolving.
vscode.chat.onDidReceiveResponse(async (turn) => {
  const { prompt, response, timestamp } = turn;
  await fetch("http://localhost:3847/mcp/call_tool", {
    method: "POST",
    body: JSON.stringify({
      name: "process_turn",
      arguments: {
        session_id: getOrCreateSessionId(),
        human_message: prompt,
        agent_response: response,
        timestamp,
      },
    }),
  });
});
```

Start the MCP server with SSE transport so a local HTTP client can reach it:

```bash
horizon serve --transport sse --port 3847
```

## Pattern 2 — Post-hoc analysis of Copilot logs

Copilot writes transcripts to VS Code's telemetry output. Collect them (with
user consent) and replay through Horizon:

```python
from horizon import FidelityMonitor

monitor = FidelityMonitor()
sid = monitor.new_conversation(metadata={"source": "copilot_log"})

for turn in load_copilot_log("~/Library/Application Support/Code/copilot/"):
    monitor.process_turn(
        session_id=sid,
        human_message=turn["prompt"],
        agent_response=turn["response"],
        timestamp=turn["timestamp"],
    )

trajectory = monitor.get_trajectory(sid)
print(f"Fidelity dropped from {trajectory.peak_fidelity:.3f} to {trajectory.current_fidelity:.3f}")
```

This works because Horizon is framework-agnostic (see
`tests/e2e/test_raw_strings_e2e.py`) — any string pair becomes a valid turn.

## Pattern 3 — Proxy the Copilot model (enterprise deployments)

In enterprise Copilot deployments that route through an on-prem model gateway,
add Horizon as a middleware:

```
Copilot Chat ──▶ gateway ──▶ model
                  │
                  └──▶ Horizon (sync) ──▶ observability pipeline
```

Hook into the gateway's response handler (whatever implementation you use —
Cloudflare AI Gateway, LiteLLM proxy, Kong) and emit each turn to Horizon the
same way the LangChain callback does.

## Which pattern should I use?

| Need | Recommended pattern |
|---|---|
| Real-time signals during Copilot chats | Pattern 1 (VS Code extension) |
| Historical quality trend for already-logged chats | Pattern 2 (replay) |
| Cross-team aggregate observability in an org | Pattern 3 (gateway middleware) |
| Privacy-sensitive environments (no outbound traffic) | Any — Horizon's default config sends nothing outbound (see `tests/unit/test_privacy.py`). |

## Privacy note

Unlike Pattern 1 (live) and Pattern 3 (gateway), Pattern 2 (replay) needs
access to historical prompts. Strip PII before feeding logs to Horizon if
that's a concern — Horizon only needs the message text, not any user
identifier.
