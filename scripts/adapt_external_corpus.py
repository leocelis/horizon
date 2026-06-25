"""Adapt a third-party multi-turn corpus into Horizon's validation schema.

Fix 4 asks for ρ on a corpus Horizon's team did not label. This adapter converts
common external formats into the `v1_rated_conversations.jsonl` schema so the V1
gate (and the OOD gate, tests/validation/test_v6_ood_external.py) can run on
external data.

Supported input record formats (autodetected per line, or via --format):
  * ShareGPT : {"conversations": [{"from": "human"|"gpt", "value": "..."}], ...}
  * OpenAI   : {"messages": [{"role": "user"|"assistant", "content": "..."}], ...}
  * Generic  : {"turns": [{"human": "...", "agent": "..."}], ...}
  * mt-bench-human (parquet): LMSYS MT-Bench expert pairwise judgments
    (lmsys/mt_bench_human_judgments on Hugging Face). Winner/loser mapped to
    high/low human_rating — third-party labels, not Horizon-generated.

A per-conversation quality label is required for correlation (V1/OOD). Provide
its key with --rating-key (default tries human_rating, then rating, then score).
Records without a usable rating are skipped (counted and reported), never invented.

Usage:
  python scripts/adapt_external_corpus.py --in third_party.jsonl \
      --out data/ood_corpus --domain wildchat --rating-key rating

  curl -fsSL -o data/external_raw/mt_bench_human.parquet \\
    'https://huggingface.co/datasets/lmsys/mt_bench_human_judgments/resolve/main/data/human-00000-of-00001-25f4910818759289.parquet'
  python scripts/adapt_external_corpus.py --format mt-bench-human \\
      --in data/external_raw/mt_bench_human.parquet --out data/ood_corpus --domain mt_bench
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

_BASE_TS = datetime(2026, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
_RATING_KEYS = ("human_rating", "rating", "score", "quality")
_WIN_RATING = 0.85
_LOSE_RATING = 0.35


def _pairs_to_turns(messages: list[tuple[str, str]], gap_minutes: int) -> list[dict]:
    """Pair (role, text) messages into {human, agent} turns with synthetic timestamps."""
    turns: list[dict] = []
    pending_human: str | None = None
    t = 0
    for role, text in messages:
        if role == "human":
            pending_human = text
        elif role == "agent" and pending_human is not None:
            t += 1
            turns.append(
                {
                    "human": pending_human,
                    "agent": text,
                    "timestamp": (_BASE_TS + timedelta(minutes=gap_minutes * t)).isoformat(),
                }
            )
            pending_human = None
    return turns


def extract_messages(record: dict) -> list[tuple[str, str]]:
    """Return a normalized [(role, text), ...] from any supported format."""
    if "conversations" in record:  # ShareGPT
        out = []
        for m in record["conversations"]:
            role = "human" if m.get("from") in ("human", "user") else "agent"
            out.append((role, str(m.get("value", ""))))
        return out
    if "messages" in record:  # OpenAI
        out = []
        for m in record["messages"]:
            role = "human" if m.get("role") in ("user", "human") else "agent"
            out.append((role, str(m.get("content", ""))))
        return out
    if "turns" in record:  # Generic Horizon-style
        out = []
        for turn in record["turns"]:
            if "human" in turn:
                out.append(("human", str(turn["human"])))
            if "agent" in turn:
                out.append(("agent", str(turn["agent"])))
        return out
    return []


def _messages_from_openai_list(messages: list[dict]) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for m in messages:
        role = "human" if m.get("role") in ("user", "human") else "agent"
        out.append((role, str(m.get("content", ""))))
    return out


def load_mt_bench_human_parquet(path: Path) -> list[dict]:
    """Expand LMSYS MT-Bench pairwise judgments into rated generic records."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SystemExit(
            "MT-Bench parquet requires pyarrow. Install with: pip install pyarrow"
        ) from exc

    table = pq.read_table(path)
    records: list[dict] = []
    for i in range(table.num_rows):
        winner = table.column("winner")[i].as_py()
        if winner not in ("model_a", "model_b"):
            continue
        qid = table.column("question_id")[i].as_py()
        turn = table.column("turn")[i].as_py()
        model_a = table.column("model_a")[i].as_py()
        model_b = table.column("model_b")[i].as_py()
        conv_a = table.column("conversation_a")[i].as_py()
        conv_b = table.column("conversation_b")[i].as_py()
        records.append(
            {
                "id": f"mt-{qid}-t{turn}-a",
                "messages": [{"role": m["role"], "content": m["content"]} for m in conv_a],
                "human_rating": _WIN_RATING if winner == "model_a" else _LOSE_RATING,
                "domain": f"mt_bench/{model_a}",
            }
        )
        records.append(
            {
                "id": f"mt-{qid}-t{turn}-b",
                "messages": [{"role": m["role"], "content": m["content"]} for m in conv_b],
                "human_rating": _WIN_RATING if winner == "model_b" else _LOSE_RATING,
                "domain": f"mt_bench/{model_b}",
            }
        )
    return records


