import json
import re
import pytest

from app import create_app
from app.models import db, User, Quote


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@freightservices.net",
            role="super_admin",
        )
        admin.set_password("StrongPass!1234")
        quote = Quote(
            quote_type="Hotshot",
            origin="12345",
            destination="67890",
            total=100.0,
            quote_metadata=json.dumps({"accessorial_total": 0, "accessorials": {}}),
            user=admin,
        )
        db.session.add_all([admin, quote])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client):
    resp = client.get("/login")
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    token = match.group(1) if match else ""
    return client.post(
        "/login",
        data={
            "email": "admin@freightservices.net",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def test_admin_quote_email_route(client, app):
    _login(client)
    with app.app_context():
        quote_id = Quote.query.first().quote_id
    resp = client.get(f"/admin/quotes/{quote_id}/email")
    assert resp.status_code == 200
    assert quote_id in resp.get_data(as_text=True)
