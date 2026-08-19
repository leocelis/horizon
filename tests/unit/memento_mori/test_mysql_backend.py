"""MySQL backend — env-gated integration tests.

These run ONLY when HORIZON_TEST_MYSQL_DSN is set (plus the CA env the
backend requires). CI and contributors without a MySQL server skip them;
no server address, credential, or deployment detail lives in this file.

    export HORIZON_TEST_MYSQL_DSN='mysql://user:pass@host:port/dbname'
    export HORIZON_MYSQL_SSL_CA=/path/to/ca.pem
"""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import date, datetime, timezone

import pytest

DSN = os.environ.get("HORIZON_TEST_MYSQL_DSN")
pytestmark = pytest.mark.skipif(not DSN, reason="HORIZON_TEST_MYSQL_DSN not set")

UTC = timezone.utc


@pytest.fixture()
def mysql_store():
    from horizon_monitor.memento import MementoStore

    store = MementoStore(dsn=DSN)
    yield store
    store.close()


@pytest.fixture()
def scope(mysql_store):
    """A throwaway tenant per test run, erased afterwards, so the test
    leaves the database exactly as it found it."""
    tid = f"pytest-{uuid.uuid4().hex[:12]}"
    sc = mysql_store.scoped(tid)
    yield sc
    sc.erase_all()


def test_roundtrip_against_real_mysql(scope):
    from horizon_monitor.memento import EventKind, ItemKind, MementoConfig, evaluate

    root = scope.register_item(
        kind=ItemKind.HORIZON, title="mysql horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC), end_date=date(2030, 1, 1),
    )
    mission = scope.register_item(
        kind=ItemKind.MISSION, title="mysql mission", parent_id=root,
        created_valid=datetime(2026, 7, 2, tzinfo=UTC), stall_days=14,
    )
    scope.record_event(item_id=mission, kind=EventKind.PROGRESS,
                       valid_time=datetime(2026, 7, 2, tzinfo=UTC))

    # timestamps round-trip with their UTC offset intact (the VARCHAR
    # decision: DATETIME would have dropped it)
    item = scope.get_item(mission)
    assert item.created_valid == datetime(2026, 7, 2, tzinfo=UTC)
    assert item.created_valid.tzinfo is not None

    rep = evaluate(scope.snapshot(), datetime(2026, 8, 18, 12, tzinfo=UTC), MementoConfig())
    m = next(r for r in rep.items if r.title == "mysql mission")
    assert m.age_days == 47
    assert m.days_since_progress == 47


def test_two_tenant_isolation_on_mysql(mysql_store):
    from horizon_monitor.memento import ItemKind

    a = mysql_store.scoped(f"pytest-a-{uuid.uuid4().hex[:8]}")
    b = mysql_store.scoped(f"pytest-b-{uuid.uuid4().hex[:8]}")
    try:
        ra = a.register_item(kind=ItemKind.HORIZON, title="A",
                             created_valid=datetime(2026, 1, 1, tzinfo=UTC),
                             end_date=date(2030, 1, 1))
        b.register_item(kind=ItemKind.HORIZON, title="B",
                        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
                        end_date=date(2030, 1, 1))
        assert {i.title for i in a.get_items()} == {"A"}
        assert b.get_item(ra) is None
        counts = a.erase_all()
        assert counts["mm_items"] == 1
        assert {i.title for i in b.get_items()} == {"B"}  # untouched
    finally:
        a.erase_all()
        b.erase_all()


def test_ensure_live_reconnects_after_server_side_close(mysql_store):
    """G-1: kill the connection out from under the store; the next call must
    succeed. Without this, the defect is only reachable by waiting out the
    server's idle timeout — invisible to every fast test."""
    tid = f"pytest-live-{uuid.uuid4().hex[:8]}"
    sc = mysql_store.scoped(tid)
    try:
        from horizon_monitor.memento import ItemKind

        sc.register_item(kind=ItemKind.HORIZON, title="live",
                         created_valid=datetime(2026, 1, 1, tzinfo=UTC),
                         end_date=date(2030, 1, 1))
        # simulate wait_timeout: close the socket underneath the backend
        mysql_store._b._conn.close()
        assert {i.title for i in sc.get_items()} == {"live"}  # reconnected
    finally:
        sc.erase_all()


def test_tenant_resolution_and_rotation_on_mysql(mysql_store):
    sha_old = hashlib.sha256(f"key-{uuid.uuid4()}".encode()).hexdigest()
    sha_new = hashlib.sha256(f"key-{uuid.uuid4()}".encode()).hexdigest()
    tid = f"pytest-rot-{uuid.uuid4().hex[:8]}"
    try:
        mysql_store.provision_tenant(tid, "Rotation Test", sha_old)
        assert mysql_store.resolve_tenant_for_key_sha(sha_old) == tid
        assert mysql_store.revoke_key(sha_old) is True
        assert mysql_store.resolve_tenant_for_key_sha(sha_old) is None  # fail closed
        mysql_store.provision_tenant(tid, "Rotation Test", sha_new)
        assert mysql_store.resolve_tenant_for_key_sha(sha_new) == tid
    finally:
        with mysql_store._txn() as b:
            b.execute("DELETE FROM horizon_api_keys WHERE tenant_id = ?", (tid,))
            b.execute("DELETE FROM horizon_tenants WHERE tenant_id = ?", (tid,))
