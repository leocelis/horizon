"""Generate a synthetic validation corpus for the V1/V2/V5 gates.

OSS gate corpus generator — synthetic, deterministic, no proprietary data.

WHY THIS EXISTS (Fix 4 + reproducibility): the v0.2.0 evidence pack referenced a
`scripts/build_validation_corpus.py` that was never committed, so the gate tests
silently skipped and the "reproducible from a fresh checkout" claim was false.
This restores a *real*, deterministic generator.

WHAT THIS IS — and IS NOT:
  * IS: a structurally valid, fully synthetic corpus in the schema the gates
    expect, so contributors can exercise the gate *logic* end to end with no
    proprietary data.
  * IS NOT: a substitute for human-labeled data. Because the conversations and
    their "human_rating" come from the same generator, a high V1 ρ here would be
    partly circular. The headline v0.2.0 numbers require a genuinely
    human-labeled corpus (see docs/reviews/V0_2_0_EVIDENCE.md) and, for
    out-of-domain evidence, a third-party corpus (see scripts/adapt_external_corpus.py).

The generator builds conversations with a *latent quality* that Horizon does not
see (it only sees text). Healthy conversations stay on-topic; degrading ones
drift and contradict. human_rating is derived from the latent, not from Horizon —
so V1 ρ, when run, is a real (if synthetic) correlation, not a tautology.

Usage:
  python scripts/build_validation_corpus.py --out data/validation_corpus --n 220
  HORIZON_VALIDATION_DATA=data/validation_corpus python -m pytest tests/validation -q
"""

from __future__ import annotations

import argparse
import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Domain → (on-topic Q/A snippets, off-topic drift snippets). Kept compact; the
# point is structural validity and a latent-quality signal, not prose realism.
DOMAINS: dict[str, dict[str, list[tuple[str, str]]]] = {
    "technical": {
        "on": [
            (
                "How does indexing speed up queries?",
                "An index is a sorted structure that turns a full scan into a logarithmic lookup.",
            ),
            (
                "When does a B-tree index hurt?",
                "On write-heavy tables and low-cardinality columns the maintenance cost can outweigh the read gain.",
            ),
            (
                "What about composite indexes?",
                "Order columns by selectivity; the leftmost-prefix rule decides which queries the index can serve.",
            ),
        ],
        "off": [
            ("What's the weather like?", "I don't have live weather, but spring is usually mild."),
            ("Recommend a movie?", "A classic thriller is always a safe pick for the weekend."),
        ],
    },
    "support": {
        "on": [
            (
                "My export keeps failing at 80%.",
                "Let's check the job log — a timeout at 80% usually means the worker hit a memory ceiling.",
            ),
            (
                "The log shows OOM.",
                "Then we raise the worker memory or stream the export in chunks instead of buffering it all.",
            ),
            (
                "How do I stream it?",
                "Enable chunked export in settings; it flushes each batch so peak memory stays flat.",
            ),
        ],
        "off": [
            (
                "Anyway, best pasta sauce?",
                "A simple garlic-and-tomato sauce works for most weeknight dinners.",
            ),
            (
                "And stock tips?",
                "I can't give financial advice, but diversified index funds are common guidance.",
            ),
        ],
    },
    "coding": {
        "on": [
            (
                "Why is my recursion stack-overflowing?",
                "Likely no base case is reached; print the depth or convert to an explicit stack.",
            ),
            (
                "It's a tree traversal.",
                "Then guard against cycles and ensure every branch terminates at a leaf.",
            ),
            (
                "Iterative version?",
                "Use an explicit stack: push children, pop and process until the stack empties.",
            ),
        ],
        "off": [
            (
                "What's a good hiking boot?",
                "Waterproof boots with ankle support handle rough terrain well.",
            ),
            (
                "Remind me what we were doing?",
                "We were discussing something technical, but I've lost the thread.",
            ),
        ],
    },
    "educational": {
        "on": [
            (
                "Explain photosynthesis simply.",
                "Plants turn sunlight, water, and CO2 into glucose and oxygen in the chloroplasts.",
            ),
            (
                "Where does the energy go?",
                "It's stored in glucose bonds and later released by respiration.",
            ),
            (
                "What limits the rate?",
                "Light intensity, CO2 concentration, and temperature each cap the rate.",
            ),
        ],
        "off": [
            ("What's trending on social media?", "I don't track live trends, sorry."),
            (
                "Tell me a joke instead.",
                "Why did the function return early? It had commitment issues.",
            ),
        ],
    },
    "creative": {
        "on": [
            (
                "Help me outline a short story.",
                "Start with a want, an obstacle, and a turn — three beats keep it tight.",
            ),
            (
                "My protagonist is a lighthouse keeper.",
                "Good — isolation gives you built-in tension; let the sea be the antagonist.",
            ),
            (
                "How should it end?",
                "Resolve the want through a cost, not a gift, so the ending feels earned.",
            ),
        ],
        "off": [
            ("What's a good crypto to buy?", "I can't offer financial advice."),
            (
                "Never mind, what were we writing?",
                "We were outlining something, but I've lost the thread.",
            ),
        ],
    },
}

