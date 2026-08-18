"""Parent constraint: facts_are_caller_provided.

horizon_memento_mori_intent.yaml::constraints[facts_are_caller_provided]
test: tests/unit/memento_mori/test_no_invention.py::test_engine_emits_no_invented_dates_amounts_or_durations

"The engine never generates, estimates, or infers a duration, a future
date, or a monetary amount from anything except arithmetic over
caller-supplied records ... an undated deferral is rejected at the schema
with no configuration override ... monetary outputs are limited to
products, sums, and quotients of stored amounts."
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from horizon_monitor.memento import engine, money, propose
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.errors import UndatedDeferralError
from horizon_monitor.memento.models import ItemKind

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


def test_undated_deferral_rejected_with_no_override(store) -> None:
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    with pytest.raises(UndatedDeferralError):
        store.register_item(
            kind=ItemKind.DEFERRAL,
            title="undated",
            parent_id=root_id,
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        )
    # No keyword anywhere on register_item can override this rejection.
    import inspect

    assert "force" not in inspect.signature(store.register_item).parameters
    assert "override" not in inspect.signature(store.register_item).parameters


def test_breakeven_derives_only_from_supplied_arithmetic(store) -> None:
    """E-15's numbers, re-asserted at the parent scope: every input to
    money.breakeven is caller-supplied or a prior arithmetic derivation
    (lam_per_day itself only exists when arrivals==departures over a
    caller-declared window) — there is no path that mints a date from an
    unmeasured rate."""
    breakeven_date, cycle_count, derivation, omitted = money.breakeven(
        t_eval=date(2026, 8, 18),
        cost_setup=Decimal("600"),
        rate=Decimal("50"),
        setup_hours=Decimal("4"),
        delta_t_hours=Decimal("2"),
        lam_per_day=0.5,
    )
    assert breakeven_date == date(2026, 9, 3)  # +16 days, matches E-15
    assert cycle_count is None
    assert omitted is None
    assert "600" in derivation and "50" in derivation  # every input traceable in the text

    # With no conserved-window lambda, no date is minted — a cycle count only.
    no_rate_date, no_rate_cycles, _, no_rate_omitted = money.breakeven(
        t_eval=date(2026, 8, 18),
        cost_setup=Decimal("600"),
        rate=Decimal("50"),
        setup_hours=Decimal("4"),
        delta_t_hours=Decimal("2"),
        lam_per_day=None,
    )
    assert no_rate_date is None
    assert no_rate_cycles == 2
    assert no_rate_omitted is not None and "guessed rate" in no_rate_omitted


def test_ttl_proposal_never_invents_a_value_for_an_empty_class() -> None:
    assert propose.ttl_proposal(item_id="x", completed_durations_days=[]) is None


def test_no_monetary_output_without_a_declared_rate(store) -> None:
    """facts_are_caller_provided binds money too: with no time_value_rate
    declared, the engine's money block is empty — never a guessed figure —
    and every non-monetary field is unaffected (cross-checked against the
    rate-declared run)."""
    build_smallco(store)
    snapshot = store.snapshot()

    report_no_rate = engine.evaluate(snapshot, EVAL_INSTANT, MementoConfig())
    assert report_no_rate.money == ()

    report_with_rate = engine.evaluate(
        snapshot, EVAL_INSTANT, MementoConfig(time_value_rate=Decimal("50"))
    )
    non_monetary_no_rate = [i.to_dict() for i in report_no_rate.items]
    non_monetary_with_rate = [i.to_dict() for i in report_with_rate.items]
    assert non_monetary_no_rate == non_monetary_with_rate
