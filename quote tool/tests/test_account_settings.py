import re
from typing import Iterator

import pytest
from flask import url_for
from flask.testing import FlaskClient

from app import create_app, limiter
from app.models import User, db


@pytest.fixture
def app():
    """Return a Flask app configured with an in-memory database for settings tests."""

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        limiter.reset()
        db.create_all()
        primary = User(
            email="user@example.com",
            first_name="Test",
            last_name="User",
            phone="555-0100",
            company_name="Acme Corp",
            company_phone="555-0200",
        )
        primary.set_password("StrongPass!1234")
        db.session.add(primary)
        secondary = User(
            email="taken@example.com",
            first_name="Other",
            last_name="Person",
            phone="555-0300",
            company_name="Example LLC",
            company_phone="555-0400",
        )
        secondary.set_password("StrongPass!1234")
        db.session.add(secondary)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        limiter.reset()


@pytest.fixture
def client(app) -> Iterator[FlaskClient]:
    """Provide a :class:`~flask.testing.FlaskClient` for account settings requests."""

    with app.test_client() as client:
        yield client


def _get_csrf_token(client: FlaskClient, path: str) -> str:
    """Fetch a CSRF token from ``path`` by parsing the rendered HTML form."""

    response = client.get(path)
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True)
    )
    assert match, "Expected CSRF token in response"
    return match.group(1)


def _login(client: FlaskClient) -> None:
    """Authenticate the seeded test user using the login form."""

    token = _get_csrf_token(client, "/login")
    response = client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def test_settings_requires_authentication(client: FlaskClient) -> None:
    """Unauthenticated visitors should be redirected to the login page."""

    response = client.get("/settings")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_settings_prefills_current_values(client: FlaskClient, app) -> None:
    """Authenticated users should see their existing profile information."""

    _login(client)
    response = client.get("/settings")
    html = response.get_data(as_text=True)
    assert "user@example.com" in html
    assert "Acme Corp" in html
    assert "Account settings" in html
    with app.test_request_context():
        assert url_for("auth.reset_request") in html


def test_settings_updates_profile_details(client: FlaskClient, app) -> None:
    """Posting new contact details should persist changes to the database."""

    _login(client)
    token = _get_csrf_token(client, "/settings")
    response = client.post(
        "/settings",
        data={
            "csrf_token": token,
            "first_name": "Updated",
            "last_name": "User",
            "email": "updated@example.com",
            "phone": "555-1111",
            "company_name": "New Corp",
            "company_phone": "555-2222",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "account settings updated" in response.get_data(as_text=True).lower()
    with app.app_context():
        user = User.query.filter_by(email="updated@example.com").first()
        assert user is not None
        assert user.first_name == "Updated"
        assert user.company_phone == "555-2222"


def test_settings_rejects_duplicate_email(client: FlaskClient) -> None:
    """Attempting to reuse another user's email should surface a warning."""

    _login(client)
    token = _get_csrf_token(client, "/settings")
    response = client.post(
        "/settings",
        data={
            "csrf_token": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "taken@example.com",
            "phone": "555-0100",
            "company_name": "Acme Corp",
            "company_phone": "555-0200",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "already uses that email" in response.get_data(as_text=True).lower()


def test_settings_updates_password_when_current_password_matches(
    client: FlaskClient, app
) -> None:
    """Providing the current password allows the user to select a new password."""

    _login(client)
    token = _get_csrf_token(client, "/settings")
    response = client.post(
        "/settings",
        data={
            "csrf_token": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "phone": "555-0100",
            "company_name": "Acme Corp",
            "company_phone": "555-0200",
            "current_password": "StrongPass!1234",
            "new_password": "EvenStronger!12345",
            "confirm_password": "EvenStronger!12345",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    html = response.get_data(as_text=True).lower()
    assert "password has been updated" in html
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None
        assert user.check_password("EvenStronger!12345")


def test_settings_rejects_incorrect_current_password(client: FlaskClient) -> None:
    """Submitting the wrong current password should not change credentials."""

    _login(client)
    token = _get_csrf_token(client, "/settings")
    response = client.post(
        "/settings",
        data={
            "csrf_token": token,
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "phone": "555-0100",
            "company_name": "Acme Corp",
            "company_phone": "555-0200",
            "current_password": "WrongPass!123",
            "new_password": "EvenStronger!12345",
            "confirm_password": "EvenStronger!12345",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "current password is incorrect" in response.get_data(as_text=True).lower()
