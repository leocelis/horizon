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
        kind=ItemKind.HORIZON,
        title="mysql horizon",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission = scope.register_item(
        kind=ItemKind.MISSION,
        title="mysql mission",
        parent_id=root,
        created_valid=datetime(2026, 7, 2, tzinfo=UTC),
        stall_days=14,
    )
    scope.record_event(
        item_id=mission, kind=EventKind.PROGRESS, valid_time=datetime(2026, 7, 2, tzinfo=UTC)
    )

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
        ra = a.register_item(
            kind=ItemKind.HORIZON,
            title="A",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        b.register_item(
            kind=ItemKind.HORIZON,
            title="B",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
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

        sc.register_item(
            kind=ItemKind.HORIZON,
            title="live",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=date(2030, 1, 1),
        )
        # simulate wait_timeout: close the socket underneath the backend
        mysql_store._b._conn.close()
        assert {i.title for i in sc.get_items()} == {"live"}  # reconnected
        # and the session settings survived the reconnect — pymysql replays only
        # init_command, so a setting applied once after connect is lost when the
        # connection is rebuilt. That regression is how a long-lived server fell
        # back to REPEATABLE READ and served rows that had already been deleted.
        iso = mysql_store._fetchone("SELECT @@transaction_isolation AS i", ())["i"]
        assert iso == "READ-COMMITTED", (
            f"isolation reverted to {iso} after reconnect — the frozen-snapshot "
            "bug is back via the reconnect path"
        )
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


# ── retry classification (runs WITHOUT a MySQL server) ──────────────────────


def test_permanent_errors_are_classified_without_a_server():
    """Unit-level: the classifier itself. Runs everywhere."""
    from horizon_monitor.memento.backends.mysql import _is_permanent

    assert _is_permanent(Exception(1045, "Access denied for user"))
    assert _is_permanent(Exception(1049, "Unknown database 'nope'"))
    assert _is_permanent(Exception(2003, "... [SSL: CERTIFICATE_VERIFY_FAILED] ..."))
    # transient network conditions MUST stay retryable
    assert not _is_permanent(Exception(2003, "Can't connect to MySQL server (timed out)"))
    assert not _is_permanent(Exception(2013, "Lost connection during query"))
    assert not _is_permanent(Exception("something unexpected"))


@pytest.mark.skipif(not DSN, reason="HORIZON_TEST_MYSQL_DSN not set")
def test_wrong_credentials_fail_fast_not_after_a_retry_storm():
    """EXECUTES the changed branch against the real server.

    Before this fix a wrong password retried 7 times with exponential backoff
    (~126s) before surfacing — long enough for a platform health check to kill
    the container mid-retry and show a crashloop instead of 'access denied'.
    """
    import time as _time
    import urllib.parse as _up

    from horizon_monitor.memento import MementoStore

    u = _up.urlparse(DSN)
    bad = DSN.replace(f":{_up.quote(u.password or '')}@", ":definitely-not-the-password@")

    started = _time.monotonic()
    with pytest.raises(RuntimeError, match="permanent reason"):
        MementoStore(dsn=bad)
    elapsed = _time.monotonic() - started
    assert elapsed < 20, f"took {elapsed:.1f}s — it retried a permanent failure"


@pytest.mark.skipif(not DSN, reason="HORIZON_TEST_MYSQL_DSN not set")
def test_a_long_lived_reader_sees_writes_from_another_connection():
    """The store holds ONE connection per process with autocommit off.

    Under InnoDB's REPEATABLE READ default that froze the read view: the first
    SELECT pinned an MVCC snapshot and every later read on that connection
    returned the same stale rows, so a mostly-reading server would report the
    same clock forever while other processes recorded progress. Fixed by
    setting READ COMMITTED at connect time.

    No SQLite test can catch this — SQLite has no such snapshot semantics — and
    no existing MySQL test could either, because each one writes (which commits
    and resets the snapshot) before reading again.
    """
    from datetime import date as _date

    from horizon_monitor.memento import ItemKind, MementoStore

    tid = f"pytest-iso-{uuid.uuid4().hex[:8]}"
    reader = MementoStore(dsn=DSN).scoped(tid)
    writer = MementoStore(dsn=DSN).scoped(tid)
    try:
        assert reader.get_items() == []  # pins the snapshot under the old default
        writer.register_item(
            kind=ItemKind.HORIZON,
            title="written by another connection",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=_date(2030, 1, 1),
        )
        titles = {i.title for i in reader.get_items()}
        assert titles == {"written by another connection"}, (
            "the long-lived reader is serving a frozen snapshot — isolation "
            "regressed to REPEATABLE READ"
        )
        assert reader._fetchone("SELECT @@transaction_isolation AS i", ())["i"] == "READ-COMMITTED"
    finally:
        reader.erase_all()
        reader.close()
        writer.close()


@pytest.mark.skipif(not DSN, reason="HORIZON_TEST_MYSQL_DSN not set")
def test_every_text_column_is_binary_collated_so_tenant_ids_cannot_collide(mysql_store):
    """A case-insensitive collation makes tenant_id='Acme' match rows stored
    under 'acme' — one tenant silently reading another's missions.

    This was live: the database was created without an explicit COLLATE and
    inherited utf8mb4_0900_ai_ci, so an upper-cased tenant id returned another
    tenant's rows. The connection-level `SET NAMES ... COLLATE utf8mb4_bin`
    does not protect it, because comparing a column to a literal resolves to
    the COLUMN's collation — so the tables must carry it themselves.

    No single-tenant test could catch this, which is why it is asserted against
    the live schema rather than the DDL string.
    """
    bad = mysql_store._fetchall(
        "SELECT TABLE_NAME, COLUMN_NAME, COLLATION_NAME "
        "FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND COLLATION_NAME IS NOT NULL "
        "AND COLLATION_NAME <> 'utf8mb4_bin'",
        (),
    )
    assert not bad, f"case-insensitive columns found: {[dict(r) for r in bad]}"


@pytest.mark.skipif(not DSN, reason="HORIZON_TEST_MYSQL_DSN not set")
def test_tenant_ids_differing_only_in_case_are_different_tenants(mysql_store):
    """The behavioural half of the collation guard."""
    from datetime import date as _date

    from horizon_monitor.memento import ItemKind

    base = f"pytest-case-{uuid.uuid4().hex[:8]}"
    lower, upper = base.lower(), base.upper()
    lo, up = mysql_store.scoped(lower), mysql_store.scoped(upper)
    try:
        lo.register_item(
            kind=ItemKind.HORIZON,
            title="lower tenant",
            created_valid=datetime(2026, 1, 1, tzinfo=UTC),
            end_date=_date(2030, 1, 1),
        )
        assert [i.title for i in lo.get_items()] == ["lower tenant"]
        assert not up.get_items(), "an upper-cased tenant id read another tenant's rows"
    finally:
        lo.erase_all()
        up.erase_all()
