"""E-16, E-18 — typed refusals: no code path returns an approximation.

memento_engine_intent.yaml::typed_refusals.
test: tests/unit/memento_mori/test_engine_refusals.py::test_refusal_list_enforced

REVIEWER NOTE [HUMAN]: the refusal LIST itself (which computations are
refused) is a product decision from PRD §6/§7 and research topic B9; a human
reviewer should confirm this list is complete before shipping (ai_generated
test provenance — IVD Rule 3: this test alone cannot mark the constraint
PASS, only that the currently-named refusals raise as documented).
"""

from __future__ import annotations

import pytest

from horizon_monitor.memento import money, paths
from horizon_monitor.memento.errors import (
    CounterfactualRefusedError,
    CurrencyConversionRefusedError,
    FinancialModellingRefusedError,
    ForecastRefusedError,
    InferentialDominanceRefusedError,
)


def test_refusal_list_enforced() -> None:
    """E-16: NPV, currency conversion, and forecast Δt/savings requests
    raise typed refusal errors naming the violated rule — never a number."""
    with pytest.raises(FinancialModellingRefusedError):
        money.npv()
    with pytest.raises(FinancialModellingRefusedError):
        money.irr()
    with pytest.raises(FinancialModellingRefusedError):
        money.discounted_cash_flow()
    with pytest.raises(CurrencyConversionRefusedError):
        money.convert_currency()
    with pytest.raises(ForecastRefusedError):
        money.forecast_savings()


def test_counterfactual_and_inferential_dominance_refused() -> None:
    """E-18: the API surface has no "would-have-taken" computation and no
    inferential path-dominance test; requesting either is a typed refusal."""
    with pytest.raises(CounterfactualRefusedError):
        paths.counterfactual_sojourn()
    with pytest.raises(InferentialDominanceRefusedError):
        paths.path_dominance_test()


def test_refused_computations_are_absent_from_the_public_api_surface() -> None:
    """E-18: beyond raising, the refused computations have no legitimate
    entry point — the only symbols money/paths export for these concepts
    are the refusal functions themselves (an API-level assertion)."""
    forbidden_names = {
        "npv_value",
        "internal_rate_of_return_value",
        "discount_rate",
        "counterfactual_path_cost",
        "path_dominates",
        "p_value",
        "confidence_interval",
    }
    money_names = set(dir(money))
    paths_names = set(dir(paths))
    assert not (forbidden_names & money_names)
    assert not (forbidden_names & paths_names)
