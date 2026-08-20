"""SQLite backend — the zero-dependency default, and the schema migrator.

Schema v2 adds ``tenant_id`` to all four mission tables plus the two
cross-plane tenancy tables. For SQLite the tenant column is carried but the
original primary keys are kept: a SQLite store is single-tenant
(``'local'``) by definition — multi-tenant deployments use the MySQL
backend, whose fresh-created schema has composite ``(tenant_id, …)`` keys.
Reconciling the two would require rebuilding SQLite primary keys in place
(create-copy-swap), the one migration step that can destroy data; the
dialect difference is documented instead of reconciled.
"""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

from horizon_monitor.memento.backends._schema import SCHEMA_VERSION

_SCHEMA_VERSION = SCHEMA_VERSION

# Fresh v2 schema. `key` is backtick-quoted because it is a MySQL reserved
# word and the store's SQL is written once for both dialects (SQLite accepts
# backtick quoting for compatibility).
SCHEMA = """
CREATE TABLE IF NOT EXISTS mm_meta (
    tenant_id TEXT NOT NULL DEFAULT 'local',
    `key`     TEXT NOT NULL,
    value     TEXT NOT NULL,
    PRIMARY KEY (tenant_id, `key`)
);

CREATE TABLE IF NOT EXISTS mm_items (
    tenant_id       TEXT NOT NULL DEFAULT 'local',
    item_id         TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    parent_id       TEXT,
    title           TEXT NOT NULL,
    created_valid   TEXT NOT NULL,
    created_tx      TEXT NOT NULL,
    end_date        TEXT,
    revisit_date    TEXT,
    ttl_start       TEXT,
    ttl_end         TEXT,
    deadline_date   TEXT,
    deadline_kind   TEXT,
    gates_item_id   TEXT,
    age_budget_days INTEGER,
    stall_days      INTEGER,
    namespace       TEXT,
    amount          TEXT,
    status          TEXT NOT NULL DEFAULT 'open',
    superseded_by   TEXT
);

CREATE TABLE IF NOT EXISTS mm_events (
    tx_seq          INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL DEFAULT 'local',
    event_id        TEXT NOT NULL UNIQUE,
    item_id         TEXT NOT NULL,
    kind            TEXT NOT NULL,
    valid_time      TEXT NOT NULL,
    tx_time         TEXT NOT NULL,
    stage           TEXT,
    wait_or_touch   TEXT,
    provenance_source_system TEXT,
    provenance_native_id     TEXT,
    provenance_raw_timestamp TEXT,
    payload         TEXT NOT NULL DEFAULT '{}',
    correction_of   TEXT
);

CREATE TABLE IF NOT EXISTS mm_fires (
    tenant_id       TEXT NOT NULL DEFAULT 'local',
    item_id         TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    state           TEXT NOT NULL,
    PRIMARY KEY (tenant_id, item_id, signal_type)
);

CREATE INDEX IF NOT EXISTS idx_mm_events_item ON mm_events(tenant_id, item_id);

CREATE TABLE IF NOT EXISTS horizon_tenants (
    tenant_id     TEXT NOT NULL,
    display_label TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'active',
    created_at    TEXT NOT NULL,
    PRIMARY KEY (tenant_id)
);

CREATE TABLE IF NOT EXISTS horizon_api_keys (
    key_sha256    TEXT NOT NULL,
    tenant_id     TEXT NOT NULL,
    label         TEXT,
    created_at    TEXT NOT NULL,
    revoked_at    TEXT,
    PRIMARY KEY (key_sha256)
);

CREATE INDEX IF NOT EXISTS idx_horizon_api_keys_tenant ON horizon_api_keys(tenant_id);
"""

_MISSION_TABLES = ("mm_items", "mm_events", "mm_fires", "mm_meta")


class SqliteBackend:
    def __init__(self, store_path: str | Path) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.store_path), check_same_thread=False, timeout=30.0)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=30000")

    # ── contract ─────────────────────────────────────────────────────────
    def execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        return self._conn.execute(sql, params)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def ensure_live(self) -> None:
        """A file handle does not go stale. Deliberate no-op."""

    # ── schema ───────────────────────────────────────────────────────────
    def init_schema(self) -> None:
        v1 = self._is_v1_store()
        if v1:
            self._migrate_v1_to_v2()
        self._conn.executescript(SCHEMA)
        row = self._conn.execute(
            "SELECT value FROM mm_meta WHERE tenant_id = 'local' AND `key` = 'schema_version'"
        ).fetchone()
        if row is None:
            self._conn.execute(
                "INSERT INTO mm_meta (tenant_id, `key`, value) VALUES ('local', 'schema_version', ?)",
                (_SCHEMA_VERSION,),
            )
        self._conn.commit()

    def _is_v1_store(self) -> bool:
        """v1 = mm_items exists and has no tenant_id column."""
        has_items = self._conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='mm_items'"
        ).fetchone()
        if not has_items:
            return False
        cols = {r["name"] for r in self._conn.execute("PRAGMA table_info(mm_items)")}
        return "tenant_id" not in cols

    def _migrate_v1_to_v2(self) -> None:
        """Additive only: every row becomes tenant 'local'. A file backup is
        taken first; row counts are asserted unchanged afterwards. Gated by
        _is_v1_store(), so a second run is a no-op by construction."""
        backup = self.store_path.with_suffix(self.store_path.suffix + ".v1.bak")
        shutil.copy2(self.store_path, backup)

        before = {
            t: self._conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()["c"]  # noqa: S608
            for t in _MISSION_TABLES
        }
        try:
            for table in _MISSION_TABLES:
                self._conn.execute(
                    f"ALTER TABLE {table} ADD COLUMN tenant_id TEXT NOT NULL DEFAULT 'local'"  # noqa: S608
                )
            self._conn.execute(
                "UPDATE mm_meta SET value = ? WHERE `key` = 'schema_version'",
                (_SCHEMA_VERSION,),
            )
            after = {
                t: self._conn.execute(f"SELECT COUNT(*) AS c FROM {t}").fetchone()[
                    "c"
                ]  # noqa: S608
                for t in _MISSION_TABLES
            }
            if before != after:
                raise RuntimeError(
                    f"v1->v2 migration row-count drift: {before} != {after}; "
                    f"backup preserved at {backup}"
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
