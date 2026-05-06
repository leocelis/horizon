"""End-to-end integration tests for the spacetime composition layer.

These tests drive *real* multi-turn conversations through
``FidelityMonitor.process_turn`` with *real* ISO-8601 timestamps and
verify that every signal in the spacetime stack — temporal gap,
circadian κ, retention, conversation velocity, ds² spacetime interval,
causal reachability, and deictic resolution — composes correctly when
the pipeline is exercised the way a real application would exercise it.

Where ``tests/unit/test_spacetime.py`` pins the math kernel
(``compute_spacetime_interval`` called with hand-picked floats), this
suite proves the *composition*: that the same ds² classification you
get from the kernel arises naturally from the monitor when you feed it
realistic ISO timestamps and conversation text.

These are not smoke tests. Each test:
  - uses real wall-clock timestamps (seconds → minutes → hours → days
    apart, including circadian phases at 04:00 / 11:00 / 22:00),
  - runs the full embedding-driven pipeline (no mocks of the embedding
    backend, no mocks of the temporal/circadian/velocity kernels),
  - asserts cross-feature invariants (e.g. retention monotonically
    decreases as gap grows, ds² flips from spacelike to timelike when
    the gap dominates over semantic shift),
  - and checks that downstream events (degradation, light-cone
    collapse, temporal_desync) fire from the composed signal —
    not from any single kernel called in isolation.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from horizon import Config, FidelityMonitor


# ── Shared corpus ────────────────────────────────────────────────────────────
# A short, realistic project-management thread. Keeps semantic content
# stable so we can isolate the *temporal* contribution to ds².
HUMANS = [
    "Can you summarise where we are with the migration?",
    "What's still pending before we can ship?",
    "Anything I should escalate today?",
    "Got it. Who owns the schema rollback plan?",
    "Thanks — let's cut a release tomorrow.",
]
AGENTS = [
    "We've migrated 4 of 6 services. Auth and billing remain.",
    "We need the staging soak test green and the on-call rota signed off.",
    "The CDN cache-invalidation timeline is the only thing without a clear owner.",
    "Sam owns rollback; she has the runbook in the migration repo.",
    "Sounds good — I'll draft the release notes when you're ready.",
]


def _ts(base: datetime, offset_seconds: float) -> str:
    return (base + timedelta(seconds=offset_seconds)).isoformat()


@pytest.fixture
def monitor() -> FidelityMonitor:
    # Tighter half-life keeps retention measurable on a multi-turn fixture
    # without forcing day-long gaps.
    return FidelityMonitor(config=Config(context_half_life_hours=12.0))


# ── 1. Temporal gap composition ──────────────────────────────────────────────


def test_real_temporal_gap_classification_across_turns(
    monitor: FidelityMonitor,
) -> None:
    """gap_class must reflect the *actual* wall-clock delta between
    consecutive ISO timestamps, computed by the live temporal kernel."""
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    sid = monitor.new_conversation()

    # Turn 1: bootstrap (no prior turn → realtime)
    r1 = monitor.process_turn(sid, HUMANS[0], AGENTS[0], timestamp=_ts(base, 0))
    # Turn 2: 30 s later → "seconds"
    r2 = monitor.process_turn(sid, HUMANS[1], AGENTS[1], timestamp=_ts(base, 30))
    # Turn 3: 5 min later → "minutes"
    r3 = monitor.process_turn(sid, HUMANS[2], AGENTS[2], timestamp=_ts(base, 30 + 300))
    # Turn 4: 2 h later → "hours"
    r4 = monitor.process_turn(
        sid, HUMANS[3], AGENTS[3], timestamp=_ts(base, 30 + 300 + 7200)
    )
    # Turn 5: 2 days later → "days"
    r5 = monitor.process_turn(
        sid,
        HUMANS[4],
        AGENTS[4],
        timestamp=_ts(base, 30 + 300 + 7200 + 2 * 86400),
    )

    assert r1.gap_class == "realtime"
    assert r2.gap_class == "seconds" and 25 <= (r2.gap_seconds or 0) <= 35
    assert r3.gap_class == "minutes" and 290 <= (r3.gap_seconds or 0) <= 310
    assert r4.gap_class == "hours" and 7100 <= (r4.gap_seconds or 0) <= 7300
    assert r5.gap_class == "days" and 2 * 86400 - 60 <= (r5.gap_seconds or 0)


def test_real_retention_decreases_monotonically_with_gap(
    monitor: FidelityMonitor,
) -> None:
    """estimated_retention must drop monotonically as the gap grows. This
    is the Half-Life Regression curve composed through the full monitor —
    not just a unit-tested kernel call."""
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    sid = monitor.new_conversation()

    monitor.process_turn(sid, HUMANS[0], AGENTS[0], timestamp=_ts(base, 0))
    short_gap = monitor.process_turn(
        sid, HUMANS[1], AGENTS[1], timestamp=_ts(base, 60)
    )
    medium_gap = monitor.process_turn(
        sid, HUMANS[2], AGENTS[2], timestamp=_ts(base, 60 + 3600)
    )
    long_gap = monitor.process_turn(
        sid, HUMANS[3], AGENTS[3], timestamp=_ts(base, 60 + 3600 + 86400)
    )

    assert short_gap.estimated_retention is not None
    assert medium_gap.estimated_retention is not None
    assert long_gap.estimated_retention is not None

    # Strict monotone decline — composition contract.
    assert short_gap.estimated_retention > medium_gap.estimated_retention
    assert medium_gap.estimated_retention > long_gap.estimated_retention
    # And the long-gap retention must be materially worse, not just rounding.
    assert short_gap.estimated_retention - long_gap.estimated_retention > 0.3


# ── 2. Circadian composition ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "hour,tz,expected_band",
    [
        # 11:00 local in UTC: peak window (10–14h) → κ == 1.0
        (11, "UTC", (0.95, 1.0)),
        # 04:00 local: nocturnal nadir → κ ≈ 0.3
        (4, "UTC", (0.28, 0.42)),
        # 23:00 local: nocturnal decline (22h+1h into the curve) → ~0.63
        (23, "UTC", (0.55, 0.72)),
    ],
)
def test_real_circadian_factor_matches_hour_of_day(
    monitor: FidelityMonitor, hour: int, tz: str, expected_band: tuple[float, float]
) -> None:
    """κ(t) must reflect the *real* hour-of-day computed from the timestamp
    + timezone propagated through ``process_turn``."""
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, hour, 0, 0, tzinfo=timezone.utc)
    r = monitor.process_turn(
        sid,
        HUMANS[0],
        AGENTS[0],
        timestamp=base.isoformat(),
        client_context={"timezone": tz},
    )

    assert r.circadian_factor is not None
    lo, hi = expected_band
    assert lo <= r.circadian_factor <= hi, (
        f"hour={hour} tz={tz} → κ={r.circadian_factor!r} (expected {lo}-{hi})"
    )


def test_real_circadian_lowers_retention_at_nadir(
    monitor: FidelityMonitor,
) -> None:
    """For the same wall-clock gap, the retention curve must be lower at
    04:00 (κ≈0.3) than at 11:00 (κ=1.0). This proves κ actually
    multiplies into the retention model end-to-end."""
    sid_day = monitor.new_conversation()
    sid_night = monitor.new_conversation()

    day_base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    night_base = datetime(2026, 4, 25, 4, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(
        sid_day, HUMANS[0], AGENTS[0], timestamp=day_base.isoformat(),
        client_context={"timezone": "UTC"},
    )
    r_day = monitor.process_turn(
        sid_day, HUMANS[1], AGENTS[1],
        timestamp=(day_base + timedelta(hours=4)).isoformat(),
        client_context={"timezone": "UTC"},
    )

    monitor.process_turn(
        sid_night, HUMANS[0], AGENTS[0], timestamp=night_base.isoformat(),
        client_context={"timezone": "UTC"},
    )
    r_night = monitor.process_turn(
        sid_night, HUMANS[1], AGENTS[1],
        timestamp=(night_base + timedelta(hours=4)).isoformat(),
        client_context={"timezone": "UTC"},
    )

    assert r_day.estimated_retention is not None
    assert r_night.estimated_retention is not None
    assert r_day.estimated_retention > r_night.estimated_retention, (
        f"day κ should preserve more memory: day={r_day.estimated_retention} "
        f"vs night={r_night.estimated_retention}"
    )


# ── 3. Velocity / acceleration composition ───────────────────────────────────


def test_real_velocity_inversely_proportional_to_gap(
    monitor: FidelityMonitor,
) -> None:
    """Same semantic shift, different time gap → velocity must scale
    inversely with the gap. This proves velocity is computed from real
    embeddings + real seconds, not a constant."""
    sid_fast = monitor.new_conversation()
    sid_slow = monitor.new_conversation()

    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    h0, a0 = "Let's debug the auth bug.", "Sure — paste the traceback."
    h1, a1 = (
        "Actually, can we plan the Q3 roadmap instead?",
        "Of course — what are the headline themes?",
    )

    monitor.process_turn(sid_fast, h0, a0, timestamp=_ts(base, 0))
    r_fast = monitor.process_turn(sid_fast, h1, a1, timestamp=_ts(base, 5))

    monitor.process_turn(sid_slow, h0, a0, timestamp=_ts(base, 0))
    r_slow = monitor.process_turn(sid_slow, h1, a1, timestamp=_ts(base, 500))

    assert r_fast.conversation_velocity is not None
    assert r_slow.conversation_velocity is not None
    # 100x gap → ~100x lower velocity (tolerate noise from tiny
    # embedding-similarity drift, but the ratio must clearly hold)
    assert r_fast.conversation_velocity > 10 * r_slow.conversation_velocity, (
        f"fast={r_fast.conversation_velocity} slow={r_slow.conversation_velocity}"
    )


# ── 4. The headline composition: ds² interval class ──────────────────────────


def test_real_long_gap_small_shift_is_timelike(monitor: FidelityMonitor) -> None:
    """A multi-day gap with the conversation continuing on-topic must
    classify as ``timelike`` once it's composed by the live monitor. This
    is the integration counterpart to the kernel-level
    ``test_large_time_gap_is_timelike`` unit test."""
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    sid = monitor.new_conversation()

    monitor.process_turn(
        sid,
        "Can you summarise where we are with the migration?",
        "We've migrated 4 of 6 services. Auth and billing remain.",
        timestamp=_ts(base, 0),
    )
    # Same exact topic, three days later
    r = monitor.process_turn(
        sid,
        "Quick check — where are we with the migration?",
        "Still 4 of 6. Auth and billing pending.",
        timestamp=_ts(base, 3 * 86400),
    )

    assert r.spacetime_interval is not None
    assert r.interval_class == "timelike", (
        f"Expected timelike, got {r.interval_class} ds²={r.spacetime_interval}"
    )
    assert r.spacetime_interval < 0


def test_real_sub_second_gap_topic_jump_is_spacelike(
    monitor: FidelityMonitor,
) -> None:
    """A sub-second gap (programmatic agent loop) with a hard topic jump
    after a focused baseline must classify as ``spacelike`` (semantic
    deltas dominate ds²).

    The kernel uses ``log(1 + Δt)``, so the time penalty grows
    aggressively with each second. With Δt = 0.2 s the time term is
    only -α·log(1.2)² ≈ -0.033, so even modest semantic deltas (D_JS,
    ε, coherence) push ds² firmly positive. This is exactly what a
    programmatic agent driving a multi-tool loop looks like — the
    realistic spacelike regime, not "Δt = 0" which the live monitor
    treats as no-temporal-signal."""
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    sid = monitor.new_conversation()

    # Baseline: focused question/answer about API SLA
    monitor.process_turn(
        sid,
        "What's the SLA on the payments API?",
        "99.95% per quarter, with a 2 hour MTTR target.",
        timestamp=_ts(base, 0),
    )
    # 200 ms later, completely different domain → big semantic deltas,
    # tiny time penalty.
    r = monitor.process_turn(
        sid,
        "Explain photosynthesis in C4 plants — Calvin cycle vs Hatch-Slack.",
        "C4 plants concentrate CO₂ via PEP carboxylase in bundle-sheath cells, "
        "decoupling carbon fixation from RuBisCO.",
        timestamp=_ts(base, 0.2),
    )

    assert r.spacetime_interval is not None
    assert r.interval_class == "spacelike", (
        f"Expected spacelike, got {r.interval_class} ds²={r.spacetime_interval}"
    )
    assert r.spacetime_interval > 0


def test_real_ds2_flips_sign_with_growing_gap(monitor: FidelityMonitor) -> None:
    """For the *same* semantic transition, ds² must shift toward more
    negative values as the time gap grows. This is the strongest possible
    composition test: it proves the time component genuinely contributes
    with the Minkowski signature in the live pipeline."""
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    h0, a0 = ("What's the migration ETA?", "Two weeks barring blockers.")
    h1, a1 = ("And the QA sign-off?", "QA needs three more days after we cut.")

    sid_short = monitor.new_conversation()
    monitor.process_turn(sid_short, h0, a0, timestamp=_ts(base, 0))
    r_short = monitor.process_turn(sid_short, h1, a1, timestamp=_ts(base, 1))

    sid_medium = monitor.new_conversation()
    monitor.process_turn(sid_medium, h0, a0, timestamp=_ts(base, 0))
    r_medium = monitor.process_turn(sid_medium, h1, a1, timestamp=_ts(base, 3600))

    sid_long = monitor.new_conversation()
    monitor.process_turn(sid_long, h0, a0, timestamp=_ts(base, 0))
    r_long = monitor.process_turn(sid_long, h1, a1, timestamp=_ts(base, 3 * 86400))

    assert r_short.spacetime_interval is not None
    assert r_medium.spacetime_interval is not None
    assert r_long.spacetime_interval is not None

    # Each step (more time, same semantics) must push ds² lower.
    assert r_short.spacetime_interval > r_medium.spacetime_interval
    assert r_medium.spacetime_interval > r_long.spacetime_interval
    # And the long-gap end must have crossed into timelike.
    assert r_long.interval_class == "timelike"


# ── 5. Deictic resolution composition ────────────────────────────────────────


def test_real_deictic_resolution_anchored_to_turn_timestamp(
    monitor: FidelityMonitor,
) -> None:
    """"yesterday" must resolve relative to the *turn's* ISO timestamp,
    not the wall clock the test runs at. Anchors deictic_refs to the
    full pipeline contract."""
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    r = monitor.process_turn(
        sid,
        "Did you see what happened yesterday during the demo?",
        "I'll look it up — what was the demo about?",
        timestamp=base.isoformat(),
    )

    assert r.temporal_references is not None
    assert len(r.temporal_references) >= 1
    yday = next(
        (t for t in r.temporal_references if "yesterday" in t.expression.lower()),
        None,
    )
    assert yday is not None, (
        f"expected 'yesterday' resolved, got {[t.expression for t in r.temporal_references]}"
    )
    assert yday.resolved is not None
    resolved_dt = datetime.fromisoformat(yday.resolved)
    # Must be 24h ± 6h before the turn timestamp (dateparser may anchor to
    # a slightly different time-of-day than the base, so allow slack).
    delta_hours = (base - resolved_dt).total_seconds() / 3600
    assert 18 <= delta_hours <= 30, (
        f"yesterday resolved {delta_hours:.1f}h before turn timestamp"
    )


# ── 6. Light-cone reachability composition ───────────────────────────────────


def test_real_light_cone_collapse_after_long_gap(monitor: FidelityMonitor) -> None:
    """A long enough gap on a long enough thread must reduce the
    reachable fraction of prior turns. Composition: temporal kernel
    (retention) ⊗ embedding kernel (semantic similarity) ⊗ session
    state (in-context flags) → reachable fraction → light-cone signal."""
    config = Config(context_half_life_hours=2.0)  # short half-life amplifies the effect
    monitor = FidelityMonitor(config=config)
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)

    # Build a thread of 5 turns 30 s apart — small reachable_fraction baseline
    for i in range(5):
        monitor.process_turn(
            sid, HUMANS[i % len(HUMANS)], AGENTS[i % len(AGENTS)],
            timestamp=_ts(base, i * 30),
        )

    # 6th turn 5 days later, on a fresh-but-related topic
    r_collapsed = monitor.process_turn(
        sid,
        "I'm back. Has anything moved on the migration since we last spoke?",
        "Welcome back — billing is now done; auth is still pending review.",
        timestamp=_ts(base, 5 * 86400),
    )

    assert r_collapsed.reachable_fraction is not None
    assert r_collapsed.reachable_turns is not None
    # After 5 days with a 2h half-life, retention is ~0 → almost no prior
    # turn should be reachable.
    assert r_collapsed.reachable_fraction <= 0.2, (
        f"reachable_fraction={r_collapsed.reachable_fraction} after 5d/2h half-life"
    )


def test_real_short_gap_keeps_high_reachability(monitor: FidelityMonitor) -> None:
    """Inverse of the collapse test: realtime turns must keep most of the
    prior thread reachable. Establishes a positive baseline so the
    collapse test is meaningful."""
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)

    for i in range(5):
        monitor.process_turn(
            sid, HUMANS[i % len(HUMANS)], AGENTS[i % len(AGENTS)],
            timestamp=_ts(base, i * 5),
        )

    r = monitor.process_turn(
        sid,
        "And just to confirm — the rollback owner is Sam?",
        "Confirmed — Sam owns rollback.",
        timestamp=_ts(base, 30),
    )

    assert r.reachable_fraction is not None
    assert r.reachable_fraction >= 0.5, (
        f"realtime thread should keep most turns reachable, got {r.reachable_fraction}"
    )


# ── 7. Cross-feature: composed signals fire downstream events ────────────────


def test_real_long_gap_emits_temporal_desync_event(monitor: FidelityMonitor) -> None:
    """The composed signal stack — gap_seconds (temporal kernel) +
    estimated_retention (HLR with κ) — must drive the
    ``signal.temporal_desync`` event when both cross threshold."""
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)

    monitor.process_turn(sid, HUMANS[0], AGENTS[0], timestamp=_ts(base, 0))
    r = monitor.process_turn(
        sid, HUMANS[1], AGENTS[1], timestamp=_ts(base, 3 * 86400),
    )

    desync = [e for e in r.events if e.type == "signal.temporal_desync"]
    assert desync, (
        f"Expected signal.temporal_desync after 3d gap; got events "
        f"{[e.type for e in r.events]} | retention={r.estimated_retention}"
    )


def test_real_long_gap_emits_light_cone_collapse_event() -> None:
    """Composed temporal-decay × semantic-similarity must trigger
    ``signal.light_cone_collapse`` when reachability falls below the
    ratio + min thresholds."""
    monitor = FidelityMonitor(config=Config(context_half_life_hours=1.0))
    sid = monitor.new_conversation()
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)

    # Build a long-enough thread that the min_threshold (3) and ratio
    # (0.3) checks are both meaningful
    for i in range(8):
        monitor.process_turn(
            sid, HUMANS[i % len(HUMANS)], AGENTS[i % len(AGENTS)],
            timestamp=_ts(base, i * 10),
        )

    r = monitor.process_turn(
        sid,
        "Coming back to this thread — quick question on the rollback plan.",
        "Sure — what specifically?",
        timestamp=_ts(base, 7 * 86400),
    )

    collapse = [e for e in r.events if e.type == "signal.light_cone_collapse"]
    assert collapse, (
        f"Expected signal.light_cone_collapse; got events "
        f"{[e.type for e in r.events]} reachable_fraction={r.reachable_fraction}"
    )


# ── 8. Spatial × temporal composition (the full 4D in one test) ──────────────


def test_real_4d_composition_temporal_circadian_velocity_spatial_geoip() -> None:
    """The single test that exercises the *entire* spacetime layer end-to-end
    on real timestamps + real GeoIP data:

      - real ISO timestamps (compose temporal_gap, retention, ds², velocity)
      - real timezone (compose circadian κ from wall-clock)
      - real MaxMind City DB lookup (compose location_class → spatial_constraint)

    The assertion bar is composition correctness — every layer's signal
    must be present, internally consistent, and reflect the inputs.
    """
    from pathlib import Path

    pytest.importorskip("geoip2")
    fixtures = Path(__file__).parent / "fixtures"
    city_db = fixtures / "GeoIP2-City-Test.mmdb"
    if not city_db.exists():
        pytest.skip("GeoIP2 City test DB missing")

    monitor = FidelityMonitor(config=Config(context_half_life_hours=12.0))
    sid = monitor.new_conversation()

    # 11:00 UTC London → London geoIP block (radius 10) → "inferred"
    base = datetime(2026, 4, 25, 11, 0, 0, tzinfo=timezone.utc)
    london_ctx = {
        "ip_address": "81.2.69.142",
        "geoip_db_path": str(city_db),
        "device_type": "laptop",
        "timezone": "Europe/London",
    }

    r1 = monitor.process_turn(
        sid,
        "Can you summarise where we are with the migration?",
        "We've migrated 4 of 6 services. Auth and billing remain.",
        timestamp=base.isoformat(),
        client_context=london_ctx,
    )

    # 6 hours later — afternoon in London (κ should still be ≥ 0.7)
    r2 = monitor.process_turn(
        sid,
        "Quick check — anything moved on auth?",
        "Auth is mid-review; billing starts tomorrow.",
        timestamp=(base + timedelta(hours=6)).isoformat(),
        client_context=london_ctx,
    )

    # Temporal layer
    assert r2.gap_seconds is not None and abs(r2.gap_seconds - 6 * 3600) < 60
    assert r2.gap_class == "hours"
    assert r2.estimated_retention is not None
    # 6h with 12h half-life and κ≈1 → retention ≈ 0.707
    assert 0.6 <= r2.estimated_retention <= 0.85

    # Circadian layer (London time = UTC time = 17:00, peak window)
    assert r2.circadian_factor is not None
    assert r2.circadian_factor >= 0.95

    # Velocity / spacetime layers — must be populated for turn 2
    assert r2.conversation_velocity is not None
    assert r2.spacetime_interval is not None
    assert r2.interval_class in {"timelike", "spacelike", "lightlike"}

    # Spatial layer (real GeoIP)
    assert r1.location_class == "inferred"
    assert r2.location_class == "inferred"
    assert r2.spatial_constraint is not None
    # Two consecutive turns from the same client_context → no frame shift
    assert r2.spatial_frame_shift == 0.0

    # And reachability must have at least the prior turn in the cone
    assert r2.reachable_turns is not None and r2.reachable_turns >= 1
