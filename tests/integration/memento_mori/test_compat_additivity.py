"""G-10, G-11 [PROPERTY] — memento_signals_intent.yaml::strict_additivity.

"With store_path=None the memento code path is not entered and the full
existing test suite produces byte-identical results; with a store
configured, sessions not associated with a mission receive zero memento
events; association is an explicit registry call."

SCOPE NOTE for the reviewer: `process_turn` wiring (the actual call site that
would append this plane's due events to `active_events` for an associated
session) is tracked as a separate, not-yet-implemented integration step —
see memento_signals_intent.yaml goal text and the parent PR description.
Until that wiring exists, G-10's "full existing test suite" clause is
structurally guaranteed by the import graph below (nothing outside
`horizon_monitor.memento` imports it, so no other test can be affected by
memento's presence), and G-11 is verified at the registry unit itself. The
end-to-end "process_turn appends zero events for an unassociated session"
check is UNVERIFIED until that wiring lands, and is called out again in the
final report.
"""

from __future__ import annotations

import ast
from pathlib import Path

import horizon_monitor
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.signals import AssociationRegistry


def _module_import_names(py_file: Path) -> set[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_store_path_none_is_the_default_and_no_other_module_imports_memento() -> None:
    """G-10: `store_path=None` is MementoConfig's default (an integrator who
    never opts in gets exactly that), and no module outside
    `horizon_monitor.memento` itself references the memento package at all
    — so no other code path in the existing test suite can be entered by,
    or diverge because of, memento's presence in the tree."""
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

    assert (
        offending == []
    ), f"non-memento modules importing memento (breaks strict_additivity): {offending}"


def test_unassociated_session_has_zero_missions() -> None:
    """G-11: a session that never called `associate_mission` is not
    associated with anything — `is_associated` is False and `missions_for`
    is empty — which is the registry-level guarantee that feeds the
    process_turn integration's "zero events for unassociated sessions"
    behavior."""
    registry = AssociationRegistry()
    assert registry.is_associated("session-not-associated") is False
    assert registry.missions_for("session-not-associated") == ()


def test_association_is_explicit_and_survives_reregistration() -> None:
    """Association is a deliberate registry call, not inferred from any
    other state, and persists across repeated lookups for the same
    session_id (the registry survives "session re-registration" in the
    sense that calling associate() again does not clear a prior
    association)."""
    registry = AssociationRegistry()
    registry.associate("session-1", "mission-a")
    assert registry.is_associated("session-1") is True
    assert registry.missions_for("session-1") == ("mission-a",)

    registry.associate("session-1", "mission-b")
    assert registry.missions_for("session-1") == ("mission-a", "mission-b")

    # A different, never-associated session remains untouched.
    assert registry.is_associated("session-2") is False
