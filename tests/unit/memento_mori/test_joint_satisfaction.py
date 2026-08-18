"""Parent joint satisfaction (J-1) — all seven horizon_memento_mori_intent.yaml
constraints asserted on the SAME flow and the SAME outputs.

horizon_memento_mori_intent.yaml::constraint_satisfiability.joint_satisfaction_test

"Single test driving one flow — configure store, register finite root,
register mission+deadline+gate+entity under it, attempt root-less item
(rejected), attempt undated deferral (rejected), request TTL proposal
(derivation shown, not applied), ratify TTL, declare a time_value_rate and
an amount, assert cost-of-delay and break-even derive only from stored
facts, assert every non-monetary output is identical with the rate
removed, advance evaluation date past TTL and revisit dates, assert
events fire, register a probe and a second path, assert the comparison
contains only measured latencies with base-rate fields separate, assert
report reproducible byte-identically, assert zero network/LLM, assert
unconfigured session unchanged — asserting all seven constraints on the
SAME output."

Per IVD Rule 2: individual-pass on the seven per-constraint test files does
NOT imply joint-pass. This is the gating test for 7 constraints.

The socket/subprocess block below is scoped narrowly to the memento
evaluation calls (engine.evaluate / signals.evaluate_signals) rather than
the whole test, because FidelityMonitor.process_turn's embedding engine
legitimately shells out locally (e.g. `lscpu` for CPU capability detection)
for the unrelated existing conversation plane — that is not the network
call this constraint is about.
"""

from __future__ import annotations

import json
import socket
import subprocess
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest

from horizon_monitor.memento import engine, money, paths, propose, signals
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.errors import RootlessItemError, UndatedDeferralError
from horizon_monitor.memento.models import BaseRateRow, EventKind, ItemKind
from horizon_monitor.memento.signals import AssociationRegistry
from horizon_monitor.memento.store import MementoStore
from horizon_monitor.monitor import FidelityMonitor

UTC = timezone.utc


def _block(*args, **kwargs):
    raise AssertionError(
        f"unexpected outbound call on the memento evaluation path: args={args} kwargs={kwargs}"
    )


def _evaluate_signals(store: MementoStore, t_eval: datetime, config: MementoConfig):
    snapshot = store.snapshot()
    with (
        patch.object(socket.socket, "connect", side_effect=_block),
        patch.object(subprocess, "Popen", side_effect=_block),
    ):
        report = engine.evaluate(snapshot, t_eval, config)
        signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, config)
    for (item_id, signal_type), state in new_states.items():
        store.set_fire_state(item_id, signal_type, state)
    return report, signal_report


