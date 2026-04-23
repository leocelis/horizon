"""Tests for the circadian cognitive factor κ(t)."""

from __future__ import annotations

from horizon.spacetime.circadian import compute_circadian_factor


def test_peak_during_morning(tmp_path: object) -> None:
    """Between 10:00 and 14:00 κ should be 1.0."""
    kappa = compute_circadian_factor("2026-04-22T11:00:00+00:00", None)
    assert kappa == 1.0


def test_post_lunch_dip() -> None:
    """14:00–16:00 should give κ = 0.7."""
    kappa = compute_circadian_factor("2026-04-22T15:00:00+00:00", None)
    assert kappa == 0.7


def test_nadir_at_5am() -> None:
    """04:00–07:00 should give κ = 0.3 (nadir)."""
    kappa = compute_circadian_factor("2026-04-22T05:30:00+00:00", None)
    assert kappa == 0.3


def test_bounds() -> None:
    """κ must always be in [0.3, 1.0]."""
    for hour in range(24):
        ts = f"2026-04-22T{hour:02d}:00:00+00:00"
        kappa = compute_circadian_factor(ts, None)
        assert 0.3 <= kappa <= 1.0, f"κ={kappa} out of bounds at hour {hour}"


def test_kappa_bounds() -> None:
    """Property referenced by horizon_intent.yaml::property_tests.circadian_bounds.

    - κ is always in [0, 1]
    - κ(peak) == 1.0
    - κ(nadir) >= 0.3
    """
    for hour in range(24):
        for minute in (0, 15, 30, 45):
            ts = f"2026-04-22T{hour:02d}:{minute:02d}:00+00:00"
            kappa = compute_circadian_factor(ts, None)
            assert 0.0 <= kappa <= 1.0
            assert kappa >= 0.3

    kappa_peak = compute_circadian_factor("2026-04-22T11:00:00+00:00", None)
    assert kappa_peak == 1.0

    kappa_nadir = compute_circadian_factor("2026-04-22T05:00:00+00:00", None)
    assert kappa_nadir >= 0.3


def test_morning_ramp_increases() -> None:
    """κ increases monotonically from 07:00 to 10:00."""
    kappa_7 = compute_circadian_factor("2026-04-22T07:00:00+00:00", None)
    kappa_8 = compute_circadian_factor("2026-04-22T08:00:00+00:00", None)
    kappa_9 = compute_circadian_factor("2026-04-22T09:00:00+00:00", None)
    assert kappa_7 < kappa_8 < kappa_9


def test_chronotype_offset_shifts_peak() -> None:
    """A positive chronotype_offset shifts the curve later (night owl)."""
    # At 10:00 with no offset = peak
    kappa_standard = compute_circadian_factor(
        "2026-04-22T10:00:00+00:00", None, chronotype_offset=0
    )
    # With +2h offset, 10:00 becomes effective 08:00 = ramp, so lower
    kappa_shifted = compute_circadian_factor(
        "2026-04-22T10:00:00+00:00", None, chronotype_offset=2.0
    )
    assert kappa_shifted < kappa_standard


def test_with_timezone() -> None:
    """Timezone conversion does not break the output."""
    # 10:00 UTC = 06:00 NYC (nadir) — should give different kappa than UTC
    kappa_utc = compute_circadian_factor("2026-04-22T10:00:00+00:00", None)
    kappa_nyc = compute_circadian_factor("2026-04-22T10:00:00+00:00", "America/New_York")
    assert kappa_utc != kappa_nyc
