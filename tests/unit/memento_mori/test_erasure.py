"""Erasure path — MementoStore.erase_all().

Added because the published privacy policy promises a right to erasure that the
store had no way to honour: there was no delete path of any kind. See the
hosted-deployment blocker note — durable hosted storage cannot ship until this
exists.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento import EventKind, ItemKind, MementoStore

UTC = timezone.utc


def _seeded(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    root = store.register_item(
        kind=ItemKind.HORIZON,
        title="engagement horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission = store.register_item(
        kind=ItemKind.MISSION,
        title="buyer-outreach",
        parent_id=root,
        created_valid=datetime(2026, 7, 2, tzinfo=UTC),
        stall_days=14,
    )
    store.record_event(
        item_id=mission,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
    )
    store.set_fire_state(mission, "mission_stalled", {"state": "RAISED"})
    return store, root, mission


def test_erase_all_destroys_every_record_and_reports_counts(tmp_path):
    store, _root, _mission = _seeded(tmp_path)
    assert store.get_items() and store.get_events()

    counts = store.erase_all()

    assert counts["mm_items"] == 2
    assert counts["mm_events"] == 1
    assert counts["mm_fires"] == 1
    assert store.get_items() == []
    assert store.get_events() == []
    assert store.get_all_fire_states() == []


def test_store_survives_erasure_and_accepts_a_new_horizon(tmp_path):
    """The schema and its version row must outlive the data."""
    store, _root, _mission = _seeded(tmp_path)
    store.erase_all()

    fresh = store.register_item(
        kind=ItemKind.HORIZON,
        title="new horizon",
        created_valid=datetime(2027, 1, 1, tzinfo=UTC),
        end_date=date(2031, 1, 1),
    )
    assert store.get_root() is not None
    assert store.get_item(fresh).title == "new horizon"


def test_erasure_survives_a_reopen(tmp_path):
    """Erasure must hit the file, not just the in-memory connection."""
    path = tmp_path / "missions.db"
    store = MementoStore(path)
    root = store.register_item(
        kind=ItemKind.HORIZON,
        title="h",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    store.record_event(
        item_id=root,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 1, 2, tzinfo=UTC),
    )
    store.erase_all()
    store.close()

    reopened = MementoStore(path)
    assert reopened.get_items() == []
    assert reopened.get_events() == []


def test_erasure_is_all_or_nothing_no_selective_delete_exists(tmp_path):
    """Guards the design decision, not just the behaviour.

    A per-row delete would let history be rewritten under a privacy label: drop
    the one stall that made a mission look bad and every surviving number still
    reads as authoritative. If someone adds one, this fails and they must argue
    for it deliberately.
    """
    public = [n for n in dir(MementoStore) if not n.startswith("_")]
    deleters = [n for n in public if "delete" in n or "remove" in n or "purge" in n]
    assert deleters == [], f"a selective delete path appeared: {deleters}"
    assert "erase_all" in public


def test_erasure_is_not_exposed_as_an_mcp_tool():
    """An agent must never be able to erase the operator's history.

    Erasure is an operator action. Exposing it as a tool means a sufficiently
    persuasive turn of conversation can destroy every mission record.
    """
    from horizon_monitor.mcp import server

    src = server.__file__ or ""
    assert src
    text = open(src, encoding="utf-8").read()
    assert "erase_all" not in text, "erase_all is reachable from the MCP surface"


def test_redaction_and_erasure_are_different_operations(tmp_path):
    """Redaction keeps the measurement; erasure removes the record."""
    store = MementoStore(tmp_path / "missions.db")
    root = store.register_item(
        kind=ItemKind.HORIZON,
        title="h",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    person = store.register_item(
        kind=ItemKind.ENTITY,
        title="Jane Doe",
        parent_id=root,
        namespace="person",
        person_namespace_confirmed=True,
        created_valid=datetime(2026, 2, 1, tzinfo=UTC),
    )
    store.redact_person_display_name(person)

    still_there = store.get_item(person)
    assert still_there is not None
    assert still_there.title != "Jane Doe"
    assert len(store.get_items()) == 2

    store.erase_all()
    assert store.get_item(person) is None


def test_privacy_policy_only_names_methods_that_exist():
    """The policy is a promise to users; every mechanism it names must be real.

    This exists because the previous version of the policy described the hosted
    server's data-at-rest behaviour in terms the code did not implement. A
    document that claims a capability it does not have is worse than silence.
    """
    import pathlib
    import re

    policy = pathlib.Path(__file__).resolve().parents[3] / "PRIVACY_POLICY.md"
    assert policy.is_file(), policy
    text = policy.read_text(encoding="utf-8")

    section = text.split("### 1.6 Mission plane store")[1].split("## 2.")[0]
    named = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)\(\)`", section))
    assert named, "section 1.6 names no mechanism at all"

    for method in named:
        assert hasattr(MementoStore, method), (
            f"PRIVACY_POLICY.md section 1.6 promises `{method}()`, "
            "which does not exist on MementoStore"
        )


def test_erase_all_separates_data_deletion_from_tenant_erasure_status(tmp_path):
    """Destroying a tenant's data and recording that the tenant *exercised
    erasure* are different events, and conflating them misstates live tenants.

    Maintenance and test cleanup destroy data without anyone invoking a right;
    flipping the tenant to `erased` there would leave an active tenant labelled
    as erased. The default stays True because this method IS the erasure path.
    """
    store = MementoStore(tmp_path / "missions.db")
    try:
        store.provision_tenant("t-live", "Live Tenant", "a" * 64)
        scope = store.scoped("t-live")

        def seed():
            root = scope.register_item(
                kind=ItemKind.HORIZON,
                title="h",
                created_valid=datetime(2026, 1, 1, tzinfo=UTC),
                end_date=date(2030, 1, 1),
            )
            scope.register_item(
                kind=ItemKind.MISSION,
                title="m",
                parent_id=root,
                created_valid=datetime(2026, 7, 2, tzinfo=UTC),
            )

        seed()

        # maintenance cleanup — data goes, status must not change
        counts = scope.erase_all(mark_tenant_erased=False)
        assert counts["mm_items"] == 2
        assert scope.get_items() == []
        row = store._fetchone("SELECT status FROM horizon_tenants WHERE tenant_id = ?", ("t-live",))
        assert row["status"] == "active", "cleanup mislabelled a live tenant as erased"

        # the real erasure path still records that the right was exercised
        seed()
        scope.erase_all()
        row = store._fetchone("SELECT status FROM horizon_tenants WHERE tenant_id = ?", ("t-live",))
        assert row["status"] == "erased"
    finally:
        store.close()
