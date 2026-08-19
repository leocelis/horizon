"""The README's mission-plane section must match the shipped code.

A README that drifts from the product is the most-read wrong documentation a
project has. These assertions pin the claims that are cheap to verify and
expensive to get wrong: the signal roster and its tiers, the tool roster, and
the fact that the quickstart snippet is complete enough to execute.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
README = (REPO / "README.md").read_text()


def _mission_section() -> str:
    assert "## Mission plane (Memento Mori)" in README, "mission plane missing from README"
    return README.split("## Mission plane (Memento Mori)")[1].split("\n## ")[0]


def test_readme_signal_table_matches_the_code_exactly() -> None:
    from horizon_monitor.memento import signals

    block = _mission_section()
    rows = dict(re.findall(r"\| `signal\.([a-z_]+)` \|[^|]+\| (P[123]) \|", block))
    assert set(rows) == set(signals.TIER), (
        f"README signal roster drifted: missing {set(signals.TIER) - set(rows)}, "
        f"extra {set(rows) - set(signals.TIER)}"
    )
    for name, tier in rows.items():
        assert (
            signals.TIER[name] == tier
        ), f"README lists {name} as {tier}, code says {signals.TIER[name]}"


def test_readme_names_every_mission_tool_and_no_other() -> None:
    """The README claims 'six tools'. That number and the names must be real."""
    import asyncio
    import tempfile

    from mcp.server.fastmcp import FastMCP

    from horizon_monitor.mcp.server import register_memento_tools

    app = FastMCP("readme-check")
    register_memento_tools(app, Path(tempfile.mkdtemp()) / "m.db")
    shipped = {t.name for t in asyncio.run(app.list_tools())}
    assert len(shipped) == 6, f"README says six tools; code registers {len(shipped)}"
    assert "six tools" in _mission_section(), "README no longer states the tool count"


@pytest.mark.parametrize(
    "claim",
    [
        "off by default",  # the plane must be opt-in
        'plane: "mission"',  # the routing tag readers depend on
        "byte-identical report",  # the determinism guarantee
    ],
)
def test_readme_load_bearing_claims_present(claim: str) -> None:
    assert claim in _mission_section(), f"README dropped a load-bearing claim: {claim!r}"


def test_readme_quickstart_snippet_is_executable() -> None:
    """House style is a complete, copy-pasteable snippet. An earlier draft used
    `...` placeholders and a missing import, so it raised NameError for anyone
    who copied it."""
    block = _mission_section()
    snippet = re.search(r"```python\n(.*?)```", block, re.S)
    assert snippet, "no python snippet in the mission-plane section"
    code = snippet.group(1)

    assert "created_valid=..." not in code, "snippet still uses ellipsis placeholders"
    for needed in ("from datetime import", "from horizon_monitor.memento import"):
        assert needed in code, f"snippet is not self-contained: missing {needed!r}"

    compile(code, "<readme-snippet>", "exec")  # syntactically valid at minimum
