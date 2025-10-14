from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base, HotshotRate
from services import hotshot_rates


@pytest.fixture
def in_memory_session(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Create an in-memory SQLite DB with sample HotshotRate data and patch Session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine)
    with TestingSession() as session:
        session.add_all(
            [
                HotshotRate(
                    miles=100,
                    zone="A",
                    per_lb=1.0,
                    min_charge=50.0,
                    weight_break=100.0,
                    fuel_pct=0.0,
                ),
                HotshotRate(
                    miles=200,
                    zone="B",
                    per_lb=1.5,
                    min_charge=75.0,
                    weight_break=100.0,
                    fuel_pct=0.0,
                ),
                HotshotRate(
                    miles=0,
                    zone="X",
                    per_lb=2.0,
                    min_charge=100.0,
                    weight_break=100.0,
                    fuel_pct=0.0,
                ),
            ]
        )
        session.commit()
    monkeypatch.setattr(hotshot_rates, "Session", TestingSession)
    yield


def test_get_hotshot_zone_by_miles_returns_zone(in_memory_session) -> None:
    """get_hotshot_zone_by_miles should return the correct zone for given miles."""
    assert hotshot_rates.get_hotshot_zone_by_miles(50) == "A"
    assert hotshot_rates.get_hotshot_zone_by_miles(150) == "B"


def test_get_hotshot_zone_by_miles_default_zone(in_memory_session) -> None:
    """Miles beyond defined tiers should map to the default zone ``"X"``."""
    assert hotshot_rates.get_hotshot_zone_by_miles(250) == "X"
    rate = hotshot_rates.get_current_hotshot_rate("X")
    assert rate.zone == "X"


def test_get_current_hotshot_rate_returns_record(in_memory_session) -> None:
    """get_current_hotshot_rate should return the HotshotRate record for the zone."""
    rate = hotshot_rates.get_current_hotshot_rate("A")
    assert rate.zone == "A"
    assert rate.miles == 100


def test_get_current_hotshot_rate_unknown_zone(in_memory_session) -> None:
    """get_current_hotshot_rate should raise ValueError when the zone does not exist."""
    with pytest.raises(ValueError):
        hotshot_rates.get_current_hotshot_rate("Z")
