"""Spatial grounding — location class inference and constraint vector Φ(σ)."""

from __future__ import annotations

from horizon.models import SpatialConstraint

SPATIAL_PROFILES: dict[tuple[str, str], SpatialConstraint] = {
    ("desktop", "office"): SpatialConstraint("high", "large", 2000, "high"),
    ("desktop", "home"): SpatialConstraint("high", "large", 2000, "high"),
    ("desktop", "unknown"): SpatialConstraint("high", "large", 2000, "high"),
    ("laptop", "office"): SpatialConstraint("high", "large", 1800, "high"),
    ("laptop", "home"): SpatialConstraint("high", "large", 1800, "high"),
    ("laptop", "transit"): SpatialConstraint("medium", "medium", 800, "medium"),
    ("mobile", "office"): SpatialConstraint("medium", "small", 600, "medium"),
    ("mobile", "home"): SpatialConstraint("medium", "small", 800, "medium"),
    ("mobile", "transit"): SpatialConstraint("low", "small", 400, "low"),
    ("mobile", "meeting"): SpatialConstraint("low", "small", 300, "low"),
    ("tablet", "office"): SpatialConstraint("medium", "medium", 1200, "medium"),
    ("tablet", "home"): SpatialConstraint("high", "medium", 1400, "high"),
}

DEFAULT_CONSTRAINT = SpatialConstraint("medium", "medium", 1000, "medium")


def infer_location_class(client_context: dict) -> str:
    """Infer the user's physical context from client_context dict.

    Priority order:
      1. Explicit location_class in client_context
      2. IP geolocation via MaxMind GeoIP2
      3. Falls back to "unknown"
    """
    explicit = client_context.get("location_class")
    if explicit and explicit != "unknown":
        return explicit

    ip = client_context.get("ip_address")
    geoip_db = client_context.get("geoip_db_path")
    if ip and geoip_db:
        try:
            import geoip2.database

            with geoip2.database.Reader(geoip_db) as reader:
                response = reader.city(ip)
                if getattr(response.traits, "is_anonymous_vpn", False):
                    return "unknown"
                if getattr(response.traits, "is_hosting_provider", False):
                    return "unknown"
                radius = getattr(response.location, "accuracy_radius", None)
                if radius and radius > 100:
                    return "unknown"
                return "inferred"
        except Exception:
            return "unknown"

    return "unknown"


def compute_spatial_constraint(client_context: dict) -> SpatialConstraint:
    """Map device type and location class to a spatial constraint vector Φ(σ)."""
    device = client_context.get("device_type", "desktop")
    location = client_context.get("location_class", "unknown")

    key = (device, location)
    return SPATIAL_PROFILES.get(key, DEFAULT_CONSTRAINT)
