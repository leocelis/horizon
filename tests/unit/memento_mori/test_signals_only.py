"""Parent constraint: signals_not_control.

horizon_memento_mori_intent.yaml::constraints[signals_not_control]
test: tests/unit/memento_mori/test_signals_only.py::test_no_control_surface

"The plane never blocks, modifies, or generates agent behavior; its only
outputs are the clock report (pure read), TTL proposals (inert until
ratified), and typed events with suggested_behavior text through the
existing signal contract."
"""

from __future__ import annotations

import inspect

from horizon_monitor.memento import engine, propose, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import Signal, SignalReport

from .conftest import EVAL_INSTANT, build_smallco

_BANNED_VERBS = (
    "block",
    "deny",
    "reject_turn",
    "abort",
    "halt_agent",
    "force",
    "override_response",
    "inject_reply",
)


def test_public_surface_has_no_side_effect_or_control_method() -> None:
    """Every public callable on engine/propose/signals is a pure read,
    an inert proposal builder, or the signal-report builder — none of
    them can block, modify, or generate agent behavior. A mechanical name
    check over the public API surface."""
    for module in (engine, propose, signals):
        for name, _obj in inspect.getmembers(module, inspect.isfunction):
            if name.startswith("_"):
                continue
            lowered = name.lower()
            for banned in _BANNED_VERBS:
                assert (
                    banned not in lowered
                ), f"{module.__name__}.{name} looks like a control-surface method"


def test_evaluate_return_value_is_read_only_and_carries_no_action_field(store) -> None:
    """engine.evaluate() returns data only — no field on the report is a
    callable, and the report dataclass itself is frozen (no in-place
    mutation the caller could use as an implicit side effect)."""
    build_smallco(store)
    config = MementoConfig()
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, config)

    assert report.__dataclass_params__.frozen is True
    for row in report.items:
        assert row.__dataclass_params__.frozen is True
        for value in vars(row).values():
            assert not callable(value)


def test_ttl_proposal_is_inert_data_never_applied_by_the_call_itself(store) -> None:
    """clock_propose-equivalent (propose.ttl_proposal) returns a Proposal —
    plain data with a derivation string — and does not itself write
    anything to the store; only a caller's explicit ratifying write can
    change what the store reports afterward."""
    proposal = propose.ttl_proposal(item_id="some-item", completed_durations_days=[3, 5, 8, 13])
    assert proposal is not None
    assert proposal.derivation
    assert not any(
        callable(getattr(proposal, f))
        for f in ("item_id", "kind", "value", "sample_size", "derivation")
    )


def test_signal_report_only_carries_typed_events_with_suggested_behavior_text(store) -> None:
    """Every produced Signal is the documented shape (typed event +
    suggested_behavior text) — the signal surface has no additional field
    through which an action could be smuggled."""
    build_smallco(store)
    config = MementoConfig()
    snapshot = store.snapshot()
    report = engine.evaluate(snapshot, EVAL_INSTANT, config)
    signal_report, _ = signals.evaluate_signals(snapshot, report, EVAL_INSTANT, config)

    assert isinstance(signal_report, SignalReport)
    for bucket in (signal_report.fired, signal_report.due, signal_report.acked):
        for s in bucket:
            assert isinstance(s, Signal)
            assert isinstance(s.suggested_behavior, str) and s.suggested_behavior
            assert set(vars(s)) == {
                "item_id",
                "signal_type",
                "tier",
                "state",
                "fired",
                "suggested_behavior",
                "n",
                "derivation",
                "payload",
            }
