"""Engine joint satisfaction — all five memento_engine_intent.yaml
constraints asserted on the SAME report (individual-pass != joint-pass).

memento_engine_intent.yaml::constraint_satisfiability.joint_satisfaction_test
"""

from __future__ import annotations

import json
import socket
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from horizon_monitor.memento import engine, money, propose
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import ItemKind

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


class _OutboundError(AssertionError):
    pass


def _block(*args, **kwargs):
    raise _OutboundError(f"unexpected outbound call: args={args} kwargs={kwargs}")


def test_all_engine_constraints_one_report(store) -> None:
    """One flow, one report, all five engine constraints:

    1. pure_function_injected_time — byte-identical, no ambient clock/network.
    2. calendar_day_arithmetic — a future-dated item clamps to age 0.
    3. degrade_by_omission — no rate -> money == (); non-conserved window ->
       lambda=None + cycle count only; unlabelled stage events -> no ratio.
    4. derivation_on_every_row — every row has a non-empty derivation.
    5. typed_refusals — a forecast-savings request raises, not a number.
    """
    ids = build_smallco(store)
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="a future task",
        parent_id=ids["M1"],
        created_valid=datetime(2026, 9, 1, tzinfo=UTC),  # after EVAL_INSTANT
    )
    snapshot = store.snapshot()

    # (1) pure_function_injected_time — no ambient clock, no network, and
    # two calls with the same (snapshot, instant) are byte-identical.
    with patch.object(socket.socket, "connect", side_effect=_block):
        with patch.object(socket.socket, "connect_ex", side_effect=_block):
            report_a = engine.evaluate(snapshot, EVAL_INSTANT, MementoConfig())
            report_b = engine.evaluate(snapshot, EVAL_INSTANT, MementoConfig())
    assert json.dumps(report_a.to_dict(), sort_keys=True, default=str) == json.dumps(
        report_b.to_dict(), sort_keys=True, default=str
    )
    assert report_a.zero_network is True and report_a.zero_llm is True

    report = report_a

    # (2) calendar_day_arithmetic — future-dated item clamps to age 0.
    future_row = next(r for r in report.items if r.item_id == task_id)
    assert future_row.age_days == 0
    assert future_row.future_dated is True

    # (3) degrade_by_omission — three independent omission paths, same report.
    assert report.money == (), "no rate declared -> zero monetary fields"
    e1_row = next(r for r in report.items if r.item_id == ids["E1"])
    assert e1_row.wait_vs_touch_ratio is None and e1_row.omitted is not None
    lam = money.derive_conserved_window_lambda(arrivals=7, departures=5, window_days=14)
    assert lam is None
    _, cycle_count, _, omitted = money.breakeven(
        t_eval=EVAL_INSTANT.date(),
        cost_setup=Decimal("600"),
        rate=Decimal("50"),
        setup_hours=Decimal("4"),
        delta_t_hours=Decimal("2"),
        lam_per_day=lam,
    )
    assert cycle_count == 2 and omitted is not None

    # (4) derivation_on_every_row — every row traceable.
    for row in report.items:
        assert row.derivation, f"{row.kind} {row.item_id} has no derivation"

    # (5) typed_refusals — a forecast request is a typed error, not a value.
    empty_proposal = propose.ttl_proposal(item_id=task_id, completed_durations_days=[])
    assert empty_proposal is None
    raised = False
    try:
        money.forecast_savings()
    except Exception as exc:  # noqa: BLE001 — asserting the specific type below
        raised = True
        from horizon_monitor.memento.errors import ForecastRefusedError

        assert isinstance(exc, ForecastRefusedError)
    assert raised, "money.forecast_savings() must raise, never return a number"
