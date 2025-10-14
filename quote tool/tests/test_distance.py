"""Tests for :mod:`quote.distance` helper functions."""

from quote import distance


def test_sanitize_zip_accepts_zip_plus_four() -> None:
    """ZIP+4 input should be truncated to five digits for Google Maps."""

    assert distance._sanitize_zip("12345-6789") == "12345,USA"


def test_sanitize_zip_rejects_short_values() -> None:
    """Inputs shorter than five digits should be rejected."""

    assert distance._sanitize_zip("1234") is None
