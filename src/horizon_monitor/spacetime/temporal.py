"""Temporal gap analysis and human retention modeling."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal


class TimestampParseError(ValueError):
    """Raised when a caller-supplied timestamp cannot be parsed as ISO 8601.

    Horizon accepts ISO 8601 strings, including the trailing "Z" (Zulu/UTC)
    suffix. This is raised instead of letting a bare ``ValueError`` /
    ``TypeError`` propagate from ``datetime.fromisoformat`` or from mixing
    naive and timezone-aware datetimes in subtraction.
    """


def parse_timestamp(ts: str) -> datetime:
    """Parse a caller-supplied ISO 8601 timestamp into a UTC-aware datetime.

    Normalizes two sources of fragility before delegating to
    ``datetime.fromisoformat``:

    - A trailing "Z" (Zulu/UTC suffix) is rewritten to "+00:00". Python's
      ``fromisoformat`` only accepts a bare "Z" natively from 3.11 onward;
      Horizon supports Python 3.10+, so a "Z"-suffixed timestamp would
      otherwise raise ``ValueError`` on 3.10.
    - A naive timestamp (no UTC offset) is treated as UTC and made
      timezone-aware, so that later subtraction between two parsed
      timestamps never raises ``TypeError`` from mixing naive and aware
      datetimes (e.g. one turn logged with an offset, the next without).

    Use this helper (not ``datetime.fromisoformat`` directly) everywhere a
    timestamp arrives from ``process_turn`` input.

    Raises:
        TimestampParseError: if `ts` is not a valid ISO 8601 string even
            after normalization.
    """
    if not isinstance(ts, str) or not ts.strip():
        raise TimestampParseError(f"Timestamp must be a non-empty ISO 8601 string, got {ts!r}")

    normalized = ts.strip()
    if normalized[-1:] in ("Z", "z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise TimestampParseError(
            f"Could not parse timestamp {ts!r} as ISO 8601 "
            f"(normalized form: {normalized!r}): {exc}"
        ) from exc

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt


def compute_temporal_gap(
    current_ts: str,
    prev_ts: str | None,
) -> tuple[float, str]:
    """Compute seconds between two ISO 8601 timestamps and classify the gap.

    Returns (gap_seconds, gap_class).

    Raises:
        TimestampParseError: if either timestamp cannot be parsed.
    """
    if prev_ts is None:
        return 0.0, "realtime"

    current = parse_timestamp(current_ts)
    prev = parse_timestamp(prev_ts)
    gap = (current - prev).total_seconds()

    return gap, classify_gap(gap)


def classify_gap(seconds: float) -> Literal["realtime", "seconds", "minutes", "hours", "days"]:
    """Classify a time gap by magnitude."""
    if seconds < 1:
        return "realtime"
    if seconds < 60:
        return "seconds"
    if seconds < 3600:
        return "minutes"
    if seconds < 86400:
        return "hours"
    return "days"


def compute_retention(
    gap_seconds: float,
    h_c_hours: float,
    kappa: float,
) -> float:
    """Estimate human retention using Half-Life Regression model.

    R = 2^(-Δt / h_c) × κ(t)

    Based on Ebbinghaus forgetting curve, adapted by Settles & Meeder (2016)
    for spaced repetition (HLR). κ adjusts for circadian cognitive position.

    Returns [0, 1].
    """
    if gap_seconds <= 0:
        return 1.0

    h_c_seconds = h_c_hours * 3600.0
    R = 2.0 ** (-gap_seconds / h_c_seconds)
    R_adjusted = R * kappa
    return max(0.0, min(1.0, R_adjusted))


def compute_temporal_asymmetry_penalty(
    gap_seconds: float,
    h_c_hours: float,
    kappa: float,
    w_memory: float = 1.0,
) -> float:
    """Compute Δτ — the temporal asymmetry between human and AI experience.

    The agent experiences zero elapsed time between turns. The human does not.
    This penalty encodes that structural asymmetry as a fidelity cost.

    Returns [0, 1]: 0 = no asymmetry (realtime), 1 = maximum decay.
    """
    if gap_seconds < 60:
        return 0.0

    retention = compute_retention(gap_seconds, h_c_hours, kappa)
    delta_tau = (1.0 - retention) * w_memory
    return delta_tau


def compute_resumption_cost(
    gap_seconds: float,
    retention: float,
) -> Literal["none", "low", "medium", "high", "extreme"]:
    """Classify the human cognitive cost of resuming this conversation."""
    if gap_seconds < 60:
        return "none"
    if gap_seconds < 300 and retention > 0.8:
        return "low"
    if gap_seconds < 3600 and retention > 0.5:
        return "medium"
    if gap_seconds < 86400:
        return "high"
    return "extreme"
