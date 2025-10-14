import pytest
from types import SimpleNamespace
from quote.logic_hotshot import calculate_hotshot_quote
from quote.logic_air import calculate_air_quote
from db import Session, ZipZone, CostZone, AirCostZone, BeyondRate
from sqlalchemy.exc import OperationalError


def test_calculate_hotshot_quote(monkeypatch):
    def zone_lookup(miles: float) -> str:
        return "A"

    rate = SimpleNamespace(
        per_lb=2.0,
        per_mile=None,
        fuel_pct=0.1,
        min_charge=50,
        weight_break=100,
    )

    def rate_lookup(zone: str):
        return rate

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 100)

    result = calculate_hotshot_quote(
        "12345", "67890", 1000, 10, zone_lookup=zone_lookup, rate_lookup=rate_lookup
    )

    assert result["zone"] == "A"
    assert result["miles"] == 100
    assert result["quote_total"] == pytest.approx(2210.0)


def test_calculate_hotshot_quote_none_weight_break(monkeypatch):
    """calculate_hotshot_quote should use weight pricing when per_mile is absent."""

    def zone_lookup(miles: float) -> str:
        return "A"

    rate = SimpleNamespace(
        per_lb=0.5,
        per_mile=None,
        fuel_pct=0.2,
        min_charge=5.0,
        weight_break=None,
    )

    def rate_lookup(zone: str):
        return rate

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    result = calculate_hotshot_quote(
        "12345", "67890", 120, 10, zone_lookup=zone_lookup, rate_lookup=rate_lookup
    )

    assert result["weight_break"] is None
    assert result["quote_total"] == pytest.approx(82.0)


def test_calculate_hotshot_quote_zone_x(monkeypatch):
    """Zone X uses fixed per-pound pricing with a mileage-based minimum."""

    def zone_lookup(miles: float) -> str:
        return "X"

    rate = SimpleNamespace(
        per_lb=0.5,
        per_mile=None,
        fuel_pct=0.2,
        min_charge=50.0,
        weight_break=200,
    )

    def rate_lookup(zone: str):
        return rate

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    result = calculate_hotshot_quote(
        "12345", "67890", 120, 10, zone_lookup=zone_lookup, rate_lookup=rate_lookup
    )

    assert result["zone"] == "X"
    assert result["quote_total"] == pytest.approx(946.0)


def test_calculate_hotshot_quote_missing_zone(monkeypatch):
    def zone_lookup(miles: float) -> str:
        return "A"

    def rate_lookup(zone: str):
        raise ValueError("missing zone")

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    with pytest.raises(ValueError):
        calculate_hotshot_quote(
            "12345", "67890", 120, 10, zone_lookup=zone_lookup, rate_lookup=rate_lookup
        )


def test_calculate_air_quote():
    with Session() as db:
        db.query(ZipZone).delete()
        db.query(CostZone).delete()
        db.query(AirCostZone).delete()
        db.query(BeyondRate).delete()
        db.add_all(
            [
                ZipZone(zipcode="12345", dest_zone=1, beyond="NO"),
                ZipZone(zipcode="67890", dest_zone=2, beyond="B1"),
                CostZone(concat="12", cost_zone="C1"),
                AirCostZone(zone="C1", min_charge=100, per_lb=1.0, weight_break=50),
                BeyondRate(zone="B1", rate=20.0, up_to_miles=0.0),
            ]
        )
        db.commit()

    result = calculate_air_quote("12345", "67890", 60, 10)

    assert result["zone"] == "12"
    assert result["beyond_total"] == 20
    assert result["quote_total"] == pytest.approx(140.0)


def test_calculate_air_quote_reverse_cost_zone():
    """calculate_air_quote should fall back to the reverse zone pair."""

    with Session() as db:
        db.query(ZipZone).delete()
        db.query(CostZone).delete()
        db.query(AirCostZone).delete()
        db.query(BeyondRate).delete()
        db.add_all(
            [
                ZipZone(zipcode="12345", dest_zone=4, beyond="NO"),
                ZipZone(zipcode="67890", dest_zone=1, beyond="B1"),
                CostZone(concat="14", cost_zone="C1"),
                AirCostZone(zone="C1", min_charge=100, per_lb=1.0, weight_break=50),
                BeyondRate(zone="B1", rate=20.0, up_to_miles=0.0),
            ]
        )
        db.commit()

    result = calculate_air_quote("12345", "67890", 60, 10)

    assert result["zone"] == "41"
    assert result["quote_total"] == pytest.approx(140.0)


