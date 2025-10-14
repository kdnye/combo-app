import re
import pytest
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
    return app.test_client()


def login(client):
    resp = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True)
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


def get_csrf(client, path):
    resp = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else ""


def test_admin_can_manage_users(client, app):
    login(client)
    token = get_csrf(client, "/admin/users/new")
    resp = client.post(
        "/admin/users/new",
        data={
            "email": "user@example.com",
            "first_name": "User",
            "last_name": "Example",
            "phone": "+1-555-123-4567",
            "company_name": "Example Co",
            "company_phone": "+1-555-765-4321",
            "password": "Pass123!",
            "role": "customer",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        user = User.query.filter_by(email="user@example.com").first()
        assert user is not None
        uid = user.id
        assert user.first_name == "User"
        assert user.last_name == "Example"
        assert user.phone == "+1-555-123-4567"
        assert user.company_name == "Example Co"
        assert user.company_phone == "+1-555-765-4321"

    token = get_csrf(client, f"/admin/users/{uid}/edit")
    resp = client.post(
        f"/admin/users/{uid}/edit",
        data={
            "email": "user2@example.com",
            "first_name": "User2",
            "last_name": "Example",
            "phone": "+1-555-123-4567",
            "company_name": "Example Co",
            "company_phone": "+1-555-765-4321",
            "role": "super_admin",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        user = db.session.get(User, uid)
        assert user.email == "user2@example.com"
        assert user.role == "super_admin"
        assert user.first_name == "User2"
        assert user.last_name == "Example"
        assert user.phone == "+1-555-123-4567"
        assert user.company_name == "Example Co"
        assert user.company_phone == "+1-555-765-4321"

    token = get_csrf(client, "/admin/")
    resp = client.post(
        f"/admin/users/{uid}/delete",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(User, uid) is None


def test_create_user_requires_csrf(client, app):
    login(client)
    resp = client.post(
        "/admin/users/new",
        data={"email": "fail@example.com", "name": "Fail", "password": "Pass123!"},
    )
    assert resp.status_code == 400


def test_admin_can_create_and_edit_employee_without_role_downgrade(client, app):
    login(client)
    token = get_csrf(client, "/admin/users/new")
    resp = client.post(
        "/admin/users/new",
        data={
            "email": "employee@example.com",
            "first_name": "Emp",
            "last_name": "Loyee",
            "password": "Pass123!",
            "role": "employee",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        employee = User.query.filter_by(email="employee@example.com").first()
        assert employee is not None
        assert employee.role == "employee"
        assert employee.employee_approved is False
        employee_id = employee.id

    token = get_csrf(client, f"/admin/users/{employee_id}/edit")
    resp = client.post(
        f"/admin/users/{employee_id}/edit",
        data={
            "email": "employee@example.com",
            "first_name": "Emp",
            "last_name": "Loyee",
            "role": "employee",
            "employee_approved": "on",
            "csrf_token": token,
        },
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        employee = db.session.get(User, employee_id)
        assert employee.role == "employee"
        assert employee.employee_approved is True
        assert employee.is_admin is False
