"""Conversation Spacetime Interval ds² — Minkowski-inspired unified metric.

ds² = -α·(log(1+Δt))² + β·(ΔD_JS)² + γ·(Δε)² + δ·(ΔC)²

Negative ds² = timelike (time dominates, conversation moved mainly in time)
Positive ds² = spacelike (semantic/ontological shift dominates)
Near-zero ds² = lightlike (balanced transition — optimal per Conjecture THCP-5)

The time axis uses log(1 + gap_seconds) to prevent raw seconds from dominating
the [0,1]-bounded semantic terms.
"""

from __future__ import annotations

import math
from typing import Literal

from horizon.config import Config


def compute_spacetime_interval(
    d_tau: float,
    d_djs: float,
    d_epsilon: float,
    d_coherence: float,
    config: Config,
) -> tuple[float, Literal["timelike", "spacelike", "lightlike"]]:
    """Compute ds² and classify the interval.

    Args:
        d_tau: Proper time gap in seconds between turns.
        d_djs: |D_JS_t - D_JS_{t-1}|
        d_epsilon: |ε_t - ε_{t-1}|
        d_coherence: |C_t - C_{t-1}|
        config: Spacetime coefficients α, β, γ, δ.

    Returns:
        (ds² value, interval class)
    """
    d_tau_norm = math.log1p(abs(d_tau))

    ds2 = (
        -config.spacetime_alpha * d_tau_norm**2
        + config.spacetime_beta * d_djs**2
        + config.spacetime_gamma * d_epsilon**2
        + config.spacetime_delta * d_coherence**2
    )

    LIGHTLIKE_EPSILON = 0.01
    if ds2 < -LIGHTLIKE_EPSILON:
        interval_class: Literal["timelike", "spacelike", "lightlike"] = "timelike"
    elif ds2 > LIGHTLIKE_EPSILON:
        interval_class = "spacelike"
    else:
        interval_class = "lightlike"

    return ds2, interval_class
