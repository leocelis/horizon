"""S-9 [PROPERTY] — fifty concurrent single-statement writes from two
connections: no lost writes; tx_time ordering total.
"""

from __future__ import annotations

import threading
from datetime import date, datetime, timezone
from pathlib import Path

from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc


def test_fifty_concurrent_writes_no_lost_writes(tmp_path: Path) -> None:
    db_path = tmp_path / "memento.db"

    setup_store = MementoStore(db_path)
    root_id = setup_store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    mission_id = setup_store.register_item(
        kind=ItemKind.MISSION,
        title="M1",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
    )
    setup_store.close()

    # Two independent connections to the SAME file, as two agent sessions.
    store_conn_a = MementoStore(db_path)
    store_conn_b = MementoStore(db_path)

    written_ids: list[str] = []
    lock = threading.Lock()
    errors: list[Exception] = []

    def _write(conn: MementoStore, n: int) -> None:
        try:
            eid = conn.record_event(
                item_id=mission_id,
                kind=EventKind.PROGRESS,
                valid_time=datetime(2026, 7, 2, tzinfo=UTC),
                payload={"seq": n},
            )
            with lock:
                written_ids.append(eid)
        except Exception as exc:  # noqa: BLE001 - captured for the assertion below
            with lock:
                errors.append(exc)

    threads = []
    for n in range(50):
        conn = store_conn_a if n % 2 == 0 else store_conn_b
        t = threading.Thread(target=_write, args=(conn, n))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    store_conn_a.close()
    store_conn_b.close()

    assert errors == [], f"unexpected write failures: {errors}"
    assert len(written_ids) == 50, "no writes may be lost"
    assert len(set(written_ids)) == 50, "no two writes may collide on the same event_id"

    verify_store = MementoStore(db_path)
    stored_events = verify_store.get_events(mission_id)
    verify_store.close()

    assert len(stored_events) == 50
    tx_seqs = [e.tx_seq for e in stored_events]
    assert len(set(tx_seqs)) == 50, "tx ordering must be total: no two events share a tx_seq"
