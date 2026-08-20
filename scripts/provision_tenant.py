#!/usr/bin/env python3
"""Operator-run tenant provisioning for the Memento Mori mission plane.

Identity operations are NOT conversational: this script is the only
sanctioned way tenants come to exist. It is never exposed as an MCP tool,
never run by an agent on its own initiative, and never triggered by an
inbound request — an unmapped key FAILS CLOSED rather than provisioning
itself (see MementoStore.resolve_tenant_for_key_sha).

The raw API key is hashed locally (sha256) and only the hash is stored;
a database compromise never yields working credentials.

Usage:
  # hosted (MySQL) — DSN + CA via the same env vars the server uses:
  export HORIZON_MEMENTO_STORE_DSN='mysql://user:pass@host:port/horizon'
  export HORIZON_MYSQL_SSL_CA=/path/to/ca.pem
  python scripts/provision_tenant.py --tenant-id acme --label "Acme Corp" \
      --key-env HORIZON_PROVISION_KEY --key-label "desktop"

  # local (SQLite):
  python scripts/provision_tenant.py --store ~/.horizon/missions.db \
      --tenant-id alice --label "Alice" --key-env HORIZON_PROVISION_KEY

  # revoke a key (tenant and its history untouched — that is the point):
  python scripts/provision_tenant.py --revoke --key-env HORIZON_PROVISION_KEY

The key is passed via an environment variable (--key-env NAME), never as a
CLI argument: argv is visible in `ps` and shell history.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--store", help="SQLite store path (or set HORIZON_MEMENTO_STORE_DSN for MySQL)"
    )
    ap.add_argument("--tenant-id", help="assigned, stable tenant id (never derived from the key)")
    ap.add_argument("--label", help="human display label for the tenant")
    ap.add_argument(
        "--key-env",
        required=True,
        help="name of the env var holding the RAW api key (never pass the key in argv)",
    )
    ap.add_argument(
        "--key-label", default=None, help="optional label for this key (e.g. 'desktop')"
    )
    ap.add_argument(
        "--revoke",
        action="store_true",
        help="revoke the key instead of provisioning; tenant + history untouched",
    )
    args = ap.parse_args()

    raw_key = os.environ.get(args.key_env, "")
    if not raw_key:
        print(f"error: env var {args.key_env} is empty — export the raw key there first")
        return 2
    key_sha = hashlib.sha256(raw_key.encode()).hexdigest()

    dsn = os.environ.get("HORIZON_MEMENTO_STORE_DSN") or None
    if not dsn and not args.store:
        print("error: give --store PATH (SQLite) or set HORIZON_MEMENTO_STORE_DSN (MySQL)")
        return 2

    from horizon_monitor.memento import MementoStore

    store = MementoStore(args.store, dsn=dsn)
    try:
        if args.revoke:
            revoked = store.revoke_key(key_sha)
            print("revoked" if revoked else "no active key with that hash — nothing changed")
            return 0 if revoked else 1

        if not (args.tenant_id and args.label):
            print("error: --tenant-id and --label are required to provision")
            return 2
        store.provision_tenant(args.tenant_id, args.label, key_sha, key_label=args.key_label)
        print(
            f"provisioned tenant {args.tenant_id!r} ({args.label}) "
            f"with key sha256 {key_sha[:12]}… (label: {args.key_label or '-'})"
        )
        return 0
    finally:
        store.close()


if __name__ == "__main__":
    sys.exit(main())
