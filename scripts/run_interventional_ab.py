"""Interventional A/B CLI — thin wrapper over horizon.analysis.interventional_ab.

Usage:
  python scripts/run_interventional_ab.py --demo
  python scripts/run_interventional_ab.py --corpus path/to/ab_corpus.jsonl --out ab.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from horizon.analysis.interventional_ab import DEFAULT_ACTIONABLE, run_interventional_ab


def _demo_conversations() -> list[list[dict]]:
    base = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)

    def ts(t: int) -> str:
        return (base + timedelta(minutes=3 * t)).isoformat()

    template = [
        (
            "How do I add an index to speed up this query?",
            "Add a B-tree index on the filtered column; it turns the scan into a logarithmic lookup.",
            None,
            "Add a B-tree index on the filtered column to turn the scan into a logarithmic lookup.",
        ),
        (
            "It's still slow on the join.",
            "Index the join keys on both tables so the planner can use a merge or hash join.",
            None,
            "Index the join keys on both tables so the planner can use a merge or hash join.",
        ),
        (
            "Now writes feel slower though.",
            "Anyway, have you considered switching to a NoSQL database entirely?",
            "Right — every index adds write cost; drop unused indexes and keep only the join/filter ones.",
            "Every index adds write overhead; keep only the indexes the join and filter queries need.",
        ),
        (
            "So which indexes do I actually keep?",
            "Honestly it depends, maybe try caching or a CDN for performance.",
            "Keep the index on the filtered column and the join keys; drop the rest to cut write cost.",
            "Keep the filter-column index and the join-key indexes; drop the others to reduce write cost.",
        ),
        (
            "Can you summarize the plan?",
            "We talked about a few things — databases, caching, lots of options really.",
            "Plan: index the filter column and join keys, drop unused indexes to protect write speed.",
            "Plan: index the filter column and the join keys, and drop unused indexes to protect writes.",
        ),
    ]
    return [
        [
            {
                "human": h,
                "agent_raw": raw,
                "agent_grounded": grounded,
                "reference": ref,
                "timestamp": ts(i + 1),
            }
            for i, (h, raw, grounded, ref) in enumerate(template)
        ]
        for _ in range(6)
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true")
    parser.add_argument(
        "--corpus",
        type=str,
        default=None,
        help="JSONL; each line {turns:[{human,agent_raw,agent_grounded,reference,timestamp}]}.",
    )
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    if args.demo:
        conversations = _demo_conversations()
        source = "synthetic-demo"
    elif args.corpus:
        conversations = []
        with Path(args.corpus).expanduser().open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    conversations.append(json.loads(line)["turns"])
        source = args.corpus
    else:
        sys.exit("Provide --demo or --corpus PATH.")

    result = run_interventional_ab(conversations, set(DEFAULT_ACTIONABLE))
    result["source"] = source
    result["caveat"] = (
        "Synthetic-demo lift demonstrates the mechanism only, not a production "
        "result. A defensible outcome claim requires a real, independent corpus."
    )
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).expanduser().write_text(text, encoding="utf-8")
        print(f"Wrote {args.out}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
