import json
import pytest
from sqlalchemy import event

from app import create_app
from app.models import (
    db,
    User,
    Quote,
    Accessorial,
    ZipZone,
    CostZone,
    AirCostZone,
    BeyondRate,
)
from config import Config
from quote.thresholds import THRESHOLD_WARNING


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True


def test_accessorial_helper_uses_cache() -> None:
    """Repeated calls to the accessorial helper should reuse one query."""

    app = create_app(TestConfig)

    with app.app_context():
        db.session.query(Accessorial).delete()
        db.session.commit()

        db.session.add(Accessorial(name="Liftgate", amount=50.0))
        db.session.commit()

        import app.quotes.routes as qr

        statements: list[str] = []

        def record_accessorial(
            conn, cursor, statement, parameters, context, executemany
        ) -> None:
            sql = statement.strip().lower()
            if sql.startswith("select") and "accessorial" in sql:
                statements.append(statement)

        event.listen(db.engine, "before_cursor_execute", record_accessorial)
        try:
            options, lookup = qr._get_accessorial_choices()
            assert options == ["Liftgate"]
            assert lookup["liftgate"].amount == 50.0

            options_again, lookup_again = qr._get_accessorial_choices()
            assert options_again == ["Liftgate"]
            assert lookup_again["liftgate"].amount == 50.0
            assert len(statements) == 1

            db.session.add(Accessorial(name="Dock Fee", amount=15.0))
            db.session.commit()

            qr.clear_accessorial_cache()
            options_after, lookup_after = qr._get_accessorial_choices()
            assert "Dock Fee" in options_after
            assert lookup_after["dock fee"].amount == 15.0
            assert len(statements) == 2
        finally:
            event.remove(db.engine, "before_cursor_execute", record_accessorial)


def test_air_rate_helper_detects_missing_tables() -> None:
    """The air rate helper caches results but still refreshes when cleared."""

    app = create_app(TestConfig)

    with app.app_context():
        for model in (ZipZone, CostZone, AirCostZone):
            db.session.query(model).delete()
        db.session.commit()

        import app.quotes.routes as qr

        statements: list[str] = []

        def record_air_tables(
            conn, cursor, statement, parameters, context, executemany
        ) -> None:
            lower = statement.lower()
            if any(
                name in lower for name in ("zip_zone", "cost_zone", "air_cost_zone")
            ):
                statements.append(lower)

        event.listen(db.engine, "before_cursor_execute", record_air_tables)
        try:
            missing_first = qr._get_missing_air_rate_tables()
            assert {"ZipZone", "CostZone", "AirCostZone"} <= set(missing_first)
            first_len = len(statements)

            missing_second = qr._get_missing_air_rate_tables()
            assert missing_second == missing_first
            assert len(statements) == first_len

            db.session.add(ZipZone(zipcode="85001", dest_zone=1, beyond=None))
            db.session.commit()

            qr.clear_air_rate_cache()
            missing_after = qr._get_missing_air_rate_tables()
            assert "ZipZone" not in missing_after
            assert len(statements) > first_len
        finally:
            event.remove(db.engine, "before_cursor_execute", record_air_tables)


def test_new_quote_applies_accessorials_and_guarantee(monkeypatch):
    """Ensure selected accessorials and Guarantee are applied to Air quotes."""

    app = create_app(TestConfig)

    with app.app_context():
        # Create a dummy user and patch current_user to bypass authentication.
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)

        db.session.add_all(
            [
                Accessorial(name="Liftgate", amount=50.0),
                Accessorial(name="Guarantee", amount=0.0, is_percentage=True),
                ZipZone(zipcode="85001", dest_zone=1, beyond=None),
                ZipZone(zipcode="85705", dest_zone=2, beyond=None),
                CostZone(concat="12", cost_zone="A"),
                AirCostZone(zone="A", min_charge=100.0, per_lb=1.0, weight_break=100.0),
                BeyondRate(zone="B1", rate=0.5, up_to_miles=100.0),
            ]
        )
        db.session.commit()

        seen = {}

        def fake_air_quote(origin, destination, weight, accessorial_total):
            seen["accessorial_total"] = accessorial_total
            return {"quote_total": 100 + accessorial_total}

        monkeypatch.setattr(qr, "calculate_air_quote", fake_air_quote)

        client = app.test_client()
        resp = client.post(
            "/quotes/new",
            data={
                "quote_type": "Air",
                "origin_zip": "85001",
                "dest_zip": "85705",
                "weight_actual": "88",
                "accessorials": ["Liftgate", "Guarantee"],
            },
            follow_redirects=True,
        )

        assert resp.status_code == 200
        # Only the fixed-dollar accessorial should be summed.
        assert seen["accessorial_total"] == 50

        q = Quote.query.first()
        meta = json.loads(q.quote_metadata)
        assert q.total == pytest.approx(100 + 50 + 100 * 0.25)
        assert meta["accessorials"]["Guarantee"] == pytest.approx(100 * 0.25)
        assert b"Liftgate: $50.00" in resp.data
        assert b"Guarantee: $25.00" in resp.data
        assert b"Accessorials Total:</strong> $75.00" in resp.data
        expected_base = f"Base Charge:</strong> $100.00".encode()
        expected_total = f'class="quote-total-amount mb-0">${q.total:.2f}</p>'.encode()
        assert expected_base in resp.data
        assert b"quote-total-highlight" in resp.data
        assert expected_total in resp.data