def _extract_rating(record: dict, rating_key: str | None) -> float | None:
    keys = (rating_key,) if rating_key else _RATING_KEYS
    for key in keys:
        if key and key in record and record[key] is not None:
            try:
                return float(record[key])
            except (TypeError, ValueError):
                return None
    return None


def adapt(
    records: list[dict], domain: str, rating_key: str | None, gap_minutes: int
) -> tuple[list[dict], int]:
    """Convert records; return (v1_records, n_skipped)."""
    out: list[dict] = []
    skipped = 0
    for i, rec in enumerate(records):
        rating = _extract_rating(rec, rating_key)
        messages = extract_messages(rec)
        if not messages and "messages" in rec:
            messages = _messages_from_openai_list(rec["messages"])
        turns = _pairs_to_turns(messages, gap_minutes)
        if rating is None or len(turns) < 2:
            skipped += 1
            continue
        # Normalize a 1-5 / 1-10 scale into [0, 1] if it looks out of range.
        norm = rating
        if rating > 1.0:
            norm = rating / 5.0 if rating <= 5.0 else rating / 10.0
        rec_domain = rec.get("domain", domain)
        out.append(
            {
                "conversation_id": rec.get("id", f"{domain}-{i:05d}"),
                "domain": rec_domain,
                "turns": turns,
                "human_rating": round(min(1.0, max(0.0, norm)), 4),
            }
        )
    return out, skipped


def load_records(infile: Path, fmt: str | None) -> list[dict]:
    if fmt == "mt-bench-human" or (fmt is None and infile.suffix == ".parquet"):
        return load_mt_bench_human_parquet(infile)
    records: list[dict] = []
    with infile.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in", dest="infile", required=True)
    parser.add_argument("--out", required=True, help="Output directory.")
    parser.add_argument(
        "--format",
        choices=("auto", "jsonl", "mt-bench-human"),
        default="auto",
        help="Input format (default: auto — parquet → mt-bench-human, else jsonl).",
    )
    parser.add_argument("--domain", default="external")
    parser.add_argument("--rating-key", default=None)
    parser.add_argument("--gap-minutes", type=int, default=3)
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max conversations to write (after filtering). Useful for faster validation runs.",
    )
    parser.add_argument(
        "--out-filename",
        default="ood_rated_conversations.jsonl",
        help="Filename the OOD gate reads (HORIZON_OOD_DATA/<this>).",
    )
    args = parser.parse_args()

    infile = Path(args.infile).expanduser()
    fmt = args.format
    if fmt == "auto":
        fmt = "mt-bench-human" if infile.suffix == ".parquet" else "jsonl"
    records = load_records(infile, fmt if fmt != "jsonl" else None)
    v1, skipped = adapt(records, args.domain, args.rating_key, args.gap_minutes)
    if args.limit is not None:
        v1 = v1[: args.limit]
    out_dir = Path(args.out).expanduser()
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / args.out_filename
    with out_path.open("w", encoding="utf-8") as fh:
        for rec in v1:
            fh.write(json.dumps(rec) + "\n")

    print(f"Wrote {len(v1)} conversations to {out_path}")
    print(f"Skipped {skipped} records (missing rating or < 2 turns).")
    if v1:
        print(
            f"\nRun the OOD gate:\n  HORIZON_OOD_DATA={out_dir} "
            f"python -m pytest tests/validation/test_v6_ood_external.py -q -s"
        )
        print(
            f"\nLeading indicator (Fix 3):\n  HORIZON_VALIDATION_DATA={out_dir} "
            f"python scripts/measure_leading_indicator.py "
            f"--filename {args.out_filename} --out docs/reviews/leading_indicator.json"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
