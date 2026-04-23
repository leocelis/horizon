"""Tests for spatial grounding and constraint vector."""

from __future__ import annotations

from horizon.spacetime.spatial import compute_spatial_constraint, infer_location_class


def test_mobile_transit_low_attention() -> None:
    """Mobile + transit should give low attention budget."""
    ctx = {"device_type": "mobile", "location_class": "transit"}
    constraint = compute_spatial_constraint(ctx)
    assert constraint.attention_budget == "low"
    assert constraint.max_response_length == 400


def test_desktop_office_high_attention() -> None:
    """Desktop + office should give high attention budget."""
    ctx = {"device_type": "desktop", "location_class": "office"}
    constraint = compute_spatial_constraint(ctx)
    assert constraint.attention_budget == "high"
    assert constraint.max_response_length == 2000


def test_default_constraint_for_unknown_device() -> None:
    """Unknown device/location falls back to medium default."""
    ctx = {"device_type": "smartwatch", "location_class": "unknown"}
    constraint = compute_spatial_constraint(ctx)
    assert constraint.attention_budget == "medium"
    assert constraint.complexity_ceiling == "medium"


def test_location_class_explicit() -> None:
    """Explicit location_class in context is returned directly."""
    ctx = {"location_class": "office"}
    result = infer_location_class(ctx)
    assert result == "office"


def test_location_class_unknown_fallback() -> None:
    """No ip_address and no explicit location → unknown."""
    ctx = {}
    result = infer_location_class(ctx)
    assert result == "unknown"


def test_location_class_private_ip_unknown() -> None:
    """Private IP addresses (RFC1918) without geoip_db → unknown."""
    ctx = {"ip_address": "192.168.1.100"}
    result = infer_location_class(ctx)
    assert result == "unknown"


def test_spatial_constraint_fields_valid() -> None:
    """All constraint fields must be valid literals."""
    valid_attention = {"high", "medium", "low"}
    valid_screen = {"large", "medium", "small"}
    valid_complexity = {"high", "medium", "low"}

    for device in ["desktop", "mobile", "tablet", "laptop"]:
        for loc in ["office", "home", "transit", "unknown"]:
            ctx = {"device_type": device, "location_class": loc}
            c = compute_spatial_constraint(ctx)
            assert c.attention_budget in valid_attention
            assert c.screen_capacity in valid_screen
            assert c.complexity_ceiling in valid_complexity
            assert c.max_response_length > 0