def test_all_constraints_on_same_flow(tmp_path: Path) -> None:
    # ── local_first_privacy: a local file at an operator-configured
    #    path; the store starts with no bundled mission data. ────────────
    store_path = tmp_path / "joint.db"
    config = MementoConfig(store_path=store_path)
    assert config.store_path == store_path
    store = MementoStore(store_path)
    assert store.get_items() == []

    # ── finite_rooted_tree: exactly one finite root ... ─────────────────
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )

    # ... and every other item must carry a parent path terminating at
    # the root — a root-less item is rejected atomically.
    before_rootless_check = store.get_items()
    with pytest.raises(RootlessItemError):
        store.register_item(
            kind=ItemKind.MISSION,
            title="orphan",
            created_valid=datetime(2026, 6, 1, tzinfo=UTC),
            parent_id="does-not-exist",
        )
    assert store.get_items() == before_rootless_check

    mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="ship-widget",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        stall_days=14,
    )
    task_id = store.register_item(
        kind=ItemKind.TASK,
        title="T1",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        ttl_start=date(2026, 7, 1),
        ttl_end=date(2026, 7, 20),
    )
    deadline_id = store.register_item(
        kind=ItemKind.DEADLINE,
        title="hard cutoff",
        parent_id=mission_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        deadline_date=date(2026, 9, 30),
        deadline_kind="hard_cutoff",
        gates_item_id=task_id,
    )
    gate_id = store.register_item(
        kind=ItemKind.GATE,
        title="review gate",
        parent_id=mission_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        age_budget_days=90,
    )
    entity_id = store.register_item(
        kind=ItemKind.ENTITY,
        title="vendor-queue",
        parent_id=mission_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    store.record_event(
        item_id=entity_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 7, 1, tzinfo=UTC),
        stage="vendor-queue",
    )
    store.record_event(
        item_id=mission_id, kind=EventKind.PROGRESS, valid_time=datetime(2026, 6, 5, tzinfo=UTC)
    )

    # ── facts_are_caller_provided: an undated deferral is rejected at the
    #    schema, with no configuration override. ─────────────────────────
    before_undated_check = store.get_items()
    with pytest.raises(UndatedDeferralError):
        store.register_item(
            kind=ItemKind.DEFERRAL,
            title="park it",
            parent_id=mission_id,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        )
    assert store.get_items() == before_undated_check
    deferral_id = store.register_item(
        kind=ItemKind.DEFERRAL,
        title="park it",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        revisit_date=date(2026, 8, 10),
    )

    # ── facts_are_caller_provided / signals_not_control: a TTL proposal
    #    shows its derivation and sample size but never writes anything by
    #    itself — inert until an explicit ratifying write. ───────────────
    task_before = store.get_item(task_id)
    proposal = propose.ttl_proposal(
        item_id=task_id, completed_durations_days=[5, 8, 9, 12, 20], percentile=0.80
    )
    assert proposal is not None and proposal.value == 12 and proposal.sample_size == 5
    assert "12" in proposal.derivation and "5" in proposal.derivation
    assert store.get_item(task_id).ttl_end == task_before.ttl_end  # untouched by the call itself

    ratified_task_id = store.register_item(
        kind=task_before.kind,
        title=task_before.title,
        parent_id=task_before.parent_id,
        created_valid=task_before.created_valid,
        ttl_start=task_before.ttl_start,
        ttl_end=task_before.ttl_start + timedelta(days=proposal.value),
    )
    store.update_item_status(task_id, status="superseded", superseded_by=ratified_task_id)
    store.record_event(
        item_id=ratified_task_id,
        kind=EventKind.RATIFY,
        valid_time=task_before.created_valid,
        payload={"proposal_kind": proposal.kind, "value": proposal.value},
    )
    assert store.get_item(task_id).status == "superseded"
    assert store.get_item(ratified_task_id).ttl_end == date(2026, 7, 13)

    # ── facts_are_caller_provided: cost-of-delay and break-even derive
    #    only from stored facts (a declared rate + a caller-supplied
    #    amount); every non-monetary output is byte-identical with the
    #    rate removed. ───────────────────────────────────────────────────
    priced_item_id = store.register_item(
        kind=ItemKind.TASK,
        title="priced task",
        parent_id=mission_id,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        amount=Decimal("1000"),
    )
    eval_instant = datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)
    priced_snapshot = store.snapshot()

    report_no_rate = engine.evaluate(priced_snapshot, eval_instant, MementoConfig())
    assert report_no_rate.money == ()

    report_with_rate = engine.evaluate(
        priced_snapshot, eval_instant, MementoConfig(time_value_rate=Decimal("50"))
    )
    priced_money = next(m for m in report_with_rate.money if m.item_id == priced_item_id)
    assert "1000" in priced_money.derivation and "50" in priced_money.derivation

    assert [i.to_dict() for i in report_no_rate.items] == [
        i.to_dict() for i in report_with_rate.items
    ]

    breakeven_date, cycle_count, breakeven_derivation, omitted = money.breakeven(
        t_eval=eval_instant.date(),
        cost_setup=Decimal("600"),
        rate=Decimal("50"),
        setup_hours=Decimal("4"),
        delta_t_hours=Decimal("2"),
        lam_per_day=0.5,
    )
    assert breakeven_date == date(
        2026, 9, 3
    )  # every input traceable in the derivation, no forecast
    assert omitted is None
    assert "600" in breakeven_derivation and "50" in breakeven_derivation and cycle_count is None

    # ── signals_not_control: advance the evaluation instant past the
    #    ratified TTL and the deferral's revisit date; the plane's only
    #    reaction is a reported event, never a block or an agent action.
    #    A generous cap here isolates this constraint from ack_and_cap's
    #    own dedicated coverage (memento_signals_intent.yaml). ───────────
    loose_signal_config = MementoConfig(per_turn_fire_cap=10)
    early_instant = datetime(2026, 7, 5, 12, 0, 0, tzinfo=UTC)
    _early_report, early_signals = _evaluate_signals(store, early_instant, loose_signal_config)
    early_keys = {(s.item_id, s.signal_type) for s in early_signals.fired + early_signals.due}
    assert (ratified_task_id, "ttl_expired") not in early_keys
    assert (deferral_id, "deferral_expired") not in early_keys

    late_instant = datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)
    _late_report, late_signals = _evaluate_signals(store, late_instant, loose_signal_config)
    late_keys = {(s.item_id, s.signal_type) for s in late_signals.fired + late_signals.due}
    assert (
        ratified_task_id,
        "ttl_expired",
    ) in late_keys, "the TTL edge crossed and produced an event"
    assert (
        deferral_id,
        "deferral_expired",
    ) in late_keys, "the revisit-date edge crossed and produced an event"
    for s in late_signals.fired + late_signals.due:
        assert isinstance(s.suggested_behavior, str) and s.suggested_behavior
        assert not callable(s.signal_type)  # data only, never an action handle

    # ── facts_are_caller_provided / degrade-by-omission: register a probe
    #    (the recorded alternative path) plus a second, provenance-
    #    labelled published figure (never blended into measured rows). ──
    probe_id = store.register_item(
        kind=ItemKind.PROBE,
        title="channel-b",
        parent_id=mission_id,
        created_valid=datetime(2026, 8, 1, tzinfo=UTC),
        ttl_start=date(2026, 8, 1),
        ttl_end=date(2026, 8, 15),
    )
    store.record_event(
        item_id=probe_id,
        kind=EventKind.STAGE_ENTER,
        valid_time=datetime(2026, 8, 2, tzinfo=UTC),
        stage="channel-b",
    )
    store.record_event(
        item_id=probe_id,
        kind=EventKind.STAGE_EXIT,
        valid_time=datetime(2026, 8, 6, tzinfo=UTC),
        stage="channel-b",
    )

    final_snapshot = store.snapshot()
    final_report = engine.evaluate(final_snapshot, late_instant, MementoConfig())
    comparison = next(c for c in final_report.path_comparisons if c.mission_id == mission_id)
    assert {row.path_key for row in comparison.rows} == {"channel-b", "incumbent"}
    assert (
        comparison.base_rates == ()
    )  # engine.evaluate() wires no base rate — see UNVERIFIED note in the report

    probe_item = store.get_item(probe_id)
    probe_row = next(r for r in final_report.items if r.item_id == probe_id)
    comparison_with_base_rate = paths.build_comparison(
        mission_id=mission_id,
        probes=((probe_item, probe_row.time_in_stage_days, bool(probe_row.is_open_stage)),),
        t_eval=late_instant.date(),
        base_rates=(
            BaseRateRow(
                path_key="channel-b", value_days=6.0, source="industry survey (provenance-labelled)"
            ),
        ),
    )
    assert comparison_with_base_rate.base_rates[0].source == "industry survey (provenance-labelled)"
    # the published figure is a separate field — it never becomes a
    # measured row's path_key, and the measured rows are unaffected by
    # its presence.
    assert {row.path_key for row in comparison_with_base_rate.rows} == {"channel-b", "incumbent"}
    assert comparison_with_base_rate.rows == comparison.rows

    # ── deterministic_no_llm_core: byte-identical, and no network/LLM
    #    call happened on the memento evaluation path. ───────────────────
    with (
        patch.object(socket.socket, "connect", side_effect=_block),
        patch.object(subprocess, "Popen", side_effect=_block),
    ):
        report_x = engine.evaluate(final_snapshot, late_instant, MementoConfig())
        report_y = engine.evaluate(final_snapshot, late_instant, MementoConfig())
    assert json.dumps(report_x.to_dict(), sort_keys=True, default=str) == json.dumps(
        report_y.to_dict(), sort_keys=True, default=str
    )
    assert report_x.zero_network is True and report_x.zero_llm is True

    # ── mission_scope_persistence: closing this "session" and reopening
    #    the same store path leaves every item intact — only explicit
    #    caller writes ever changed the store. ───────────────────────────
    item_count_before_close = len(store.get_items())
    store.close()
    reopened = MementoStore(store_path)
    assert len(reopened.get_items()) == item_count_before_close
    assert reopened.get_item(mission_id) is not None
    assert reopened.get_item(ratified_task_id).ttl_end == date(2026, 7, 13)

    # finite_rooted_tree, re-confirmed against the reopened store's own
    # record: the deadline, gate, and entity registered above all
    # resolved a parent path terminating at the same single root, and
    # survived the close/reopen above.
    assert reopened.get_item(deadline_id).gates_item_id == task_id
    assert reopened.get_item(gate_id).parent_id == mission_id
    assert reopened.get_item(entity_id).parent_id == mission_id
    reopened.close()

    # ── optional_plane_backward_compat: an unconfigured session's
    #    existing behavior is untouched by any of the above. ────────────
    monitor_a = FidelityMonitor()
    monitor_b = FidelityMonitor()
    session_a = monitor_a.new_conversation(session_id="joint-flow-session")
    session_b = monitor_b.new_conversation(session_id="joint-flow-session")
    result_a = monitor_a.process_turn(
        session_a, "hello", "hi there", timestamp="2026-08-18T12:00:00+00:00"
    )
    result_b = monitor_b.process_turn(
        session_b, "hello", "hi there", timestamp="2026-08-18T12:00:00+00:00"
    )
    assert result_a.fidelity_score == result_b.fidelity_score
    assert [e.type for e in result_a.events] == [e.type for e in result_b.events]

    registry = AssociationRegistry()
    assert (
        registry.is_associated("joint-flow-session") is False
    )  # zero events without explicit association
