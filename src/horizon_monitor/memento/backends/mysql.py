"""MySQL backend — optional extra for durable multi-tenant deployments.

Requires ``pip install horizon-monitor[mysql]`` (PyMySQL). Configuration is
one DSN plus a CA certificate:

    HORIZON_MEMENTO_STORE_DSN   mysql://user:pass@host:port/dbname
    HORIZON_MYSQL_SSL_CA        path to the server's CA certificate (PEM), or
    HORIZON_MYSQL_SSL_CA_B64    the same PEM base64-encoded (for platforms
                                whose filesystems are ephemeral — the PEM is
                                materialised to a temp file at startup)

TLS verification is MANDATORY: this backend refuses to connect without a CA.
A hosted mission store crosses networks an operator does not control, and an
unverified TLS connection is indistinguishable from a verified one right up
until it is intercepted.

Dialect notes (each mirrors a reviewed defect class in the deployment spec):

* placeholders   — the store's SQL is written once with ``?``; converted to
                   ``%s`` mechanically here (no SQL string in the store
                   contains a literal ``?``)
* ``key``        — MySQL reserved word; the store's SQL backtick-quotes it,
                   which SQLite also accepts
* upserts        — SELECT-then-INSERT-or-UPDATE inside the store's own
                   transaction; never ``ON DUPLICATE KEY UPDATE``
* timestamps     — stay VARCHAR: MySQL DATETIME drops the UTC offset the
                   store writes via ``isoformat()``
* amounts        — stay VARCHAR: Decimal round-trips as exact text
* collation      — ``utf8mb4_bin``: case-insensitive collation would collide
                   tenant ids differing only in case
* liveness       — managed MySQL closes idle connections (wait_timeout);
                   ``ensure_live()`` pings and reconnects with backoff, and is
                   only called at transaction/read boundaries
"""

from __future__ import annotations

import base64
import logging
import os
import tempfile
import time
import urllib.parse

_log = logging.getLogger("horizon_monitor.memento.mysql")

_SCHEMA_VERSION = "2"

DDL = """
CREATE TABLE IF NOT EXISTS mm_meta (
    tenant_id   VARCHAR(64)  NOT NULL DEFAULT 'local',
    `key`       VARCHAR(64)  NOT NULL,
    value       TEXT         NOT NULL,
    PRIMARY KEY (tenant_id, `key`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS mm_items (
    tenant_id       VARCHAR(64)  NOT NULL DEFAULT 'local',
    item_id         CHAR(36)     NOT NULL,
    kind            VARCHAR(32)  NOT NULL,
    parent_id       CHAR(36)         NULL,
    title           VARCHAR(512) NOT NULL,
    created_valid   VARCHAR(32)  NOT NULL,
    created_tx      VARCHAR(32)  NOT NULL,
    end_date        CHAR(10)         NULL,
    revisit_date    CHAR(10)         NULL,
    ttl_start       CHAR(10)         NULL,
    ttl_end         CHAR(10)         NULL,
    deadline_date   CHAR(10)         NULL,
    deadline_kind   VARCHAR(32)      NULL,
    gates_item_id   CHAR(36)         NULL,
    age_budget_days INT              NULL,
    stall_days      INT              NULL,
    namespace       VARCHAR(64)      NULL,
    amount          VARCHAR(64)      NULL,
    status          VARCHAR(32)  NOT NULL DEFAULT 'open',
    superseded_by   CHAR(36)         NULL,
    PRIMARY KEY (tenant_id, item_id),
    KEY idx_mm_items_parent (tenant_id, parent_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS mm_events (
    tx_seq          BIGINT       NOT NULL AUTO_INCREMENT,
    tenant_id       VARCHAR(64)  NOT NULL DEFAULT 'local',
    event_id        CHAR(36)     NOT NULL,
    item_id         CHAR(36)     NOT NULL,
    kind            VARCHAR(32)  NOT NULL,
    valid_time      VARCHAR(32)  NOT NULL,
    tx_time         VARCHAR(32)  NOT NULL,
    stage           VARCHAR(64)      NULL,
    wait_or_touch   VARCHAR(16)      NULL,
    provenance_source_system VARCHAR(64)  NULL,
    provenance_native_id     VARCHAR(191) NULL,
    provenance_raw_timestamp VARCHAR(64)  NULL,
    payload         TEXT         NOT NULL,
    correction_of   CHAR(36)         NULL,
    PRIMARY KEY (tx_seq),
    UNIQUE KEY uq_mm_events_event (tenant_id, event_id),
    KEY idx_mm_events_item (tenant_id, item_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS mm_fires (
    tenant_id   VARCHAR(64) NOT NULL DEFAULT 'local',
    item_id     CHAR(36)    NOT NULL,
    signal_type VARCHAR(64) NOT NULL,
    state       TEXT        NOT NULL,
    PRIMARY KEY (tenant_id, item_id, signal_type)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS horizon_tenants (
    tenant_id     VARCHAR(64)  NOT NULL,
    display_label VARCHAR(128) NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'active',
    created_at    VARCHAR(32)  NOT NULL,
    PRIMARY KEY (tenant_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;

CREATE TABLE IF NOT EXISTS horizon_api_keys (
    key_sha256    CHAR(64)     NOT NULL,
    tenant_id     VARCHAR(64)  NOT NULL,
    label         VARCHAR(128)     NULL,
    created_at    VARCHAR(32)  NOT NULL,
    revoked_at    VARCHAR(32)      NULL,
    PRIMARY KEY (key_sha256),
    KEY idx_horizon_api_keys_tenant (tenant_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC;
"""

