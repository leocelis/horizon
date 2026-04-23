"""Deictic temporal expression resolution using dateparser."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from horizon.models import TemporalReference


def resolve_deictic_expressions(
    text: str,
    reference_timestamp: str,
) -> list[TemporalReference]:
    """Find and resolve relative temporal expressions in text.

    Examples: "yesterday", "next Monday", "in 3 hours", "last week".

    Uses dateparser with the conversation timestamp as the relative base.
    Returns TemporalReference objects; unresolvable expressions have resolved=None.
    """
    try:
        import dateparser.search
    except ImportError:
        return []

    base_dt = datetime.fromisoformat(reference_timestamp)

    try:
        results = dateparser.search.search_dates(
            text,
            settings={
                "RELATIVE_BASE": base_dt,
                "RETURN_AS_TIMEZONE_AWARE": True,
                "PREFER_DAY_OF_MONTH": "first",
            },
        )
    except Exception:
        return []

    if not results:
        return []

    refs = []
    for expression, resolved_dt in results:
        expr_lower = expression.lower()
        ref_type = _classify_expression(expr_lower)
        refs.append(
            TemporalReference(
                expression=expression,
                resolved=resolved_dt.isoformat() if resolved_dt else None,
                type=ref_type,
            )
        )

    return refs


def _classify_expression(expr_lower: str) -> str:
    """Heuristic classification of a temporal expression type."""
    time_markers = {"hour", "minute", "second", "am", "pm", ":"}
    duration_markers = {"for ", "during", "past", "ago", "since"}
    date_markers = {"week", "month", "year", "day", "yesterday", "tomorrow", "today"}

    if any(m in expr_lower for m in time_markers):
        return "TIME"
    if any(m in expr_lower for m in duration_markers):
        return "DURATION"
    if any(m in expr_lower for m in date_markers):
        return "DATE"
    return "UNKNOWN"
