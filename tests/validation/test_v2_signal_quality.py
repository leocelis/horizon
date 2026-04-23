"""V2 gate: per-event-type precision / recall.

Gate (from horizon_intent.yaml::constraints[v2_signal_precision_recall]):
  Every event type hits precision >= 0.7 AND recall >= 0.7 on a labeled
  dataset with >= 300 labeled turns per event type across 3+ domains.
"""

from __future__ import annotations

import pytest

from horizon import FidelityMonitor
from tests.validation._helpers import load_jsonl, require_dataset

EVENT_TYPES = (
    "checkpoint.clarification",
    "checkpoint.comprehension",
    "alert.drift",
    "alert.contradiction",
    "alert.verbosity",
    "signal.convergence",
    "signal.optimal_length",
    "signal.horizon_widening",
    "signal.session_reset",
    "signal.temporal_desync",
    "signal.broken_reference",
    "signal.frame_shift",
    "signal.pace_shift",
    "signal.light_cone_collapse",
)


def _precision_recall(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    return precision, recall


def test_per_event_precision_recall() -> None:
    """V2 per-event gate. Skips when the labeled corpus is absent."""
    labels_path = require_dataset("v2_labeled_events.jsonl")
    convos_path = require_dataset("v2_conversations.jsonl")

    labels_by_turn: dict[tuple[str, int, str], bool] = {}
    for rec in load_jsonl(labels_path):
        labels_by_turn[(rec["conversation_id"], int(rec["turn"]), rec["event_type"])] = bool(rec["label"])

    predictions_by_turn: dict[tuple[str, int, str], bool] = {}

    monitor = FidelityMonitor()
    monitor.configure(
        event_modes={etype: "active" for etype in EVENT_TYPES},
    )
    for convo in load_jsonl(convos_path):
        sid = monitor.new_conversation()
        monitor.configure(
            session_id=sid,
            event_modes={etype: "active" for etype in EVENT_TYPES},
        )
        for i, turn in enumerate(convo["turns"], start=1):
            result = monitor.process_turn(
                sid,
                turn["human"],
                turn["agent"],
                timestamp=turn.get("timestamp"),
                client_context=turn.get("client_context"),
            )
            fired = {e.type for e in result.events if e.active}
            for etype in EVENT_TYPES:
                predictions_by_turn[(convo["conversation_id"], i, etype)] = etype in fired

    counts: dict[str, dict[str, int]] = {
        etype: {"tp": 0, "fp": 0, "fn": 0} for etype in EVENT_TYPES
    }
    for key, label in labels_by_turn.items():
        predicted = predictions_by_turn.get(key, False)
        etype = key[2]
        if predicted and label:
            counts[etype]["tp"] += 1
        elif predicted and not label:
            counts[etype]["fp"] += 1
        elif (not predicted) and label:
            counts[etype]["fn"] += 1

    failures: list[str] = []
    for etype, c in counts.items():
        labeled = sum(1 for k, v in labels_by_turn.items() if k[2] == etype)
        if labeled < 300:
            pytest.skip(f"Event {etype} has only {labeled} labels (need 300)")
        p, r = _precision_recall(c["tp"], c["fp"], c["fn"])
        if p < 0.7 or r < 0.7:
            failures.append(f"{etype}: precision={p:.2f}, recall={r:.2f}")

    assert not failures, "V2 gate failures:\n  " + "\n  ".join(failures)
