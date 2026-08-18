"""SQLite-backed store for the Memento Mori mission plane.

Per MEMENTO_MORI_TECH_SPEC.md §3 and memento_store_intent.yaml. Same
storage/ conventions as horizon_monitor.storage.sqlite: stdlib sqlite3, WAL
mode, no external dependencies. This store is deliberately separate from
the conversation plane's PersistentDynamicsStore — a distinct file, never
read by the conversation plane, and the mission plane never reads
conversation content (horizon_memento_mori_intent.yaml::local_first_privacy).

Validation runs BEFORE any row is written, so a rejected write raises
before touching the database — the store is left byte-identical
(memento_store_intent.yaml::schema_rejections_total). The one write-time
host-clock read (tx_time / created_tx, when THIS store learned a fact) is
intentional and distinct from the engine's evaluation path, which never
reads the ambient clock (memento_engine_intent.yaml::pure_function_injected_time).
"""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from horizon_monitor.memento.errors import (
    ArtifactProvenanceRequiredError,
    DuplicateRootError,
    NonFiniteRootError,
    PersonNamespaceUnflaggedError,
    RootlessItemError,
    UndatedDeferralError,
)
from horizon_monitor.memento.models import (
    ClockEvent,
    EventKind,
    Item,
    ItemKind,
    Provenance,
    StoreSnapshot,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS mm_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS mm_items (
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
    item_id         TEXT NOT NULL,
    signal_type     TEXT NOT NULL,
    state           TEXT NOT NULL,
    PRIMARY KEY (item_id, signal_type)
);

CREATE INDEX IF NOT EXISTS idx_mm_events_item ON mm_events(item_id);
"""

_SCHEMA_VERSION = "1"


def _iso(dt: datetime | date | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def _parse_dt(s: str | None) -> datetime | None:
    if s is None:
        return None
    return datetime.fromisoformat(s)


def _parse_date(s: str | None) -> date | None:
    if s is None:
        return None
    return date.fromisoformat(s)


class MementoStore:
    """A local, append-only-discipline SQLite store for one horizon tree.

    Thread-safe via an internal lock, mirroring
    horizon_monitor.storage.sqlite.PersistentDynamicsStore's pattern.
    Multiple independent MementoStore instances may point at the same file
    (multiple agent sessions); SQLite's own writer serialization plus a
    busy_timeout handle cross-connection concurrency (test S-9).
    """

    def __init__(self, store_path: str | Path) -> None:
        self.store_path = Path(store_path)
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._conn = self._connect()
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.store_path), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(SCHEMA)
            self._conn.execute(
                "INSERT OR IGNORE INTO mm_meta (key, value) VALUES ('schema_version', ?)",
                (_SCHEMA_VERSION,),
            )
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    @contextmanager
    def _txn(self) -> Generator[sqlite3.Connection, None, None]:
        with self._lock:
            try:
                yield self._conn
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    # ── Items ────────────────────────────────────────────────────────────

    def register_item(
        self,
        kind: ItemKind,
        title: str,
        created_valid: datetime,
        parent_id: str | None = None,
        end_date: date | None = None,
        revisit_date: date | None = None,
        ttl_start: date | None = None,
        ttl_end: date | None = None,
        deadline_date: date | None = None,
        deadline_kind: str | None = None,
        gates_item_id: str | None = None,
        age_budget_days: int | None = None,
        stall_days: int | None = None,
        namespace: str | None = None,
        person_namespace_confirmed: bool = False,
        amount: Decimal | None = None,
    ) -> str:
        """Validate then write a new Item. Raises before writing on any
        schema violation (memento_store_intent.yaml::schema_rejections_total)."""
        with self._lock:
            self._validate_item(
                kind=kind,
                parent_id=parent_id,
                end_date=end_date,
                revisit_date=revisit_date,
                namespace=namespace,
                person_namespace_confirmed=person_namespace_confirmed,
            )

            resolved_namespace = namespace
            if kind == ItemKind.ENTITY and resolved_namespace is None:
                resolved_namespace = "slot"

            item_id = str(uuid.uuid4())
            created_tx = datetime.now(timezone.utc)
            try:
                self._conn.execute(
                    """
                    INSERT INTO mm_items (
                        item_id, kind, parent_id, title, created_valid, created_tx,
                        end_date, revisit_date, ttl_start, ttl_end, deadline_date,
                        deadline_kind, gates_item_id, age_budget_days, stall_days,
                        namespace, amount, status, superseded_by
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        item_id,
                        kind.value,
                        parent_id,
                        title,
                        _iso(created_valid),
                        _iso(created_tx),
                        _iso(end_date),
                        _iso(revisit_date),
                        _iso(ttl_start),
                        _iso(ttl_end),
                        _iso(deadline_date),
                        deadline_kind,
                        gates_item_id,
                        age_budget_days,
                        stall_days,
                        resolved_namespace,
                        str(amount) if amount is not None else None,
                        "open",
                        None,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            return item_id

    def _validate_item(
        self,
        kind: ItemKind,
        parent_id: str | None,
        end_date: date | None,
        revisit_date: date | None,
        namespace: str | None,
        person_namespace_confirmed: bool,
    ) -> None:
        if kind == ItemKind.HORIZON:
            if end_date is None:
                raise NonFiniteRootError()
            if self._has_root():
                raise DuplicateRootError()
            return  # HORIZON has no parent to validate

        # every non-root kind must resolve a parent chain that terminates
        # at the single root (finite_rooted_tree)
        self._require_rooted(parent_id)

        if kind == ItemKind.DEFERRAL and revisit_date is None:
            raise UndatedDeferralError()

        if kind == ItemKind.ENTITY and namespace == "person" and not person_namespace_confirmed:
            raise PersonNamespaceUnflaggedError()

    def _has_root(self) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM mm_items WHERE kind = ? LIMIT 1", (ItemKind.HORIZON.value,)
        ).fetchone()
        return row is not None

    def _require_rooted(self, parent_id: str | None) -> None:
        if parent_id is None:
            raise RootlessItemError()
        seen: set[str] = set()
        current = parent_id
        while current is not None:
            if current in seen:
                raise RootlessItemError()  # cycle — never terminates at root
            seen.add(current)
            row = self._conn.execute(
                "SELECT kind, parent_id FROM mm_items WHERE item_id = ?", (current,)
            ).fetchone()
            if row is None:
                raise RootlessItemError()
            if row["kind"] == ItemKind.HORIZON.value:
                return  # terminates at root
            current = row["parent_id"]
        raise RootlessItemError()

    def get_item(self, item_id: str) -> Item | None:
        row = self._conn.execute("SELECT * FROM mm_items WHERE item_id = ?", (item_id,)).fetchone()
        return self._row_to_item(row) if row else None

    def get_items(self) -> list[Item]:
        rows = self._conn.execute("SELECT * FROM mm_items ORDER BY item_id").fetchall()
        return [self._row_to_item(r) for r in rows]

    def get_root(self) -> Item | None:
        row = self._conn.execute(
            "SELECT * FROM mm_items WHERE kind = ? LIMIT 1", (ItemKind.HORIZON.value,)
        ).fetchone()
        return self._row_to_item(row) if row else None

    def update_item_status(
        self, item_id: str, status: str, superseded_by: str | None = None
    ) -> None:
        """mm_items rows mutate only status/superseded_by (append_only_bitemporal)."""
        with self._txn() as conn:
            conn.execute(
                "UPDATE mm_items SET status = ?, superseded_by = ? WHERE item_id = ?",
                (status, superseded_by, item_id),
            )

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> Item:
        return Item(
            item_id=row["item_id"],
            kind=ItemKind(row["kind"]),
            parent_id=row["parent_id"],
            title=row["title"],
            created_valid=_parse_dt(row["created_valid"]),
            created_tx=_parse_dt(row["created_tx"]),
            end_date=_parse_date(row["end_date"]),
            revisit_date=_parse_date(row["revisit_date"]),
            ttl_start=_parse_date(row["ttl_start"]),
            ttl_end=_parse_date(row["ttl_end"]),
            deadline_date=_parse_date(row["deadline_date"]),
            deadline_kind=row["deadline_kind"],
            gates_item_id=row["gates_item_id"],
            age_budget_days=row["age_budget_days"],
            stall_days=row["stall_days"],
            namespace=row["namespace"],
            amount=Decimal(row["amount"]) if row["amount"] is not None else None,
            status=row["status"],
            superseded_by=row["superseded_by"],
        )

    # ── Events ───────────────────────────────────────────────────────────

    def record_event(
        self,
        item_id: str,
        kind: EventKind,
        valid_time: datetime,
        tx_time: datetime | None = None,
        stage: str | None = None,
        wait_or_touch: str | None = None,
        provenance: Provenance | None = None,
        payload: dict | None = None,
        correction_of: str | None = None,
    ) -> str:
        """Append an event row. mm_events is insert-only; corrections
        supersede via correction_of, never overwrite (append_only_bitemporal)."""
        with self._lock:
            if kind == EventKind.ARTIFACT:
                self._validate_provenance(provenance)

            event_id = str(uuid.uuid4())
            resolved_tx_time = tx_time or datetime.now(timezone.utc)
            try:
                self._conn.execute(
                    """
                    INSERT INTO mm_events (
                        event_id, item_id, kind, valid_time, tx_time, stage,
                        wait_or_touch, provenance_source_system, provenance_native_id,
                        provenance_raw_timestamp, payload, correction_of
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        event_id,
                        item_id,
                        kind.value,
                        _iso(valid_time),
                        _iso(resolved_tx_time),
                        stage,
                        wait_or_touch,
                        provenance.source_system if provenance else None,
                        provenance.native_id if provenance else None,
                        _iso(provenance.raw_timestamp) if provenance else None,
                        json.dumps(payload or {}),
                        correction_of,
                    ),
                )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise
            return event_id

    @staticmethod
    def _validate_provenance(provenance: Provenance | None) -> None:
        if provenance is None:
            raise ArtifactProvenanceRequiredError(("source_system", "native_id", "raw_timestamp"))
        missing = tuple(
            field
            for field, value in (
                ("source_system", provenance.source_system),
                ("native_id", provenance.native_id),
                ("raw_timestamp", provenance.raw_timestamp),
            )
            if not value
        )
        if missing:
            raise ArtifactProvenanceRequiredError(missing)

    def get_events(self, item_id: str | None = None) -> list[ClockEvent]:
        if item_id is not None:
            rows = self._conn.execute(
                "SELECT * FROM mm_events WHERE item_id = ? ORDER BY tx_seq", (item_id,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM mm_events ORDER BY tx_seq").fetchall()
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> ClockEvent:
        provenance = None
        if row["provenance_source_system"] is not None:
            provenance = Provenance(
                source_system=row["provenance_source_system"],
                native_id=row["provenance_native_id"],
                raw_timestamp=_parse_dt(row["provenance_raw_timestamp"]),
            )
        return ClockEvent(
            event_id=row["event_id"],
            item_id=row["item_id"],
            kind=EventKind(row["kind"]),
            valid_time=_parse_dt(row["valid_time"]),
            tx_time=_parse_dt(row["tx_time"]),
            stage=row["stage"],
            wait_or_touch=row["wait_or_touch"],
            provenance=provenance,
            payload=json.loads(row["payload"]),
            correction_of=row["correction_of"],
            tx_seq=row["tx_seq"],
        )

    # ── Signal fire-state (mm_fires) ────────────────────────────────────

    def get_fire_state(self, item_id: str, signal_type: str) -> dict | None:
        row = self._conn.execute(
            "SELECT state FROM mm_fires WHERE item_id = ? AND signal_type = ?",
            (item_id, signal_type),
        ).fetchone()
        return json.loads(row["state"]) if row else None

    def set_fire_state(self, item_id: str, signal_type: str, state: dict) -> None:
        with self._txn() as conn:
            conn.execute(
                """
                INSERT INTO mm_fires (item_id, signal_type, state) VALUES (?, ?, ?)
                ON CONFLICT(item_id, signal_type) DO UPDATE SET state = excluded.state
                """,
                (item_id, signal_type, json.dumps(state)),
            )

    def get_all_fire_states(self) -> list[tuple[tuple[str, str], dict]]:
        rows = self._conn.execute(
            "SELECT item_id, signal_type, state FROM mm_fires ORDER BY item_id, signal_type"
        ).fetchall()
        return [((r["item_id"], r["signal_type"]), json.loads(r["state"])) for r in rows]

    # ── Snapshot for the pure evaluation engine ─────────────────────────

    def snapshot(self) -> StoreSnapshot:
        """A frozen point-in-time view for engine.evaluate(). Collections
        are ordered by stable keys so two snapshots taken of an unchanged
        store always compare/serialize identically."""
        items = tuple(self.get_items())
        events = tuple(self.get_events())
        fire_states = tuple(self.get_all_fire_states())
        return StoreSnapshot(items=items, events=events, fire_states=fire_states)
