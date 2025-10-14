import os
import sys
from typing import Iterator

# Use a dedicated SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")

# Ensure project root is on sys.path for imports
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from db import (
    Base,
    engine,
    Session,
    Accessorial,
    BeyondRate,
    HotshotRate,
)

# Create all tables once for the test database
Base.metadata.create_all(engine)


@pytest.fixture
def seed_rates() -> Iterator[None]:
    """Seed rate-related tables with sample data.

    Includes a percentage-based "Guarantee" accessorial and a fixed-cost
    "Liftgate" entry.
    """
    with Session() as session:
        session.query(HotshotRate).delete()
        session.query(Accessorial).delete()
        session.query(BeyondRate).delete()
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
                BeyondRate(zone="B1", rate=2.0, up_to_miles=10.0),
                Accessorial(name="Liftgate", amount=25.0, is_percentage=False),
                Accessorial(name="Guarantee", amount=5.0, is_percentage=True),
            ]
        )
        session.commit()
    yield
    with Session() as session:
        session.query(HotshotRate).delete()
        session.query(Accessorial).delete()
        session.query(BeyondRate).delete()
        session.commit()


@pytest.fixture(autouse=True)
def clear_quote_caches() -> Iterator[None]:
    """Ensure cached quote helpers do not leak state between tests."""

    from app.quotes import routes as quote_routes

    quote_routes.clear_accessorial_cache()
    quote_routes.clear_air_rate_cache()
    yield
    quote_routes.clear_accessorial_cache()
    quote_routes.clear_air_rate_cache()
