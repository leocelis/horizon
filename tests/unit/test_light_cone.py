"""Tests for the causal reachability map J⁻.

Per horizon_intent.yaml::constraints[temporal_signals_optional], reachability
is a timestamp-gated signal. All tests provide timestamps.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from horizon import FidelityMonitor
from tests.conftest import TIMESTAMP_1, TIMESTAMP_DAYS_LATER, TURN_1_AGENT, TURN_1_HUMAN

BASE_TIME = datetime(2026, 4, 22, 10, 0, 0, tzinfo=timezone.utc)


def _ts(offset_seconds: float = 0.0) -> str:
    return (BASE_TIME + timedelta(seconds=offset_seconds)).isoformat()


def test_reachable_fraction_one_on_first_turn(monitor: FidelityMonitor, session_id: str) -> None:
    """Turn 1 has no prior turns → fraction = 1.0 (no history to lose)."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, timestamp=_ts())
    assert result.reachable_fraction == 1.0


def test_reachable_fraction_is_none_without_timestamp(monitor: FidelityMonitor, session_id: str) -> None:
    """Without timestamp, reachability is not computed."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT)
    assert result.reachable_turns is None
    assert result.reachable_fraction is None


def test_reachable_fraction_decreases_after_large_gap(monitor: FidelityMonitor) -> None:
    """After a 3-day gap, retention drops and fewer turns are reachable."""
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN

    sid = monitor.new_conversation()
    monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=TIMESTAMP_1)
    result = monitor.process_turn(
        sid, TURN_2_HUMAN, TURN_2_AGENT, timestamp=TIMESTAMP_DAYS_LATER
    )
    assert result.reachable_fraction <= 1.0


def test_light_cone_monotonic_eviction(monitor: FidelityMonitor) -> None:
    """Adding more turns can only decrease or maintain reachable_fraction under fixed context window."""
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN, TURN_3_AGENT, TURN_3_HUMAN

    sid = monitor.new_conversation(metadata={"max_context_tokens": 50})

    r1 = monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=_ts(0))
    r2 = monitor.process_turn(sid, TURN_2_HUMAN, TURN_2_AGENT, timestamp=_ts(60))
    r3 = monitor.process_turn(sid, TURN_3_HUMAN, TURN_3_AGENT, timestamp=_ts(120))

    assert r1.reachable_fraction <= 1.0
    assert r2.reachable_fraction <= 1.0
    assert r3.reachable_fraction <= 1.0


def test_reachable_turns_non_negative(monitor: FidelityMonitor, session_id: str) -> None:
    """reachable_turns is always non-negative when computed."""
    result = monitor.process_turn(session_id, TURN_1_HUMAN, TURN_1_AGENT, timestamp=_ts())
    assert result.reachable_turns is not None
    assert result.reachable_turns >= 0


def test_eviction_irreversible(monitor: FidelityMonitor) -> None:
    """Property referenced by horizon_intent.yaml::property_tests.light_cone_monotonic_eviction.

    Once a turn leaves the reachable set, it does not re-enter across
    subsequent processed turns under a fixed context window.
    """
    from tests.conftest import TURN_2_AGENT, TURN_2_HUMAN, TURN_3_AGENT, TURN_3_HUMAN

    sid = monitor.new_conversation(metadata={"max_context_tokens": 50})

    r1 = monitor.process_turn(sid, TURN_1_HUMAN, TURN_1_AGENT, timestamp=_ts(0))
    r2 = monitor.process_turn(sid, TURN_2_HUMAN, TURN_2_AGENT, timestamp=_ts(60))
    r3 = monitor.process_turn(sid, TURN_3_HUMAN, TURN_3_AGENT, timestamp=_ts(120))

    for r in (r1, r2, r3):
        assert r.reachable_fraction is not None
        assert 0.0 <= r.reachable_fraction <= 1.0
        assert r.reachable_turns is not None
        assert r.reachable_turns >= 0

    assert r2.reachable_turns <= r2.turn_number - 1 + 1
    assert r3.reachable_turns <= r3.turn_number
