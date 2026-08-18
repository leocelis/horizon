"""E-3 [HUMAN] — recording-path check distinguishes "no work" from "no
capture".

PRD §4.3: "Every stall signal pairs with a recording-path check: a mission
with no derived events AND no caller writes is flagged 'no capture',
distinguishable from 'no work'."
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from horizon_monitor.memento import engine
from horizon_monitor.memento.config import MementoConfig
from horizon_monitor.memento.models import ItemKind

from .conftest import EVAL_INSTANT, build_smallco

UTC = timezone.utc


def _row(report, item_id: str):
    return next(r for r in report.items if r.item_id == item_id)


def test_mission_with_events_flags_no_recent_work(store) -> None:
    """M1 has progress events (none recent) -> 'no recent work', not 'no
    capture'.

    REVIEWER NOTE [HUMAN]: this assertion encodes the intended distinction
    per PRD §4.3; a human reviewer should confirm 'no recent work' is the
    correct label text before this ships (ai_generated test provenance —
    IVD Rule 3: an ai_generated test alone cannot mark this constraint
    PASS)."""
    ids = build_smallco(store)
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    m1 = _row(report, ids["M1"])
    assert m1.recording_path == "no recent work"


def test_mission_with_zero_events_ever_flags_no_capture(store) -> None:
    """A mission with zero progress events ever -> 'no capture', a
    structurally distinct flag from 'no recent work'.

    REVIEWER NOTE [HUMAN]: same provenance caveat as above."""
    root_id = store.register_item(
        kind=ItemKind.HORIZON,
        title="root",
        created_valid=datetime(2026, 1, 1, tzinfo=UTC),
        end_date=date(2030, 1, 1),
    )
    silent_mission_id = store.register_item(
        kind=ItemKind.MISSION,
        title="never instrumented",
        parent_id=root_id,
        created_valid=datetime(2026, 6, 1, tzinfo=UTC),
        stall_days=14,
    )
    report = engine.evaluate(store.snapshot(), EVAL_INSTANT, MementoConfig())
    row = _row(report, silent_mission_id)
    assert row.recording_path == "no capture"
    assert row.days_since_progress is None
