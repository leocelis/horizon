"""Conversation "spacetime interval" ds² — a weighted 4-term distance.

NOTE ON FRAMING: the Minkowski / "spacetime" vocabulary is a *metaphor* that
inspired this metric; it is not a physical claim. Mathematically ds² is just a
weighted sum of squared per-turn deltas:

    ds² = -α·(log(1+Δt))² + β·(ΔD_JS)² + γ·(Δε)² + δ·(ΔC)²

The negative coefficient on the time term is a sign *convention* (so that
time-dominated transitions land below zero); it carries no invariant physical
meaning, and flipping α would flip the classification. The interval and its class
are emitted as descriptive metadata only — no event or fidelity score depends on
them (see events/evaluator.py).

Classification (purely a sign bucket of ds²):
  ds² < -ε  → "timelike"   (time dominates the transition)
  ds² >  ε  → "spacelike"  (semantic / ontological shift dominates)
  |ds²| ≤ ε → "lightlike"  (balanced transition)

The time axis uses log(1 + gap_seconds) to keep raw seconds from dominating the
[0,1]-bounded semantic terms.
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