def test_calculate_air_quote_missing_zip():
    with Session() as db:
        db.query(ZipZone).delete()
        db.query(CostZone).delete()
        db.query(AirCostZone).delete()
        db.query(BeyondRate).delete()
        db.add_all(
            [
                ZipZone(zipcode="67890", dest_zone=2, beyond="B1"),
                CostZone(concat="12", cost_zone="C1"),
                AirCostZone(zone="C1", min_charge=100, per_lb=1.0, weight_break=50),
                BeyondRate(zone="B1", rate=20.0, up_to_miles=0.0),
            ]
        )
        db.commit()

    result = calculate_air_quote("12345", "67890", 60, 10)

    assert result["quote_total"] == 0
    assert "Origin ZIP code 12345 not found" in (result["error"] or "")


def test_calculate_air_quote_missing_destination():
    with Session() as db:
        db.query(ZipZone).delete()
        db.query(CostZone).delete()
        db.query(AirCostZone).delete()
        db.query(BeyondRate).delete()
        db.add_all(
            [
                ZipZone(zipcode="12345", dest_zone=1, beyond="NO"),
                CostZone(concat="11", cost_zone="C1"),
                AirCostZone(zone="C1", min_charge=100, per_lb=1.0, weight_break=50),
                BeyondRate(zone="B1", rate=20.0, up_to_miles=0.0),
            ]
        )
        db.commit()

    result = calculate_air_quote("12345", "67890", 60, 10)

    assert result["quote_total"] == 0
    assert "Destination ZIP code 67890 not found" in (result["error"] or "")


def test_calculate_air_quote_origin_missing_dest_zone():
    def zip_lookup(zipcode: str):
        if zipcode == "12345":
            return SimpleNamespace(beyond="NO")
        return SimpleNamespace(dest_zone=2, beyond="B1")

    def unused(*_: object, **__: object) -> None:
        raise AssertionError("Should not be called")

    result = calculate_air_quote(
        "12345",
        "67890",
        60,
        10,
        zip_lookup=zip_lookup,
        cost_zone_lookup=unused,
        air_cost_lookup=unused,
        beyond_rate_lookup=unused,
    )

    assert result["quote_total"] == 0
    assert "Origin ZIP code 12345 missing dest_zone" in (result["error"] or "")


def test_calculate_air_quote_origin_missing_beyond():
    def zip_lookup(zipcode: str):
        if zipcode == "12345":
            return SimpleNamespace(dest_zone=1)
        return SimpleNamespace(dest_zone=2, beyond="B1")

    def unused(*_: object, **__: object) -> None:
        raise AssertionError("Should not be called")

    result = calculate_air_quote(
        "12345",
        "67890",
        60,
        10,
        zip_lookup=zip_lookup,
        cost_zone_lookup=unused,
        air_cost_lookup=unused,
        beyond_rate_lookup=unused,
    )

    assert result["quote_total"] == 0
    assert "Origin ZIP code 12345 missing beyond" in (result["error"] or "")


def test_calculate_air_quote_dest_missing_dest_zone():
    def zip_lookup(zipcode: str):
        if zipcode == "12345":
            return SimpleNamespace(dest_zone=1, beyond="NO")
        return SimpleNamespace(beyond="B1")

    def unused(*_: object, **__: object) -> None:
        raise AssertionError("Should not be called")

    result = calculate_air_quote(
        "12345",
        "67890",
        60,
        10,
        zip_lookup=zip_lookup,
        cost_zone_lookup=unused,
        air_cost_lookup=unused,
        beyond_rate_lookup=unused,
    )

    assert result["quote_total"] == 0
    assert "Destination ZIP code 67890 missing dest_zone" in (result["error"] or "")


def test_calculate_air_quote_dest_missing_beyond():
    def zip_lookup(zipcode: str):
        if zipcode == "12345":
            return SimpleNamespace(dest_zone=1, beyond="NO")
        return SimpleNamespace(dest_zone=2)

    def unused(*_: object, **__: object) -> None:
        raise AssertionError("Should not be called")

    result = calculate_air_quote(
        "12345",
        "67890",
        60,
        10,
        zip_lookup=zip_lookup,
        cost_zone_lookup=unused,
        air_cost_lookup=unused,
        beyond_rate_lookup=unused,
    )

    assert result["quote_total"] == 0
    assert "Destination ZIP code 67890 missing beyond" in (result["error"] or "")


def test_get_zip_zone_operational_error(monkeypatch):
    import quote.logic_air as la

    class DummySession:
        def __enter__(self):
            class DummyDB:
                def query(self, *args, **kwargs):
                    raise OperationalError("test", None, None)

            return DummyDB()

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(la, "Session", lambda: DummySession())
    assert la.get_zip_zone("85001") is None


def test_get_beyond_rate_operational_error(monkeypatch):
    import quote.logic_air as la

    class DummySession:
        def __enter__(self):
            class DummyDB:
                def query(self, *args, **kwargs):
                    raise OperationalError("test", None, None)

            return DummyDB()

        def __exit__(self, exc_type, exc, tb):
            pass

    monkeypatch.setattr(la, "Session", lambda: DummySession())
    assert la.get_beyond_rate("B1") == 0.0
