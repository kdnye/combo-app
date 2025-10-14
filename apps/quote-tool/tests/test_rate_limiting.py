"""Integration tests covering authentication rate limiting."""

from typing import Iterator

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app, limiter
from app.models import User, db
from config import Config


class RateLimitTestConfig(Config):
    """Minimal configuration enabling deterministic limiter behaviour."""

    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = "100 per minute"
    AUTH_LOGIN_RATE_LIMIT = "5 per minute"
    AUTH_REGISTER_RATE_LIMIT = "5 per minute"
    AUTH_RESET_RATE_LIMIT = "5 per minute"


@pytest.fixture
def app_with_user() -> Iterator[Flask]:
    """Yield a Flask app seeded with a single active user."""

    limiter.reset()
    app = create_app(RateLimitTestConfig)
    with app.app_context():
        user = User(name="Rate Limit", email="ratelimit@example.com", is_active=True)
        user.set_password("ValidPass!123")
        db.session.add(user)
        db.session.commit()
    yield app
    limiter.reset()
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app_with_user: Flask) -> Iterator[FlaskClient]:
    """Provide a test client with a deterministic remote address."""

    with app_with_user.test_client() as test_client:
        test_client.environ_base["REMOTE_ADDR"] = "203.0.113.10"
        yield test_client


def _registration_form(email: str, answer: str) -> dict:
    """Return a valid registration payload using ``email`` and ``answer``."""

    return {
        "first_name": "Rate",
        "last_name": "Limit",
        "email": email,
        "phone": "+1-555-0100",
        "company_name": "Limiter Inc.",
        "company_phone": "+1-555-0101",
        "password": "StrongPass!123",
        "confirm_password": "StrongPass!123",
        "human_verification": answer,
    }


def test_login_rate_limit_returns_429(client: FlaskClient) -> None:
    """Ensure repeated login attempts trigger a 429 Too Many Requests."""

    for _ in range(5):
        response = client.post(
            "/login",
            data={"email": "ratelimit@example.com", "password": "WrongPass!"},
            follow_redirects=False,
        )
        assert response.status_code != 429

    blocked = client.post(
        "/login",
        data={"email": "ratelimit@example.com", "password": "WrongPass!"},
        follow_redirects=False,
    )
    assert blocked.status_code == 429


def test_register_rate_limit_returns_429(client: FlaskClient) -> None:
    """Ensure repeated registration attempts are throttled after five posts."""

    email = "register-ratelimit@example.com"
    answer = "42"
    for _ in range(5):
        with client.session_transaction() as flask_session:
            flask_session["registration_challenge_answer"] = answer
        response = client.post(
            "/register",
            data=_registration_form(email, answer),
            follow_redirects=False,
        )
        assert response.status_code != 429

    with client.session_transaction() as flask_session:
        flask_session["registration_challenge_answer"] = answer
    blocked = client.post(
        "/register",
        data=_registration_form(email, answer),
        follow_redirects=False,
    )
    assert blocked.status_code == 429


def test_reset_rate_limit_returns_429(client: FlaskClient) -> None:
    """Verify password reset requests are throttled after multiple attempts."""

    login_response = client.post(
        "/login",
        data={"email": "ratelimit@example.com", "password": "ValidPass!123"},
        follow_redirects=False,
    )
    assert login_response.status_code in {302, 303}

    for _ in range(5):
        response = client.post(
            "/reset",
            data={},
            follow_redirects=False,
        )
        assert response.status_code != 429

    blocked = client.post(
        "/reset",
        data={},
        follow_redirects=False,
    )
    assert blocked.status_code == 429
