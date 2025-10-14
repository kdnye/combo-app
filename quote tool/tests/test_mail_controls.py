import json
import re
from typing import Any, Generator

import pytest
from flask import url_for

from app import create_app
from app.models import db, EmailDispatchLog, Quote, User, AppSetting
from services.settings import set_setting


class DummySMTP:
    """Lightweight SMTP stub used to avoid external calls in tests."""

    sent_messages: list = []
    login_calls: list = []

    def __init__(
        self, *args, **kwargs
    ) -> None:  # noqa: D401 - Signature matches smtplib
        DummySMTP.sent_messages = []
        DummySMTP.login_calls = []

    def __enter__(self) -> "DummySMTP":
        return self

    def __exit__(self, *exc_info) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, *_args, **_kwargs) -> None:
        DummySMTP.login_calls.append(_args)
        return None

    def send_message(self, message) -> None:
        DummySMTP.sent_messages.append(message)


@pytest.fixture
def app(monkeypatch) -> Generator:
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY=1,
        MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR=10,
        MAIL_RATE_LIMIT_PER_USER_PER_HOUR=5,
        MAIL_RATE_LIMIT_PER_USER_PER_DAY=5,
        MAIL_DEFAULT_SENDER="quote@freightservices.net",
        MAIL_ALLOWED_SENDER_DOMAIN="freightservices.net",
        MAIL_PRIVILEGED_DOMAIN="freightservices.net",
        MAIL_SERVER="smtp.office365.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        GOOGLE_MAPS_API_KEY="test-key",
    )

    monkeypatch.setattr("app.admin.csrf.protect", lambda: None)
    monkeypatch.setattr("smtplib.SMTP", DummySMTP)
    monkeypatch.setattr("smtplib.SMTP_SSL", DummySMTP)
    monkeypatch.setattr(
        "quote.distance.get_distance_miles", lambda *_args, **_kwargs: 100.0
    )

    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _create_user(
    email: str,
    password: str,
    *,
    name: str = "Test User",
    role: str = "customer",
    employee_approved: bool = False,
) -> User:
    """Persist a user record for login tests."""

    user = User(
        email=email,
        name=name,
        is_active=True,
        role=role,
        employee_approved=employee_approved,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def _get_setting_value(key: str) -> str | None:
    record = AppSetting.query.filter_by(key=key).one_or_none()
    return record.value if record else None


def test_send_email_requires_login(app, client):
    response = client.post(
        "/send",
        data={
            "origin_zip": "30301",
            "destination_zip": "90210",
            "email": "customer@example.com",
        },
    )
    assert response.status_code == 302
    with app.test_request_context():
        login_url = url_for("auth.login")
    assert response.headers["Location"].startswith(login_url)


def test_send_email_rejects_non_privileged_user(app, client):
    with app.app_context():
        _create_user("customer@example.com", "SafePass!1234")

    client.post(
        "/login",
        data={"email": "customer@example.com", "password": "SafePass!1234"},
        follow_redirects=True,
    )

    response = client.post(
        "/send",
        data={
            "origin_zip": "30301",
            "destination_zip": "90210",
            "email": "customer@example.com",
        },
        follow_redirects=True,
    )
    assert (
        "Quote emails are limited to Freight Services staff accounts."
        in response.get_data(as_text=True)
    )


def test_send_email_rejects_unapproved_employee(app, client):
    with app.app_context():
        _create_user(
            "pending@freightservices.net",
            "SafePass!1234",
            role="employee",
            employee_approved=False,
        )

    client.post(
        "/login",
        data={"email": "pending@freightservices.net", "password": "SafePass!1234"},
        follow_redirects=True,
    )

    response = client.post(
        "/send",
        data={
            "origin_zip": "30301",
            "destination_zip": "90210",
            "email": "customer@example.com",
        },
        follow_redirects=True,
    )
    assert (
        "Quote emails are limited to Freight Services staff accounts."
        in response.get_data(as_text=True)
    )


def test_quote_email_rate_limit_per_recipient(app, client):
    with app.app_context():
        _create_user(
            "agent@freightservices.net",
            "SafePass!1234",
            role="employee",
            employee_approved=True,
        )

    client.post(
        "/login",
        data={"email": "agent@freightservices.net", "password": "SafePass!1234"},
        follow_redirects=True,
    )

    response = client.post(
        "/send",
        data={
            "origin_zip": "30301",
            "destination_zip": "90210",
            "email": "customer@example.com",
        },
        follow_redirects=True,
    )
    assert "Quote email sent." in response.get_data(as_text=True)

    response2 = client.post(
        "/send",
        data={
            "origin_zip": "30301",
            "destination_zip": "90210",
            "email": "customer@example.com",
        },
        follow_redirects=True,
    )
    assert "Too many emails have been sent to this recipient" in response2.get_data(
        as_text=True
    )

    with app.app_context():
        assert EmailDispatchLog.query.count() == 1


def _create_user_and_quote(
    email: str,
    password: str,
    *,
    role: str = "customer",
    employee_approved: bool = False,
) -> tuple[str, str]:
    metadata = {
        "accessorial_total": 0,
        "accessorials": {},
        "miles": None,
        "pieces": 1,
        "details": {},
    }
    user = _create_user(
        email,
        password,
        role=role,
        employee_approved=employee_approved,
    )
    quote = Quote(
        user=user,
        user_email=email,
        quote_type="Hotshot",
        origin="30301",
        destination="90210",
        weight=100.0,
        weight_method="Actual",
        total=100.0,
        quote_metadata=json.dumps(metadata),
    )
    db.session.add(quote)
    db.session.commit()
    return email, quote.quote_id


def _extract_page_data(html: str) -> dict[str, Any]:
    """Return the JSON payload embedded in the email request template.

    Args:
        html: Rendered HTML output for the booking or volume request form.

    Returns:
        Parsed dictionary passed to the browser-side script powering the
        "Compose Email" interaction.
    """

    match = re.search(r"const data = (\{.*?\});", html, re.DOTALL)
    assert match, "Email request page should embed a data block for the form"
    return json.loads(match.group(1))


def test_email_request_requires_freight_domain(app, client):
    with app.app_context():
        email, quote_id = _create_user_and_quote(
            "customer@example.com", "SafePass!1234"
        )

    client.post(
        "/login",
        data={"email": email, "password": "SafePass!1234"},
        follow_redirects=True,
    )

    booking_response = client.get(f"/quotes/{quote_id}/email", follow_redirects=True)
    assert (
        "Email booking is restricted to Freight Services staff."
        in booking_response.get_data(as_text=True)
    )
    assert booking_response.request.path == "/quotes/new"

    volume_response = client.get(
        f"/quotes/{quote_id}/email-volume", follow_redirects=True
    )
    assert (
        "Email booking is restricted to Freight Services staff."
        in volume_response.get_data(as_text=True)
    )
    assert volume_response.request.path == "/quotes/new"


def test_email_request_allows_privileged_user(app, client):
    with app.app_context():
        email, quote_id = _create_user_and_quote(
            "agent@freightservices.net",
            "SafePass!1234",
            role="employee",
            employee_approved=True,
        )

    client.post(
        "/login",
        data={"email": email, "password": "SafePass!1234"},
        follow_redirects=True,
    )

    booking_response = client.get(f"/quotes/{quote_id}/email")
    assert booking_response.status_code == 200
    booking_html = booking_response.get_data(as_text=True)
    assert "Email Booking Request" in booking_html
    assert "includes $15.00 email admin fee" in booking_html
    assert "I'd like to go ahead and book the following quote" in booking_html
    booking_data = _extract_page_data(booking_html)
    assert booking_data["admin_fee"] == pytest.approx(15.0)
    assert booking_data["total_with_fee"] == pytest.approx(115.0)
    assert booking_data["subject_prefix"] == "New Booking request"

    volume_response = client.get(f"/quotes/{quote_id}/email-volume")
    assert volume_response.status_code == 200
    volume_html = volume_response.get_data(as_text=True)
    assert "Email Volume Pricing Request" in volume_html
    assert "includes $15.00 email admin fee" not in volume_html
    assert (
        "I'd like to move forward with volume pricing for the following quote"
        in volume_html
    )
    volume_data = _extract_page_data(volume_html)
    assert volume_data["admin_fee"] == pytest.approx(0.0)
    assert volume_data["total_with_fee"] == pytest.approx(100.0)
    assert volume_data["subject_prefix"] == "Volume pricing request"


def test_send_email_prefers_manual_mail_settings(app):
    with app.app_context():
        set_setting("mail_username", "manual@freightservices.net")
        set_setting("mail_password", "AppPass123!", is_secret=True)
        set_setting("mail_use_tls", "false")
        set_setting("mail_use_ssl", "false")
        db.session.commit()

        from app import send_email

        send_email("customer@example.com", "Subject", "Body")

        assert DummySMTP.login_calls == [("manual@freightservices.net", "AppPass123!")]
        assert len(DummySMTP.sent_messages) == 1


def test_super_admin_updates_mail_settings(app, client):
    with app.app_context():
        admin = _create_user(
            "admin@freightservices.net",
            "SafePass!1234",
            role="super_admin",
            employee_approved=True,
        )
        admin.is_admin = True
        db.session.commit()

    client.post(
        "/login",
        data={"email": "admin@freightservices.net", "password": "SafePass!1234"},
        follow_redirects=True,
    )

    response = client.get("/admin/settings")
    assert response.status_code == 200

    def _create_setting(key: str, value: str, *, secret: bool = False) -> None:
        payload = {"key": key, "value": value}
        if secret:
            payload["is_secret"] = "y"
        save_response = client.post(
            "/admin/settings/new",
            data=payload,
            follow_redirects=True,
        )
        assert save_response.status_code == 200
        body = save_response.get_data(as_text=True)
        assert "Saved setting" in body

    _create_setting("mail_server", "smtp.office365.com")
    _create_setting("mail_port", "587")
    _create_setting("mail_use_tls", "true")
    _create_setting("mail_use_ssl", "false")
    _create_setting("mail_username", "manual@freightservices.net")
    _create_setting("mail_password", "Secret123!", secret=True)

    with app.app_context():
        assert _get_setting_value("mail_server") == "smtp.office365.com"
        assert _get_setting_value("mail_port") == "587"
        assert _get_setting_value("mail_username") == "manual@freightservices.net"
        assert _get_setting_value("mail_use_tls") == "true"
        assert _get_setting_value("mail_use_ssl") == "false"
        password_row = AppSetting.query.filter_by(key="mail_password").one()
        password_id = password_row.id
        assert password_row.value == "Secret123!"
        assert password_row.is_secret is True

    clear_response = client.post(
        f"/admin/settings/{password_id}/edit",
        data={"key": "mail_password", "value": ""},
        follow_redirects=True,
    )
    assert clear_response.status_code == 200
    assert "Saved setting MAIL_PASSWORD" in clear_response.get_data(as_text=True)

    with app.app_context():
        assert _get_setting_value("mail_password") is None