_RETRIES = int(os.environ.get("MYSQL_CONN_RETRIES", "7"))
_DELAY = float(os.environ.get("MYSQL_CONN_DELAY", "2"))


def _resolve_ca_path() -> str:
    path = os.environ.get("HORIZON_MYSQL_SSL_CA")
    if path:
        return path
    b64 = os.environ.get("HORIZON_MYSQL_SSL_CA_B64")
    if b64:
        tmp = tempfile.NamedTemporaryFile(
            mode="wb", suffix=".pem", delete=False, prefix="horizon_ca_"
        )
        tmp.write(base64.b64decode(b64))
        tmp.close()
        return tmp.name
    raise RuntimeError(
        "MySQL backend requires TLS verification: set HORIZON_MYSQL_SSL_CA "
        "(path to the server CA PEM) or HORIZON_MYSQL_SSL_CA_B64 (base64 PEM). "
        "Refusing to connect unverified."
    )


class MySQLBackend:
    ph = "%s"

    def __init__(self, dsn: str) -> None:
        try:
            import pymysql  # noqa: F401
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "MySQL backend requires PyMySQL: pip install horizon-monitor[mysql]"
            ) from exc
        self._params = self._parse(dsn)
        self._conn = self._connect_with_retry()

    @staticmethod
    def _parse(dsn: str) -> dict:
        u = urllib.parse.urlparse(dsn)
        if u.scheme != "mysql":
            raise ValueError(f"unsupported DSN scheme {u.scheme!r}; expected mysql://")
        if not (u.hostname and u.username and u.path.lstrip("/")):
            raise ValueError("DSN must be mysql://user:pass@host:port/dbname")
        import pymysql.cursors

        return {
            "host": u.hostname,
            "port": u.port or 3306,
            "user": urllib.parse.unquote(u.username),
            "password": urllib.parse.unquote(u.password or ""),
            "database": u.path.lstrip("/"),
            "charset": "utf8mb4",
            "init_command": "SET NAMES utf8mb4 COLLATE utf8mb4_bin",
            "cursorclass": pymysql.cursors.DictCursor,
            "ssl": {"ca": _resolve_ca_path()},
            "connect_timeout": 30,
            "read_timeout": 60,
            "write_timeout": 60,
            "autocommit": False,
        }

    def _connect_with_retry(self):
        import pymysql

        last: Exception | None = None
        for attempt in range(_RETRIES):
            try:
                conn = pymysql.connect(**self._params)
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
                return conn
            except Exception as exc:  # noqa: BLE001
                last = exc
                if attempt < _RETRIES - 1:
                    wait = _DELAY * (2**attempt)
                    _log.warning("mysql connect failed (%s); retry in %.1fs", exc, wait)
                    time.sleep(wait)
        raise RuntimeError(f"mysql connection failed after {_RETRIES} attempts") from last

    # ── contract ─────────────────────────────────────────────────────────
    def execute(self, sql: str, params: tuple = ()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), params)
        return cur

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def ensure_live(self) -> None:
        """Ping; on a dead connection, reconnect with backoff. Only called at
        transaction/read boundaries — never mid-transaction (see package
        docstring: a mid-transaction reconnect silently drops txn state)."""
        try:
            self._conn.ping(reconnect=True)
        except Exception:  # noqa: BLE001
            _log.warning("mysql connection lost; reconnecting")
            self._conn = self._connect_with_retry()

    # ── schema ───────────────────────────────────────────────────────────
    def init_schema(self) -> None:
        self.ensure_live()
        try:
            for stmt in DDL.split(";"):
                if stmt.strip():
                    self._conn.cursor().execute(stmt)
            cur = self._conn.cursor()
            cur.execute(
                "SELECT value FROM mm_meta WHERE tenant_id = 'local' AND `key` = 'schema_version'"
            )
            if cur.fetchone() is None:
                self._conn.cursor().execute(
                    "INSERT INTO mm_meta (tenant_id, `key`, value) "
                    "VALUES ('local', 'schema_version', %s)",
                    (_SCHEMA_VERSION,),
                )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
