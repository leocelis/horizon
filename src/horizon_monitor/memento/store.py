"""Backend-agnostic store for the Memento Mori mission plane.

Per MEMENTO_MORI_TECH_SPEC.md §3 and memento_store_intent.yaml. SQLite is
the zero-dependency default (stdlib sqlite3, WAL mode); MySQL is an
optional extra for durable multi-tenant deployments (see
memento/backends/). This store is deliberately separate from the
conversation plane's PersistentDynamicsStore — a distinct file/database,
never read by the conversation plane, and the mission plane never reads
conversation content (horizon_memento_mori_intent.yaml::local_first_privacy).

Tenancy: a MementoStore IS a tenant scope. The default tenant is
``'local'``, so single-operator installs and the entire pre-tenancy API are
unchanged. ``store.scoped(tenant_id)`` returns a lightweight view over the
SAME backend connection and lock, predicated on another tenant — every SQL
statement in this file carries the scope's tenant_id, so cross-tenant reads
and writes are impossible to express, not merely avoided. Multi-tenant
callers (the MCP layer) resolve a tenant from authentication and call
through the scope; erasure (``erase_all``) is scoped by construction, so
one tenant's erasure request can never touch another's history.

Validation runs BEFORE any row is written, so a rejected write raises
before touching the database — the store is left byte-identical
(memento_store_intent.yaml::schema_rejections_total). The one write-time
host-clock read (tx_time / created_tx, when THIS store learned a fact) is
intentional and distinct from the engine's evaluation path, which never
reads the ambient clock (memento_engine_intent.yaml::pure_function_injected_time).
"""

from __future__ import annotations

