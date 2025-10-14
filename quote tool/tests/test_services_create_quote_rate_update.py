import pytest

from services import quote as quote_service
from db import Session, HotshotRate


@pytest.mark.usefixtures("seed_rates")
def test_create_quote_reflects_rate_changes(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_quote should use updated rate values."""
    monkeypatch.setattr("quote.logic_hotshot.get_distance_miles", lambda o, d: 80)

    q1, _ = quote_service.create_quote(
        1, "user@example.com", "Hotshot", "12345", "67890", 120
    )
    assert q1.total == pytest.approx(120.0)

    with Session() as session:
        rate = session.query(HotshotRate).filter_by(zone="A").first()
        rate.per_lb = 2.0
        session.commit()

    q2, _ = quote_service.create_quote(
        1, "user@example.com", "Hotshot", "12345", "67890", 120
    )
    assert q2.total == pytest.approx(240.0)
