"""Unit coverage for the MCP server CLI (src/horizon_monitor/mcp/cli.py), using
Click's ``CliRunner``.

``horizon_monitor.mcp.cli.main()`` builds its ``click.Group`` locally (inside the
function body) and immediately invokes it against ``sys.argv`` — the group
object is never exposed at module level, so it can't be handed to
``CliRunner.invoke()`` directly. The ``cli_group`` fixture below captures
the ``click.Group`` by intercepting ``click.Command.main`` (the method
every click command's ``__call__`` delegates to, on installed click 8.4.x —
note ``click.BaseCommand`` is a deprecated alias no longer in ``Command``'s
MRO, so it must not be used for this patch) for exactly one call, then
restores it — giving true ``CliRunner`` coverage of the real argument
parser without ever needing to change ``src/``.

Every test here uses ``--help`` or an intentionally invalid option so the
``serve`` command's actual callback — which imports the MCP server and
calls ``app.run(...)``, blocking forever on stdio — never executes.
"""

from __future__ import annotations

import click
import pytest
from click.testing import CliRunner

from horizon_monitor.mcp import cli as cli_module


@pytest.fixture
def cli_group(monkeypatch):
    """Capture the click.Group that cli_module.main() constructs internally,
    without letting it actually run against real process argv."""
    captured: dict = {}
    orig_main = click.Command.main

    def _capture_and_abort(self, *args, **kwargs):
        captured["group"] = self
        raise SystemExit(0)

    monkeypatch.setattr(click.Command, "main", _capture_and_abort)
    try:
        with pytest.raises(SystemExit):
            cli_module.main()
    finally:
        # Restore immediately — CliRunner.invoke() below also calls
        # Command.main() and must hit the real implementation.
        monkeypatch.setattr(click.Command, "main", orig_main)

    assert "group" in captured, "failed to capture the click.Group from main()"
    return captured["group"]


# ── top-level --help ─────────────────────────────────────────────────────


def test_top_level_help_exits_zero_and_lists_commands(cli_group) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_group, ["--help"])

    assert result.exit_code == 0
    assert "Horizon Fidelity Monitor CLI" in result.output
    assert "serve" in result.output
    assert "version" in result.output


def test_unknown_command_exits_nonzero(cli_group) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_group, ["not-a-real-command"])

    assert result.exit_code != 0
    assert "No such command" in result.output


# ── `serve` argument parsing (never actually invoked) ───────────────────


def test_serve_help_documents_all_flags(cli_group) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_group, ["serve", "--help"])

    assert result.exit_code == 0
    assert "--transport" in result.output
    assert "stdio" in result.output
    assert "sse" in result.output
    assert "streamable-http" in result.output
    assert "--port" in result.output
    assert "--host" in result.output
    assert "--preload" in result.output


def test_serve_rejects_invalid_transport_choice(cli_group) -> None:
    runner = CliRunner()
    result = runner.invoke(cli_group, ["serve", "--transport", "carrier-pigeon"])

    assert result.exit_code != 0
    assert "carrier-pigeon" in result.output or "Invalid value" in result.output


def test_serve_transport_choices_are_exactly_the_three_documented(cli_group) -> None:
    """Confirms the --transport Choice set matches the docstring's three
    documented transports (stdio default, sse, streamable-http) — parsing
    only, via --help, never invoking serve's real callback."""
    serve_cmd = cli_group.commands["serve"]
    transport_param = next(p for p in serve_cmd.params if p.name == "transport")

    assert isinstance(transport_param.type, click.Choice)
    assert set(transport_param.type.choices) == {"stdio", "sse", "streamable-http"}
    assert transport_param.default == "stdio"


def test_serve_preload_flag_defaults_true(cli_group) -> None:
    """--preload is declared as a bare is_flag (not --preload/--no-preload),
    defaulting to True. Documented here as current parsing behavior."""
    serve_cmd = cli_group.commands["serve"]
    preload_param = next(p for p in serve_cmd.params if p.name == "preload")

    assert preload_param.is_flag is True
    assert preload_param.default is True


# ── `version` ─────────────────────────────────────────────────────────────


def test_version_command_prints_package_version(cli_group) -> None:
    from horizon_monitor import __version__

    runner = CliRunner()
    result = runner.invoke(cli_group, ["version"])

    assert result.exit_code == 0
    assert __version__ in result.output
    assert "horizon-monitor" in result.output
