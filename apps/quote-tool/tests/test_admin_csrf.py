import pytest
import re
from app import create_app
from app.models import db, User
from quote.theme import init_fsi_theme

@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        init_fsi_theme(app)
        db.create_all()
        admin_user = User(
            name="Admin",
            email="admin@example.com",
            role="super_admin",
        )
        admin_user.set_password("StrongPass!1234")
        target = User(name="Target", email="target@example.com", is_active=True)
        target.set_password("StrongPass!1234")
        db.session.add_all([admin_user, target])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login(client):
    resp = client.get("/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    token = match.group(1) if match else ""
    return client.post(
        "/login",
        data={"email": "admin@example.com", "password": "StrongPass!1234", "csrf_token": token},
        follow_redirects=False,
    )


def _get_csrf_token(client):
    resp = client.get("/admin/")
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else ""


def test_toggle_user_requires_csrf(client, app):
    login(client)
    with app.app_context():
        target_id = User.query.filter_by(email="target@example.com").first().id
    resp = client.post(f"/admin/toggle/{target_id}")
    assert resp.status_code == 400
    token = _get_csrf_token(client)
    resp = client.post(f"/admin/toggle/{target_id}", data={"csrf_token": token})
    assert resp.status_code == 302


def test_promote_user_requires_csrf(client, app):
    login(client)
    with app.app_context():
        target_id = User.query.filter_by(email="target@example.com").first().id
    resp = client.post(f"/admin/promote/{target_id}")
    assert resp.status_code == 400
    token = _get_csrf_token(client)
    resp = client.post(f"/admin/promote/{target_id}", data={"csrf_token": token})
    assert resp.status_code == 302
