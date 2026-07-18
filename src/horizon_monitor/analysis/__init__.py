"""Offline analysis utilities over Horizon trajectories.

These helpers operate on data Horizon already produces (per-turn fidelity scores
and the event log). They are not part of the realtime ``process_turn`` pipeline
and add no runtime cost.
"""

from __future__ import annotations

from horizon.analysis.interventional_ab import (
    DEFAULT_ACTIONABLE,
    OUTCOME_METRIC,
    run_interventional_ab,
    sign_test,
)
from horizon.analysis.leading_indicator import (
    EventLeadStats,
    LeadingIndicatorReport,
    analyze_leading_indicator,
    analyze_session_leading_indicator,
)

__all__ = [
    "EventLeadStats",
    "LeadingIndicatorReport",
    "analyze_leading_indicator",
    "analyze_session_leading_indicator",
    "DEFAULT_ACTIONABLE",
    "OUTCOME_METRIC",
    "run_interventional_ab",
    "sign_test",
]
