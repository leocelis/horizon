"""MySQL connection POLICY — startup budget vs steady-state patience.

These need no MySQL server: they pin the retry policy, not the connection. They
live apart from test_mysql_backend.py precisely so the module-level "skip unless
a DSN is configured" cannot hide them — the defect they guard failed a
production deploy on a machine that had no test DSN either.
"""

from __future__ import annotations

import pytest


def test_the_startup_connect_is_bounded_by_a_budget(monkeypatch):
    """A readiness probe is counting during the first connect.

    The full ladder is 2+4+8+16+32+64 = 126s of sleeps plus a connect timeout
    per attempt. Against a 120s readiness deadline that turns one transient
    database blip into a failed deploy and an automatic rollback — which is
    exactly what happened on 2026-08-24. Startup must fail fast and let the
    supervisor restart; only ensure_live() gets to be patient.

    Runs without a MySQL server: the point is the budget, not the connection.
    """
    import time as _time

    from horizon_monitor.memento.backends import mysql as mod

    monkeypatch.setattr(mod, "_STARTUP_BUDGET_S", 3.0)
    monkeypatch.setattr(mod, "_STARTUP_CONNECT_TIMEOUT_S", 1)
    monkeypatch.setenv("HORIZON_MYSQL_SSL_CA", __file__)  # any path; never reached

    started = _time.monotonic()
    with pytest.raises(RuntimeError, match="startup budget"):
        # 203.0.113.1 is TEST-NET-3 (RFC 5737) — reserved, routes nowhere
        mod.MySQLBackend("mysql://u:p@203.0.113.1:3306/db")
    elapsed = _time.monotonic() - started

    assert elapsed < 30, (
        f"startup took {elapsed:.1f}s against a 3s budget — the bound is not "
        "being enforced, and a readiness probe would have killed the deploy"
    )


def test_reconnects_keep_the_patient_ladder():
    """The budget is a startup concern only. A long-lived process reconnecting
    mid-life should keep retrying: nobody is holding a deadline over it, and
    giving up costs a working process."""
    import inspect

    from horizon_monitor.memento.backends.mysql import MySQLBackend

    src = inspect.getsource(MySQLBackend.ensure_live)
    assert "budget_seconds" not in src, (
        "ensure_live passed a startup budget; a mid-life reconnect must not "
        "inherit the startup deadline"
    )
