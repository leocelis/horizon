"""Register the Memento Mori plane's own construction as a mission in a
local dev store — "the clock clocks its own construction."

This is not a synthetic demo: it points ``GitLocalAdapter`` at this
checkout's own git history, pulls every commit whose message references
"memento" (case-insensitive — this build's own commits), and records each as
an ``ARTIFACT`` event with full provenance on a MISSION item representing
this build. No PROGRESS event is fabricated — the commit history itself is
the evidence the recording-path check reads (engine.py counts ARTIFACT
events toward ``days_since_progress``, same as PROGRESS).

Idempotent: safe to re-run against the same store — existing commits are
never re-inserted, and the root/mission are reused if already present.

Usage:
  python scripts/memento_register_self_build.py [--store-path var/memento_self.sqlite]
  python scripts/memento_register_self_build.py --print-report
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from horizon_monitor.memento import engine, signals
from horizon_monitor.memento.adapters.git_local import GitLocalAdapter
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import EventKind, ItemKind
from horizon_monitor.memento.store import MementoStore

UTC = timezone.utc
REPO_ROOT = Path(__file__).resolve().parents[1]
MISSION_TITLE = "memento-mori-plane-build"


def _find_mission(store: MementoStore) -> str | None:
    return next(
        (
            i.item_id
            for i in store.get_items()
            if i.kind == ItemKind.MISSION and i.title == MISSION_TITLE
        ),
        None,
    )


def register_self_build(store: MementoStore, horizon_end_date: date) -> str:
    """Ensure a root + mission exist for this build, then append any commit
    (matched on "memento", case-insensitive) not already recorded. Returns
    the mission's item_id."""
    root = store.get_root()
    root_id = root.item_id if root is not None else None

    mission_id = _find_mission(store)
    first_commit_time: datetime | None = None

    adapter = GitLocalAdapter(repo_path=str(REPO_ROOT))
    artifacts = [
        a for a in adapter.pull(since=None) if "memento" in a.payload.get("subject", "").lower()
    ]
    artifacts = sorted(artifacts, key=lambda a: a.provenance.raw_timestamp)

    if artifacts:
        first_commit_time = artifacts[0].provenance.raw_timestamp

    if root_id is None:
        root_id = store.register_item(
            kind=ItemKind.HORIZON,
            title="horizon-dev-root",
            created_valid=first_commit_time or datetime.now(UTC),
            end_date=horizon_end_date,
        )

    if mission_id is None:
        mission_id = store.register_item(
            kind=ItemKind.MISSION,
            title=MISSION_TITLE,
            parent_id=root_id,
            created_valid=first_commit_time or datetime.now(UTC),
        )

    already_recorded_native_ids = {
        e.provenance.native_id
        for e in store.get_events(mission_id)
        if e.kind == EventKind.ARTIFACT and e.provenance
    }

    appended = 0
    for artifact in artifacts:
        if artifact.provenance.native_id in already_recorded_native_ids:
            continue
        store.record_event(
            item_id=mission_id,
            kind=EventKind.ARTIFACT,
            valid_time=artifact.provenance.raw_timestamp,
            provenance=artifact.provenance,
            payload=artifact.payload,
        )
        appended += 1

    print(
        f"mission_id={mission_id} commits_seen={len(artifacts)} commits_appended_this_run={appended}"
    )
    return mission_id


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-path", default=str(REPO_ROOT / "var" / "memento_self.sqlite"))
    parser.add_argument(
        "--horizon-end-date",
        default=None,
        help="ISO date for the dev root's horizon; defaults to 90 days after the first matched commit.",
    )
    parser.add_argument(
        "--print-report", action="store_true", help="also print the evaluate()/signals surface"
    )
    args = parser.parse_args()

    store_path = Path(args.store_path)
    store_path.parent.mkdir(parents=True, exist_ok=True)
    store = MementoStore(store_path)

    if args.horizon_end_date:
        horizon_end_date = date.fromisoformat(args.horizon_end_date)
    else:
        adapter = GitLocalAdapter(repo_path=str(REPO_ROOT))
        commits = sorted(
            (
                a
                for a in adapter.pull(since=None)
                if "memento" in a.payload.get("subject", "").lower()
            ),
            key=lambda a: a.provenance.raw_timestamp,
        )
        anchor = commits[0].provenance.raw_timestamp if commits else datetime.now(UTC)
        horizon_end_date = (anchor + timedelta(days=90)).date()

    mission_id = register_self_build(store, horizon_end_date)

    if args.print_report:
        t_eval = datetime.now(UTC)
        snapshot = store.snapshot()
        config = MementoConfig()
        report = engine.evaluate(snapshot, t_eval, config)
        signal_report, new_states = signals.evaluate_signals(snapshot, report, t_eval, config)
        for (item_id, signal_type), state in new_states.items():
            store.set_fire_state(item_id, signal_type, state)
        mission_row = next(r for r in report.items if r.item_id == mission_id)
        print(json.dumps(mission_row.to_dict(), indent=2, default=str))
        print(json.dumps(signal_report.to_dict(), indent=2, default=str))

    store.close()


if __name__ == "__main__":
    main()
