"""Real MaxMind GeoIP2 integration tests.

These tests exercise the full GeoIP code path against the canonical
MaxMind reference test databases (``GeoIP2-City-Test.mmdb`` and
``GeoIP2-Anonymous-IP-Test.mmdb``) shipped under
``tests/integration/fixtures/``.

The reference databases are the same ones MaxMind themselves use to
validate their official client SDKs (``maxmind/MaxMind-DB`` on GitHub,
MIT-licensed, ~30 KB total). Every assertion below pins to a real
record in those databases — there are no mocks, no fakes, no
``monkeypatch`` of the ``geoip2`` module. If the spatial.py pipeline
breaks against a real ``.mmdb`` file, these tests catch it.

For the lighter, mock-based code-path coverage (e.g. simulating the
``geoip2`` library being absent), see ``test_geoip.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from horizon import FidelityMonitor
from horizon.spacetime.spatial import infer_location_class

pytest.importorskip("geoip2")

FIXTURES = Path(__file__).parent / "fixtures"
CITY_DB = FIXTURES / "GeoIP2-City-Test.mmdb"
ANON_DB = FIXTURES / "GeoIP2-Anonymous-IP-Test.mmdb"


@pytest.fixture(autouse=True)
def _require_fixtures() -> None:
    if not CITY_DB.exists() or not ANON_DB.exists():
        pytest.skip(
            "MaxMind reference test DBs missing under "
            f"{FIXTURES}; download them from "
            "https://github.com/maxmind/MaxMind-DB/tree/main/test-data"
        )


# ── Real City DB lookups ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "ip,expected",
    [
        # London, GB — accuracy radius 10 km → high precision → "inferred"
        ("81.2.69.142", "inferred"),
        # Milton, US (Washington) — radius 22 km → "inferred"
        ("216.160.83.56", "inferred"),
        # Linköping, SE — radius 76 km → still under the 100 km threshold
        ("89.160.20.112", "inferred"),
    ],
)
def test_geoip_high_precision_returns_inferred(ip: str, expected: str) -> None:
    """Real lookup against the City DB must classify high-precision records
    as ``inferred``."""
    loc = infer_location_class(
        {"ip_address": ip, "geoip_db_path": str(CITY_DB)}
    )
    assert loc == expected, (
        f"IP {ip} resolved to {loc!r} (expected {expected!r}) — "
        "the spatial pipeline may have regressed against real MaxMind data."
    )


@pytest.mark.parametrize(
    "ip",
    [
        # Bhutan — accuracy radius 534 km → too coarse → "unknown"
        "67.43.156.1",
        # US city-block radius 1000 km → country-level only → "unknown"
        "149.101.100.1",
        # Philippines — radius 121 km → just over the 100 km threshold → "unknown"
        "202.196.224.1",
    ],
)
def test_geoip_low_precision_returns_unknown(ip: str) -> None:
    """Real lookup against the City DB must reject records whose accuracy
    radius exceeds the 100 km cut-off."""
    loc = infer_location_class(
        {"ip_address": ip, "geoip_db_path": str(CITY_DB)}
    )
    assert loc == "unknown", (
        f"IP {ip} resolved to {loc!r} (expected 'unknown') — "
        "the accuracy-radius gate may be miscalibrated."
    )


def test_geoip_unknown_address_falls_back_to_unknown() -> None:
    """Real ``AddressNotFoundError`` from the City DB must collapse to
    ``unknown`` (fail-soft contract)."""
    loc = infer_location_class(
        {"ip_address": "203.0.113.99", "geoip_db_path": str(CITY_DB)}
    )
    assert loc == "unknown"


# ── Real Anonymous-IP DB lookups ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "ip,reason",
    [
        # Real VPN exit (anonymous_vpn=True) per the Anonymous-IP test DB
        ("1.2.0.1", "vpn"),
        # Real hosting + Tor + VPN composite
        ("81.2.69.0", "hosting+tor+vpn"),
        # Real anonymous proxy
        ("186.30.236.0", "anonymous"),
        # Real Tor exit
        ("65.4.3.2", "tor"),
    ],
)
def test_geoip_anonymous_db_suppresses_inferred(ip: str, reason: str) -> None:
    """When ``geoip_anonymous_db_path`` is supplied, any IP flagged as
    VPN/hosting/Tor/anonymous in the Anonymous-IP DB must be downgraded to
    ``unknown`` even if the City DB lookup would otherwise have succeeded."""
    loc = infer_location_class(
        {
            "ip_address": ip,
            "geoip_db_path": str(CITY_DB),
            "geoip_anonymous_db_path": str(ANON_DB),
        }
    )
    assert loc == "unknown", (
        f"IP {ip} ({reason}) resolved to {loc!r} (expected 'unknown') — "
        "Anonymous-IP DB suppression is not wired through."
    )


def test_geoip_anonymous_db_alone_does_not_grant_inference() -> None:
    """Anonymous-IP suppression is a *negative* signal — it must never act
    as a *positive* one. With only ``geoip_anonymous_db_path`` configured
    (no City DB), even a known-good London IP must collapse to ``unknown``,
    because the inference path requires a City-DB lookup to succeed.

    This pins the API contract: callers who want VPN/hosting suppression
    must still provide a City DB; the anon DB never independently
    "grants" a location class.
    """
    loc = infer_location_class(
        {
            "ip_address": "81.2.69.142",  # London, radius 10 in City DB
            "geoip_anonymous_db_path": str(ANON_DB),
            # NOTE: geoip_db_path intentionally omitted
        }
    )
    assert loc == "unknown"


# ── End-to-end: GeoIP feeds the full monitor pipeline ────────────────────────


def test_geoip_real_lookup_flows_into_monitor_result() -> None:
    """The real GeoIP lookup must propagate through ``process_turn`` into
    ``location_class`` on the result and shape the spatial constraint
    vector accordingly. This proves spatial grounding is wired end-to-end,
    not just inside ``infer_location_class``."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    result = monitor.process_turn(
        sid,
        "Help me draft a quick standup update.",
        "Sure — what shipped, what's blocked, what's next?",
        client_context={
            "ip_address": "81.2.69.142",  # London GB, radius 10 → "inferred"
            "geoip_db_path": str(CITY_DB),
            "device_type": "laptop",
        },
        timestamp="2026-04-25T15:00:00+00:00",
    )

    assert result.location_class == "inferred", (
        f"Real-DB IP did not propagate: location_class={result.location_class!r}"
    )
    # Spatial constraint must be derived from (device_type, location_class)
    # — i.e. the GeoIP result actively shapes downstream signals.
    assert result.spatial_constraint is not None
    # (laptop, "inferred") is not in SPATIAL_PROFILES → DEFAULT_CONSTRAINT,
    # so we just check the vector is well-formed.
    assert result.spatial_constraint.screen_capacity in {"large", "medium", "small"}
    assert result.spatial_constraint.attention_budget in {"high", "medium", "low"}
    assert result.spatial_constraint.complexity_ceiling in {"high", "medium", "low"}
    assert result.spatial_constraint.max_response_length > 0


def test_geoip_real_anonymous_ip_collapses_monitor_to_unknown() -> None:
    """A real VPN IP (per Anonymous-IP test DB) flowing through the full
    monitor with both DB paths configured must end up as ``unknown`` on
    the result, not just inside ``infer_location_class``."""
    monitor = FidelityMonitor()
    sid = monitor.new_conversation()

    result = monitor.process_turn(
        sid,
        "What's the weather?",
        "I don't have realtime data, but check your local forecast.",
        client_context={
            "ip_address": "1.2.0.1",  # VPN per Anonymous-IP test DB
            "geoip_db_path": str(CITY_DB),
            "geoip_anonymous_db_path": str(ANON_DB),
            "device_type": "mobile",
        },
        timestamp="2026-04-25T15:00:00+00:00",
    )

    assert result.location_class == "unknown"
