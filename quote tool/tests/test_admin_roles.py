import re

import pytest

from flask_app import create_app

from app.models import User, db


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@example.com",
            role="super_admin",
            is_admin=True,
            employee_approved=True,
        )
        admin.set_password("StrongPass!1234")
        employee = User(
            name="Employee",
            email="employee@example.com",
            role="employee",
            employee_approved=True,
        )
        employee.set_password("StrongPass!1234")
        db.session.add_all([admin, employee])
        db.session.commit()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def _login(client) -> None:
    login_page = client.get("/login")
    match = re.search(
        r'name="csrf_token" value="([^"]+)"', login_page.get_data(as_text=True)
    )
    token = match.group(1) if match else ""
    client.post(
        "/login",
        data={
            "email": "admin@example.com",
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def _csrf_token(client) -> str:
    resp = client.get("/admin/")
    match = re.search(r'name="csrf_token" value="([^"]+)"', resp.get_data(as_text=True))
    return match.group(1) if match else ""


def test_demote_restores_employee_role(client, app):
    _login(client)

    with app.app_context():
        employee = User.query.filter_by(email="employee@example.com").first()
        assert employee is not None
        employee_id = employee.id
        assert employee.role == "employee"
        assert employee.employee_approved is True
        assert employee.is_admin is False

    promote_token = _csrf_token(client)
    resp = client.post(
        f"/admin/promote/{employee_id}",
        data={"csrf_token": promote_token},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        employee = db.session.get(User, employee_id)
        assert employee is not None
        assert employee.is_admin is True
        assert employee.role == "super_admin"
        assert employee.admin_previous_role == "employee"
        assert employee.admin_previous_employee_approved is True

    demote_token = _csrf_token(client)
    resp = client.post(
        f"/admin/demote/{employee_id}",
        data={"csrf_token": demote_token},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    with app.app_context():
        employee = db.session.get(User, employee_id)
        assert employee is not None
        assert employee.is_admin is False
        assert employee.role == "employee"
        assert employee.employee_approved is True
        assert employee.admin_previous_role is None
        assert employee.admin_previous_employee_approved is None
