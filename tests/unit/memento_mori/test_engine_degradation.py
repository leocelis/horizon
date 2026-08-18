"""degrade_by_omission — missing optional inputs degrade by omission with
an explanatory field, never by substitution of a guessed value.

memento_engine_intent.yaml::degrade_by_omission.
test: tests/unit/memento_mori/test_engine_degradation.py::test_omission_never_substitution
"""

from __future__ import annotations

from decimal import Decimal

from horizon_monitor.memento import engine, money, propose
from horizon_monitor.memento.config import MementoConfig

from .conftest import EVAL_INSTANT, build_smallco


def test_omission_never_substitution(store) -> None:
    """Four degrade paths, each an explanatory omission — never a
    substituted value: (1) missing rate -> no monetary fields; (2)
    non-conserved arrivals/departures window -> lambda=None, cycle count
    only; (3) empty comparable class -> no TTL proposal; (4) unlabeled
    stage events -> no wait/touch ratio."""
    ids = build_smallco(store)

    # (1) Missing rate: no MoneyBlock at all; every non-monetary field is
    # untouched (proven precisely by E-14's identity test).
    report_no_rate = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    assert report_no_rate.money == ()

    # (2) Non-conserved window: arrivals != departures -> lambda is None,
    # never a guessed rate.
    lam = money.derive_conserved_window_lambda(arrivals=7, departures=5, window_days=14)
    assert lam is None
    breakeven_date, cycle_count, derivation, omitted = money.breakeven(
        t_eval=EVAL_INSTANT.date(),
        cost_setup=Decimal("600"),
        rate=Decimal("50"),
        setup_hours=Decimal("4"),
        delta_t_hours=Decimal("2"),
        lam_per_day=lam,
    )
    assert breakeven_date is None
    assert cycle_count == 2  # ceil(4/2) — cycles only, no date minted
    assert omitted is not None and "lambda" in omitted.lower()

    # (3) Empty comparable class -> no proposal (never an invented default).
    proposal = propose.ttl_proposal(item_id=ids["T1"], completed_durations_days=[], percentile=0.80)
    assert proposal is None

    # (4) Unlabeled stage events -> no wait/touch ratio (see
    # test_engine_entities.py::test_wait_touch_ratio_only_from_caller_labels
    # for the full case; re-asserted here as part of the constraint's own
    # named test).
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    e1 = next(r for r in report.items if r.item_id == ids["E1"])
    assert e1.wait_vs_touch_ratio is None
    assert e1.omitted is not None


def test_conserved_window_lambda_when_arrivals_equal_departures(store) -> None:
    lam = money.derive_conserved_window_lambda(arrivals=7, departures=7, window_days=14)
    assert lam == 0.5
