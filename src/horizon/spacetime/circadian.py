"""Circadian cognitive factor κ(t).

Based on Valdez et al. (2012) — reaction time varies 9–34% across 24h.
Schmidt et al. (2007) — dual-peak model with post-lunch dip.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional


def compute_circadian_factor(
    timestamp: str,
    timezone_str: Optional[str],
    chronotype_offset: float = 0.0,
) -> float:
    """Estimate the human's cognitive capacity at the given wall-clock time.

    Returns κ ∈ [0.3, 1.0]:
      - 1.0 = peak cognitive capacity (morning 10-14h, afternoon 16-22h)
      - 0.7 = post-lunch dip (14-16h)
      - 0.3 = nocturnal nadir (04-07h)

    chronotype_offset shifts the entire curve (positive = night owl,
    negative = morning lark). Units: hours.
    """
    dt = datetime.fromisoformat(timestamp)

    if timezone_str:
        try:
            from zoneinfo import ZoneInfo

            local_tz = ZoneInfo(timezone_str)
            dt = dt.astimezone(local_tz)
        except (ImportError, KeyError, ValueError):
            pass

    hour = dt.hour + dt.minute / 60.0 - chronotype_offset
    hour = hour % 24.0

    if 7.0 <= hour < 10.0:
        # Morning ramp: 0.5 → 1.0
        return 0.5 + 0.5 * (hour - 7.0) / 3.0
    elif 10.0 <= hour < 14.0:
        return 1.0
    elif 14.0 <= hour < 16.0:
        return 0.7
    elif 16.0 <= hour < 22.0:
        return 1.0
    elif hour >= 22.0 or hour < 4.0:
        # Nocturnal decline: 0.7 → 0.3 over 6h starting at 22:00
        t = hour - 22.0 if hour >= 22.0 else hour + 2.0
        return max(0.3, 0.7 - 0.4 * t / 6.0)
    else:
        # 4:00–7:00 nadir
        return 0.3
