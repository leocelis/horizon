"""Per-event heuristic baseline vs Horizon on the V2 corpus.

Closes the v0.2.0 audit gap "no competitive benchmark vs prompt-engineering
mitigation" for the *per-event* dimension. v0.1's V3 gate compared the
single fidelity score to a length-based heuristic for *contradiction
detection* only. This script extends that comparison to all 16 event
types — for each event, a hand-rolled regex/heuristic detector tries to
fire on the same V2-labelled turns Horizon's engines see.

For each event we report:
  - Horizon  : (precision, recall) on the same labels (re-measured here).
  - Baseline : (precision, recall) of the heuristic detector.
  - Lift     : Horizon-(P+R) / Baseline-(P+R).

Usage:
  HORIZON_VALIDATION_DATA=ada/playground/horizon/data/horizon_validation_corpus_v1 \
      python scripts/measure_heuristic_baseline.py
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from horizon import FidelityMonitor

# ── Heuristic baselines ──────────────────────────────────────────────────────
#
# Each baseline is a callable that takes a *full conversation context* up to
# and including the current turn and returns a bool. Inputs available:
#
#   turn_idx           : 1-indexed position of the current turn.
#   human, agent       : raw text of the current turn.
#   prev_human, prev_agent : raw text of the previous turn (None on turn 1).
#   gap_seconds        : seconds since the previous turn (None on turn 1).
#   prev_gap_seconds   : gap between turns N-1 and N-2 (None when undefined).
#   client_context     : optional dict from the corpus turn record.
#   prev_context       : client_context of the previous turn.
#
# These are *deliberately simple* — the baseline is "what could a smart
# engineer ship in an afternoon with regex + counts + timestamps"? If
# Horizon doesn't beat that, the engines aren't earning their keep.

WORD_RE = re.compile(r"\b\w+\b")


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in WORD_RE.findall(text or "")}


def _word_count(text: str) -> int:
    return len(WORD_RE.findall(text or ""))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not (ta or tb):
        return 1.0
    return len(ta & tb) / len(ta | tb)


# Keyword bags --------------------------------------------------------------

CLARIFY_HINTS = re.compile(
    r"\b(what|why|how|when|where|which|who|could you|can you|do you mean|"
    r"clarify|specifically|in particular)\b",
    re.IGNORECASE,
)
RECAP_HINTS = re.compile(
    r"\b(in summary|to summarise|to summarize|to recap|so to confirm|"
    r"got it|understood|so you('re| are) saying)\b",
    re.IGNORECASE,
)
CONTRADICT_HINTS = re.compile(
    r"\b(actually|never mind|scratch that|on second thought|i was wrong|"
    r"contrary to what|let me correct)\b",
    re.IGNORECASE,
)
SHORT_REPLY_HINTS = re.compile(
    r"^\s*(ok|okay|thanks|thank you|sounds good|got it|cool|yes|yep|yeah|"
    r"no|nope|sure|done)[\s.!?]*$",
    re.IGNORECASE,
)
DEFER_HINTS = re.compile(
    r"\b(let me know|tell me when|report back|try it|test it|run it|when "
    r"you('re| are) done|come back|once you|after you)\b",
    re.IGNORECASE,
)
COMPLETION_HINTS = re.compile(
    r"\b(done|tried|ran|tested|finished|completed)\b",
    re.IGNORECASE,
)
REFERENCE_HINTS = re.compile(
    r"\b(the .* you (mentioned|said|wrote|referenced)|earlier you|previously you|"
    r"as you said|going back to)\b",
    re.IGNORECASE,
)
GROUNDING_HINTS = re.compile(
    r"\b\d{4}\b|\b\d+(\.\d+)?%|\$\d+|\bversion \d|\bRFC \d|\bAPI key\b|"
    r"\b(largest|smallest|fastest|slowest|first|only)\b",
    re.IGNORECASE,
)


@dataclass
class BaselineCtx:
    turn_idx: int
    human: str
    agent: str
    prev_human: str | None
    prev_agent: str | None
    gap_seconds: float | None
    prev_gap_seconds: float | None
    client_context: dict | None
    prev_context: dict | None
    history_humans: list[str]
    history_agents: list[str]


def b_clarification(c: BaselineCtx) -> bool:
    return bool(c.agent and "?" in c.agent and CLARIFY_HINTS.search(c.agent))


def b_comprehension(c: BaselineCtx) -> bool:
    return bool(c.agent and RECAP_HINTS.search(c.agent))


def b_drift(c: BaselineCtx) -> bool:
    if c.prev_agent is None:
        return False
    # very different topic words from the prior agent reply
    return _jaccard(c.agent, c.prev_agent) < 0.10


def b_contradiction(c: BaselineCtx) -> bool:
    if c.agent and CONTRADICT_HINTS.search(c.agent):
        return True
    # disagreement marker: agent says "no" / "incorrect" near user's claim
    return bool(re.search(r"\b(no,|incorrect|that's wrong|not quite)\b", c.agent or "", re.IGNORECASE))


def b_verbosity(c: BaselineCtx) -> bool:
    return _word_count(c.agent) > 200


def b_convergence(c: BaselineCtx) -> bool:
    if c.turn_idx < 3:
        return False
    last_three = c.history_humans[-3:] + [c.human]
    last_three = last_three[-3:]
    return all(SHORT_REPLY_HINTS.match(h or "") for h in last_three)


def b_optimal_length(c: BaselineCtx) -> bool:
    return c.turn_idx >= 8


def b_horizon_widening(c: BaselineCtx) -> bool:
    if c.prev_agent is None:
        return False
    new_terms = _tokens(c.agent) - _tokens(c.prev_agent)
    return len(new_terms) >= 25


def b_session_reset(c: BaselineCtx) -> bool:
    return c.turn_idx > 25


def b_temporal_desync(c: BaselineCtx) -> bool:
    return bool(c.gap_seconds and c.gap_seconds > 3600)


def b_broken_reference(c: BaselineCtx) -> bool:
    return bool(c.human and REFERENCE_HINTS.search(c.human)) and c.turn_idx > 5


def b_frame_shift(c: BaselineCtx) -> bool:
    if not (c.client_context and c.prev_context):
        return False
    keys = ("device_type", "location_class", "timezone")
    return any(c.client_context.get(k) != c.prev_context.get(k) for k in keys)


def b_pace_shift(c: BaselineCtx) -> bool:
    if c.gap_seconds is None or c.prev_gap_seconds is None:
        return False
    if c.prev_gap_seconds <= 0:
        return False
    ratio = c.gap_seconds / c.prev_gap_seconds
    return ratio > 4 or ratio < 0.25


def b_light_cone_collapse(c: BaselineCtx) -> bool:
    return c.turn_idx > 5 and bool(c.gap_seconds and c.gap_seconds > 86400)


def b_grounding_required(c: BaselineCtx) -> bool:
    return bool(c.agent and GROUNDING_HINTS.search(c.agent))


def b_pace_premature_report(c: BaselineCtx) -> bool:
    if not (c.prev_agent and DEFER_HINTS.search(c.prev_agent)):
        return False
    if c.gap_seconds is None or c.gap_seconds > 30:
        return False
    return not (c.human and COMPLETION_HINTS.search(c.human))


HEURISTIC: dict[str, Callable[[BaselineCtx], bool]] = {
    "checkpoint.clarification": b_clarification,
    "checkpoint.comprehension": b_comprehension,
    "alert.drift": b_drift,
    "alert.contradiction": b_contradiction,
    "alert.verbosity": b_verbosity,
    "signal.convergence": b_convergence,
    "signal.optimal_length": b_optimal_length,
    "signal.horizon_widening": b_horizon_widening,
    "signal.session_reset": b_session_reset,
    "signal.temporal_desync": b_temporal_desync,
    "signal.broken_reference": b_broken_reference,
    "signal.frame_shift": b_frame_shift,
    "signal.pace_shift": b_pace_shift,
    "signal.light_cone_collapse": b_light_cone_collapse,
    "signal.grounding_required": b_grounding_required,
    "signal.pace_premature_report": b_pace_premature_report,
}

EVENT_TYPES = tuple(HEURISTIC.keys())


# ── I/O helpers ──────────────────────────────────────────────────────────────


def _load_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _gap_seconds(ts: str | None, prev_ts: str | None) -> float | None:
    if not (ts and prev_ts):
        return None
    try:
        a = datetime.fromisoformat(ts)
        b = datetime.fromisoformat(prev_ts)
        return (a - b).total_seconds()
    except ValueError:
        return None


def _build_baseline_predictions(
    convos: list[dict],
) -> dict[tuple[str, int, str], bool]:
    out: dict[tuple[str, int, str], bool] = {}
    for convo in convos:
        cid = convo["conversation_id"]
        history_h: list[str] = []
        history_a: list[str] = []
        prev_ts: str | None = None
        prev_gap: float | None = None
        prev_ctx: dict | None = None
        for i, turn in enumerate(convo["turns"], start=1):
            ts = turn.get("timestamp")
            gap = _gap_seconds(ts, prev_ts)
            ctx = turn.get("client_context")
            bctx = BaselineCtx(
                turn_idx=i,
                human=turn["human"],
                agent=turn["agent"],
                prev_human=history_h[-1] if history_h else None,
                prev_agent=history_a[-1] if history_a else None,
                gap_seconds=gap,
                prev_gap_seconds=prev_gap,
                client_context=ctx,
                prev_context=prev_ctx,
                history_humans=list(history_h),
                history_agents=list(history_a),
            )
            for etype, fn in HEURISTIC.items():
                try:
                    out[(cid, i, etype)] = bool(fn(bctx))
                except Exception:
                    out[(cid, i, etype)] = False
            history_h.append(turn["human"])
            history_a.append(turn["agent"])
            prev_gap = gap
            prev_ts = ts
            prev_ctx = ctx
    return out


def _build_horizon_predictions(
    convos: list[dict],
) -> dict[tuple[str, int, str], bool]:
    monitor = FidelityMonitor()
    monitor.configure(event_modes={e: "active" for e in EVENT_TYPES})
    out: dict[tuple[str, int, str], bool] = {}
    for convo in convos:
        sid = monitor.new_conversation(metadata=convo.get("metadata"))
        monitor.configure(
            session_id=sid,
            event_modes={e: "active" for e in EVENT_TYPES},
        )
        for i, turn in enumerate(convo["turns"], start=1):
            r = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            fired = {e.type for e in r.events if e.active}
            for etype in EVENT_TYPES:
                out[(convo["conversation_id"], i, etype)] = etype in fired
    return out


def _pr(tp: int, fp: int, fn: int) -> tuple[float, float]:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    return p, r


def _score(
    labels: dict[tuple[str, int, str], bool],
    preds: dict[tuple[str, int, str], bool],
) -> dict[str, tuple[float, float, int]]:
    counts: dict[str, dict[str, int]] = {
        e: {"tp": 0, "fp": 0, "fn": 0, "n": 0} for e in EVENT_TYPES
    }
    for key, label in labels.items():
        etype = key[2]
        if etype not in counts:
            continue
        counts[etype]["n"] += 1
        predicted = preds.get(key, False)
        if predicted and label:
            counts[etype]["tp"] += 1
        elif predicted and not label:
            counts[etype]["fp"] += 1
        elif (not predicted) and label:
            counts[etype]["fn"] += 1
    return {
        e: (*_pr(c["tp"], c["fp"], c["fn"]), c["n"]) for e, c in counts.items()
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=0, help="Cap on conversations (0 = full)")
    parser.add_argument(
        "--per-event-limit",
        type=int,
        default=0,
        help="Sample at most N conversations per event_type (balanced sampling). "
             "Set this to get statistically meaningful per-event metrics in a "
             "fraction of the full-corpus runtime.",
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)

    env = os.environ.get("HORIZON_VALIDATION_DATA")
    if not env:
        print("HORIZON_VALIDATION_DATA not set", file=sys.stderr)
        return 2
    root = Path(env).expanduser()

    labels_records = _load_jsonl(root / "v2_labeled_events.jsonl")
    convos = _load_jsonl(root / "v2_conversations.jsonl")

    if args.per_event_limit:
        # Balanced sampling: keep at most N conversations per event_type so
        # every event gets equal statistical weight. The corpus naming
        # convention is "v2-<event_type>-<idx>-<pos|neg>".
        keep_counts: dict[str, int] = {e: 0 for e in EVENT_TYPES}
        balanced: list[dict] = []
        for c in convos:
            cid = c["conversation_id"]
            for etype in EVENT_TYPES:
                if cid.startswith(f"v2-{etype}-"):
                    if keep_counts[etype] < args.per_event_limit:
                        balanced.append(c)
                        keep_counts[etype] += 1
                    break
        convos = balanced
        ids_kept = {c["conversation_id"] for c in convos}
    elif args.limit:
        ids_kept = {c["conversation_id"] for c in convos[: args.limit]}
        convos = convos[: args.limit]
    else:
        ids_kept = {c["conversation_id"] for c in convos}

    labels: dict[tuple[str, int, str], bool] = {
        (rec["conversation_id"], int(rec["turn"]), rec["event_type"]): bool(rec["label"])
        for rec in labels_records
        if rec["conversation_id"] in ids_kept
    }

    print(f"Per-event heuristic baseline vs Horizon — {len(convos)} conversations, {len(labels)} labels")
    print()

    print("Running heuristic baseline …", flush=True)
    baseline_preds = _build_baseline_predictions(convos)
    baseline_scores = _score(labels, baseline_preds)

    print("Running Horizon (this is the slow one) …", flush=True)
    horizon_preds = _build_horizon_predictions(convos)
    horizon_scores = _score(labels, horizon_preds)

    print()
    header = f"{'event':<32} {'horizon P':>10} {'horizon R':>10} {'base P':>8} {'base R':>8} {'lift':>8} {'N':>6}"
    print(header)
    print("-" * len(header))

    summary: dict[str, dict] = {}
    horizon_wins = 0
    for etype in EVENT_TYPES:
        hp, hr, n = horizon_scores[etype]
        bp, br, _ = baseline_scores[etype]
        h_sum = hp + hr
        b_sum = bp + br
        lift = (h_sum - b_sum) / b_sum if b_sum > 0 else float("inf")
        summary[etype] = {
            "horizon_precision": hp,
            "horizon_recall": hr,
            "baseline_precision": bp,
            "baseline_recall": br,
            "lift_relative": None if b_sum == 0 else lift,
            "n_labels": n,
        }
        if h_sum > b_sum:
            horizon_wins += 1
        lift_str = "inf" if b_sum == 0 else f"{lift*100:+.0f}%"
        print(f"{etype:<32} {hp:>10.2f} {hr:>10.2f} {bp:>8.2f} {br:>8.2f} {lift_str:>8} {n:>6}")

    print()
    print(f"Horizon beats baseline on {horizon_wins} / {len(EVENT_TYPES)} event types (P+R sum).")

    # Macro averages
    macro_h_p = sum(horizon_scores[e][0] for e in EVENT_TYPES) / len(EVENT_TYPES)
    macro_h_r = sum(horizon_scores[e][1] for e in EVENT_TYPES) / len(EVENT_TYPES)
    macro_b_p = sum(baseline_scores[e][0] for e in EVENT_TYPES) / len(EVENT_TYPES)
    macro_b_r = sum(baseline_scores[e][1] for e in EVENT_TYPES) / len(EVENT_TYPES)
    print(f"Macro avg — horizon P/R = {macro_h_p:.2f}/{macro_h_r:.2f}, baseline P/R = {macro_b_p:.2f}/{macro_b_r:.2f}")

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(
                {
                    "n_conversations": len(convos),
                    "n_labels": len(labels),
                    "per_event": summary,
                    "macro": {
                        "horizon_precision": macro_h_p,
                        "horizon_recall": macro_h_r,
                        "baseline_precision": macro_b_p,
                        "baseline_recall": macro_b_r,
                    },
                    "horizon_wins": horizon_wins,
                    "n_events": len(EVENT_TYPES),
                },
                indent=2,
            )
        )
        print(f"\nWrote {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
