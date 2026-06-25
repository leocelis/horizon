"""V6 gate: out-of-domain correlation on a THIRD-PARTY corpus (Fix 4).

The V1/V5 gates run on a corpus the Horizon team built. This gate runs the same
fidelity-vs-human-rating correlation on a corpus Horizon's team did *not* label,
to show the signal transfers off-domain.

It reads ``HORIZON_OOD_DATA/ood_rated_conversations.jsonl`` (produce it with
``scripts/adapt_external_corpus.py`` from a public dataset) and **skips** when
that data is absent — exactly like the other validation gates. When data is
present it asserts a lenient OOD floor (conversation-level Spearman ρ ≥ 0.3) and
prints the measured ρ so it can be recorded in the evidence pack.

Acceptance (Fix 4): correlation holds on at least one corpus Horizon's team did
not label. This test is the mechanism; the published result requires running it
against real third-party data.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from horizon import FidelityMonitor
from tests.validation._helpers import load_jsonl

# Lenient floor: OOD correlation is expected to degrade vs in-domain (V1 uses
# ρ > 0.6). Fix 4 only asks that the signal *transfers*, not that it matches.
OOD_RHO_FLOOR = 0.3


def _spearman(xs: list[float], ys: list[float]) -> float:
    import numpy as np

    if len(xs) < 2:
        return 0.0
    rx = np.argsort(np.argsort(xs))
    ry = np.argsort(np.argsort(ys))
    d = rx - ry
    n = len(xs)
    return 1.0 - (6.0 * float((d * d).sum())) / (n * (n * n - 1))


def _ood_dataset() -> Path:
    env = os.environ.get("HORIZON_OOD_DATA")
    if not env:
        pytest.skip(
            "HORIZON_OOD_DATA not set — the OOD gate needs a third-party corpus. "
            "Build one with scripts/adapt_external_corpus.py."
        )
    path = Path(env).expanduser() / "ood_rated_conversations.jsonl"
    if not path.exists():
        pytest.skip(f"OOD dataset missing: {path}")
    return path


def test_out_of_domain_correlation() -> None:
    dataset = _ood_dataset()

    monitor = FidelityMonitor()
    per_conv_fidelity: list[float] = []
    per_conv_rating: list[float] = []
    domains: set[str] = set()

    conversations = list(load_jsonl(dataset))
    assert (
        len(conversations) >= 30
    ), f"OOD gate wants >= 30 conversations for a stable ρ, have {len(conversations)}"

    for convo in conversations:
        sid = monitor.new_conversation()
        domains.add(convo.get("domain", "unknown"))
        scores: list[float] = []
        for turn in convo["turns"]:
            result = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            scores.append(result.fidelity_score)
        if scores:
            per_conv_fidelity.append(sum(scores) / len(scores))
            per_conv_rating.append(float(convo["human_rating"]))

    rho_conv = _spearman(per_conv_fidelity, per_conv_rating)
    print(
        f"\n[V6 OOD] domains={sorted(domains)} n={len(per_conv_fidelity)} "
        f"conversation-level Spearman ρ = {rho_conv:.3f}"
    )
    assert (
        rho_conv >= OOD_RHO_FLOOR
    ), f"OOD conversation-level ρ {rho_conv:.3f} < floor {OOD_RHO_FLOOR}"
