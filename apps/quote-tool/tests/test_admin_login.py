import re
import pytest
from flask_app import create_app
from app.models import db, User


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        user = User(name="User", email="user@example.com")
        user.set_password("StrongPass!1234")
        db.session.add(user)
        db.session.commit()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def get_csrf_token(client, path="/login"):
    resp = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else None


def test_admin_routes_require_login(client):
    token = get_csrf_token(client)

    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

    resp_toggle = client.post(
        "/admin/toggle/1", data={"csrf_token": token}, follow_redirects=False
    )
    assert resp_toggle.status_code == 302
    assert "/login" in resp_toggle.headers["Location"]

    resp_promote = client.post(
        "/admin/promote/1", data={"csrf_token": token}, follow_redirects=False
    )
    assert resp_promote.status_code == 302
    assert "/login" in resp_promote.headers["Location"]


def login(client) -> None:
    token = get_csrf_token(client)
    client.post(
        "/login",
        data={
            "email": "user@example.com",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_non_admin_forbidden(client):
    login(client)
    resp = client.get("/admin/", follow_redirects=False)
    assert resp.status_code == 403
