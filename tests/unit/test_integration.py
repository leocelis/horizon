"""Framework-agnostic guarantees.

Verifies that the core `horizon` package imports and runs with zero transitive
framework dependencies (no langchain, openai, llama_index required to call
process_turn).

Referenced by horizon_intent.yaml::constraints[framework_agnostic].
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from typing import Iterable

import pytest

from horizon import FidelityMonitor


FRAMEWORKS_THAT_MUST_NOT_BE_REQUIRED: tuple[str, ...] = (
    "langchain",
    "langchain_core",
    "langchain_community",
    "llama_index",
    "llamaindex",
)


def _imported_top_level_modules() -> set[str]:
    """Top-level modules currently loaded into ``sys.modules``."""
    return {name.split(".", 1)[0] for name in sys.modules}


def test_zero_framework_imports_in_core() -> None:
    """Constraint: framework_agnostic.

    Importing `horizon` and running the core pipeline must not pull in
    LangChain / LlamaIndex. OpenAI and Anthropic SDKs are *optional* and may
    be present in the dev venv; the check focuses on non-optional frameworks.
    """
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    monitor.process_turn(sid, "hello", "world")

    loaded = _imported_top_level_modules()
    for mod in FRAMEWORKS_THAT_MUST_NOT_BE_REQUIRED:
        assert mod not in loaded, (
            f"Core pipeline imported forbidden framework '{mod}'. "
            "Horizon must not require LangChain/LlamaIndex."
        )


def test_framework_agnostic_zero_imports() -> None:
    """Clean subprocess check — import horizon and exercise core pipeline
    in a fresh interpreter, then verify no optional frameworks leaked in.

    Alias of horizon_intent.yaml::test_cases.framework_agnostic_zero_imports.
    """
    script = (
        "import sys\n"
        "from horizon import FidelityMonitor\n"
        "m = FidelityMonitor()\n"
        "sid = m.new_conversation()\n"
        "r = m.process_turn(sid, 'hi', 'hello')\n"
        "assert 0.0 <= r.fidelity_score <= 1.0, r.fidelity_score\n"
        "bad = {'langchain', 'llama_index', 'langgraph'}\n"
        "loaded = {n.split('.', 1)[0] for n in sys.modules}\n"
        "assert not (bad & loaded), f'leaked: {bad & loaded}'\n"
        "print('ok')\n"
    )

    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, (
        f"Subprocess failed (exit {proc.returncode}):\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    assert "ok" in proc.stdout


def test_process_turn_accepts_plain_strings_returns_plain_object() -> None:
    """process_turn() accepts plain `str`s and returns a plain dataclass.

    The public API surface does not require framework-specific types.
    """
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    result = monitor.process_turn(sid, "plain string in", "plain string out")

    assert hasattr(result, "fidelity_score")
    assert hasattr(result, "events")
    assert isinstance(result.events, list)
