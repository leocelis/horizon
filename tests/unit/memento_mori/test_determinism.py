"""Parent constraint: deterministic_no_llm_core.

horizon_memento_mori_intent.yaml::constraints[deterministic_no_llm_core]
test: tests/unit/memento_mori/test_determinism.py::test_reproducible_report

"The clock evaluation path makes zero LLM calls and zero network calls;
identical store contents plus identical evaluation timestamp produce a
byte-identical report; semantic judgments ... enter the store only as
caller-supplied metadata."

This is the parent-scoped assertion; test_engine_determinism.py carries the
same evidence at the sub-module (memento_engine_intent) level — both point
at the same code path, gated by different intent documents (parent vs
sub-module), so duplication here is intentional, not redundant coverage.
"""

from __future__ import annotations

import ast
import json
import socket
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


class _NoAmbientClockDatetime(datetime):
    """A datetime subclass whose .now()/.utcnow() raise — proves
    evaluate() never reads the ambient clock. Every other classmethod
    (fromisoformat, constructor, ...) is unchanged."""

    @classmethod
    def now(cls, tz=None):  # noqa: D102
        raise AssertionError("evaluate() must never call datetime.now()")

    @classmethod
    def utcnow(cls):  # noqa: D102
        raise AssertionError("evaluate() must never call datetime.utcnow()")


def _block(*args, **kwargs):
    raise AssertionError(f"unexpected outbound call: args={args} kwargs={kwargs}")


def test_reproducible_report(store, monkeypatch) -> None:
    build_smallco(store)
    config = MementoConfig()
    snapshot = store.snapshot()

    monkeypatch.setattr(engine, "datetime", _NoAmbientClockDatetime)

    with patch.object(socket.socket, "connect", side_effect=_block):
        with patch.object(subprocess, "Popen", side_effect=_block):
            report_1 = engine.evaluate(snapshot, EVAL_INSTANT, config)
            report_2 = engine.evaluate(snapshot, EVAL_INSTANT, config)

    serialized_1 = json.dumps(report_1.to_dict(), sort_keys=True, default=str)
    serialized_2 = json.dumps(report_2.to_dict(), sort_keys=True, default=str)
    assert serialized_1 == serialized_2
    assert report_1.zero_network is True
    assert report_1.zero_llm is True


def test_no_network_or_llm_client_import_on_the_evaluation_path() -> None:
    """Structural check: no module on the clock evaluation path (engine,
    money, paths, propose) imports an LLM or HTTP client library — the
    absence is load-time, not just runtime-mocked."""
    banned_modules = {"openai", "anthropic", "httpx", "requests", "aiohttp", "urllib3"}
    memento_dir = Path(engine.__file__).parent
    for name in ("engine.py", "money.py", "paths.py", "propose.py"):
        tree = ast.parse((memento_dir / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported = {alias.name.split(".")[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported = {node.module.split(".")[0]}
            else:
                continue
            assert not (
                imported & banned_modules
            ), f"{name} imports a network/LLM client: {imported}"


@pytest.mark.parametrize("field", ["stage", "wait_or_touch"])
def test_semantic_metadata_is_caller_supplied_never_derived(store, field: str) -> None:
    """Progress meaning and wait/touch classification are stored exactly as
    the caller wrote them; the engine never infers or overwrites either."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    entity_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=root_id,
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
    )
    kwargs = (
        {"stage": "vendor-queue"}
        if field == "stage"
        else {"stage": "vendor-queue", "wait_or_touch": "wait"}
    )
    store.record_event(
        item_id=entity_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 1, 2, tzinfo=UTC),
        **kwargs,
    )
    stored = store.get_events(entity_id)[0]
    if field == "stage":
        assert stored.stage == "vendor-queue"
    else:
        assert stored.wait_or_touch == "wait"
