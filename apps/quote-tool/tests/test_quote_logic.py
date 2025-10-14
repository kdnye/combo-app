"""Unit tests covering the pricing helpers in the ``quote`` package."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote


def test_calculate_hotshot_quote_zone_x(monkeypatch):
    """Zone ``X`` should use the special mileage-based calculation."""

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 175)

    def zone_lookup(_miles: float) -> str:
        return "X"

    rate = SimpleNamespace(
        per_lb=1.0,
        per_mile=5.0,
        fuel_pct=0.2,
        min_charge=80.0,
        weight_break=200,
    )

    def rate_lookup(_zone: str) -> SimpleNamespace:
        return rate

    result = calculate_hotshot_quote(
        "30301",
        "98101",
        weight=120.0,
        accessorial_total=15.0,
        zone_lookup=zone_lookup,
        rate_lookup=rate_lookup,
    )

    assert result["zone"] == "X"
    assert result["per_mile"] == 5.2
    expected_total = max(175 * 5.2, 120.0 * 5.1) * 1.2 + 15.0
    assert result["quote_total"] == pytest.approx(expected_total)


def test_calculate_air_quote_handles_reversed_zone():
    """Cost-zone lookup should fall back to the reversed origin/destination pair."""

    origin = SimpleNamespace(dest_zone=1, beyond="NO")
    destination = SimpleNamespace(dest_zone=4, beyond="B1")

    def zip_lookup(zipcode: str) -> SimpleNamespace | None:
        if zipcode == "30301":
            return origin
        if zipcode == "98101":
            return destination
        return None

    def cost_lookup(concat: str) -> SimpleNamespace | None:
        if concat == "14":
            return SimpleNamespace(cost_zone="C1")
        if concat == "41":
            return SimpleNamespace(cost_zone="C1")
        return None

    def air_cost_lookup(zone: str) -> SimpleNamespace | None:
        if zone == "C1":
            return SimpleNamespace(min_charge=100.0, per_lb=1.0, weight_break=50.0)
        return None

    def beyond_lookup(zone: str | None) -> float:
        if zone == "B1":
            return 25.0
        return 0.0

    result = calculate_air_quote(
        "30301",
        "98101",
        weight=60.0,
        accessorial_total=10.0,
        zip_lookup=zip_lookup,
        cost_zone_lookup=cost_lookup,
        air_cost_lookup=air_cost_lookup,
        beyond_rate_lookup=beyond_lookup,
    )

    assert result["zone"] == "14"
    assert result["origin_beyond"] is None
    assert result["dest_charge"] == 25.0
    expected_total = ((60.0 - 50.0) * 1.0 + 100.0) + 10.0 + 25.0
    assert result["quote_total"] == pytest.approx(expected_total)


def test_calculate_air_quote_missing_origin():
    """Missing ZIP lookups should return an informative error payload."""

    result = calculate_air_quote(
        "00000",
        "11111",
        weight=10.0,
        accessorial_total=0.0,
        zip_lookup=lambda _zip: None,
    )

    assert result["quote_total"] == 0
    assert "Origin ZIP code" in result["error"]

