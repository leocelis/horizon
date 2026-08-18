"""TTL / break-even proposals (``clock_propose``).

Per MEMENTO_MORI_TECH_SPEC.md §4 step 5 and PRD §6: a nearest-rank
percentile over the operator's OWN completed comparables — reference-class
arithmetic, never a prediction. A ``Proposal`` is always inert: nothing in
this module writes to a store. It is applied only by an explicit
``EventKind.RATIFY`` write through ``MementoStore``
(horizon_memento_mori_intent.yaml::facts_are_caller_provided — "never
applied without an explicit ratifying write").
"""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from horizon_monitor.memento import money
from horizon_monitor.memento.models import Proposal


def ttl_proposal(
    item_id: str,
    completed_durations_days: list[int],
    percentile: float = 0.80,
) -> Proposal | None:
    """Nearest-rank percentile over the caller's own completed comparable
    durations. An empty comparable class returns ``None`` — never an
    invented default (memento_engine_intent.yaml::degrade_by_omission)."""
    if not completed_durations_days:
        return None

    sorted_durations = sorted(completed_durations_days)
    n = len(sorted_durations)
    rank = max(1, min(n, math.ceil(percentile * n)))
    value = sorted_durations[rank - 1]

    derivation = (
        f"P{int(round(percentile * 100))} nearest-rank over n={n} completed "
        f"durations {sorted_durations}: rank=ceil({percentile}*{n})={rank} -> "
        f"value={value}d. Inert: unapplied until an explicit RATIFY event."
    )
    return Proposal(item_id=item_id, kind="ttl", value=value, sample_size=n, derivation=derivation)


def breakeven_proposal(
    item_id: str,
    t_eval: date,
    cost_setup: Decimal,
    rate: Decimal,
    setup_hours: Decimal,
    delta_t_hours: Decimal,
    lam_per_day: float | None,
) -> Proposal:
    """Wraps ``money.breakeven()`` as an inert Proposal — never applied
    without an explicit RATIFY event."""
    breakeven_date, cycle_count, derivation, omitted = money.breakeven(
        t_eval=t_eval,
        cost_setup=cost_setup,
        rate=rate,
        setup_hours=setup_hours,
        delta_t_hours=delta_t_hours,
        lam_per_day=lam_per_day,
    )
    value: object
    value = breakeven_date if breakeven_date is not None else {"cycle_count": cycle_count}
    full_derivation = derivation if omitted is None else f"{derivation}; {omitted}"
    return Proposal(
        item_id=item_id,
        kind="breakeven",
        value=value,
        sample_size=1,
        derivation=full_derivation,
    )
