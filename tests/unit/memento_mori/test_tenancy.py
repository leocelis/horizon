"""Tenancy — scope isolation, fail-closed resolution, v1→v2 migration.

The isolation tests deliberately seed TWO tenants with overlapping shapes:
a single-tenant fixture passes every isolation assertion trivially and
proves nothing (the fixture-that-passes-by-luck failure).
"""

from __future__ import annotations

import hashlib
import pathlib
import sqlite3
from datetime import date, datetime, timezone

import pytest

from horizon_monitor.memento import (
    EventKind,
    ItemKind,
    KeyAlreadyBoundError,
    MementoConfig,
    MementoStore,
    evaluate,
)
from horizon_monitor.memento import store as store_module

UTC = timezone.utc


def _seed(scope: MementoStore, tag: str) -> tuple[str, str]:
    root = scope.register_item(
        kind=ItemKind.HORIZON,
        title=f"horizon-{tag}",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission = scope.register_item(
        kind=ItemKind.MISSION,
        title=f"mission-{tag}",
        parent_id=root,
        created_valid=datetime(2026, 7, 2, tzinfo=UTC),
        stall_days=14,
    )
    scope.record_event(
        item_id=mission,
        kind=EventKind.PROGRESS,
        valid_time=datetime(2026, 7, 2, tzinfo=UTC),
    )
    scope.set_fire_state(mission, "mission_stalled", {"state": "RAISED", "tag": tag})
    return root, mission


@pytest.fixture()
def two_tenants(tmp_path):
    store = MementoStore(tmp_path / "missions.db")  # tenant 'local'
    a = store.scoped("tenant-a")
    b = store.scoped("tenant-b")
    ids_a = _seed(a, "a")
    ids_b = _seed(b, "b")
    return store, a, b, ids_a, ids_b


def test_scopes_share_one_backend_connection(two_tenants):
    store, a, b, *_ = two_tenants
    assert a._b is store._b is b._b
    assert a._lock is store._lock


def test_each_tenant_has_its_own_root(two_tenants):
    """Two roots in one database is correct — one per tenant — and each
    scope's rooted-tree invariant sees only its own."""
    _store, a, b, *_ = two_tenants
    assert a.get_root().title == "horizon-a"
    assert b.get_root().title == "horizon-b"


def test_snapshot_is_tenant_scoped(two_tenants):
    """G-2: snapshot() feeds evaluate(), so a leak here silently computes
    one tenant's numbers from another tenant's facts."""
    _store, a, b, *_ = two_tenants
    snap_a, snap_b = a.snapshot(), b.snapshot()
    assert {i.title for i in snap_a.items} == {"horizon-a", "mission-a"}
    # every event in A's snapshot belongs to an item in A's snapshot — the
    # assertion this replaced was vacuous (`... or True` is always true)
    a_item_ids = {i.item_id for i in snap_a.items}
    b_item_ids = {i.item_id for i in snap_b.items}
    assert {e.item_id for e in snap_a.events} <= a_item_ids
    assert not ({e.item_id for e in snap_a.events} & b_item_ids)
    assert len(snap_a.events) == 1
    assert len(snap_a.fire_states) == 1
    assert snap_a.fire_states[0][1]["tag"] == "a"
    # and the engine computes cleanly over the scoped snapshot
    rep = evaluate(snap_a, datetime(2026, 8, 18, tzinfo=UTC), MementoConfig())
    assert {r.title for r in rep.items} == {"horizon-a", "mission-a"}


def test_cross_tenant_reads_by_id_return_nothing(two_tenants):
    _store, a, b, (_, mission_a), (_, mission_b) = two_tenants
    assert a.get_item(mission_b) is None
    assert b.get_item(mission_a) is None
    assert a.get_events(mission_b) == []
    assert a.get_fire_state(mission_b, "mission_stalled") is None


def test_cross_tenant_writes_by_id_touch_nothing(two_tenants):
    _store, a, b, (_, mission_a), (_, mission_b) = two_tenants
    a.update_item_status(mission_b, "closed")  # predicate excludes it: no-op
    assert b.get_item(mission_b).status == "open"


def test_erase_all_is_tenant_scoped(two_tenants):
    """T-4: one tenant's erasure request must never touch another tenant's
    history. This is the highest-severity finding in the deployment review."""
    _store, a, b, _ids_a, (_root_b, mission_b) = two_tenants
    counts = a.erase_all()
    assert counts["mm_items"] == 2
    assert counts["mm_events"] == 1
    assert counts["mm_fires"] == 1
    # tenant A: gone
    assert a.get_items() == []
    # tenant B: completely intact
    assert len(b.get_items()) == 2
    assert len(b.get_events()) == 1
    assert b.get_fire_state(mission_b, "mission_stalled") is not None


def test_local_tenant_is_isolated_from_named_tenants(two_tenants):
    store, _a, _b, *_ = two_tenants
    assert store.get_items() == []  # 'local' saw nothing of a/b
    _seed(store, "local")
    assert len(store.get_items()) == 2


# ── fail-closed tenant resolution ────────────────────────────────────────────


def test_resolution_fails_closed_for_unknown_and_revoked_keys(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    sha = hashlib.sha256(b"hzn_x_secret").hexdigest()

    assert store.resolve_tenant_for_key_sha(sha) is None  # unknown: refused

    store.provision_tenant("tenant-x", "Tenant X", sha, key_label="laptop")
    assert store.resolve_tenant_for_key_sha(sha) == "tenant-x"

    assert store.revoke_key(sha) is True
    assert store.resolve_tenant_for_key_sha(sha) is None  # revoked: refused
    assert store.revoke_key(sha) is False  # idempotent

    # revocation never touched mission data, and no tenant was auto-created
    # for the revoked key on its next lookup (fail closed, not fail-fresh)
    assert store.resolve_tenant_for_key_sha(sha) is None


def test_rotation_preserves_history(tmp_path):
    """T-1: the reason tenant identity is assigned, never derived from the
    key. Rotate the key; the mission history must be fully reachable."""
    store = MementoStore(tmp_path / "missions.db")
    old_sha = hashlib.sha256(b"hzn_test_key_v1").hexdigest()
    new_sha = hashlib.sha256(b"hzn_test_key_v2").hexdigest()

    store.provision_tenant("tenant-a", "Tenant A", old_sha)
    scope = store.scoped(store.resolve_tenant_for_key_sha(old_sha))
    _seed(scope, "a")

    # rotation = revoke old + bind new, tenant untouched
    store.revoke_key(old_sha)
    store.provision_tenant("tenant-a", "Tenant A", new_sha, key_label="rotated")

    resolved = store.resolve_tenant_for_key_sha(new_sha)
    assert resolved == "tenant-a"
    assert len(store.scoped(resolved).get_items()) == 2  # nothing orphaned


def test_key_hash_cannot_be_rebound(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    sha = hashlib.sha256(b"hzn_shared").hexdigest()
    store.provision_tenant("t1", "One", sha)
    with pytest.raises(KeyAlreadyBoundError):
        store.provision_tenant("t2", "Two", sha)


def test_erasure_marks_tenant_status(tmp_path):
    store = MementoStore(tmp_path / "missions.db")
    sha = hashlib.sha256(b"hzn_e").hexdigest()
    store.provision_tenant("t-erase", "Erase Me", sha)
    scope = store.scoped("t-erase")
    _seed(scope, "e")
    scope.erase_all()
    row = store._fetchone("SELECT status FROM horizon_tenants WHERE tenant_id = ?", ("t-erase",))
    assert row["status"] == "erased"


# ── v1 → v2 migration ────────────────────────────────────────────────────────

_V1_SCHEMA = """
CREATE TABLE mm_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE mm_items (
    item_id TEXT PRIMARY KEY, kind TEXT NOT NULL, parent_id TEXT,
    title TEXT NOT NULL, created_valid TEXT NOT NULL, created_tx TEXT NOT NULL,
    end_date TEXT, revisit_date TEXT, ttl_start TEXT, ttl_end TEXT,
    deadline_date TEXT, deadline_kind TEXT, gates_item_id TEXT,
    age_budget_days INTEGER, stall_days INTEGER, namespace TEXT, amount TEXT,
    status TEXT NOT NULL DEFAULT 'open', superseded_by TEXT
);
CREATE TABLE mm_events (
    tx_seq INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
    item_id TEXT NOT NULL, kind TEXT NOT NULL, valid_time TEXT NOT NULL,
    tx_time TEXT NOT NULL, stage TEXT, wait_or_touch TEXT,
    provenance_source_system TEXT, provenance_native_id TEXT,
    provenance_raw_timestamp TEXT, payload TEXT NOT NULL DEFAULT '{}',
    correction_of TEXT
);
CREATE TABLE mm_fires (
    item_id TEXT NOT NULL, signal_type TEXT NOT NULL, state TEXT NOT NULL,
    PRIMARY KEY (item_id, signal_type)
);
CREATE INDEX idx_mm_events_item ON mm_events(item_id);
"""


def _make_v1_store_with_data(path) -> None:
    """A REAL v1 fixture with real rows — an empty-store migration passes
    trivially and proves nothing."""
    conn = sqlite3.connect(path)
    conn.executescript(_V1_SCHEMA)
    conn.execute("INSERT INTO mm_meta VALUES ('schema_version', '1')")
    conn.execute(
        "INSERT INTO mm_items (item_id, kind, parent_id, title, created_valid, created_tx, end_date) "
        "VALUES ('root-1', 'horizon', NULL, 'old horizon', "
        "'2026-01-01T00:00:00+00:00', '2026-01-01T00:00:00+00:00', '2030-01-01')"
    )
    conn.execute(
        "INSERT INTO mm_items (item_id, kind, parent_id, title, created_valid, created_tx) "
        "VALUES ('m-1', 'mission', 'root-1', 'old mission', "
        "'2026-07-02T00:00:00+00:00', '2026-07-02T00:00:00+00:00')"
    )
    conn.execute(
        "INSERT INTO mm_events (event_id, item_id, kind, valid_time, tx_time, payload) "
        "VALUES ('e-1', 'm-1', 'progress', '2026-07-02T00:00:00+00:00', "
        "'2026-07-02T00:00:00+00:00', '{}')"
    )
    conn.execute(
        "INSERT INTO mm_fires VALUES ('m-1', 'mission_stalled', '{\"state\": \"RAISED\"}')"
    )
    conn.commit()
    conn.close()


def test_v1_store_migrates_with_data_intact(tmp_path):
    path = tmp_path / "missions.db"
    _make_v1_store_with_data(path)

    store = MementoStore(path)  # opening IS the migration

    items = store.get_items()
    assert {i.title for i in items} == {"old horizon", "old mission"}
    assert len(store.get_events()) == 1
    assert store.get_fire_state("m-1", "mission_stalled") == {"state": "RAISED"}
    # version bumped, backup taken
    row = store._fetchone(
        "SELECT value FROM mm_meta WHERE tenant_id='local' AND `key`='schema_version'"
    )
    assert row["value"] == "2"
    assert (tmp_path / "missions.db.v1.bak").exists()


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "missions.db"
    _make_v1_store_with_data(path)
    s1 = MementoStore(path)
    n_items = len(s1.get_items())
    s1.close()

    s2 = MementoStore(path)  # second open must be a no-op
    assert len(s2.get_items()) == n_items
    cols = [r["name"] for r in s2._fetchall("PRAGMA table_info(mm_items)")]
    assert cols.count("tenant_id") == 1  # not added twice


def test_migrated_rows_belong_to_local_tenant(tmp_path):
    path = tmp_path / "missions.db"
    _make_v1_store_with_data(path)
    store = MementoStore(path)
    assert len(store.get_items()) == 2  # 'local' sees everything
    assert store.scoped("someone-else").get_items() == []


def test_fresh_and_migrated_sqlite_stores_differ_in_key_shape_by_design(tmp_path):
    """Documents a real, deliberate divergence so it is never a surprise.

    ALTER TABLE ADD COLUMN cannot change a primary key, and rebuilding one in
    SQLite (create-copy-swap) is the single migration step that can destroy
    data — deliberately eliminated. So a MIGRATED store keeps its v1 keys while
    a FRESH store gets the tenant-composite ones.

    This is safe because SQLite is single-tenant by design (multi-tenant
    deployments use MySQL, created fresh with composite keys): the constraints
    differ, but no reachable operation depends on the difference. The test
    exists so that if someone later builds multi-tenancy on SQLite, this fails
    loudly and they see the trap first.
    """
    fresh_p, mig_p = tmp_path / "fresh.db", tmp_path / "mig.db"
    MementoStore(fresh_p).close()
    _make_v1_store_with_data(mig_p)
    MementoStore(mig_p).close()

    def table_sql(path, table):
        conn = sqlite3.connect(path)
        try:
            return conn.execute(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)
            ).fetchone()[0]
        finally:
            conn.close()

    # fresh: tenant is part of the key
    assert "PRIMARY KEY (tenant_id, `key`)" in table_sql(fresh_p, "mm_meta")
    assert "PRIMARY KEY (tenant_id, item_id, signal_type)" in table_sql(fresh_p, "mm_fires")
    # migrated: v1 keys survive, tenant_id is a plain column
    assert "key TEXT PRIMARY KEY" in table_sql(mig_p, "mm_meta")
    assert "PRIMARY KEY (item_id, signal_type)" in table_sql(mig_p, "mm_fires")
    assert "tenant_id" in table_sql(mig_p, "mm_meta")

    # and both behave identically for the single tenant they are built for
    for path in (fresh_p, mig_p):
        s = MementoStore(path)
        try:
            root = s.get_root()
            if root is None:
                root = s.register_item(
                    kind=ItemKind.HORIZON,
                    title="h",
                    created_valid=datetime(2026, 1, 1, tzinfo=UTC),
                    end_date=date(2030, 1, 1),
                )
                root = s.get_item(root)
            m = s.register_item(
                kind=ItemKind.MISSION,
                title="m",
                parent_id=root.item_id,
                created_valid=datetime(2026, 7, 2, tzinfo=UTC),
            )
            s.set_fire_state(m, "mission_stalled", {"state": "RAISED"})
            assert s.get_fire_state(m, "mission_stalled") == {"state": "RAISED"}
        finally:
            s.close()


def test_store_sql_uses_only_placeholder_question_marks():
    """The MySQL backend translates `?` -> `%s` positionally inside execute().

    That translation cannot distinguish a placeholder from a literal `?` in,
    say, a LIKE pattern — it would corrupt the statement on MySQL while working
    fine on SQLite, the worst kind of divergence. This pins the constraint that
    makes the translation safe.
    """
    import re

    src = pathlib.Path(store_module.__file__).read_text()
    # every double-quoted SQL-ish fragment in the store
    for frag in re.findall(r'"([^"\n]*?)"', src):
        if not any(k in frag.upper() for k in ("SELECT", "INSERT", "UPDATE", "DELETE")):
            continue
        for m in re.finditer(r"\?", frag):
            before = frag[: m.start()]
            # a placeholder is preceded by a delimiter, never by a quote/percent
            assert not before.rstrip().endswith(("'", "%")), (
                f"literal '?' inside a SQL string would be mangled by the "
                f"MySQL placeholder translation: {frag!r}"
            )


def test_scoped_carries_every_instance_attribute():
    """scoped() builds its view with object.__new__, bypassing __init__.

    If __init__ later gains a field, scoped() would silently produce a clone
    missing it — a defect that surfaces only on the tenant path. This fails the
    moment the attribute sets diverge.
    """
    import tempfile

    store = MementoStore(pathlib.Path(tempfile.mkdtemp()) / "m.db")
    try:
        view = store.scoped("t-1")
        assert set(vars(view)) == set(vars(store)), (
            "scoped() did not carry every attribute set by __init__; "
            f"missing={set(vars(store)) - set(vars(view))}"
        )
        assert view.tenant_id == "t-1" and store.tenant_id == "local"
        assert view._b is store._b and view._lock is store._lock
    finally:
        store.close()


def test_default_tenant_is_configurable_but_never_overrides_an_authenticated_key(
    tmp_path, monkeypatch
):
    """HORIZON_MEMENTO_TENANT_ID sets the tenant for callers with NO key.

    That is what lets a locally-run server read the same tenant a hosted one
    would resolve for an API key. It must NOT let an authenticated caller reach
    a different tenant — over an authenticated transport the key's mapping in
    horizon_api_keys always wins.
    """
    import hashlib as _h

    from mcp.server.fastmcp import FastMCP

    from horizon_monitor.mcp import auth as auth_mod
    from horizon_monitor.mcp.server import register_memento_tools

    db = tmp_path / "missions.db"
    monkeypatch.setenv("HORIZON_MEMENTO_TENANT_ID", "workstation-1")
    store, _cfg = register_memento_tools(FastMCP("t"), db)
    try:
        # unauthenticated: the env var decides
        assert store.tenant_id == "workstation-1"

        # authenticated: the key's mapping decides, env var ignored
        sha = _h.sha256(b"hzn_real_key").hexdigest()
        store.provision_tenant("tenant-from-key", "Real", sha)
        token = auth_mod.current_key_sha.set(sha)
        try:
            assert store.resolve_tenant_for_key_sha(sha) == "tenant-from-key"
        finally:
            auth_mod.current_key_sha.reset(token)
    finally:
        store.close()
