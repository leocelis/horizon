#!/usr/bin/env python3
"""Ingest artifacts from an append-only source into a mission's event log.

This is the capture path the research ranks first: subscribing to records a
team already produces costs no new habit, whereas an agent that must *remember*
to write is worth nothing on the day it forgets, and retrospective
reconstruction reliably dies (PRD §4.3).

It is a script rather than an MCP tool on purpose. "Subscribe to this source"
is a standing arrangement, not a conversational act — so it belongs to the
operator and the scheduler, and it never depends on an agent choosing to run it.

Safe to run on a schedule: ingestion is idempotent. Artifacts are deduped on the
source's own `(source_system, native_id)`, and each run asks the source only for
what is newer than the last artifact recorded.

The mission link is yours to supply. An adapter has no method or parameter
capable of attaching one — `--item-id` is required, and nothing infers it.

Usage:
    # local SQLite store
    python scripts/ingest_artifacts.py --store ~/.horizon/missions.db \
        --repo /path/to/repo --item-id <mission-uuid>

    # MySQL store (same env the server uses)
    export HORIZON_MEMENTO_STORE_DSN='mysql://user:pass@host:3306/horizon'
    export HORIZON_MYSQL_SSL_CA=/path/to/ca.pem
    python scripts/ingest_artifacts.py --repo /path/to/repo --item-id <mission-uuid>

    # what missions does this repo suggest? (writes nothing)
    python scripts/ingest_artifacts.py --store ~/.horizon/missions.db \
        --repo /path/to/repo --propose

    # cron: every hour, quietly
    0 * * * * python scripts/ingest_artifacts.py --repo ... --item-id ... --quiet

Exit codes: 0 success (including "nothing new"), 1 refused, 2 bad arguments.
"""

from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--store", help="SQLite store path (or set HORIZON_MEMENTO_STORE_DSN)")
    ap.add_argument("--repo", required=True, help="path to an existing local git checkout")
    ap.add_argument(
        "--item-id",
        help="the mission (or child item) these artifacts belong to — the caller-supplied "
        "link; no adapter can infer it",
    )
    ap.add_argument("--tenant", default=None, help="tenant id for a multi-tenant store")
    ap.add_argument(
        "--since",
        default=None,
        help="ISO-8601 lower bound; omit to continue from the last artifact recorded",
    )
    ap.add_argument(
        "--propose",
        action="store_true",
        help="propose missions this source's artifacts suggest, and write nothing; "
        "--item-id is not required with this flag",
    )
    ap.add_argument("--dry-run", action="store_true", help="pull and report, write nothing")
    ap.add_argument("--quiet", action="store_true", help="print only on error or on new work")
    args = ap.parse_args()

    dsn = os.environ.get("HORIZON_MEMENTO_STORE_DSN") or None
    if not dsn and not args.store:
        print("error: give --store PATH or set HORIZON_MEMENTO_STORE_DSN", file=sys.stderr)
        return 2

    from datetime import datetime

    from horizon_monitor.memento import MementoStore, ingest_artifacts, propose_missions
    from horizon_monitor.memento.adapters.git_local import GitLocalAdapter

    since = datetime.fromisoformat(args.since) if args.since else None
    adapter = GitLocalAdapter(repo_path=args.repo)

    store = MementoStore(args.store, dsn=dsn)
    scope = store.scoped(args.tenant) if args.tenant else store
    try:
        if args.propose:
            proposals = propose_missions(scope, adapter, since=since)
            if not proposals:
                print("no missions proposed: this source's artifacts are already recorded")
                return 0
            for p in proposals:
                print(p.summary())
                print(f"  derivation: {p.derivation}")
                print(
                    "  to ratify: clock_register(kind='mission', title=<yours>, "
                    f"parent_id=<horizon id>, created_valid='"
                    f"{p.suggested_created_valid.isoformat()}')"
                )
            return 0

        if not args.item_id:
            print("error: --item-id is required unless --propose is given", file=sys.stderr)
            return 2

        if args.dry_run:
            resolved = since or scope.latest_artifact_time(adapter.source_system)
            pulled = adapter.pull(resolved)
            known = scope.known_artifact_ids(adapter.source_system)
            new = [a for a in pulled if a.provenance.native_id not in known]
            print(
                f"dry run — would ingest {len(new)} of {len(pulled)} pulled "
                f"(since {resolved.isoformat() if resolved else 'the beginning'}); "
                f"nothing written"
            )
            return 0

        result = ingest_artifacts(scope, adapter, item_id=args.item_id, since=since)
        if result.ingested or not args.quiet:
            print(result.summary())
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"ingestion refused: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
