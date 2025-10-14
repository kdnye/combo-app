import re
import pytest
from app import create_app
from app.models import User, db
from config import Config
from quote.theme import init_fsi_theme


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        init_fsi_theme(app)
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@example.com",
            role="super_admin",
        )
        admin.set_password("StrongPass!1234")
        user = User(name="User", email="user@example.com", role="customer")
        user.set_password("StrongPass!1234")
        db.session.add_all([admin, user])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login(client, email: str) -> None:
    resp = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True)
    ).group(1)
    client.post(
        "/login",
        data={"email": email, "password": "StrongPass!1234", "csrf_token": token},
        follow_redirects=False,
    )


def test_non_admin_cannot_access_rate_views(client) -> None:
    login(client, "user@example.com")
    resp = client.get("/admin/hotshot_rates/new")
    assert resp.status_code == 403
    resp = client.get("/admin/accessorials/new")
    assert resp.status_code == 403
