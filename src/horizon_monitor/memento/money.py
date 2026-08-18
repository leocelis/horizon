"""Monetary block — the engine may divide by money, never guess money.

Per MEMENTO_MORI_TECH_SPEC.md §4 step 3 and PRD §6: cost-of-delay and
break-even are pure arithmetic over an operator-declared rate and
caller-supplied amounts/durations. The automatic per-evaluation money block
(engine.py) is skipped entirely when ``time_value_rate`` is ``None``; every
non-monetary ``ItemClock`` field is then byte-identical either way
(memento_engine_intent.yaml::degrade_by_omission,
horizon_memento_mori_intent.yaml::facts_are_caller_provided).

Refused: NPV/IRR/DCF, discount-rate selection, currency conversion, tax, and
any forecast of a savings/Δlatency figure that was not measured
(memento_engine_intent.yaml::typed_refusals; PRD §6).
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import ROUND_CEILING, Decimal

from horizon_monitor.memento.errors import (
    CurrencyConversionRefusedError,
    FinancialModellingRefusedError,
    ForecastRefusedError,
)


def derive_conserved_window_lambda(
    arrivals: int, departures: int, window_days: int
) -> float | None:
    """λ = departures / window_days, but ONLY on a conserved window
    (arrivals == departures accounted for the same window). Otherwise
    ``None`` — never a guessed rate."""
    if arrivals != departures or window_days <= 0:
        return None
    return departures / window_days


def cost_of_delay(amount: Decimal, rate: Decimal, elapsed_hours: Decimal) -> Decimal:
    """``cost_of_delay = amount x rate x elapsed_hours`` (PRD §6). All three
    factors are caller-supplied or measured; nothing invented."""
    return amount * rate * elapsed_hours


def breakeven(
    t_eval: date,
    cost_setup: Decimal,
    rate: Decimal,
    setup_hours: Decimal,
    delta_t_hours: Decimal,
    lam_per_day: float | None,
) -> tuple[date | None, int | None, str, str | None]:
    """``breakeven_date = t_eval + (C_s + rate*T_s) / (rate*Δt*λ)``
    (MEMENTO_MORI_TECH_SPEC.md §4 step 3). When ``lam_per_day`` is ``None``
    (no conserved window to derive a completion rate from) this degrades to
    a cycle count ``N = ceil(T_s / Δt)`` only — no date is ever minted from
    a guessed rate.

    Returns ``(breakeven_date, cycle_count, derivation, omitted)``; exactly
    one of ``breakeven_date`` / ``omitted`` is non-None.
    """
    cycle_count = math.ceil(setup_hours / delta_t_hours) if delta_t_hours > 0 else None

    if lam_per_day is None:
        derivation = (
            f"cycle_count = ceil(T_s/dt) = ceil({setup_hours}/{delta_t_hours}) = {cycle_count}"
        )
        omitted = (
            "omitted: breakeven date requires a conserved-window lambda (measured "
            "cycles/day); none was available, so this degrades to a cycle count "
            "only — no date is minted from a guessed rate."
        )
        return None, cycle_count, derivation, omitted

    savings_per_day = rate * delta_t_hours * Decimal(str(lam_per_day))
    if savings_per_day <= 0:
        derivation = (
            f"savings_per_day = rate*dt*lambda = {rate}*{delta_t_hours}*{lam_per_day} = "
            f"{savings_per_day} (non-positive)"
        )
        omitted = "omitted: non-positive measured savings rate — no breakeven date can be derived."
        return None, cycle_count, derivation, omitted

    numerator = cost_setup + rate * setup_hours
    days_exact = numerator / savings_per_day
    days_count = int(days_exact.to_integral_value(rounding=ROUND_CEILING))
    breakeven_date = t_eval + timedelta(days=days_count)

    derivation = (
        f"savings_per_day = rate*dt*lambda = {rate}*{delta_t_hours}*{lam_per_day} = "
        f"{savings_per_day}/day; t_be = t_eval({t_eval}) + (C_s+rate*T_s)/savings_per_day "
        f"= t_eval + ({cost_setup}+{rate}*{setup_hours})/{savings_per_day} = "
        f"t_eval + {days_count}d = {breakeven_date}"
    )
    return breakeven_date, None, derivation, None


def npv(*args: object, **kwargs: object) -> None:
    """No net-present-value computation exists on this path. See
    errors.FinancialModellingRefusedError; PRD §6, intent non_goals."""
    raise FinancialModellingRefusedError("npv")


def irr(*args: object, **kwargs: object) -> None:
    """No internal-rate-of-return computation exists on this path."""
    raise FinancialModellingRefusedError("irr")


def discounted_cash_flow(*args: object, **kwargs: object) -> None:
    """No discounted-cash-flow / discount-rate selection exists on this path."""
    raise FinancialModellingRefusedError("discounted cash flow")


def convert_currency(*args: object, **kwargs: object) -> None:
    """No currency conversion exists; ``rate_currency`` is a label only."""
    raise CurrencyConversionRefusedError()


def forecast_savings(*args: object, **kwargs: object) -> None:
    """No forecast of an unmeasured savings/Δlatency figure exists on this
    path — only arithmetic over already-measured durations."""
    raise ForecastRefusedError("a forecast savings/delta-latency figure")
