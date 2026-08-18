"""E-12, E-13 — TTL proposal arithmetic and inertness.

memento_engine_intent.yaml::degrade_by_omission (E-12 [GOLDEN]);
memento_engine_intent.yaml::pure_function_injected_time / facts_are_caller_provided (E-13 [HUMAN]).
"""

from __future__ import annotations

from datetime import date, timedelta

from horizon_monitor.memento import propose
from horizon_monitor.memento.models import EventKind

from .conftest import build_smallco, load_golden


def test_ttl_proposal_nearest_rank_p80_matches_golden() -> None:
    """E-12 [GOLDEN]: comparable class {5,8,9,12,20}d -> P80 = 12d
    (nearest-rank), sample_size 5, derivation string shown."""
    golden = load_golden()
    proposal = propose.ttl_proposal(
        item_id="some-task",
        completed_durations_days=golden["ttl_proposal_durations"],
        percentile=0.80,
    )
    assert proposal is not None
    assert proposal.value == golden["ttl_proposal_p80"] == 12
    assert proposal.sample_size == golden["ttl_proposal_sample_size"] == 5
    assert "12" in proposal.derivation and "5" in proposal.derivation


def test_ttl_proposal_empty_class_returns_none() -> None:
    """Empty comparable class -> no proposal (never an invented default)."""
    proposal = propose.ttl_proposal(
        item_id="some-task", completed_durations_days=[], percentile=0.80
    )
    assert proposal is None


def test_proposal_is_inert_until_ratified(store) -> None:
    """E-13 [HUMAN]: a proposal is returned but the TTL is unchanged until
    an explicit RATIFY event; propose.ttl_proposal() is a pure function
    that never touches the store — it takes plain durations, not even a
    store handle, so it structurally cannot write.

    Applying a proposal requires the caller to explicitly (1) register a
    new item carrying the ratified TTL and (2) mark the old item
    superseded — mm_items rows mutate only status/superseded_by
    (memento_store_intent.yaml::append_only_bitemporal); there is no
    in-place TTL mutation anywhere in the store API.

    REVIEWER NOTE [HUMAN]: confirm this register-new + supersede-old +
    RATIFY-event sequence is the intended shape of "an explicit ratifying
    write" (ai_generated test provenance — IVD Rule 3)."""
    ids = build_smallco(store)
    task_before = store.get_item(ids["T1"])

    proposal = propose.ttl_proposal(
        item_id=ids["T1"], completed_durations_days=[5, 8, 9, 12, 20], percentile=0.80
    )
    assert proposal is not None
    assert proposal.value == 12

    # The proposal changed nothing: propose.ttl_proposal() never touched
    # the store at all (no store argument exists in its signature).
    task_still_unchanged = store.get_item(ids["T1"])
    assert task_still_unchanged.ttl_end == task_before.ttl_end
    assert task_still_unchanged.status == "open"

    # Ratifying is an explicit, separate write: register the new TTL as a
    # new item, mark the old one superseded, and record the RATIFY event.
    new_item_id = store.register_item(
        kind=task_before.kind,
        title=task_before.title,
        parent_id=task_before.parent_id,
        created_valid=task_before.created_valid,
        ttl_start=task_before.ttl_start,
        ttl_end=task_before.ttl_start + timedelta(days=proposal.value),
    )
    store.update_item_status(ids["T1"], status="superseded", superseded_by=new_item_id)
    store.record_event(
        item_id=new_item_id,
        kind=EventKind.RATIFY,
        valid_time=task_before.created_valid,
        payload={"proposal_kind": proposal.kind, "value": proposal.value},
    )

    old_after = store.get_item(ids["T1"])
    assert old_after.status == "superseded"
    assert old_after.superseded_by == new_item_id
    new_item = store.get_item(new_item_id)
    assert new_item.ttl_end == date(2026, 7, 13)  # 12 days after ttl_start, per the proposal

    ratify_events = [e for e in store.get_events(new_item_id) if e.kind == EventKind.RATIFY]
    assert len(ratify_events) == 1
