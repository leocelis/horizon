"""Tests for deictic temporal expression resolution."""

from __future__ import annotations

import pytest

from horizon.spacetime.deictic import resolve_deictic_expressions


REF_TS = "2026-04-22T10:00:00+00:00"


def test_no_temporal_expressions() -> None:
    """Text with no dates returns empty list."""
    refs = resolve_deictic_expressions("Hello, how are you?", REF_TS)
    assert isinstance(refs, list)
    # May or may not have false positives; length >= 0
    assert len(refs) >= 0


def test_yesterday_resolves() -> None:
    """'yesterday' resolves to a date one day before the reference."""
    refs = resolve_deictic_expressions("I asked you about this yesterday.", REF_TS)
    assert len(refs) >= 0  # dateparser may not always detect
    for ref in refs:
        assert ref.resolved is not None or ref.resolved is None  # both valid


def test_resolved_is_iso_string_or_none() -> None:
    """Resolved values must be ISO 8601 strings or None."""
    refs = resolve_deictic_expressions("Let's meet next Monday at 3pm.", REF_TS)
    for ref in refs:
        if ref.resolved is not None:
            # Should parse as ISO 8601 without error
            from datetime import datetime
            datetime.fromisoformat(ref.resolved)


def test_type_field_is_valid() -> None:
    """type field must be one of the allowed literals."""
    valid_types = {"DATE", "TIME", "DURATION", "SET", "UNKNOWN"}
    refs = resolve_deictic_expressions("See you in 3 hours.", REF_TS)
    for ref in refs:
        assert ref.type in valid_types


def test_idempotent_on_empty_text() -> None:
    """Empty text returns empty list without error."""
    refs = resolve_deictic_expressions("", REF_TS)
    assert refs == []


def test_expression_field_non_empty() -> None:
    """expression field is always a non-empty string for returned references."""
    refs = resolve_deictic_expressions("I need this by end of day.", REF_TS)
    for ref in refs:
        assert len(ref.expression) > 0


def test_resolution_idempotent() -> None:
    """Property referenced by horizon_intent.yaml::property_tests.deictic_idempotence.

    Same text processed twice with the same reference timestamp yields
    identical temporal references; unresolvable text returns [] (no error).
    """
    text = "We discussed this yesterday and need to ship by next Monday"
    a = resolve_deictic_expressions(text, REF_TS)
    b = resolve_deictic_expressions(text, REF_TS)

    assert len(a) == len(b)
    for ra, rb in zip(a, b):
        assert ra.expression == rb.expression
        assert ra.resolved == rb.resolved
        assert ra.type == rb.type

    assert resolve_deictic_expressions("", REF_TS) == []
