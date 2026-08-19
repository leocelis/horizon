"""Storage backends for the Memento Mori mission store.

The store's SQL is written once, in SQLite placeholder style (`?`); each
backend adapts placeholders, DDL dialect, and connection liveness. SQLite
remains the zero-dependency default; MySQL is an optional extra for durable
multi-tenant deployments (``pip install horizon-monitor[mysql]``).

Backends deliberately share one contract:

* ``ph``            — the parameter placeholder token
* ``execute()``     — run one statement, return a cursor-like with fetchone/fetchall
* ``ensure_live()`` — make the connection usable *now* (no-op for SQLite;
                      ping+reconnect for MySQL, whose servers close idle
                      connections). Called at transaction/read boundaries,
                      NEVER mid-transaction — a mid-transaction reconnect
                      would silently drop the open transaction's state.
* ``init_schema()`` — create the dialect's schema; migrate v1 stores.
"""

from __future__ import annotations

from horizon_monitor.memento.backends.sqlite import SqliteBackend

__all__ = ["SqliteBackend", "resolve_backend"]


def resolve_backend(store_path=None, dsn: str | None = None):
    """One constructor for both backends. ``dsn`` wins when both are given,
    matching MementoConfig's documented precedence."""
    if dsn:
        from horizon_monitor.memento.backends.mysql import MySQLBackend

        return MySQLBackend(dsn)
    if store_path is None:
        raise ValueError("either store_path or dsn is required")
    return SqliteBackend(store_path)
