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
    """Infer the user's physical context from ``client_context`` dict.

    Priority order:
      1. Explicit ``location_class`` in client_context
      2. IP geolocation via MaxMind GeoIP2 (City DB, optional Anonymous-IP DB)
      3. Falls back to ``"unknown"``

    GeoIP2 inputs:
      - ``ip_address``: IPv4/IPv6 string to look up.
      - ``geoip_db_path``: Path to a MaxMind ``GeoIP2-City`` (or
        ``GeoLite2-City``) ``.mmdb`` file. Used for accuracy-radius and
        — when the licence tier carries them — VPN / hosting flags.
      - ``geoip_anonymous_db_path`` *(optional)*: Path to a MaxMind
        ``GeoIP2-Anonymous-IP`` ``.mmdb`` file. The City DB on the free
        ``GeoLite2`` tier does not include VPN / hosting flags, so an
        Anonymous-IP DB is the only way to get them with real data. When
        provided, an IP that the Anonymous-IP DB flags as VPN, hosting,
        Tor exit, or anonymous proxy is mapped to ``"unknown"`` even if
        the City lookup would otherwise have returned ``"inferred"``.

    The full pipeline is fail-soft — any exception (missing DB, malformed
    IP, address-not-found) collapses to ``"unknown"`` rather than raising.
    """
    explicit = client_context.get("location_class")
    if explicit and explicit != "unknown":
        return explicit

    ip = client_context.get("ip_address")
    geoip_db = client_context.get("geoip_db_path")
    if not (ip and geoip_db):
        return "unknown"

    try:
        import geoip2.database
    except ImportError:
        return "unknown"

    anon_db = client_context.get("geoip_anonymous_db_path")
    if anon_db:
        try:
            with geoip2.database.Reader(anon_db) as anon_reader:
                anon = anon_reader.anonymous_ip(ip)
                if (
                    anon.is_anonymous_vpn
                    or anon.is_hosting_provider
                    or anon.is_tor_exit_node
                    or anon.is_anonymous
                ):
                    return "unknown"
        except Exception:  # noqa: BLE001 — fail-soft, see docstring
            pass

    try:
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
    except Exception:  # noqa: BLE001 — fail-soft, see docstring
        return "unknown"


def compute_spatial_constraint(client_context: dict) -> SpatialConstraint:
    """Map device type and location class to a spatial constraint vector Φ(σ)."""
    device = client_context.get("device_type", "desktop")
    location = client_context.get("location_class", "unknown")

    key = (device, location)
    return SPATIAL_PROFILES.get(key, DEFAULT_CONSTRAINT)
