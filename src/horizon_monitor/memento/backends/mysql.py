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
* collation      — ``utf8mb4_bin``, declared on EVERY table rather than
                   inherited from the database. A case-insensitive collation
                   makes ``tenant_id='Acme'`` match rows stored under ``'acme'`` —
                   a cross-tenant read that no single-tenant test can see. The
                   connection-level ``SET NAMES ... COLLATE utf8mb4_bin`` does
                   NOT protect this: comparing a column against a literal
                   resolves to the COLUMN's collation, so the table must carry
                   it. (Observed live: a database created without an explicit
                   COLLATE inherited ``utf8mb4_0900_ai_ci`` and an upper-cased
                   tenant id returned another tenant's rows.)
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

from horizon_monitor.memento.backends._schema import SCHEMA_VERSION

_log = logging.getLogger("horizon_monitor.memento.mysql")

_SCHEMA_VERSION = SCHEMA_VERSION

DDL = """
CREATE TABLE IF NOT EXISTS mm_meta (
    tenant_id   VARCHAR(64)  NOT NULL DEFAULT 'local',
    `key`       VARCHAR(64)  NOT NULL,
    value       TEXT         NOT NULL,
    PRIMARY KEY (tenant_id, `key`)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

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
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

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
    payload         TEXT         NOT NULL DEFAULT ('{}'),
    correction_of   CHAR(36)         NULL,
    PRIMARY KEY (tx_seq),
    UNIQUE KEY uq_mm_events_event (tenant_id, event_id),
    KEY idx_mm_events_item (tenant_id, item_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS mm_fires (
    tenant_id   VARCHAR(64) NOT NULL DEFAULT 'local',
    item_id     CHAR(36)    NOT NULL,
    signal_type VARCHAR(64) NOT NULL,
    state       TEXT        NOT NULL,
    PRIMARY KEY (tenant_id, item_id, signal_type)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS horizon_tenants (
    tenant_id     VARCHAR(64)  NOT NULL,
    display_label VARCHAR(128) NOT NULL,
    status        VARCHAR(16)  NOT NULL DEFAULT 'active',
    created_at    VARCHAR(32)  NOT NULL,
    PRIMARY KEY (tenant_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;

CREATE TABLE IF NOT EXISTS horizon_api_keys (
    key_sha256    CHAR(64)     NOT NULL,
    tenant_id     VARCHAR(64)  NOT NULL,
    label         VARCHAR(128)     NULL,
    created_at    VARCHAR(32)  NOT NULL,
    revoked_at    VARCHAR(32)      NULL,
    PRIMARY KEY (key_sha256),
    KEY idx_horizon_api_keys_tenant (tenant_id)
) ENGINE=InnoDB ROW_FORMAT=DYNAMIC
  DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin;
"""

_RETRIES = int(os.environ.get("MYSQL_CONN_RETRIES", "7"))
_DELAY = float(os.environ.get("MYSQL_CONN_DELAY", "2"))

# MySQL server error codes that will NEVER succeed on retry. Retrying these
# turns a clear misconfiguration into a multi-minute hang: with the default
# 7 attempts and exponential backoff, a wrong password costs ~126s before
# surfacing, long enough for a platform health check to kill the container
# mid-retry and present the operator with a crashloop instead of "access
# denied". These are canonical numeric codes, not text classification.
_PERMANENT_ERRNOS = frozenset(
    {
        1044,  # access denied for user to database
        1045,  # access denied (bad credentials)
        1049,  # unknown database
        1698,  # access denied (auth plugin)
        2059,  # authentication plugin cannot be loaded
    }
)

# OpenSSL emits this exact constant when CA verification fails; pymysql wraps
# it in a generic 2003, so the errno alone cannot distinguish "server is down"
# (retry) from "your CA is wrong" (never retries successfully).
_PERMANENT_TLS_MARKER = "CERTIFICATE_VERIFY_FAILED"


def _is_permanent(exc: BaseException) -> bool:
    """True when retrying cannot possibly help — fail fast and say why."""
    errno = exc.args[0] if getattr(exc, "args", None) else None
    if isinstance(errno, int) and errno in _PERMANENT_ERRNOS:
        return True
    return _PERMANENT_TLS_MARKER in str(exc)


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

    @staticmethod
    def _apply_session_settings(conn) -> None:
        """Session state that MUST survive every (re)connection.

        pymysql replays only `init_command` when it reconnects, so a setting
        applied once after connect is silently lost the moment the connection is
        rebuilt — and the session reverts to the server default. That is how the
        READ COMMITTED fix regressed in production: a long-lived, sparsely-used
        server reconnected on an idle timeout, fell back to REPEATABLE READ,
        pinned an MVCC snapshot, and went on serving rows that had since been
        deleted. Applying the settings here, from BOTH the connect path and the
        reconnect path, is what makes them durable.
        """
        with conn.cursor() as cur:
            cur.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
        conn.commit()

    def _connect_with_retry(self):
        import pymysql

        last: Exception | None = None
        for attempt in range(_RETRIES):
            try:
                conn = pymysql.connect(**self._params)
                self._apply_session_settings(conn)
                with conn.cursor() as cur:
                    # READ COMMITTED, not InnoDB's REPEATABLE READ default.
                    #
                    # The store holds ONE connection for the life of the
                    # process, and autocommit is off so multi-statement writes
                    # stay atomic. Under REPEATABLE READ that combination is a
                    # trap: the first SELECT pins an MVCC snapshot, and every
                    # later read on that connection returns the same frozen view
                    # until something commits. A server that only reads —
                    # clock_status in a long session — would report the same
                    # numbers forever while other processes recorded progress.
                    # A clock that silently stops is the exact failure this
                    # plane exists to prevent, so reads must see what is true
                    # NOW, not what was true when the process first looked.
                    cur.execute("SELECT 1")
                    cur.fetchone()
                conn.commit()
                return conn
            except Exception as exc:  # noqa: BLE001
                last = exc
                if _is_permanent(exc):
                    # Credentials, database name, or TLS trust are wrong.
                    # No amount of waiting fixes any of them.
                    raise RuntimeError(
                        f"mysql connection refused for a permanent reason " f"(not retried): {exc}"
                    ) from exc
                if attempt < _RETRIES - 1:
                    wait = _DELAY * (2**attempt)
                    _log.warning("mysql connect failed (%s); retry in %.1fs", exc, wait)
                    time.sleep(wait)
        raise RuntimeError(f"mysql connection failed after {_RETRIES} attempts") from last

    # ── contract ─────────────────────────────────────────────────────────
    def execute(self, sql: str, params: tuple = ()):
        cur = self._conn.cursor()
        cur.execute(sql.replace("?", "%s"), params or None)
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
            # reconnect=False deliberately: pymysql's transparent reconnect does
            # NOT re-apply session settings (see _apply_session_settings), so we
            # own the reconnect and rebuild the session ourselves.
            self._conn.ping(reconnect=False)
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