def test_air_quote_invalid_zip_shows_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """An invalid ZIP should not create a quote and must flash an error."""

    app = create_app(TestConfig)

    with app.app_context():
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add_all(
            [
                user,
                Accessorial(name="Liftgate", amount=50.0),
                ZipZone(zipcode="85001", dest_zone=1, beyond=None),
                ZipZone(zipcode="85705", dest_zone=2, beyond=None),
                CostZone(concat="12", cost_zone="A"),
                AirCostZone(zone="A", min_charge=100.0, per_lb=1.0, weight_break=100.0),
            ]
        )
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)

        def fake_air_quote(
            origin: str, destination: str, weight: float, accessorial_total: float
        ) -> dict:
            return {"error": "Invalid ZIP"}

        monkeypatch.setattr(qr, "calculate_air_quote", fake_air_quote)

        client = app.test_client()
        resp = client.post(
            "/quotes/new",
            data={
                "quote_type": "Air",
                "origin_zip": "85001",
                "dest_zip": "85705",
                "weight_actual": "88",
            },
            follow_redirects=True,
        )

        assert resp.status_code == 400
        assert b"Invalid ZIP" in resp.data
        assert Quote.query.count() == 0


def test_air_quote_missing_rate_tables_returns_warning(monkeypatch):
    """Air quote route should warn when rate tables are absent."""

    app = create_app(TestConfig)

    with app.app_context():
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add_all([user, Accessorial(name="Liftgate", amount=50.0)])
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)

        # Drop required air rate tables to simulate an uninitialized database.
        for table in [ZipZone.__table__, CostZone.__table__, AirCostZone.__table__]:
            table.drop(db.engine)

        qr.clear_air_rate_cache()

        client = app.test_client()
        resp = client.post(
            "/quotes/new",
            data={
                "quote_type": "Air",
                "origin_zip": "85001",
                "dest_zip": "85705",
                "weight_actual": "88",
            },
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert b"Air rate table(s) missing or empty" in resp.data
        q = Quote.query.first()
        assert "Air rate table(s) missing or empty" in q.warnings


def test_hotshot_quote_shows_miles_and_accessorials(monkeypatch):
    app = create_app(TestConfig)

    with app.app_context():
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add(user)
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)

        db.session.add(Accessorial(name="Liftgate", amount=50.0))
        db.session.commit()

        def fake_hotshot_quote(origin, destination, weight, accessorial_total):
            return {"quote_total": 200 + accessorial_total, "miles": 123}

        monkeypatch.setattr(qr, "calculate_hotshot_quote", fake_hotshot_quote)

        client = app.test_client()
        resp = client.post(
            "/quotes/new",
            data={
                "quote_type": "Hotshot",
                "origin_zip": "85001",
                "dest_zip": "85705",
                "weight_actual": "88",
                "accessorials": ["Liftgate"],
                "pieces": "3",
            },
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert b"Total Miles: 123" in resp.data
        assert b"Liftgate: $50.00" in resp.data
        assert b"Accessorials Total:</strong> $50.00" in resp.data
        assert b"Pieces: 3" in resp.data
        q = Quote.query.first()
        expected_base = f"Base Charge:</strong> ${(q.total - 50):.2f}".encode()
        expected_total = f'class="quote-total-amount mb-0">${q.total:.2f}</p>'.encode()
        assert expected_base in resp.data
        assert b"quote-total-highlight" in resp.data
        assert expected_total in resp.data


def test_new_quote_exceeds_limits_warns(monkeypatch):
    """Quotes beyond configured limits should trigger a warning message."""

    app = create_app(TestConfig)

    with app.app_context():
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add_all([user, Accessorial(name="Liftgate", amount=50.0)])
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)
        monkeypatch.setattr(qr, "user_has_mail_privileges", lambda _user: True)

        def fake_hotshot_quote(origin, destination, weight, accessorial_total):
            return {"quote_total": 7000, "miles": 123}

        monkeypatch.setattr(qr, "calculate_hotshot_quote", fake_hotshot_quote)

        client = app.test_client()
        resp = client.post(
            "/quotes/new",
            data={
                "quote_type": "Hotshot",
                "origin_zip": "85001",
                "dest_zip": "85705",
                "weight_actual": "3100",
            },
            follow_redirects=True,
        )

        assert resp.status_code == 200
        assert THRESHOLD_WARNING.encode() in resp.data
        assert b"Email for help with volume quote pricing" in resp.data
        q = Quote.query.first()
        assert THRESHOLD_WARNING in q.warnings


def test_new_quote_json_response_includes_threshold_flag(monkeypatch):
    """JSON quote responses should include a threshold indicator flag."""

    app = create_app(TestConfig)

    with app.app_context():
        user = User(email="tester@example.com")
        user.set_password("secret")
        db.session.add_all([user, Accessorial(name="Liftgate", amount=50.0)])
        db.session.commit()

        import app.quotes.routes as qr

        monkeypatch.setattr(qr, "current_user", user)

        def fake_hotshot_quote(origin, destination, weight, accessorial_total):
            if weight > 3000:
                return {"quote_total": 7000}
            return {"quote_total": 500}

        monkeypatch.setattr(qr, "calculate_hotshot_quote", fake_hotshot_quote)

        client = app.test_client()

        resp = client.post(
            "/quotes/new",
            json={
                "quote_type": "Hotshot",
                "origin": "85001",
                "destination": "85705",
                "weight_actual": 100,
            },
        )

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["exceeds_threshold"] is False
        assert data["warnings"] == ""

        resp_high = client.post(
            "/quotes/new",
            json={
                "quote_type": "Hotshot",
                "origin": "85001",
                "destination": "85705",
                "weight_actual": 3100,
            },
        )

        assert resp_high.status_code == 200
        data_high = resp_high.get_json()
        assert data_high["exceeds_threshold"] is True
        assert THRESHOLD_WARNING in data_high["warnings"]
