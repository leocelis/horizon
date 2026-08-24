"""Artifact ingestion — the capture path the research ranks first.

C1 (capture burden) ranks strategies by persistence: subscribing to append-only
artifacts a team already produces is rank 1 ("no extra habit"); an agent
remembering to write is rank 2 ("zero if the agent forgets"); retrospective
reconstruction is rank 5 ("dies"). These tests pin the rank-1 path.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import pytest

from horizon_monitor.memento import (
    ArtifactProvenanceRequiredError,
    EventKind,
    ItemKind,
    MementoStore,
    Provenance,
    ingest_artifacts,
)
from horizon_monitor.memento.adapters.base import RawArtifact

UTC = timezone.utc


@dataclass
class FakeAdapter:
    """A recording stand-in for a real source. Captures the `since` it was
    asked for, so the incremental contract can be asserted."""

    artifacts: tuple
    source_system: str = "fake_source"
    last_since: datetime | None = None
    pulls: int = 0

    def pull(self, since):
        self.last_since = since
        self.pulls += 1
        return self.artifacts


def _artifact(native_id: str, when: datetime, source: str = "fake_source") -> RawArtifact:
    return RawArtifact(
        provenance=Provenance(source_system=source, native_id=native_id, raw_timestamp=when),
        payload={"subject": f"work {native_id}"},
    )


@pytest.fixture()
def mission(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    root = store.register_item(
        kind=ItemKind.HORIZON,
        title="h",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mid = store.register_item(
        kind=ItemKind.MISSION,
        title="m",
        parent_id=root,
        created_valid=datetime(2026, 7, 1, tzinfo=UTC),
    )
    yield store, mid
    store.close()


def test_artifacts_become_events_with_provenance(mission):
    store, mid = mission
    base = datetime(2026, 7, 2, 9, tzinfo=UTC)
    adapter = FakeAdapter(tuple(_artifact(f"c{i}", base + timedelta(days=i)) for i in range(3)))

    result = ingest_artifacts(store, adapter, item_id=mid)

    assert (result.ingested, result.skipped_duplicates, result.pulled) == (3, 0, 3)
    events = store.get_events(mid)
    assert len(events) == 3
    for e in events:
        assert e.kind is EventKind.ARTIFACT
        # provenance is mandatory for ARTIFACT and the store enforces it
        assert e.provenance.source_system == "fake_source"
        assert e.provenance.native_id.startswith("c")
        assert e.provenance.raw_timestamp is not None
        # valid_time is the SOURCE's timestamp, not the ingestion clock
        assert e.valid_time == e.provenance.raw_timestamp


def test_ingestion_is_idempotent(mission):
    """A capture path that is unsafe to re-run will not be automated, and one
    that is not automated depends on somebody remembering."""
    store, mid = mission
    arts = tuple(
        _artifact(f"c{i}", datetime(2026, 7, 2, tzinfo=UTC) + timedelta(days=i)) for i in range(3)
    )

    first = ingest_artifacts(store, FakeAdapter(arts), item_id=mid)
    second = ingest_artifacts(store, FakeAdapter(arts), item_id=mid)

    assert first.ingested == 3
    assert second.ingested == 0
    assert second.skipped_duplicates == 3
    assert len(store.get_events(mid)) == 3, "a repeat run double-counted the same artifacts"


def test_dedupe_is_on_native_id_not_payload(mission):
    """The source's own identifier is the identity. Deduping on payload would
    re-ingest a commit whose message was amended."""
    store, mid = mission
    when = datetime(2026, 7, 2, tzinfo=UTC)
    ingest_artifacts(store, FakeAdapter((_artifact("c1", when),)), item_id=mid)

    amended = RawArtifact(
        provenance=Provenance("fake_source", "c1", when),
        payload={"subject": "COMPLETELY DIFFERENT MESSAGE"},
    )
    again = ingest_artifacts(store, FakeAdapter((amended,)), item_id=mid)

    assert again.ingested == 0
    assert len(store.get_events(mid)) == 1


def test_second_run_asks_the_source_only_for_what_is_new(mission):
    store, mid = mission
    newest = datetime(2026, 7, 4, tzinfo=UTC)
    arts = (_artifact("c1", datetime(2026, 7, 2, tzinfo=UTC)), _artifact("c2", newest))
    ingest_artifacts(store, FakeAdapter(arts), item_id=mid)

    second = FakeAdapter(())
    ingest_artifacts(store, second, item_id=mid)
    assert second.last_since == newest, "incremental pull did not use the recorded high-water mark"


def test_an_explicit_since_overrides_the_high_water_mark(mission):
    store, mid = mission
    ingest_artifacts(
        store, FakeAdapter((_artifact("c1", datetime(2026, 7, 2, tzinfo=UTC)),)), item_id=mid
    )
    forced = datetime(2020, 1, 1, tzinfo=UTC)
    a = FakeAdapter(())
    ingest_artifacts(store, a, item_id=mid, since=forced)
    assert a.last_since == forced


def test_the_mission_link_must_be_supplied_by_the_caller(mission):
    """C1 F6: 'this artifact belongs to mission M' is a fact the log cannot
    know. It is a required argument here, and the adapter has no way to set it."""
    store, mid = mission
    with pytest.raises(TypeError):
        ingest_artifacts(store, FakeAdapter(()))  # no item_id
    # and the adapter contract itself offers no link parameter
    assert not any(f in RawArtifact.__dataclass_fields__ for f in ("item_id", "mission_id"))


def test_empty_source_is_not_an_error(mission):
    store, mid = mission
    result = ingest_artifacts(store, FakeAdapter(()), item_id=mid)
    assert (result.ingested, result.pulled) == (0, 0)
    assert store.get_events(mid) == []


def test_ingested_artifacts_are_tenant_scoped(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    try:
        a = store.scoped("tenant-a")
        root = a.register_item(
            kind=ItemKind.HORIZON,
            title="h",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        mid = a.register_item(
            kind=ItemKind.MISSION,
            title="m",
            parent_id=root,
            created_valid=datetime(2026, 7, 1, tzinfo=UTC),
        )
        ingest_artifacts(
            a, FakeAdapter((_artifact("c1", datetime(2026, 7, 2, tzinfo=UTC)),)), item_id=mid
        )
        assert len(a.get_events(mid)) == 1
        assert store.scoped("tenant-b").known_artifact_ids("fake_source") == frozenset()
    finally:
        store.close()


def test_an_artifact_without_full_provenance_is_refused(mission):
    """The store validates before writing, so a bad source cannot half-land."""
    store, mid = mission
    bad = RawArtifact(provenance=Provenance("fake_source", "", None), payload={})
    with pytest.raises(ArtifactProvenanceRequiredError):
        ingest_artifacts(store, FakeAdapter((bad,)), item_id=mid)
    assert store.get_events(mid) == [], "a rejected artifact still wrote something"


# ── mission proposals: structure derived, meaning supplied ───────────────────


def test_a_proposal_derives_structure_from_real_artifacts(tmp_path):
    from horizon_monitor.memento import propose_missions

    store = MementoStore(tmp_path / "m.db")
    try:
        arts = tuple(
            _artifact(f"c{i}", datetime(2026, 6, 1, tzinfo=UTC) + timedelta(days=i * 10))
            for i in range(5)
        )
        (proposal,) = propose_missions(store, FakeAdapter(arts))
        assert proposal.artifact_count == 5
        assert proposal.first_artifact == datetime(2026, 6, 1, tzinfo=UTC)
        assert proposal.span_days == 40
        # the start date is OBSERVED — the earliest artifact, not a guess
        assert proposal.suggested_created_valid == proposal.first_artifact
        assert "observed, not estimated" in proposal.derivation
    finally:
        store.close()


def test_a_proposal_never_invents_a_title(tmp_path):
    """Structure can be derived; meaning cannot. A proposed name would be the
    plane's first invented fact."""
    from horizon_monitor.memento import MissionProposal, propose_missions

    assert "title" not in MissionProposal.__dataclass_fields__

    store = MementoStore(tmp_path / "m.db")
    try:
        (p,) = propose_missions(
            store, FakeAdapter((_artifact("c1", datetime(2026, 6, 1, tzinfo=UTC)),))
        )
        assert "You supply the title" in p.summary()
    finally:
        store.close()


