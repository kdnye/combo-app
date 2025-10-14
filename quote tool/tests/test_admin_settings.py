import pytest

from app import create_app
from app.models import AppSetting, User, db


@pytest.fixture
def app(monkeypatch):
    app = create_app()
    app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
    )
    monkeypatch.setattr("app.admin.csrf.protect", lambda: None)
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
    role: str = "customer",
    employee_approved: bool = False,
) -> User:
    user = User(
        email=email,
        name="Test User",
        role=role,
        is_active=True,
        employee_approved=employee_approved,
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    return user


def test_employee_cannot_access_settings(app, client):
    with app.app_context():
        _create_user(
            "employee@example.com",
            "SecurePass!123",
            role="employee",
            employee_approved=True,
        )

    client.post(
        "/login",
        data={"email": "employee@example.com", "password": "SecurePass!123"},
        follow_redirects=True,
    )

    response = client.get("/admin/settings")
    assert response.status_code == 403


def test_settings_crud_updates_configuration(app, client):
    with app.app_context():
        admin = _create_user(
            "admin@example.com",
            "SecurePass!123",
            role="super_admin",
            employee_approved=True,
        )
        admin.is_admin = True
        db.session.commit()

    client.post(
        "/login",
        data={"email": "admin@example.com", "password": "SecurePass!123"},
        follow_redirects=True,
    )

    create_response = client.post(
        "/admin/settings/new",
        data={"key": "AUTH_LOGIN_RATE_LIMIT", "value": "2 per minute"},
        follow_redirects=True,
    )
    assert create_response.status_code == 200
    assert "Saved setting AUTH_LOGIN_RATE_LIMIT" in create_response.get_data(
        as_text=True
    )

    with app.app_context():
        setting = AppSetting.query.filter_by(key="auth_login_rate_limit").one()
        assert app.config["AUTH_LOGIN_RATE_LIMIT"] == "2 per minute"
        setting_id = setting.id

    update_response = client.post(
        f"/admin/settings/{setting_id}/edit",
        data={"key": "AUTH_LOGIN_RATE_LIMIT", "value": "3 per minute"},
        follow_redirects=True,
    )
    assert update_response.status_code == 200
    assert "Saved setting AUTH_LOGIN_RATE_LIMIT" in update_response.get_data(
        as_text=True
    )

    with app.app_context():
        assert app.config["AUTH_LOGIN_RATE_LIMIT"] == "3 per minute"

    delete_response = client.post(
        f"/admin/settings/{setting_id}/delete",
        follow_redirects=True,
    )
    assert delete_response.status_code == 200
    assert "Deleted setting AUTH_LOGIN_RATE_LIMIT" in delete_response.get_data(
        as_text=True
    )

    with app.app_context():
        assert (
            AppSetting.query.filter_by(key="auth_login_rate_limit").one_or_none()
            is None
        )
        assert app.config["AUTH_LOGIN_RATE_LIMIT"] == "5 per minute"
