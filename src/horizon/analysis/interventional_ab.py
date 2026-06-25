"""Interventional A/B analysis — does acting on Horizon events improve outcomes?

Measures whether a governor that switches to a grounded response after actionable
events beats always using the raw response. Outcome = cosine(response, gold reference),
independent of Horizon's fidelity composite.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from horizon import FidelityMonitor
from horizon.engines.embedding import EmbeddingEngine

DEFAULT_ACTIONABLE: frozenset[str] = frozenset(
    {
        "alert.drift",
        "checkpoint.clarification",
        "signal.broken_reference",
        "signal.light_cone_collapse",
        "signal.session_reset",
    }
)

OUTCOME_METRIC = "cosine(agent_response, gold_reference) — independent of Horizon fidelity"


def sign_test(deltas: list[float], eps: float = 1e-6) -> tuple[int, int, float]:
    """Two-sided sign test. Returns (wins, losses, p_value)."""
    wins = sum(1 for d in deltas if d > eps)
    losses = sum(1 for d in deltas if d < -eps)
    n = wins + losses
    if n == 0:
        return 0, 0, 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(0, k + 1)) * (0.5**n)
    return wins, losses, min(1.0, 2.0 * tail)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))


def _run_side(
    monitor: FidelityMonitor,
    embed: EmbeddingEngine,
    turns: list[dict[str, Any]],
    *,
    treatment: bool,
    actionable: set[str],
) -> list[float]:
    sid = monitor.new_conversation()
    outcomes: list[float] = []
    prev_fired_actionable = False
    for turn in turns:
        if treatment and prev_fired_actionable and turn.get("agent_grounded"):
            used = turn["agent_grounded"]
        else:
            used = turn["agent_raw"]
        result = monitor.process_turn(sid, turn["human"], used, timestamp=turn.get("timestamp"))
        reference = turn.get("reference", turn["human"])
        outcomes.append(_cosine(embed.embed(used), embed.embed(reference)))
        prev_fired_actionable = any(e.type in actionable for e in result.events)
    return outcomes


def run_interventional_ab(
    conversations: list[list[dict[str, Any]]],
    actionable: set[str] | None = None,
) -> dict[str, Any]:
    """Run control vs treatment interventional A/B over ``conversations``."""
    actionable = set(actionable or DEFAULT_ACTIONABLE)
    monitor = FidelityMonitor()
    embed = EmbeddingEngine()

    control_all: list[float] = []
    treatment_all: list[float] = []
    deltas: list[float] = []

    for turns in conversations:
        control = _run_side(monitor, embed, turns, treatment=False, actionable=actionable)
        treatment = _run_side(monitor, embed, turns, treatment=True, actionable=actionable)
        control_all.extend(control)
        treatment_all.extend(treatment)
        deltas.extend(t - c for c, t in zip(control, treatment, strict=False))

    mean_c = sum(control_all) / len(control_all) if control_all else 0.0
    mean_t = sum(treatment_all) / len(treatment_all) if treatment_all else 0.0
    abs_lift = mean_t - mean_c
    rel_lift = (abs_lift / mean_c) if mean_c else 0.0
    wins, losses, p = sign_test(deltas)

    return {
        "n_conversations": len(conversations),
        "n_turns": len(control_all),
        "mean_control_outcome": round(mean_c, 4),
        "mean_treatment_outcome": round(mean_t, 4),
        "absolute_lift": round(abs_lift, 4),
        "relative_lift": round(rel_lift, 4),
        "sign_test": {"wins": wins, "losses": losses, "p_value": round(p, 5)},
        "actionable_events": sorted(actionable),
        "outcome_metric": OUTCOME_METRIC,
    }
