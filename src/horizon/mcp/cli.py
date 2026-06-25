"""CLI entry point for the Horizon MCP server.

Usage::

    # stdio transport (for Cursor / Claude Desktop) — default
    python -m horizon.mcp.server

    # Or via the installed script:
    horizon serve

    # SSE transport (legacy web / local SSE clients)
    horizon serve --transport sse --port 3847

    # Streamable HTTP transport (production / multi-user / enterprise)
    horizon serve --transport streamable-http --port 3847
"""

from __future__ import annotations

import sys


def main() -> None:
    """Main entry point registered as 'horizon' script in pyproject.toml."""
    try:
        import click
    except ImportError:
        print(
            "ERROR: click is required. Install with: pip install 'horizon-monitor[mcp]'",
            file=sys.stderr,
        )
        sys.exit(1)

    @click.group()
    def cli() -> None:
        """Horizon Fidelity Monitor CLI."""

    @cli.command()
    @click.option(
        "--transport",
        default="stdio",
        type=click.Choice(["stdio", "sse", "streamable-http"]),
        help=(
            "MCP transport:\n"
            "  stdio           — default; Cursor / Claude Desktop / local clients.\n"
            "  sse             — legacy SSE (still widely supported).\n"
            "  streamable-http — production / multi-user / enterprise.\n"
        ),
    )
    @click.option("--port", default=3847, help="Port for SSE / streamable-http transport.")
    @click.option("--host", default="127.0.0.1", help="Host for SSE / streamable-http transport.")
    @click.option("--preload", is_flag=True, default=True, help="Preload embedding model on startup.")
    def serve(transport: str, port: int, host: str, preload: bool) -> None:
        """Start the Horizon MCP server."""
        try:
            from horizon.mcp.server import create_app

            app = create_app()

            if preload:
                # Warm the embedding model before the first client call so
                # process_turn latency is predictable from turn 1 onwards.
                try:
                    from horizon.mcp.server import _get_monitor
                    _get_monitor().preload_models()
                except Exception:
                    pass  # non-fatal; model loads on first call instead

            if transport == "stdio":
                app.run(transport="stdio")
            elif transport == "sse":
                # FastMCP SSE: host/port come from the FastMCP constructor;
                # override them here by mutating the app settings.
                app._host = host
                app._port = port
                app.run(transport="sse")
            else:  # streamable-http
                app._host = host
                app._port = port
                app.run(transport="streamable-http")

        except ImportError as exc:
            click.echo(
                f"MCP serve requires: pip install 'horizon-monitor[mcp]'\n{exc}",
                err=True,
            )
            sys.exit(1)

    @cli.command()
    def version() -> None:
        """Print Horizon version."""
        from horizon import __version__

        click.echo(f"horizon-monitor {__version__}")

    cli()


if __name__ == "__main__":
    main()
