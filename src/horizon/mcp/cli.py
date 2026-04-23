"""CLI entry point for the Horizon MCP server.

Usage::

    # stdio transport (for Cursor/Claude Desktop)
    horizon serve

    # SSE transport (for web integrations)
    horizon serve --transport sse --port 3847
"""

from __future__ import annotations

import sys


def main() -> None:
    """Main entry point registered as 'horizon' script in pyproject.toml."""
    try:
        import click
    except ImportError:
        print(
            "ERROR: click is required. Install with: pip install horizon-monitor[mcp]",
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
        type=click.Choice(["stdio", "sse"]),
        help="MCP transport: stdio (Cursor/Claude) or sse (web)",
    )
    @click.option("--port", default=3847, help="Port for SSE transport")
    @click.option("--host", default="127.0.0.1", help="Host for SSE transport")
    def serve(transport: str, port: int, host: str) -> None:
        """Start the Horizon MCP server."""
        try:
            import asyncio

            from mcp.server.stdio import stdio_server

            from horizon.mcp.server import create_app

            app = create_app()

            if transport == "stdio":

                async def _run() -> None:
                    async with stdio_server() as (read_stream, write_stream):
                        await app.run(
                            read_stream,
                            write_stream,
                            app.create_initialization_options(),
                        )

                asyncio.run(_run())
            else:
                try:
                    import uvicorn
                    from mcp.server.sse import SseServerTransport
                    from starlette.applications import Starlette
                    from starlette.routing import Mount, Route

                    sse_transport = SseServerTransport("/messages/")

                    async def handle_sse(request):  # noqa: ANN001
                        async with sse_transport.connect_sse(
                            request.scope, request.receive, request._send
                        ) as streams:
                            await app.run(
                                streams[0],
                                streams[1],
                                app.create_initialization_options(),
                            )

                    starlette_app = Starlette(
                        routes=[
                            Route("/sse", endpoint=handle_sse),
                            Mount("/messages/", app=sse_transport.handle_post_message),
                        ]
                    )
                    uvicorn.run(starlette_app, host=host, port=port)
                except ImportError as exc:
                    click.echo(f"SSE transport requires uvicorn and starlette: {exc}", err=True)
                    sys.exit(1)

        except ImportError as exc:
            click.echo(f"MCP serve requires: pip install horizon-monitor[mcp]\n{exc}", err=True)
            sys.exit(1)

    @cli.command()
    def version() -> None:
        """Print Horizon version."""
        from horizon import __version__

        click.echo(f"horizon-monitor {__version__}")

    cli()


if __name__ == "__main__":
    main()
