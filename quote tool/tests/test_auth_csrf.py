import pytest
import re
from flask_app import create_app
from app.models import db, User


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def get_register_form_data(client):
    resp = client.get("/register")
    page = resp.get_data(as_text=True)
    token_match = re.search(r'name="csrf_token" value="([^"]+)"', page)
    challenge_match = re.search(r"Human Verification: What is (\d+) \+ (\d+)\?", page)
    token = token_match.group(1) if token_match else None
    if not challenge_match:
        raise AssertionError(
            "Registration form is missing the human verification prompt"
        )
    answer = str(int(challenge_match.group(1)) + int(challenge_match.group(2)))
    return token, answer


def test_register_csrf(app, client):
    # Without CSRF token the request should be rejected
    token, answer = get_register_form_data(client)
    resp = client.post(
        "/register",
        data={
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "phone": "+1-555-123-4567",
            "company_name": "Example Co",
            "company_phone": "+1-555-765-4321",
            "password": "StrongPass!1234",
            "confirm_password": "StrongPass!1234",
            "human_verification": answer,
        },
    )
    assert resp.status_code == 400

    token, answer = get_register_form_data(client)
    resp = client.post(
        "/register",
        data={
            "first_name": "New",
            "last_name": "User",
            "email": "new@example.com",
            "phone": "+1-555-123-4567",
            "company_name": "Example Co",
            "company_phone": "+1-555-765-4321",
            "password": "StrongPass!1234",
            "confirm_password": "StrongPass!1234",
            "csrf_token": token,
            "human_verification": answer,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.filter_by(email="new@example.com").count() == 1
