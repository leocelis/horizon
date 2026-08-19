"""M-7 — the evaluation instant's provenance is visible, never silent.

The engine is pure: ``t_eval`` is always a parameter
(memento_engine_intent.yaml::pure_function_injected_time). The MCP boundary is
the single place permitted to read a wall clock, and only when the host injects
no ``timestamp``. Two identical calls with no timestamp legitimately produce
different reports; ``eval_instant_source`` is what makes that visible instead of
looking like non-determinism.
"""

from __future__ import annotations

from datetime import datetime, timezone

from horizon_monitor.mcp import server as mcp_server

UTC = timezone.utc


def test_m7_injected_timestamp_is_reported_as_injected() -> None:
    t_eval, source = mcp_server._resolve_eval_instant("2026-08-18T12:00:00+00:00")
    assert source == "injected"
    assert t_eval == datetime(2026, 8, 18, 12, 0, 0, tzinfo=UTC)


def test_m7_absent_timestamp_is_reported_as_host_clock() -> None:
    before = datetime.now(UTC)
    t_eval, source = mcp_server._resolve_eval_instant(None)
    after = datetime.now(UTC)
    assert source == "host_clock", (
        "a boundary-defaulted instant must be labelled, otherwise an auditor "
        "cannot tell it from a host-injected one"
    )
    assert before <= t_eval <= after
    assert t_eval.tzinfo is not None, "the instant must be timezone-aware"


def test_m7_the_boundary_is_the_only_clock_reader() -> None:
    """The engine module itself must contain no ambient-clock read on the
    evaluation path — the whole point of routing through one helper."""
    import inspect

    from horizon_monitor.memento import engine

    src = inspect.getsource(engine)
    assert (
        "datetime.now" not in src and "utcnow" not in src
    ), "engine.evaluate() must never read an ambient clock; t_eval is a parameter"
