"""End-to-end positive coverage for the MaxMind GeoIP2 spatial-grounding path.

The intent advertises three location-class sources: explicit, GeoIP2,
"unknown" fallback. Until v0.2.0 only the first and third had tests. Here
we use a fake ``geoip2.database`` reader (installed onto ``sys.modules``
for the test) to drive the full code path without a network or licensed
MaxMind database. This is the standard pattern for testing optional
heavyweight integrations: real wiring, fake backend.
"""

from __future__ import annotations

import sys
import types

import pytest

from horizon.spacetime.spatial import infer_location_class

# ── Fake geoip2.database module ──────────────────────────────────────────────


class _Traits:
    def __init__(self, *, anonymous_vpn: bool = False, hosting: bool = False) -> None:
        self.is_anonymous_vpn = anonymous_vpn
        self.is_hosting_provider = hosting


class _Location:
    def __init__(self, accuracy_radius: int | None = 10) -> None:
        self.accuracy_radius = accuracy_radius


class _Response:
    def __init__(self, *, location: _Location, traits: _Traits) -> None:
        self.location = location
        self.traits = traits


class _FakeReader:
    """Minimal stand-in for geoip2.database.Reader with a context-manager API."""

    def __init__(
        self,
        *,
        location: _Location | None = None,
        traits: _Traits | None = None,
        raise_on_lookup: Exception | None = None,
    ) -> None:
        self._response = _Response(
            location=location or _Location(),
            traits=traits or _Traits(),
        )
        self._raise = raise_on_lookup

    def __enter__(self) -> "_FakeReader":
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def city(self, ip: str) -> _Response:  # noqa: ARG002
        if self._raise is not None:
            raise self._raise
        return self._response


def _install_fake_geoip2(monkeypatch: pytest.MonkeyPatch, reader_factory) -> None:
    fake_database = types.SimpleNamespace(Reader=reader_factory)
    fake_geoip2 = types.SimpleNamespace(database=fake_database)
    monkeypatch.setitem(sys.modules, "geoip2", fake_geoip2)
    monkeypatch.setitem(sys.modules, "geoip2.database", fake_database)


# ── Tests ────────────────────────────────────────────────────────────────────


def test_geoip_returns_inferred_for_high_accuracy_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_geoip2(
        monkeypatch,
        lambda _path: _FakeReader(
            location=_Location(accuracy_radius=5),
            traits=_Traits(),
        ),
    )

    loc = infer_location_class(
        {
            "ip_address": "8.8.8.8",
            "geoip_db_path": "/dev/null",  # path is opaque to the fake reader
        }
    )
    assert loc == "inferred"


def test_geoip_returns_unknown_for_low_accuracy_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Accuracy radius > 100km is too coarse to act on — fall back to unknown."""
    _install_fake_geoip2(
        monkeypatch,
        lambda _path: _FakeReader(
            location=_Location(accuracy_radius=250),
        ),
    )

    loc = infer_location_class(
        {"ip_address": "8.8.8.8", "geoip_db_path": "/dev/null"}
    )
    assert loc == "unknown"


def test_geoip_anonymous_vpn_marked_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_geoip2(
        monkeypatch,
        lambda _path: _FakeReader(
            location=_Location(accuracy_radius=5),
            traits=_Traits(anonymous_vpn=True),
        ),
    )

    loc = infer_location_class(
        {"ip_address": "8.8.8.8", "geoip_db_path": "/dev/null"}
    )
    assert loc == "unknown"


def test_geoip_hosting_provider_marked_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Datacenter IPs aren't user locations — they get suppressed."""
    _install_fake_geoip2(
        monkeypatch,
        lambda _path: _FakeReader(
            location=_Location(accuracy_radius=5),
            traits=_Traits(hosting=True),
        ),
    )

    loc = infer_location_class(
        {"ip_address": "8.8.8.8", "geoip_db_path": "/dev/null"}
    )
    assert loc == "unknown"


def test_geoip_lookup_failure_falls_back_to_unknown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A missing DB file or corrupt index must not crash the pipeline."""
    _install_fake_geoip2(
        monkeypatch,
        lambda _path: _FakeReader(
            raise_on_lookup=RuntimeError("address not found"),
        ),
    )

    loc = infer_location_class(
        {"ip_address": "8.8.8.8", "geoip_db_path": "/dev/null"}
    )
    assert loc == "unknown"


def test_explicit_location_class_overrides_geoip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the caller supplies location_class, GeoIP is not consulted at all."""
    called: list[bool] = []

    def reader_factory(_path: str) -> _FakeReader:
        called.append(True)
        return _FakeReader()

    _install_fake_geoip2(monkeypatch, reader_factory)

    loc = infer_location_class(
        {
            "location_class": "office",
            "ip_address": "8.8.8.8",
            "geoip_db_path": "/dev/null",
        }
    )
    assert loc == "office"
    assert called == [], "GeoIP must not be invoked when location_class is explicit"
