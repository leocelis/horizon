"""V3 gates: outperform naive heuristic baseline.

Gates (from horizon_intent.yaml::constraints):
  v3_beats_heuristics_rho:
    Monitor beats (turn-count + keyword-overlap) heuristic by > 25% relative on
    fidelity-quality Spearman rho.
  v3_beats_heuristics_structural:
    Monitor detects >= 1 class of sheaf-gluing failure (global incoherence not
    visible in any single turn) with precision >= 0.6, which the baseline
    structurally cannot.
"""

from __future__ import annotations

import pytest

from horizon import FidelityMonitor
from tests.validation._helpers import load_jsonl, require_dataset
from tests.validation.test_v1_proxy import _spearman


def _heuristic_fidelity(turns: list[dict]) -> list[float]:
    """Naive baseline: 1 / (1 + turn_index) modulated by keyword overlap."""
    prev_tokens: set[str] = set()
    out: list[float] = []
    for i, t in enumerate(turns):
        tokens = set((t["human"] + " " + t["agent"]).lower().split())
        overlap = len(tokens & prev_tokens) / max(1, len(tokens | prev_tokens))
        out.append(overlap * (1.0 / (1 + 0.05 * i)))
        prev_tokens = tokens
    return out


def test_heuristic_rho_comparison() -> None:
    """Horizon fidelity must beat the heuristic by > 25% relative on rho."""
    dataset_path = require_dataset("v1_rated_conversations.jsonl")

    horizon_scores: list[float] = []
    heuristic_scores: list[float] = []
    ratings: list[float] = []

    monitor = FidelityMonitor()
    for convo in load_jsonl(dataset_path):
        sid = monitor.new_conversation()
        h_scores = []
        for turn in convo["turns"]:
            res = monitor.process_turn(
                sid, turn["human"], turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            h_scores.append(res.fidelity_score)
        if not h_scores:
            continue

        horizon_scores.append(sum(h_scores) / len(h_scores))
        heur = _heuristic_fidelity(convo["turns"])
        heuristic_scores.append(sum(heur) / len(heur))
        ratings.append(float(convo["human_rating"]))

    rho_horizon = _spearman(horizon_scores, ratings)
    rho_heur = _spearman(heuristic_scores, ratings)

    lift = (rho_horizon - rho_heur) / max(abs(rho_heur), 1e-6)
    assert lift > 0.25, (
        f"V3 rho lift {lift:.2%} must be > 25%. "
        f"rho_horizon={rho_horizon:.3f}, rho_heuristic={rho_heur:.3f}"
    )


def test_structural_failure_detection() -> None:
    """Detect at least one class of global incoherence on held-out examples."""
    dataset_path = require_dataset("v3_structural_failures.jsonl")

    monitor = FidelityMonitor()
    monitor.configure(event_modes={"alert.contradiction": "active"})

    tp = 0
    fp = 0
    labeled = 0
    for convo in load_jsonl(dataset_path):
        labeled += 1
        sid = monitor.new_conversation()
        monitor.configure(session_id=sid, event_modes={"alert.contradiction": "active"})
        events = []
        for turn in convo["turns"]:
            r = monitor.process_turn(sid, turn["human"], turn["agent"])
            events.extend(r.events)
        predicted_incoherent = any(
            e.active and e.type in {"alert.contradiction", "alert.drift"} for e in events
        )
        truly_incoherent = bool(convo.get("is_globally_incoherent"))
        if predicted_incoherent and truly_incoherent:
            tp += 1
        elif predicted_incoherent and not truly_incoherent:
            fp += 1

    if labeled < 50:
        pytest.skip(f"Structural-failure dataset too small ({labeled}); need >= 50")

    precision = tp / max(1, (tp + fp))
    assert precision >= 0.6, (
        f"Structural-failure precision {precision:.2f} < 0.6 (tp={tp}, fp={fp})"
    )