def test_a_proposal_writes_nothing(tmp_path):
    """Inert: registering the mission is the ratifying act, and it is the
    operator's — as with TTL proposals, which stay unapplied until RATIFY."""
    from horizon_monitor.memento import propose_missions

    store = MementoStore(tmp_path / "m.db")
    try:
        propose_missions(store, FakeAdapter((_artifact("c1", datetime(2026, 6, 1, tzinfo=UTC)),)))
        assert store.get_items() == []
        assert store.get_events() == []
    finally:
        store.close()


def test_nothing_is_proposed_once_the_work_is_already_recorded(mission):
    """A source whose artifacts are ingested already has a mission holding them."""
    from horizon_monitor.memento import propose_missions

    store, mid = mission
    arts = (_artifact("c1", datetime(2026, 7, 2, tzinfo=UTC)),)
    assert propose_missions(store, FakeAdapter(arts))  # before: proposed
    ingest_artifacts(store, FakeAdapter(arts), item_id=mid)
    assert propose_missions(store, FakeAdapter(arts)) == ()  # after: silent


def test_an_empty_source_proposes_nothing(tmp_path):
    from horizon_monitor.memento import propose_missions

    store = MementoStore(tmp_path / "m.db")
    try:
        assert propose_missions(store, FakeAdapter(())) == ()
    finally:
        store.close()
