import hashlib
import re

import pytest
from flask import url_for

from app import create_app, limiter
from app.models import PasswordResetToken, User, db


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        limiter.reset()
        db.create_all()
        user = User(name="Reset", email="reset@example.com", is_active=True)
        user.set_password("OldPass!1234")
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        limiter.reset()


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client, path):
    resp = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    assert match, "CSRF token not found"
    return match.group(1)


def login_client(client, email="reset@example.com", password="OldPass!1234"):
    token = get_csrf_token(client, "/login")
    response = client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": token},
        follow_redirects=False,
    )
    assert response.status_code in {302, 303}


def test_login_page_offers_password_reset_link(client, app):
    resp = client.get("/login")
    html = resp.get_data(as_text=True)
    with app.test_request_context():
        reset_url = url_for("auth.reset_request")
    assert "Forgot your password?" in html
    assert reset_url in html


def test_password_reset_flow(client, app):
    login_client(client)
    token = get_csrf_token(client, "/reset")
    resp = client.post(
        "/reset",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    html = resp.get_data(as_text=True)
    assert "you're signed in as" in html.lower()
    assert "reset link ready" in html.lower()
    assert "copy the secure link below" in html.lower()
    link_match = re.search(r'href="([^"]+/reset/([^"]+))"', html)
    assert link_match is not None
    full_link, t = link_match.groups()
    assert full_link.endswith(f"/reset/{t}")
    token_match = re.search(r'id="reset-token"[^>]*value="([^"]+)"', html)
    if token_match is None:
        token_match = re.search(r'value="([^"]+)"[^>]*id="reset-token"', html)
    assert token_match is not None
    assert token_match.group(1) == t
    with app.app_context():
        reset = PasswordResetToken.query.first()
        assert reset is not None
        expected_digest = hashlib.sha256(t.encode("utf-8")).hexdigest()
        assert reset.token == expected_digest
        assert reset.token != t
    token2 = get_csrf_token(client, f"/reset/{t}")
    resp2 = client.post(
        f"/reset/{t}",
        data={
            "new_password": "NewStrongPass!1234",
            "confirm_password": "NewStrongPass!1234",
            "csrf_token": token2,
        },
        follow_redirects=True,
    )
    assert "password has been reset" in resp2.get_data(as_text=True).lower()
    with app.app_context():
        user = User.query.filter_by(email="reset@example.com").first()
        assert user.check_password("NewStrongPass!1234")
        hashed = hashlib.sha256(t.encode("utf-8")).hexdigest()
        assert PasswordResetToken.query.filter_by(token=hashed).first().used

    # Attempting to use the database value directly should fail because it is hashed.
    with app.app_context():
        hashed_token = PasswordResetToken.query.first().token
    resp3 = client.get(f"/reset/{hashed_token}", follow_redirects=True)
    assert "invalid or expired token" in resp3.get_data(as_text=True).lower()


def test_password_reset_rate_limit(client, app):
    login_client(client)
    token = get_csrf_token(client, "/reset")
    client.post(
        "/reset",
        data={"csrf_token": token},
        follow_redirects=True,
    )
    token2 = get_csrf_token(client, "/reset")
    resp2 = client.post(
        "/reset",
        data={"csrf_token": token2},
        follow_redirects=True,
    )
    assert "already requested" in resp2.get_data(as_text=True).lower()
    with app.app_context():
        assert PasswordResetToken.query.count() == 1


def test_invalid_token(client):
    resp = client.get("/reset/invalidtoken", follow_redirects=True)
    assert resp.status_code == 200
    assert "invalid or expired token" in resp.get_data(as_text=True).lower()


def test_reset_page_requires_authentication(client):
    resp = client.get("/reset")
    html = resp.get_data(as_text=True)
    assert "password resets can only be generated" in html.lower()
    assert "generate reset link" not in html.lower()
