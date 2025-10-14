"""Ensure admins can reach quote history from the dashboard and nav."""

from __future__ import annotations

import re

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.models import db, User
from quote.theme import init_fsi_theme


@pytest.fixture
def app():
    """Configure a Flask app backed by an in-memory database.

    Creates a single admin user for authentication in tests.
    """

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        init_fsi_theme(app)
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@example.com",
            role="super_admin",
        )
        admin.set_password("StrongPass!1234")
        db.session.add(admin)
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Provide a :class:`~flask.testing.FlaskClient` for requests."""

    return app.test_client()


def login(client: FlaskClient) -> None:
    """Authenticate as the admin user using CSRF token from the login page."""

    resp = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"',
        resp.get_data(as_text=True),
    ).group(1)
    client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_dashboard_links_quotes_and_page_accessible(client: FlaskClient) -> None:
    """Dashboard should link to quotes list and allow access for admins."""

    login(client)
    resp = client.get("/admin/")
    html = resp.get_data(as_text=True)
    assert "/admin/quotes" in html

    quotes_resp = client.get("/admin/quotes")
    assert quotes_resp.status_code == 200
