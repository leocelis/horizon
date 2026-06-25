"""Leading-indicator measurement for Horizon events.

Answers Fix 3's leading-indicator question on real Horizon runs: when an event
fires at turn t, does fidelity degrade in the next k turns (leading), or does the
event only trail a drop that already happened (lagging)? It runs the actual
``FidelityMonitor`` over a corpus, collects each conversation's fidelity
trajectory and event log, and pools them through
``horizon.analysis.leading_indicator``.

This measures *prediction*, not *intervention value*. Whether acting on a leading
event improves outcomes is a separate question answered by
``scripts/run_interventional_ab.py``.

Usage:
  # Against a labeled corpus (v1 schema: conversation_id, domain, turns[], human_rating)
  HORIZON_VALIDATION_DATA=path/to/corpus python scripts/measure_leading_indicator.py

  # Self-contained demo (no external data; synthetic drifting conversations)
  python scripts/measure_leading_indicator.py --demo

  # Tunables
  python scripts/measure_leading_indicator.py --demo --k 3 --drop-threshold 0.05
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horizon import FidelityMonitor
from horizon.analysis import analyze_leading_indicator


def _run_conversation(
    monitor: FidelityMonitor, turns: list[dict]
) -> tuple[list[float], list[tuple[int, str]]]:
    """Process one conversation; return (fidelity_scores, [(turn, event_type), ...])."""
    sid = monitor.new_conversation()
    events: list[tuple[int, str]] = []
    for i, turn in enumerate(turns, start=1):
        result = monitor.process_turn(
            sid,
            turn["human"],
            turn["agent"],
            timestamp=turn.get("timestamp"),
            client_context=turn.get("client_context"),
        )
        for ev in result.events:
            events.append((i, ev.type))
    scores = list(monitor.get_trajectory(sid).scores)
    return scores, events


def _load_corpus(data_dir: Path, filename: str) -> list[list[dict]]:
    path = data_dir / filename
    if not path.exists():
        sys.exit(f"Corpus file not found: {path}")
    conversations: list[list[dict]] = []
    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            conversations.append(rec["turns"])
    return conversations


def _demo_conversations() -> list[list[dict]]:
    """Deterministic synthetic conversations that start coherent and drift.

    Clearly synthetic — used only to exercise the pipeline end to end with no
    external data. The reported numbers describe *these* toy conversations.
    """
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    def ts(turn: int) -> str:
        return (base + timedelta(minutes=2 * turn)).isoformat()

    coherent = [
        (
            "How does Python manage memory?",
            "Python uses reference counting plus a cyclic garbage collector to reclaim unreachable objects.",
        ),
        (
            "What triggers the cyclic collector?",
            "It runs on allocation thresholds across three generations, collecting younger objects more often.",
        ),
        (
            "Can I tune those thresholds?",
            "Yes — gc.set_threshold lets you adjust the generation-0 allocation trigger and the ratios.",
        ),
    ]
    drift = [
        (
            "Anyway, what's a good pasta recipe?",
            "For a quick weeknight pasta, sauté garlic in olive oil, add tomatoes, and toss with spaghetti.",
        ),
        (
            "And the best hiking boots?",
            "Look for waterproof boots with ankle support and a Vibram sole for rough terrain.",
        ),
        (
            "What about stock picks for next quarter?",
            "I can't give financial advice, but diversification and low-cost index funds are common guidance.",
        ),
        (
            "Wait, what were we configuring earlier?",
            "We were discussing something technical, but I've lost the thread — could you remind me?",
        ),
    ]
    convos: list[list[dict]] = []
    for _ in range(8):  # repeat for enough samples to clear the min-samples gate
        turns = []
        seq = coherent + drift
        for t, (h, a) in enumerate(seq, start=1):
            turns.append({"human": h, "agent": a, "timestamp": ts(t)})
        convos.append(turns)
    return convos


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=str, default=os.environ.get("HORIZON_VALIDATION_DATA"))
    parser.add_argument("--filename", type=str, default="v1_rated_conversations.jsonl")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run on synthetic drifting conversations (no external data).",
    )
    parser.add_argument("--k", type=int, default=3, help="Look-ahead window in turns.")
    parser.add_argument("--drop-threshold", type=float, default=0.05)
    parser.add_argument("--min-samples", type=int, default=3)
    parser.add_argument("--out", type=str, default=None, help="Write JSON report to this path.")
    args = parser.parse_args()

    if args.demo:
        source = "synthetic-demo"
        conversations = _demo_conversations()
    elif args.data:
        source = str(Path(args.data) / args.filename)
        conversations = _load_corpus(Path(args.data).expanduser(), args.filename)
    else:
        sys.exit(
            "No data source. Set HORIZON_VALIDATION_DATA (or --data DIR) for a real "
            "corpus, or pass --demo for the synthetic demonstration."
        )

    monitor = FidelityMonitor()
    all_scores: list[list[float]] = []
    all_events: list[list[tuple[int, str]]] = []
    for turns in conversations:
        scores, events = _run_conversation(monitor, turns)
        all_scores.append(scores)
        all_events.append(events)

    report = analyze_leading_indicator(
        all_scores,
        all_events,
        horizon_k=args.k,
        drop_threshold=args.drop_threshold,
        min_samples=args.min_samples,
    )

    out = {
        "source": source,
        "n_conversations": len(conversations),
        "caveat": (
            "Measures whether events PRECEDE fidelity drops (prediction), not whether "
            "acting on them improves outcomes (intervention). Synthetic-demo numbers "
            "describe the toy conversations only."
            if args.demo
            else (
                "Measures whether events PRECEDE fidelity drops (prediction), not whether "
                "acting on them improves outcomes (intervention). Numbers describe the "
                "corpus in source only — report classifications honestly even if lagging "
                "or insufficient-data."
            )
        ),
        **report.to_dict(),
    }
    text = json.dumps(out, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)

    leading = report.leading_events()
    print(
        f"\nLeading-indicator event types ({len(leading)}): {', '.join(leading) or '(none)'}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
