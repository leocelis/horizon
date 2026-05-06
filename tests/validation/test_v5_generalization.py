"""V5 gate: cross-domain generalization.

Gate (from horizon_intent.yaml::constraints[v5_domain_generalization]):
  On >= 5 domains not in V1/V2 sets, composite fidelity rho must degrade by
  < 20% relative (per-turn rho >= 0.4, conversation-level rho >= 0.48).
"""

from __future__ import annotations

from collections import defaultdict

from horizon import FidelityMonitor
from tests.validation._helpers import load_jsonl, require_dataset
from tests.validation.test_v1_proxy import _spearman


def test_cross_domain_rho() -> None:
    """V5 cross-domain rho gate. Skips when held-out domains dataset is absent."""
    dataset_path = require_dataset("v5_heldout_conversations.jsonl")

    # Per domain we keep (fidelity_per_turn, conv_rating, per_turn_ratings_or_None)
    by_domain: dict[
        str, list[tuple[list[float], float, list[float] | None]]
    ] = defaultdict(list)
    monitor = FidelityMonitor()

    for convo in load_jsonl(dataset_path):
        sid = monitor.new_conversation()
        fidelity_scores: list[float] = []
        for turn in convo["turns"]:
            r = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            fidelity_scores.append(r.fidelity_score)
        if not fidelity_scores:
            continue

        per_turn = convo.get("turn_ratings")
        if isinstance(per_turn, list) and len(per_turn) == len(fidelity_scores):
            ratings_for_turns: list[float] | None = [float(x) for x in per_turn]
        else:
            ratings_for_turns = None

        by_domain[convo["domain"]].append(
            (fidelity_scores, float(convo["human_rating"]), ratings_for_turns)
        )

    assert len(by_domain) >= 5, f"V5 requires >= 5 held-out domains, have {sorted(by_domain)}"

    failures: list[str] = []
    for domain, rows in by_domain.items():
        if len(rows) < 10:
            continue
        per_conv_fid = [sum(s) / len(s) for s, _, _ in rows]
        per_conv_rate = [r for _, r, _ in rows]
        rho_conv = _spearman(per_conv_fid, per_conv_rate)

        # Prefer real per-turn labels when the corpus provides them — falling
        # back to the conversation-level rating broadcast across each turn
        # only when the corpus omits per-turn ground truth.
        per_turn_fid: list[float] = []
        per_turn_rate: list[float] = []
        for fids, conv_rating, turn_ratings in rows:
            if turn_ratings is not None:
                per_turn_fid.extend(fids)
                per_turn_rate.extend(turn_ratings)
            else:
                per_turn_fid.extend(fids)
                per_turn_rate.extend([conv_rating] * len(fids))
        rho_turn = _spearman(per_turn_fid, per_turn_rate)

        if rho_turn < 0.4 or rho_conv < 0.48:
            failures.append(
                f"{domain}: per-turn={rho_turn:.3f} (need >=0.4), "
                f"conversation={rho_conv:.3f} (need >=0.48)"
            )

    assert not failures, "V5 gate failures:\n  " + "\n  ".join(failures)
