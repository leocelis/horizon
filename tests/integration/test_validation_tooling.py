"""Smoke tests for the Fix 3/Fix 4 validation tooling scripts.

These exercise the script *logic* (corpus generation, external-corpus adaptation,
and the interventional A/B harness) end to end on tiny inputs so the suite stays
fast. They assert structural correctness, not specific ρ / lift thresholds —
those depend on real labeled data, which these scripts deliberately do not fake.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from horizon import FidelityMonitor

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# ── build_validation_corpus ──────────────────────────────────────────────────


def test_build_validation_corpus_schema(tmp_path: Path) -> None:
    bvc = _load("build_validation_corpus")
    counts = bvc.build(tmp_path, n=6, seed=123)

    assert counts["v1_conversations"] == 6
    for fname in (
        "v1_rated_conversations.jsonl",
        "v5_heldout_conversations.jsonl",
        "v2_conversations.jsonl",
        "v2_labeled_events.jsonl",
    ):
        assert (tmp_path / fname).exists(), f"missing {fname}"

    import json

    v1 = [
        json.loads(ln)
        for ln in (tmp_path / "v1_rated_conversations.jsonl").read_text().splitlines()
    ]
    assert len(v1) == 6
    rec = v1[0]
    assert {"conversation_id", "domain", "turns", "human_rating"} <= set(rec)
    assert 0.0 <= rec["human_rating"] <= 1.0
    assert rec["turns"] and {"human", "agent", "timestamp"} <= set(rec["turns"][0])

    # V1 and V5 domains must be disjoint (V5 is "held out").
    v5 = [
        json.loads(ln)
        for ln in (tmp_path / "v5_heldout_conversations.jsonl").read_text().splitlines()
    ]
    v1_domains = {r["domain"] for r in v1}
    v5_domains = {r["domain"] for r in v5}
    assert v1_domains.isdisjoint(v5_domains)


def test_generated_corpus_is_processable(tmp_path: Path) -> None:
    """A generated conversation must run through the real monitor without error."""
    bvc = _load("build_validation_corpus")
    bvc.build(tmp_path, n=6, seed=7)
    import json

    v1 = [
        json.loads(ln)
        for ln in (tmp_path / "v1_rated_conversations.jsonl").read_text().splitlines()
    ]
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()
    for turn in v1[0]["turns"]:
        result = monitor.process_turn(
            sid, turn["human"], turn["agent"], timestamp=turn["timestamp"]
        )
        assert 0.0 <= result.fidelity_score <= 1.0


# ── adapt_external_corpus ────────────────────────────────────────────────────


def test_extract_messages_formats() -> None:
    aec = _load("adapt_external_corpus")

    sharegpt = {
        "conversations": [{"from": "human", "value": "hi"}, {"from": "gpt", "value": "hello"}]
    }
    openai = {
        "messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    }
    generic = {"turns": [{"human": "hi", "agent": "hello"}]}

    for rec in (sharegpt, openai, generic):
        msgs = aec.extract_messages(rec)
        assert msgs == [("human", "hi"), ("agent", "hello")]


def test_adapt_skips_unrated_and_normalizes_scale() -> None:
    aec = _load("adapt_external_corpus")
    two_turns = [
        {"role": "user", "content": "a"},
        {"role": "assistant", "content": "b"},
        {"role": "user", "content": "c"},
        {"role": "assistant", "content": "d"},
    ]
    records = [
        {"messages": two_turns, "rating": 4.0},
        {"messages": two_turns},  # no rating → skip
        {"conversations": [{"from": "human", "value": "x"}]},  # < 2 turns → skip
    ]
    out, skipped = aec.adapt(records, domain="ext", rating_key="rating", gap_minutes=2)
    assert len(out) == 1
    assert skipped == 2
    # rating 4.0 on a 1-5 scale normalizes to 0.8.
    assert out[0]["human_rating"] == pytest.approx(0.8)
    assert out[0]["domain"] == "ext"
    assert len(out[0]["turns"]) == 2


# ── run_interventional_ab ────────────────────────────────────────────────────


def test_interventional_ab_runs_and_reports() -> None:
    from horizon.analysis.interventional_ab import DEFAULT_ACTIONABLE, run_interventional_ab

    convo = [
        {
            "human": "How do I index this query?",
            "agent_raw": "Add a B-tree index on the filter column.",
            "agent_grounded": None,
            "reference": "Add a B-tree index on the filter column.",
            "timestamp": "2026-01-01T09:00:00+00:00",
        },
        {
            "human": "Still slow on the join.",
            "agent_raw": "Anyway, have you considered switching databases entirely?",
            "agent_grounded": "Index the join keys so the planner can use a hash join.",
            "reference": "Index the join keys so the planner can use a hash join.",
            "timestamp": "2026-01-01T09:03:00+00:00",
        },
    ]
    result = run_interventional_ab([convo], set(DEFAULT_ACTIONABLE))
    assert result["n_conversations"] == 1
    assert result["n_turns"] == 2
    assert "absolute_lift" in result and "relative_lift" in result
    assert set(result["sign_test"]) == {"wins", "losses", "p_value"}
    assert -1.0 <= result["mean_control_outcome"] <= 1.0
    assert -1.0 <= result["mean_treatment_outcome"] <= 1.0


def test_sign_test_math() -> None:
    from horizon.analysis.interventional_ab import sign_test

    wins, losses, p = sign_test([0.1, 0.2, 0.3, 0.4, 0.5])
    assert (wins, losses) == (5, 0)
    assert p < 0.1
    wins, losses, p = sign_test([0.1, -0.1])
    assert (wins, losses) == (1, 1)
    assert p == pytest.approx(1.0)
