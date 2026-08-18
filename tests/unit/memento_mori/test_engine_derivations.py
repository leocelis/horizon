"""E-14, E-15, E-17, E-19 — every row traceable to a derivation.

memento_engine_intent.yaml::derivation_on_every_row.
test: tests/unit/memento_mori/test_engine_derivations.py::test_every_row_traceable
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from horizon_monitor.memento import engine, money
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import ItemKind

from .conftest import EVAL_INSTANT, build_smallco, load_golden

UTC = timezone.utc


def test_every_row_traceable(store) -> None:
    """E-15/E-17/E-19 [GOLDEN] (umbrella): every ItemClock row on the
    smallco fixture exposes a non-empty derivation string, and any row with
    a summary statistic (time_in_stage, wait ratio) carries n."""
    build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    for row in report.items:
        assert row.derivation, f"{row.kind} {row.item_id} has no derivation string"
        if row.time_in_stage_days is not None:
            assert row.n is not None, f"{row.kind} {row.item_id} has a summary stat with no n"
    for comparison in report.path_comparisons:
        assert comparison.derivation, "path comparison has no derivation string"
        for path_row in comparison.rows:
            assert path_row.n is not None


def test_breakeven_arithmetic_matches_golden() -> None:
    """E-15 [GOLDEN]: C_s=600, rate=50/h, T_s=4h, dt=2h/cycle, lam=0.5/day
    -> s=50*2*0.5=50/day; t_be = t_eval + (600+200)/50 = +16 days."""
    golden = load_golden()
    breakeven_date, cycle_count, derivation, omitted = money.breakeven(
        t_eval=EVAL_INSTANT.date(),
        cost_setup=Decimal(str(golden["breakeven_cost_setup"])),
        rate=Decimal(str(golden["breakeven_rate_per_hour"])),
        setup_hours=Decimal(str(golden["breakeven_setup_hours"])),
        delta_t_hours=Decimal(str(golden["breakeven_delta_t_hours_per_cycle"])),
        lam_per_day=golden["breakeven_lambda_cycles_per_day"],
    )
    expected_days = golden["breakeven_days_from_eval"]
    assert breakeven_date == EVAL_INSTANT.date() + timedelta(days=expected_days) == date(2026, 9, 3)
    assert cycle_count is None
    assert omitted is None
    assert "600" in derivation and "50" in derivation and "16" in derivation


def test_money_identity_non_monetary_bytes_unchanged_with_rate_removed(store) -> None:
    """E-14 [PROPERTY]: register one item with a caller amount; evaluate
    with the rate declared and with it removed — every non-monetary byte of
    the serialized report is identical, and money is present only when the
    rate is declared."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="a task with a declared value at stake",
        parent_id=root_id,
        created_valid=datetime(2026, 8, 1, tzinfo=UTC),
        amount=Decimal("100"),
    )
    snapshot = store.snapshot()

    report_with_rate = engine.evaluate(
        snapshot, EVAL_INSTANT, MementoConfig(time_value_rate=Decimal("50"))
    )
    report_without_rate = engine.evaluate(snapshot, EVAL_INSTANT, MementoConfig())

    assert report_without_rate.money == ()
    assert len(report_with_rate.money) == 1
    assert report_with_rate.money[0].item_id == task_id
    assert report_with_rate.money[0].cost_of_delay is not None

    dict_with = report_with_rate.to_dict()
    dict_without = report_without_rate.to_dict()
    dict_with.pop("money")
    dict_without.pop("money")
    assert json.dumps(dict_with, sort_keys=True) == json.dumps(
        dict_without, sort_keys=True
    ), "every non-monetary byte must be identical with the rate removed"


def test_path_comparison_matches_golden(store) -> None:
    """E-17 [GOLDEN]: P1 sojourn 4d vs incumbent accrued delay 17d since
    2026-08-01; path_ahead True; no synthetic latency field exists on
    PathComparisonRow (schema-level: sojourn_days/accrued_delay_days are the
    only latency fields, both drawn from recorded timestamps)."""
    golden = load_golden()
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())

    comparison = next(c for c in report.path_comparisons if c.mission_id == ids["M1"])
    probe_row = next(r for r in comparison.rows if r.is_probe)
    incumbent_row = next(r for r in comparison.rows if not r.is_probe)

    assert probe_row.sojourn_days == golden["path_p1_sojourn_days"] == 4
    assert incumbent_row.accrued_delay_days == golden["path_incumbent_accrued_delay_days"] == 17
    assert comparison.path_ahead is golden["path_ahead"] is True
    assert "2026-08-01" in comparison.derivation


def test_no_synthetic_latency_field_exists_on_path_comparison_row() -> None:
    """E-17: the PathComparisonRow schema itself has only two latency
    fields (sojourn_days, accrued_delay_days), both populated from recorded
    timestamps — there is no field a synthetic/simulated value could be
    written into (an API-level assertion, not just a behavioral one)."""
    from horizon_monitor.memento.models import PathComparisonRow

    field_names = {f.name for f in __import__("dataclasses").fields(PathComparisonRow)}
    assert field_names == {
        "path_key",
        "sojourn_days",
        "accrued_delay_days",
        "n",
        "is_probe",
        "completed",
    }