import json
import threading
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from horizon_monitor.memento.backends import resolve_backend
from horizon_monitor.memento.errors import (
    ArtifactProvenanceRequiredError,
    DuplicateRootError,
    KeyAlreadyBoundError,
    NonFiniteRootError,
    PersonNamespaceUnflaggedError,
    RetentionScopeError,
    RootlessItemError,
    StoreCorruptionError,
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

LOCAL_TENANT = "local"


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
    """A tenant-scoped, append-only-discipline store for one horizon tree
    per tenant.

    Thread-safe via an internal RLock. Multiple independent MementoStore
    instances may point at the same SQLite file (multiple agent sessions);
    SQLite's own writer serialization plus a busy_timeout handle
    cross-connection concurrency (test S-9). For MySQL, one backend
    connection per process (the deployment spec's connection budget);
    scopes share it.
    """

    def __init__(
        self,
        store_path: str | Path | None = None,
        *,
        dsn: str | None = None,
        tenant_id: str = LOCAL_TENANT,
    ) -> None:
        self.store_path = Path(store_path) if store_path is not None else None
        self._tenant = tenant_id
        # RLock, not Lock: register_item holds the lock and then calls
        # _validate_item -> _has_root -> _fetchone, which acquires it again.
        # Pre-tenancy those reads went straight to the connection, so a plain
        # Lock sufficed; routing every read through the scoped _fetchone made
        # the path re-entrant. A Lock here deadlocks on the first write.
        self._lock = threading.RLock()
        self._b = resolve_backend(store_path=store_path, dsn=dsn)
        # Only the store that opened the backend may close it. Scopes are views
        # over the same connection (see scoped()), so closing one must not tear
        # the connection out from under the others.
        self._owns_backend = True
        with self._lock:
            self._b.init_schema()

    @property
    def tenant_id(self) -> str:
        return self._tenant

    def scoped(self, tenant_id: str) -> MementoStore:
        """A view over the SAME backend connection, predicated on another
        tenant. Cheap enough to create per request; the connection count
        stays at one per process."""
        clone = object.__new__(MementoStore)
        clone.store_path = self.store_path
        clone._tenant = tenant_id
        clone._lock = self._lock
        clone._b = self._b
        clone._owns_backend = False  # a view never closes the shared connection
        return clone

    def close(self) -> None:
        """Close the backend — but only from the store that opened it.

        Calling close() on a scope returned by :meth:`scoped` is a deliberate
        no-op. Scopes share one connection (that is the point: one connection
        per process, not per tenant), so honouring close() on a view would tear
        the connection out from under the owner and every sibling scope. In the
        hosted server, where a scope is created per request, that would take
        every tenant offline until the next reconnect.
        """
        if not self._owns_backend:
            return
        with self._lock:
            self._b.close()

    # ── plumbing ──────────────────────────────────────────────────────────

    @contextmanager
    def _txn(self) -> Generator:
        """ensure_live() runs at the boundary, before the first statement —
        never mid-transaction, where a reconnect would silently drop the
        open transaction's state."""
        with self._lock:
            self._b.ensure_live()
            try:
                yield self._b
                self._b.commit()
            except Exception:
                self._b.rollback()
                raise

    def _fetchone(self, sql: str, params: tuple = ()):
        with self._lock:
            self._b.ensure_live()
            return self._b.execute(sql, params).fetchone()

    def _fetchall(self, sql: str, params: tuple = ()):
        with self._lock:
            self._b.ensure_live()
            return self._b.execute(sql, params).fetchall()

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
            self._b.ensure_live()
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
                self._b.execute(
                    """
                    INSERT INTO mm_items (
                        tenant_id, item_id, kind, parent_id, title, created_valid,
                        created_tx, end_date, revisit_date, ttl_start, ttl_end,
                        deadline_date, deadline_kind, gates_item_id, age_budget_days,
                        stall_days, namespace, amount, status, superseded_by
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        self._tenant,
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
                self._b.commit()
            except Exception:
                self._b.rollback()
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
        row = self._fetchone(
            "SELECT 1 FROM mm_items WHERE tenant_id = ? AND kind = ? LIMIT 1",
            (self._tenant, ItemKind.HORIZON.value),
        )
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
            row = self._fetchone(
                "SELECT kind, parent_id FROM mm_items WHERE tenant_id = ? AND item_id = ?",
                (self._tenant, current),
            )
            if row is None:
                raise RootlessItemError()
            if row["kind"] == ItemKind.HORIZON.value:
                return  # terminates at root
            current = row["parent_id"]
        raise RootlessItemError()

    def get_item(self, item_id: str) -> Item | None:
        row = self._fetchone(
            "SELECT * FROM mm_items WHERE tenant_id = ? AND item_id = ?",
            (self._tenant, item_id),
        )
        return self._row_to_item(row) if row else None

    def get_items(self) -> list[Item]:
        rows = self._fetchall(
            "SELECT * FROM mm_items WHERE tenant_id = ? ORDER BY item_id",
            (self._tenant,),
        )
        return [self._row_to_item(r) for r in rows]

    def get_root(self) -> Item | None:
        row = self._fetchone(
            "SELECT * FROM mm_items WHERE tenant_id = ? AND kind = ? LIMIT 1",
            (self._tenant, ItemKind.HORIZON.value),
        )
        return self._row_to_item(row) if row else None

    def update_item_status(
        self, item_id: str, status: str, superseded_by: str | None = None
    ) -> None:
        """mm_items rows mutate only status/superseded_by (append_only_bitemporal)."""
        with self._txn() as b:
            b.execute(
                "UPDATE mm_items SET status = ?, superseded_by = ? "
                "WHERE tenant_id = ? AND item_id = ?",
                (status, superseded_by, self._tenant, item_id),
            )

    REDACTED_TITLE = "[redacted — retention]"

    def redact_person_display_name(self, item_id: str) -> None:
        """Replace a person-namespace entity's display name with a placeholder.

        PRD §8 keeps a third party's display name only for the open wait, with
        short retention after it ends. The engine FLAGS eligibility
        (``ItemClock.retention_due``); this is the explicit operation that acts
        on it, so the destruction is always a recorded decision rather than a
        silent background sweep. Latency measurement is unaffected — only the
        name goes.
        """
        with self._txn() as b:
            row = b.execute(
                "SELECT namespace FROM mm_items WHERE tenant_id = ? AND item_id = ?",
                (self._tenant, item_id),
            ).fetchone()
            if row is None:
                raise StoreCorruptionError(item_id, "<no such item in this tenant scope>")
            if row["namespace"] != "person":
                raise RetentionScopeError(item_id, row["namespace"])
            b.execute(
                "UPDATE mm_items SET title = ? WHERE tenant_id = ? AND item_id = ?",
                (self.REDACTED_TITLE, self._tenant, item_id),
            )

    def erase_all(self) -> dict[str, int]:
        """Destroy every mission record in THIS TENANT's scope. The
        right-to-erasure path.

        Erasure is deliberately **all-or-nothing within the tenant**. There is
        no selective row delete and there must not be one: ``mm_events`` is
        append-only precisely so that any number the plane reports traces back
        to a fact the operator recorded. A per-row delete would be a
        history-rewriting tool wearing a privacy label — it could quietly
        remove the one stall that made a mission look bad, and every surviving
        number would still be presented with full authority.

        Tenant-scoped by construction: every DELETE carries this scope's
        tenant_id, so one tenant's erasure request can never touch another
        tenant's history. If a ``horizon_tenants`` row exists for this tenant
        its status becomes ``'erased'`` in the same transaction, so an erased
        tenant is distinguishable from one that never existed.

        Complements :meth:`redact_person_display_name`, which removes one third
        party's display name while preserving the latency measurement. This
        removes the records themselves. The schema and its ``schema_version``
        row survive, so the store stays usable and a fresh horizon can be
        registered immediately afterwards.

        Returns per-table counts of what was destroyed, so the caller can record
        the erasure rather than merely perform it.
        """
        counts: dict[str, int] = {}
        with self._txn() as b:
            for table in ("mm_fires", "mm_events", "mm_items"):
                counts[table] = b.execute(
                    f"SELECT COUNT(*) AS c FROM {table} WHERE tenant_id = ?",  # noqa: S608
                    (self._tenant,),
                ).fetchone()["c"]
                b.execute(
                    f"DELETE FROM {table} WHERE tenant_id = ?",  # noqa: S608
                    (self._tenant,),
                )
            counts["mm_meta"] = b.execute(
                "SELECT COUNT(*) AS c FROM mm_meta "
                "WHERE tenant_id = ? AND `key` != 'schema_version'",
                (self._tenant,),
            ).fetchone()["c"]
            b.execute(
                "DELETE FROM mm_meta WHERE tenant_id = ? AND `key` != 'schema_version'",
                (self._tenant,),
            )
            b.execute(
                "UPDATE horizon_tenants SET status = 'erased' WHERE tenant_id = ?",
                (self._tenant,),
            )
        return counts

    @staticmethod
    def _row_to_item(row) -> Item:
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
            self._b.ensure_live()
            if kind == EventKind.ARTIFACT:
                self._validate_provenance(provenance)

            event_id = str(uuid.uuid4())
            resolved_tx_time = tx_time or datetime.now(timezone.utc)
            try:
                self._b.execute(
                    """
                    INSERT INTO mm_events (
                        tenant_id, event_id, item_id, kind, valid_time, tx_time,
                        stage, wait_or_touch, provenance_source_system,
                        provenance_native_id, provenance_raw_timestamp, payload,
                        correction_of
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        self._tenant,
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
                self._b.commit()
            except Exception:
                self._b.rollback()
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
            rows = self._fetchall(
                "SELECT * FROM mm_events WHERE tenant_id = ? AND item_id = ? ORDER BY tx_seq",
                (self._tenant, item_id),
            )
        else:
            rows = self._fetchall(
                "SELECT * FROM mm_events WHERE tenant_id = ? ORDER BY tx_seq",
                (self._tenant,),
            )
        return [self._row_to_event(r) for r in rows]

    @staticmethod
    def _row_to_event(row) -> ClockEvent:
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
        row = self._fetchone(
            "SELECT state FROM mm_fires WHERE tenant_id = ? AND item_id = ? AND signal_type = ?",
            (self._tenant, item_id, signal_type),
        )
        return json.loads(row["state"]) if row else None

    def set_fire_state(self, item_id: str, signal_type: str, state: dict) -> None:
        """SELECT-then-INSERT-or-UPDATE inside one transaction — deliberately
        NOT a dialect upsert (``ON CONFLICT`` is SQLite-only and
        ``ON DUPLICATE KEY UPDATE`` hides insert-vs-update intent)."""
        with self._txn() as b:
            existing = b.execute(
                "SELECT 1 FROM mm_fires WHERE tenant_id = ? AND item_id = ? AND signal_type = ?",
                (self._tenant, item_id, signal_type),
            ).fetchone()
            if existing:
                b.execute(
                    "UPDATE mm_fires SET state = ? "
                    "WHERE tenant_id = ? AND item_id = ? AND signal_type = ?",
                    (json.dumps(state), self._tenant, item_id, signal_type),
                )
            else:
                b.execute(
                    "INSERT INTO mm_fires (tenant_id, item_id, signal_type, state) "
                    "VALUES (?, ?, ?, ?)",
                    (self._tenant, item_id, signal_type, json.dumps(state)),
                )

    def get_all_fire_states(self) -> list[tuple[tuple[str, str], dict]]:
        rows = self._fetchall(
            "SELECT item_id, signal_type, state FROM mm_fires "
            "WHERE tenant_id = ? ORDER BY item_id, signal_type",
            (self._tenant,),
        )
        return [((r["item_id"], r["signal_type"]), json.loads(r["state"])) for r in rows]

    # ── Tenancy (horizon_tenants / horizon_api_keys) ─────────────────────
    #
    # Identity tables are NOT tenant-scoped — they define tenants. They are
    # written by the operator's provisioning script (scripts/provision_tenant.py),
    # never by an MCP tool: identity operations are not conversational.

    def resolve_tenant_for_key_sha(self, key_sha256: str) -> str | None:
        """tenant_id for an ACTIVE (non-revoked) key hash; None otherwise.

        None means FAIL CLOSED: a key that authenticates but has no active
        mapping gets no mission access. Never auto-provision here — creating
        a tenant on first sight of an unmapped key would let any valid key
        mint itself a namespace, and would turn a revoked key into a fresh
        empty tenant instead of a refusal.
        """
        row = self._fetchone(
            "SELECT tenant_id FROM horizon_api_keys " "WHERE key_sha256 = ? AND revoked_at IS NULL",
            (key_sha256,),
        )
        return row["tenant_id"] if row else None

    def provision_tenant(
        self, tenant_id: str, display_label: str, key_sha256: str, key_label: str | None = None
    ) -> None:
        """Operator-run provisioning: one tenant row + one active key row.
        Idempotent on the tenant; refuses to re-bind an existing key hash."""
        now = datetime.now(timezone.utc).isoformat()
        with self._txn() as b:
            existing = b.execute(
                "SELECT tenant_id FROM horizon_tenants WHERE tenant_id = ?",
                (tenant_id,),
            ).fetchone()
            if existing is None:
                b.execute(
                    "INSERT INTO horizon_tenants (tenant_id, display_label, status, created_at) "
                    "VALUES (?, ?, 'active', ?)",
                    (tenant_id, display_label, now),
                )
            bound = b.execute(
                "SELECT tenant_id FROM horizon_api_keys WHERE key_sha256 = ?",
                (key_sha256,),
            ).fetchone()
            if bound is not None:
                raise KeyAlreadyBoundError(bound["tenant_id"])
            b.execute(
                "INSERT INTO horizon_api_keys (key_sha256, tenant_id, label, created_at, revoked_at) "
                "VALUES (?, ?, ?, ?, NULL)",
                (key_sha256, tenant_id, key_label, now),
            )

    def revoke_key(self, key_sha256: str) -> bool:
        """Revocation is a row update, not a redeploy. Returns True if a row
        was revoked. Mission history is untouched — that is the entire point
        of tenant identity being assigned rather than derived from the key."""
        with self._txn() as b:
            row = b.execute(
                "SELECT revoked_at FROM horizon_api_keys WHERE key_sha256 = ?",
                (key_sha256,),
            ).fetchone()
            if row is None or row["revoked_at"] is not None:
                return False
            b.execute(
                "UPDATE horizon_api_keys SET revoked_at = ? WHERE key_sha256 = ?",
                (datetime.now(timezone.utc).isoformat(), key_sha256),
            )
            return True

    # ── Snapshot for the pure evaluation engine ─────────────────────────

    def snapshot(self) -> StoreSnapshot:
        """A frozen point-in-time view for engine.evaluate(). Collections
        are ordered by stable keys so two snapshots taken of an unchanged
        store always compare/serialize identically. Tenant-scoped: contains
        only this scope's items, events and fire states, so every number
        the engine computes is derived exclusively from this tenant's
        recorded facts."""
        items = tuple(self.get_items())
        events = tuple(self.get_events())
        fire_states = tuple(self.get_all_fire_states())
        return StoreSnapshot(items=items, events=events, fire_states=fire_states)
