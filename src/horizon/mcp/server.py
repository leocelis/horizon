"""MCP server for Horizon — exposes core API as Model Context Protocol tools.

Requires: pip install horizon-monitor[mcp]

Cursor integration (.cursor/mcp.json)::

    {
      "mcpServers": {
        "horizon": {
          "command": "horizon",
          "args": ["serve"],
          "env": {}
        }
      }
    }

Claude Desktop (claude_desktop_config.json)::

    {
      "mcpServers": {
        "horizon": {
          "command": "horizon",
          "args": ["serve"],
          "env": {}
        }
      }
    }
"""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from horizon import Config, FidelityMonitor
from horizon.monitor import SessionNotFoundError


def create_app(config: Config | None = None) -> Any:
    """Build and return the MCP Server application.

    Returns the server object. Transport (stdio/SSE) is applied in cli.py.
    """
    try:
        import mcp.types as types
        from mcp.server import Server
    except ImportError as exc:
        raise ImportError(
            "MCP support requires: pip install horizon-monitor[mcp]"
        ) from exc

    monitor = FidelityMonitor(config)
    app = Server("horizon-fidelity-monitor")

    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name="new_conversation",
                description=(
                    "Initialise a new Horizon conversation session. "
                    "Returns a session_id UUID. Must be called before process_turn."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "metadata": {
                            "type": "object",
                            "description": "Optional: domain, user_id, agent_name, config overrides",
                        }
                    },
                },
            ),
            types.Tool(
                name="process_turn",
                description=(
                    "Process a single conversation turn. Returns fidelity score, "
                    "all 4D spacetime signals, and fired events."
                ),
                inputSchema={
                    "type": "object",
                    "required": ["session_id", "human_message", "agent_response"],
                    "properties": {
                        "session_id": {"type": "string"},
                        "human_message": {"type": "string"},
                        "agent_response": {"type": "string"},
                        "timestamp": {
                            "type": "string",
                            "description": "ISO 8601 wall-clock time of the human message",
                        },
                        "client_context": {
                            "type": "object",
                            "description": "device_type, timezone, location_class, ip_address",
                        },
                    },
                },
            ),
            types.Tool(
                name="get_trajectory",
                description="Return the full per-session fidelity trajectory and T* estimate.",
                inputSchema={
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {"session_id": {"type": "string"}},
                },
            ),
            types.Tool(
                name="get_events",
                description="Return all events fired during the session.",
                inputSchema={
                    "type": "object",
                    "required": ["session_id"],
                    "properties": {
                        "session_id": {"type": "string"},
                        "active_only": {
                            "type": "boolean",
                            "description": "If true, return only active-mode events",
                        },
                    },
                },
            ),
            types.Tool(
                name="configure",
                description="Override thresholds and event modes for a session or globally.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "clarification_threshold": {"type": "number"},
                        "convergence_window": {"type": "integer"},
                        "event_modes": {"type": "object"},
                        "domain": {"type": "string"},
                        "chronotype_offset": {"type": "number"},
                        "context_half_life_hours": {"type": "number"},
                    },
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        try:
            result = _dispatch(monitor, name, arguments)
            return [types.TextContent(type="text", text=json.dumps(result, default=str))]
        except SessionNotFoundError as exc:
            return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]
        except Exception as exc:
            return [types.TextContent(type="text", text=json.dumps({"error": str(exc)}))]

    return app


def _dispatch(monitor: FidelityMonitor, name: str, args: dict) -> dict:
    """Route MCP tool calls to FidelityMonitor methods."""
    if name == "new_conversation":
        sid = monitor.new_conversation(metadata=args.get("metadata"))
        return {"session_id": sid}

    if name == "process_turn":
        result = monitor.process_turn(
            session_id=args["session_id"],
            human_message=args["human_message"],
            agent_response=args["agent_response"],
            timestamp=args.get("timestamp"),
            client_context=args.get("client_context"),
        )
        return dataclasses.asdict(result)

    if name == "get_trajectory":
        traj = monitor.get_trajectory(args["session_id"])
        return dataclasses.asdict(traj)

    if name == "get_events":
        events = monitor.get_events(
            args["session_id"],
            active_only=args.get("active_only", False),
        )
        return {"events": [dataclasses.asdict(e) for e in events]}

    if name == "configure":
        kwargs = {k: v for k, v in args.items() if k != "session_id"}
        result = monitor.configure(
            session_id=args.get("session_id"),
            **kwargs,
        )
        return dataclasses.asdict(result)

    raise ValueError(f"Unknown tool: {name}")
