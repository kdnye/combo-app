import pytest

from services import quote as quote_service
from db import (
    Base,
    engine,
    Session,
    Quote,
    Accessorial,
    HotshotRate,
    AirCostZone,
    ZipZone,
    CostZone,
    BeyondRate,
)

# Create tables once for the test database
Base.metadata.create_all(engine)


@pytest.fixture(autouse=True)
def clear_db():
    """Ensure a clean database for each test."""
    with Session() as session:
        session.query(Quote).delete()
        session.query(Accessorial).delete()
        session.query(HotshotRate).delete()
        session.query(AirCostZone).delete()
        session.query(ZipZone).delete()
        session.query(CostZone).delete()
        session.query(BeyondRate).delete()
        session.commit()
    yield


def test_create_quote_hotshot(monkeypatch):
    with Session() as db:
        db.add_all(
            [
                HotshotRate(
                    miles=100,
                    zone="A",
                    per_lb=2.0,
                    fuel_pct=0.1,
                    min_charge=50,
                    weight_break=100,
                ),
                HotshotRate(
                    miles=200,
                    zone="X",
                    per_lb=0.5,
                    per_mile=1.5,
                    fuel_pct=0.2,
                    min_charge=50.0,
                    weight_break=200,
                ),
            ]
        )
        db.commit()

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    q, meta = quote_service.create_quote(
        1,
        "user@example.com",
        "Hotshot",
        "12345",
        "67890",
        120,
        accessorial_total=10,
    )

    assert q.total == pytest.approx(946.0)
    assert q.zone == "X"
    assert meta["miles"] == 150


def test_create_quote_air():
    with Session() as db:
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

    q, meta = quote_service.create_quote(
        1,
        "user@example.com",
        "Air",
        "12345",
        "67890",
        60,
        accessorial_total=10,
    )

    assert q.total == pytest.approx(140.0)
    assert q.zone == "12"
    assert meta["accessorial_total"] == 10


def test_create_quote_air_with_guarantee():
    with Session() as db:
        db.add_all(
            [
                ZipZone(zipcode="12345", dest_zone=1, beyond="NO"),
                ZipZone(zipcode="67890", dest_zone=2, beyond="B1"),
                CostZone(concat="12", cost_zone="C1"),
                AirCostZone(zone="C1", min_charge=100, per_lb=1.0, weight_break=50),
                BeyondRate(zone="B1", rate=20.0, up_to_miles=0.0),
                Accessorial(name="Guarantee", amount=25.0, is_percentage=True),
            ]
        )
        db.commit()

    q, meta = quote_service.create_quote(
        1,
        "user@example.com",
        "Air",
        "12345",
        "67890",
        60,
        accessorial_total=10,
        accessorials=["Guarantee"],
    )

    assert q.total == pytest.approx(172.5)
    assert meta["accessorials"]["Guarantee"] == pytest.approx(32.5)
    assert meta["accessorial_total"] == pytest.approx(42.5)


def test_accessorial_case_insensitive(monkeypatch):
    with Session() as db:
        db.add_all(
            [
                HotshotRate(
                    miles=100,
                    zone="A",
                    per_lb=2.0,
                    fuel_pct=0.1,
                    min_charge=50,
                    weight_break=100,
                ),
                HotshotRate(
                    miles=200,
                    zone="X",
                    per_lb=0.0,
                    per_mile=1.5,
                    fuel_pct=0.2,
                    min_charge=50.0,
                    weight_break=200,
                ),
                Accessorial(name="Liftgate", amount=25.0),
            ]
        )
        db.commit()

    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 150)

    q, meta = quote_service.create_quote(
        1,
        "user@example.com",
        "Hotshot",
        "12345",
        "67890",
        120,
        accessorial_total=10,
        accessorials=["liftGATE"],
    )

    assert q.total == pytest.approx(971.0)
    assert meta["accessorials"]["Liftgate"] == 25.0
    assert meta["accessorial_total"] == 35.0


def test_create_quote_uses_precomputed_dim_weight(monkeypatch):
    monkeypatch.setattr(
        quote_service,
        "calculate_hotshot_quote",
        lambda *a, **k: {"quote_total": 0, "zone": "A"},
    )

    q, meta = quote_service.create_quote(
        1,
        "user@example.com",
        "Hotshot",
        "12345",
        "67890",
        10,
        dim_weight=60,
    )

    assert q.weight == 60
    assert q.weight_method == "Dimensional"
    assert q.actual_weight == 10
    assert q.dim_weight == 60


def test_create_quote_threshold_warnings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quotes over limits should include the standard warning."""

    warning_msg = (
        "Warning! Quote exceeds the limits of this tool please call FSI directly for the most accurate quote. "
        "Main Office: 800-651-0423 | Fax: 520-777-3853 | Email: Operations@freightservices.net"
    )

    monkeypatch.setattr(
        quote_service,
        "calculate_hotshot_quote",
        lambda *a, **k: {"quote_total": 7000, "zone": "A"},
    )

    q, _ = quote_service.create_quote(
        1,
        "user@example.com",
        "Hotshot",
        "12345",
        "67890",
        4000,
    )

    assert warning_msg in q.warnings
