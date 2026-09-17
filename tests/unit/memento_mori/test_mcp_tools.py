"""M — MCP surface & agent contract (memento_signals_intent.yaml segment).

Per docs/spec/MEMENTO_MORI_TEST_PLAN.md §M and
docs/integrations/MEMENTO_MORI_AGENTS.md (the normative agent-rules doc).
These cases join the G-cases in the signals segment's verification.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import pytest
from mcp.server.fastmcp import FastMCP

from horizon_monitor.mcp.server import (
    _LOUD_CONTRACT_LINE,
    _serialize_memento_error,
    register_memento_tools,
)
from horizon_monitor.memento.errors import (
    MementoError,
    PersonRankingRefusedError,
    RootlessItemError,
    UndatedDeferralError,
)

_MISSION_TOOL_NAMES = frozenset(
    {
        "clock_register",
        "clock_progress",
        "clock_status",
        "clock_propose",
        "clock_ack",
        "clock_close",
        "associate_mission",
    }
)

_AGENTS_DOC = (
    Path(__file__).resolve().parents[3] / "docs" / "integrations" / "MEMENTO_MORI_AGENTS.md"
)


def _list_tool_names(app: FastMCP) -> set[str]:
    tools = asyncio.run(app.list_tools())
    return {t.name for t in tools}


# ── M-1 [PROPERTY] — Tool discovery gating ──────────────────────────────────


def test_m1_seven_mission_tools_register_when_store_configured(tmp_path) -> None:
    app = FastMCP("test-configured")
    result = register_memento_tools(app, tmp_path / "store.db")
    assert result is not None

    names = _list_tool_names(app)
    assert _MISSION_TOOL_NAMES <= names


def test_m1_mission_tools_do_not_appear_at_all_with_store_path_none() -> None:
    """With store_path=None, register_memento_tools registers NOTHING — the
    six tools are absent from tool discovery entirely, not merely disabled
    when called (memento_signals_intent.yaml::strict_additivity's
    "code path not entered" mechanism, same as G-10)."""
    app = FastMCP("test-unconfigured")
    result = register_memento_tools(app, None)
    assert result is None

    names = _list_tool_names(app)
    assert names.isdisjoint(_MISSION_TOOL_NAMES)


# ── M-2 [GOLDEN] — Typed error serialization ────────────────────────────────


def test_m2_typed_error_serialization_has_no_stack_trace_and_no_coercion() -> None:
    """UndatedDeferralError over MCP => {error_type, rule, fix}; no stack
    trace, no silent coercion. Hand-checked golden values."""
    exc = UndatedDeferralError("park it")
    serialized = _serialize_memento_error(exc)

    assert serialized == {
        "error_type": "UndatedDeferralError",
        "rule": "intent.non_goals — 'an undated deferral is invalid, not incomplete'.",
        "fix": "kind=deferral requires revisit_date; none was supplied for 'park it'. "
        "No configuration flag can bypass this.",
    }
    # No stack trace anywhere in the serialized payload.
    assert "Traceback" not in str(serialized)
    assert 'File "' not in str(serialized)


def test_m2_second_golden_case_covers_a_refusal_error() -> None:
    """A second hand-checked case from a different exception family
    (RefusalError, not SchemaError) — proves the shape generalizes rather
    than being hand-tuned to one message."""
    exc = PersonRankingRefusedError()
    serialized = _serialize_memento_error(exc)

    assert serialized == {
        "error_type": "PersonRankingRefusedError",
        "rule": "intent non_goals — 'people analytics ... agents must not rank people in suggested_behavior'.",
        "fix": "the engine never ranks, scores, or orders identifiable people.",
    }


@pytest.mark.parametrize(
    "exc",
    [UndatedDeferralError(), RootlessItemError(), PersonRankingRefusedError()],
)
def test_m2_every_serialized_error_has_all_three_keys_and_is_a_memento_error(
    exc: MementoError,
) -> None:
    serialized = _serialize_memento_error(exc)
    assert set(serialized) == {"error_type", "rule", "fix"}
    assert all(isinstance(v, str) and v for v in serialized.values())
    assert isinstance(exc, MementoError)


def test_m2_clock_register_returns_typed_error_not_a_raised_exception(tmp_path) -> None:
    """End-to-end through the actual tool: registering an undated deferral
    under a mission returns the typed error shape as the tool's return
    value — it does not propagate as a raw exception across the MCP
    boundary."""
    app = FastMCP("test-m2-e2e")
    register_memento_tools(app, tmp_path / "store.db")

    async def _run() -> dict:
        root = await app.call_tool(
            "clock_register",
            {
                "item": {
                    "kind": "horizon",
                    "title": "root",
                    "created_valid": "2026-01-01T00:00:00+00:00",
                    "end_date": "2030-01-01",
                }
            },
        )
        root_id = json.loads(root[0].text)["item_id"]
        mission = await app.call_tool(
            "clock_register",
            {
                "item": {
                    "kind": "mission",
                    "title": "M1",
                    "parent_id": root_id,
                    "created_valid": "2026-06-01T00:00:00+00:00",
                }
            },
        )
        mission_id = json.loads(mission[0].text)["item_id"]
        rejected = await app.call_tool(
            "clock_register",
            {
                "item": {
                    "kind": "deferral",
                    "title": "park it",
                    "parent_id": mission_id,
                    "created_valid": "2026-07-01T00:00:00+00:00",
                }
            },
        )
        return json.loads(rejected[0].text)

    d = asyncio.run(_run())
    assert d["error"]["error_type"] == "UndatedDeferralError"
    assert "revisit_date" in d["error"]["fix"]


# ── M-5 [HUMAN] — Loud-contract text in tool descriptions ──────────────────


def test_m5_every_mission_tool_description_carries_the_loud_contract_line(tmp_path) -> None:
    """Each mission tool's MCP description embeds the loud-contract line
    from docs/integrations/MEMENTO_MORI_AGENTS.md §1-2 ("surface this;
    never absorb silently"), so a schema-only client still inherits the
    behavioral contract."""
    app = FastMCP("test-m5")
    register_memento_tools(app, tmp_path / "store.db")
    tools = {t.name: t for t in asyncio.run(app.list_tools())}

    for name in _MISSION_TOOL_NAMES:
        assert name in tools, f"{name} did not register"
        description = tools[name].description or ""
        assert (
            "surface" in description.lower() and "absorb" in description.lower()
        ), f"{name} description missing the loud-contract line: {description!r}"
    assert "surface this" in _LOUD_CONTRACT_LINE.lower() or "surface" in _LOUD_CONTRACT_LINE.lower()


def test_m5_conversation_tool_descriptions_do_not_carry_the_loud_contract_line() -> None:
    """The loud-contract line is specific to the mission plane; the
    pre-existing conversation tools (invisible-by-design, see _INSTRUCTIONS)
    must not pick it up as an accidental side effect of this change."""
    from horizon_monitor.mcp.server import mcp as real_app

    names = _list_tool_names(real_app)
    conversation_tools = names & {"new_conversation", "process_turn", "configure_session"}
    assert conversation_tools  # sanity: the always-on tools are there
    tools = {t.name: t for t in asyncio.run(real_app.list_tools())}
    for name in conversation_tools:
        description = tools[name].description or ""
        assert "surface this" not in description


# ── M-6 [HUMAN, made executable] — Instructions doc / tool-surface sync ────


def _tool_names_in_agents_doc_section_3() -> set[str]:
    """Parse the fenced ```text block under '## 3. Canonical agent-rules
    block' in docs/integrations/MEMENTO_MORI_AGENTS.md and return every
    tool-shaped identifier (clock_* / associate_*) it names."""
    text = _AGENTS_DOC.read_text(encoding="utf-8")
    match = re.search(r"## 3\. Canonical agent-rules block.*?```text\n(.*?)```", text, re.DOTALL)
    assert match is not None, "docs/integrations/MEMENTO_MORI_AGENTS.md §3 code block not found"
    block = match.group(1)
    return set(re.findall(r"\b(clock_[a-z_]+|associate_[a-z_]+)\b", block))


def test_m6_agents_doc_section_3_names_every_shipped_tool_and_no_other(tmp_path) -> None:
    """Doc-code consistency check (test plan M-6): the §3 rules block in
    docs/integrations/MEMENTO_MORI_AGENTS.md names every shipped mission
    tool, and nothing it names is an unshipped tool."""
    app = FastMCP("test-m6")
    register_memento_tools(app, tmp_path / "store.db")
    shipped_mission_tools = _list_tool_names(app) & _MISSION_TOOL_NAMES

    named_in_doc = _tool_names_in_agents_doc_section_3()

    missing_from_doc = shipped_mission_tools - named_in_doc
    unshipped_but_named = named_in_doc - shipped_mission_tools

    assert missing_from_doc == set(), f"shipped tool(s) not named in §3: {missing_from_doc}"
    assert (
        unshipped_but_named == set()
    ), f"§3 names tool(s) that do not exist: {unshipped_but_named}"
    assert named_in_doc == _MISSION_TOOL_NAMES == shipped_mission_tools


# ── M-7 — clock_close retires a subtree without deleting it ────────────────


def test_m7_clock_close_cascades_and_keeps_rows_visible_on_clock_status(tmp_path) -> None:
    """Closing a mission retires its deadline with it (the deadline would
    otherwise keep firing after the mission was replaced — the 2026-09-17
    drift: a superseded $20K ITV mission and a stale $2K LoreMaster mission
    kept their deadlines live). Rows stay on clock_status carrying status,
    and the horizon root refuses to close."""
    app = FastMCP("test-m7")
    register_memento_tools(app, tmp_path / "store.db")

    async def _run() -> dict:
        root = await app.call_tool(
            "clock_register",
            {"item": {"kind": "horizon", "title": "root",
                      "created_valid": "2026-01-01T00:00:00+00:00", "end_date": "2030-01-01"}},
        )
        root_id = json.loads(root[0].text)["item_id"]
        old = await app.call_tool(
            "clock_register",
            {"item": {"kind": "mission", "title": "old $20K", "parent_id": root_id,
                      "created_valid": "2026-06-01T00:00:00+00:00"}},
        )
        old_id = json.loads(old[0].text)["item_id"]
        dl = await app.call_tool(
            "clock_register",
            {"item": {"kind": "deadline", "title": "old deadline", "parent_id": old_id,
                      "created_valid": "2026-06-01T00:00:00+00:00",
                      "deadline_date": "2026-12-31", "deadline_kind": "external"}},
        )
        dl_id = json.loads(dl[0].text)["item_id"]
        new = await app.call_tool(
            "clock_register",
            {"item": {"kind": "mission", "title": "new $10K", "parent_id": root_id,
                      "created_valid": "2026-09-17T00:00:00+00:00"}},
        )
        new_id = json.loads(new[0].text)["item_id"]

        bad_root = json.loads((await app.call_tool("clock_close", {"item_id": root_id}))[0].text)
        bad_sup = json.loads((await app.call_tool(
            "clock_close", {"item_id": old_id, "status": "superseded"}))[0].text)
        ok = json.loads((await app.call_tool(
            "clock_close", {"item_id": old_id, "status": "superseded", "superseded_by": new_id}))[0].text)
        status = json.loads((await app.call_tool(
            "clock_status", {"timestamp": "2026-12-20T00:00:00+00:00"}))[0].text)
        return {"bad_root": bad_root, "bad_sup": bad_sup, "ok": ok, "status": status,
                "old_id": old_id, "dl_id": dl_id, "new_id": new_id}

    d = asyncio.run(_run())
    assert "error" in d["bad_root"] and "root" in d["bad_root"]["error"]["rule"]
    assert "error" in d["bad_sup"] and "superseded_by" in d["bad_sup"]["error"]["rule"]
    assert set(d["ok"]["closed"]) == {d["old_id"], d["dl_id"]}
    rows = {r["item_id"]: r for r in d["status"]["items"]}
    assert rows[d["old_id"]]["status"] == "superseded"
    assert rows[d["old_id"]]["superseded_by"] == d["new_id"]
    assert rows[d["dl_id"]]["status"] == "superseded"
    assert rows[d["new_id"]]["status"] == "open"
