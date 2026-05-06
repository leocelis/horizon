"""V1 stability across embedding backends.

Re-runs the V1 proxy-correlation pipeline with multiple sentence-transformer
backends and reports Spearman ρ stability. Closes the v0.2.0 audit gap
"embedding-model lock-in unvalidated" — measures whether Horizon's fidelity
score remains correlated with human ratings when the embedding backend
changes.

Usage:
  HORIZON_VALIDATION_DATA=ada/playground/horizon/data/horizon_validation_corpus_v1 \
      python scripts/measure_embedding_stability.py

The corpus files are git-ignored runtime data — point ``HORIZON_VALIDATION_DATA``
at the directory produced by ``ada/playground/horizon/build_validation_corpus.py``.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from horizon import Config, FidelityMonitor

# Local-only sentence-transformers backends — no network at inference time
# beyond the initial model download. Each is downloaded once and cached.
DEFAULT_BACKENDS = [
    "all-MiniLM-L6-v2",   # default; 22 M params, 384-d, 80 MB
    "all-MiniLM-L12-v2",  # deeper variant; 33 M params, 384-d, 120 MB
    "all-mpnet-base-v2",  # higher-quality reference; 110 M params, 768-d, 420 MB
]


@dataclass
class BackendResult:
    backend: str
    rho_conv: float
    rho_turn: float
    n_conv: int
    n_turn: int
    domains: list[str]
    seconds: float


def _spearman(xs: list[float], ys: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    rx = np.argsort(np.argsort(xs))
    ry = np.argsort(np.argsort(ys))
    d = rx - ry
    n = len(xs)
    return 1.0 - (6.0 * float((d * d).sum())) / (n * (n * n - 1))


def _load_corpus(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _run_v1(monitor: FidelityMonitor, conversations: list[dict]) -> tuple[float, float, int, int, list[str]]:
    per_turn_fidelity: list[float] = []
    per_turn_rating: list[float] = []
    per_conv_fidelity: list[float] = []
    per_conv_rating: list[float] = []
    domains: set[str] = set()

    for convo in conversations:
        sid = monitor.new_conversation()
        domains.add(convo.get("domain", "unknown"))
        scores: list[float] = []
        ratings = convo.get("turn_ratings", [])

        for turn in convo["turns"]:
            r = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            scores.append(r.fidelity_score)

        if ratings and len(ratings) == len(scores):
            per_turn_fidelity.extend(scores)
            per_turn_rating.extend(ratings)

        if scores:
            per_conv_fidelity.append(sum(scores) / len(scores))
            per_conv_rating.append(float(convo["human_rating"]))

    rho_conv = _spearman(per_conv_fidelity, per_conv_rating)
    rho_turn = (
        _spearman(per_turn_fidelity, per_turn_rating)
        if per_turn_fidelity
        else 0.0
    )
    return rho_conv, rho_turn, len(per_conv_fidelity), len(per_turn_fidelity), sorted(domains)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backends",
        nargs="+",
        default=DEFAULT_BACKENDS,
        help="Sentence-transformers model slugs to evaluate",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Cap on conversations (0 = full corpus)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output path",
    )
    args = parser.parse_args(argv)

    env = os.environ.get("HORIZON_VALIDATION_DATA")
    if not env:
        print("HORIZON_VALIDATION_DATA not set", file=sys.stderr)
        return 2
    corpus_path = Path(env).expanduser() / "v1_rated_conversations.jsonl"
    if not corpus_path.exists():
        print(f"corpus missing: {corpus_path}", file=sys.stderr)
        return 2

    conversations = _load_corpus(corpus_path)
    if args.limit:
        conversations = conversations[: args.limit]

    print(f"V1 cross-embedding stability — {len(conversations)} conversations")
    print(f"Backends: {args.backends}")
    print()

    results: list[BackendResult] = []
    for backend in args.backends:
        print(f"  • {backend} … ", end="", flush=True)
        t0 = time.time()
        monitor = FidelityMonitor(config=Config(embedding_model=backend))
        rho_conv, rho_turn, n_conv, n_turn, domains = _run_v1(monitor, conversations)
        elapsed = time.time() - t0
        results.append(
            BackendResult(
                backend=backend,
                rho_conv=rho_conv,
                rho_turn=rho_turn,
                n_conv=n_conv,
                n_turn=n_turn,
                domains=domains,
                seconds=elapsed,
            )
        )
        print(
            f"rho_conv={rho_conv:.3f}  rho_turn={rho_turn:.3f}  "
            f"({n_conv} convs / {n_turn} turns / {elapsed:.1f}s)"
        )

    print()
    print("Summary")
    print("-------")
    print(f"{'backend':<24} {'rho_conv':>10} {'rho_turn':>10} {'time(s)':>10}")
    for r in results:
        print(
            f"{r.backend:<24} {r.rho_conv:>10.3f} {r.rho_turn:>10.3f} {r.seconds:>10.1f}"
        )

    rho_convs = [r.rho_conv for r in results]
    rho_turns = [r.rho_turn for r in results]
    print()
    print(f"rho_conv  : min={min(rho_convs):.3f}  max={max(rho_convs):.3f}  spread={max(rho_convs)-min(rho_convs):.3f}")
    print(f"rho_turn  : min={min(rho_turns):.3f}  max={max(rho_turns):.3f}  spread={max(rho_turns)-min(rho_turns):.3f}")
    print()

    # Gate-style verdict — every backend must clear V1 thresholds and the
    # spread must be small enough that swapping backends doesn't break the
    # gate.
    pass_v1 = all(r.rho_conv >= 0.6 and r.rho_turn >= 0.5 for r in results)
    spread_ok = (max(rho_convs) - min(rho_convs)) <= 0.15 and (max(rho_turns) - min(rho_turns)) <= 0.15
    verdict = "STABLE" if (pass_v1 and spread_ok) else "UNSTABLE"
    print(f"Verdict: {verdict}  (V1 gate met by every backend AND spread <= 0.15)")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "n_conversations": len(conversations),
                    "results": [r.__dict__ for r in results],
                    "rho_conv_spread": max(rho_convs) - min(rho_convs),
                    "rho_turn_spread": max(rho_turns) - min(rho_turns),
                    "verdict": verdict,
                },
                indent=2,
            )
        )
        print(f"\nWrote {args.output}")

    return 0 if verdict == "STABLE" else 1


if __name__ == "__main__":
    sys.exit(main())
