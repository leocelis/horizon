"""Path comparison + probe arithmetic — measured, never simulated.

Per MEMENTO_MORI_TECH_SPEC.md §4 step 4 and PRD §7: only recorded probe
sojourns and the incumbent's accrued delay since a probe's registration ever
appear in a comparison. No synthetic latency, and no inferential "path A
beats path B" distributional claim (no p-value, confidence interval,
posterior, or sequential/always-valid test) is computed by this module —
those are typed refusals (memento_engine_intent.yaml::typed_refusals;
research topic B9 / intent v0.5).

The only descriptive predicate this module supports is ``path_ahead``: the
probe's completed sojourn is shorter than the incumbent's accrued delay
since the alternative was registered — labelled as exactly those two
intervals, never as a claim about which path is "better" in general.
"""

from __future__ import annotations

from datetime import date

from horizon_monitor.memento.errors import (
    CounterfactualRefusedError,
    InferentialDominanceRefusedError,
)
from horizon_monitor.memento.models import BaseRateRow, Item, PathComparison, PathComparisonRow


def build_comparison(
    mission_id: str,
    probes: tuple[tuple[Item, int | None, bool], ...],
    t_eval: date,
    base_rates: tuple[BaseRateRow, ...] = (),
) -> PathComparison | None:
    """Build one mission's path comparison from already-measured probe
    sojourns. ``probes`` is a tuple of ``(probe_item, sojourn_days, is_open)``
    triples — ``sojourn_days`` is the probe's most recent recorded stage
    sojourn length, or ``None`` if it has no stage events yet; ``is_open`` is
    ``True`` while that sojourn is still running (never a completed
    measurement). Returns ``None`` when the mission has no registered
    probes — there is then nothing to compare.
    """
    if not probes:
        return None

    rows: list[PathComparisonRow] = []
    path_ahead = False
    derivation_parts: list[str] = []

    for probe_item, sojourn_days, is_open in probes:
        accrued = (t_eval - probe_item.created_valid.date()).days
        completed = sojourn_days is not None and not is_open

        rows.append(
            PathComparisonRow(
                path_key=probe_item.title,
                sojourn_days=sojourn_days if completed else None,
                accrued_delay_days=None,
                n=1 if completed else 0,
                is_probe=True,
                completed=completed,
            )
        )
        rows.append(
            PathComparisonRow(
                path_key="incumbent",
                sojourn_days=None,
                accrued_delay_days=accrued,
                n=1,
                is_probe=False,
                completed=False,
            )
        )

        if completed and sojourn_days is not None and sojourn_days < accrued:
            path_ahead = True

        sojourn_text = "not yet completed" if not completed else f"{sojourn_days}d"
        derivation_parts.append(
            f"probe {probe_item.title!r} sojourn={sojourn_text} vs incumbent accrued "
            f"delay={accrued}d since registered {probe_item.created_valid.date()}"
        )

    return PathComparison(
        mission_id=mission_id,
        rows=tuple(rows),
        base_rates=base_rates,
        path_ahead=path_ahead,
        derivation="; ".join(derivation_parts),
    )


def counterfactual_sojourn(*args: object, **kwargs: object) -> None:
    """No "what the untaken path would have cost" computation exists. The
    honest substitute is the incumbent's accruing measured delay
    (``path_ahead`` above). See errors.CounterfactualRefusedError; PRD §7,
    intent non_goals."""
    raise CounterfactualRefusedError()


def path_dominance_test(*args: object, **kwargs: object) -> None:
    """No p-value / confidence interval / posterior / sequential or
    always-valid test on path latencies exists. See
    errors.InferentialDominanceRefusedError; research topic B9, intent v0.5
    signal redesign (``signal.path_dominated`` -> ``signal.path_ahead``)."""
    raise InferentialDominanceRefusedError()