# V5 uses domains disjoint from V1/V2.
V1_DOMAINS = ["technical", "support", "coding"]
V5_DOMAINS = ["educational", "creative"]


def _make_conversation(
    rng: random.Random, domain: str, healthy: bool, conv_idx: int
) -> tuple[dict, float]:
    """Build one conversation record plus its latent quality.

    Healthy conversations stay on-topic (high latent). Degrading ones start
    on-topic then drift off-topic (declining latent)."""
    snippets = DOMAINS[domain]
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc) + timedelta(days=conv_idx)
    turns: list[dict] = []

    n_on = len(snippets["on"])
    # Latent quality trajectory: healthy stays ~0.85; degrading decays to ~0.35.
    if healthy:
        latents = [0.85 + rng.uniform(-0.05, 0.05) for _ in range(n_on + 2)]
        seq = list(snippets["on"]) + [rng.choice(snippets["on"]) for _ in range(2)]
    else:
        decay = [0.85, 0.8, 0.7, 0.5, 0.35]
        latents = [v + rng.uniform(-0.04, 0.04) for v in decay]
        seq = list(snippets["on"]) + list(snippets["off"])

    for t, (human, agent) in enumerate(seq, start=1):
        ts = (base + timedelta(minutes=3 * t)).isoformat()
        turns.append({"human": human, "agent": agent, "timestamp": ts})

    latent_quality = sum(latents[: len(turns)]) / len(turns)
    # human_rating derived from latent + small deterministic noise (NOT from Horizon).
    human_rating = round(min(1.0, max(0.0, latent_quality + rng.uniform(-0.05, 0.05))), 3)

    record = {
        "conversation_id": f"{domain}-{'h' if healthy else 'd'}-{conv_idx:04d}",
        "domain": domain,
        "turns": turns,
        "human_rating": human_rating,
    }
    return record, latent_quality


def _write_jsonl(path: Path, records: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")


def build(out_dir: Path, n: int, seed: int) -> dict[str, int]:
    rng = random.Random(seed)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── V1 corpus ────────────────────────────────────────────────────────────
    v1: list[dict] = []
    for i in range(n):
        domain = V1_DOMAINS[i % len(V1_DOMAINS)]
        healthy = i % 2 == 0
        rec, _ = _make_conversation(rng, domain, healthy, i)
        v1.append(rec)
    _write_jsonl(out_dir / "v1_rated_conversations.jsonl", v1)

    # ── V5 held-out corpus (disjoint domains) ─────────────────────────────────
    n5 = max(40, n // 4)
    v5: list[dict] = []
    for i in range(n5):
        domain = V5_DOMAINS[i % len(V5_DOMAINS)]
        healthy = i % 2 == 0
        rec, _ = _make_conversation(rng, domain, healthy, 10_000 + i)
        v5.append(rec)
    _write_jsonl(out_dir / "v5_heldout_conversations.jsonl", v5)

    # ── V2 conversations + (modest) event labels ──────────────────────────────
    # We label only a couple of robust, construction-derived event types. The V2
    # gate needs >= 300 labels per event type and will *skip* any type below that
    # — an honest skip, not a failure. Producing 300+ trustworthy synthetic labels
    # per event would itself be fabrication, so we don't.
    v2_convos: list[dict] = []
    v2_labels: list[dict] = []
    for i in range(min(n, 60)):
        domain = V1_DOMAINS[i % len(V1_DOMAINS)]
        healthy = i % 2 == 0
        rec, _ = _make_conversation(rng, domain, healthy, 20_000 + i)
        cid = rec["conversation_id"]
        v2_convos.append(
            {"conversation_id": cid, "metadata": {"domain": domain}, "turns": rec["turns"]}
        )
        # Degrading conversations should drift in their later turns.
        for turn_idx in range(1, len(rec["turns"]) + 1):
            label = (not healthy) and turn_idx >= len(rec["turns"]) - 1
            v2_labels.append(
                {
                    "conversation_id": cid,
                    "turn": turn_idx,
                    "event_type": "alert.drift",
                    "label": bool(label),
                }
            )
    _write_jsonl(out_dir / "v2_conversations.jsonl", v2_convos)
    _write_jsonl(out_dir / "v2_labeled_events.jsonl", v2_labels)

    return {
        "v1_conversations": len(v1),
        "v5_conversations": len(v5),
        "v2_conversations": len(v2_convos),
        "v2_labels": len(v2_labels),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=str, default="data/validation_corpus")
    parser.add_argument(
        "--n", type=int, default=220, help="Number of V1 conversations (>=200 to run the V1 gate)."
    )
    parser.add_argument("--seed", type=int, default=20260617)
    args = parser.parse_args()

    out_dir = Path(args.out).expanduser()
    counts = build(out_dir, args.n, args.seed)
    print(f"Wrote synthetic validation corpus to {out_dir}/")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    print(
        "\nNOTE: fully synthetic and self-derived — exercises gate LOGIC only. "
        "It is not human-labeled data and does not reproduce the v0.2.0 headline numbers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
