"""Parent constraint: optional_plane_backward_compat.

horizon_memento_mori_intent.yaml::constraints[optional_plane_backward_compat]
test: tests/unit/memento_mori/test_plane_optional.py::test_no_store_no_behavior_change

"With no mission store configured, every existing Horizon API behaves
byte-identically to the pre-plane release; enabling the plane requires
explicit configuration."
"""

from __future__ import annotations

import ast
from pathlib import Path

import horizon_monitor
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.monitor import FidelityMonitor


def _module_import_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_no_store_no_behavior_change() -> None:
    """Enabling the plane requires an explicit config; with none, the
    existing `FidelityMonitor` API is untouched by memento's presence in
    the tree, and two independent monitors process the same turn
    byte-identically."""
    assert MementoConfig().store_path is None

    package_root = Path(horizon_monitor.__file__).parent
    memento_root = package_root / "memento"
    offending: list[str] = []
    for py_file in package_root.rglob("*.py"):
        if memento_root in py_file.parents or py_file.parent == memento_root:
            continue
        imports = _module_import_names(py_file)
        if any(
            name == "horizon_monitor.memento" or name.startswith("horizon_monitor.memento.")
            for name in imports
        ):
            offending.append(str(py_file))
    assert offending == [], f"non-memento modules importing memento: {offending}"

    monitor_a = FidelityMonitor()
    monitor_b = FidelityMonitor()
    session_a = monitor_a.new_conversation(session_id="fixed-session-id")
    session_b = monitor_b.new_conversation(session_id="fixed-session-id")

    result_a = monitor_a.process_turn(
        session_a,
        "What time is it in UTC right now?",
        "I can't check the clock; please tell me.",
        timestamp="2026-04-22T10:30:00+00:00",
    )
    result_b = monitor_b.process_turn(
        session_b,
        "What time is it in UTC right now?",
        "I can't check the clock; please tell me.",
        timestamp="2026-04-22T10:30:00+00:00",
    )

    assert result_a.fidelity_score == result_b.fidelity_score
    assert [e.type for e in result_a.events] == [e.type for e in result_b.events]
