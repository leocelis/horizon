"""V1 gate: proxy-to-human-rating correlation (Spearman rho).

Gate (from horizon_intent.yaml::constraints[v1_proxy_correlation]):
  rho > 0.5 per-turn AND rho > 0.6 conversation-level across >= 200
  conversations from >= 3 domains.
"""

from __future__ import annotations

from horizon import FidelityMonitor
from tests.validation._helpers import load_jsonl, require_dataset


def _spearman(xs: list[float], ys: list[float]) -> float:
    import numpy as np

    if len(xs) < 2:
        return 0.0
    rx = np.argsort(np.argsort(xs))
    ry = np.argsort(np.argsort(ys))
    d = rx - ry
    n = len(xs)
    return 1.0 - (6.0 * float((d * d).sum())) / (n * (n * n - 1))


def test_fidelity_correlation() -> None:
    """V1 proxy correlation. Skips when the labeled corpus is absent."""
    dataset_path = require_dataset("v1_rated_conversations.jsonl")

    per_turn_fidelity: list[float] = []
    per_turn_rating: list[float] = []
    per_conv_fidelity: list[float] = []
    per_conv_rating: list[float] = []
    domains: set[str] = set()

    monitor = FidelityMonitor()
    conversations = list(load_jsonl(dataset_path))
    assert len(conversations) >= 200, f"V1 requires >= 200 conversations, have {len(conversations)}"

    for convo in conversations:
        sid = monitor.new_conversation()
        domains.add(convo.get("domain", "unknown"))
        fidelity_scores: list[float] = []
        turn_ratings: list[float] = convo.get("turn_ratings", [])

        for turn in convo["turns"]:
            result = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            fidelity_scores.append(result.fidelity_score)

        if turn_ratings and len(turn_ratings) == len(fidelity_scores):
            per_turn_fidelity.extend(fidelity_scores)
            per_turn_rating.extend(turn_ratings)

        if fidelity_scores:
            per_conv_fidelity.append(sum(fidelity_scores) / len(fidelity_scores))
            per_conv_rating.append(float(convo["human_rating"]))

    assert len(domains) >= 3, f"V1 requires >= 3 domains, have {sorted(domains)}"

    rho_conv = _spearman(per_conv_fidelity, per_conv_rating)
    assert rho_conv > 0.6, f"Conversation-level Spearman rho {rho_conv:.3f} < 0.6"

    if per_turn_fidelity:
        rho_turn = _spearman(per_turn_fidelity, per_turn_rating)
        assert rho_turn > 0.5, f"Per-turn Spearman rho {rho_turn:.3f} < 0.5"
