"""Tests for authentication service helpers."""

from __future__ import annotations

import logging
from typing import Iterator

import pytest
from flask import Flask

from config import Config
from app.models import db, User
from services import auth_utils


@pytest.fixture()
def app_ctx() -> Iterator[None]:
    """Provide a Flask app context bound to the test database.

    This binds the global SQLAlchemy ``db`` object to the SQLite database
    configured for tests, allowing ``db.session`` and model queries to work
    without mocking.
    """
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    with app.app_context():
        db.create_all()
        yield


@pytest.fixture(autouse=True)
def clear_users(app_ctx: None) -> Iterator[None]:
    """Ensure the users table is empty before and after each test."""
    db.session.query(User).delete()
    db.session.commit()
    yield
    db.session.query(User).delete()
    db.session.commit()


def test_authenticate_valid(app_ctx: None) -> None:
    """authenticate returns a user when given valid credentials."""
    user = User(email="tester@example.com", name="Tester", is_active=True)
    user.set_password("StrongPass!1234")
    db.session.add(user)
    db.session.commit()

    found, error = auth_utils.authenticate("tester@example.com", "StrongPass!1234")
    assert error is None
    assert found is not None
    assert found.email == "tester@example.com"


def test_authenticate_invalid_email(app_ctx: None) -> None:
    """authenticate rejects syntactically invalid email addresses."""
    user, error = auth_utils.authenticate("bad-email", "password")
    assert user is None
    assert error == "Invalid email address"


def test_authenticate_wrong_password(app_ctx: None) -> None:
    """authenticate reports an error when the password is incorrect."""
    user = User(email="tester@example.com", name="Tester", is_active=True)
    user.set_password("StrongPass!1234")
    db.session.add(user)
    db.session.commit()

    found, error = auth_utils.authenticate("tester@example.com", "WrongPass!1234")
    assert found is None
    assert error == "Invalid credentials"


def test_authenticate_inactive_user(app_ctx: None) -> None:
    """authenticate prevents login for inactive accounts."""
    user = User(email="inactive@example.com", name="Inactive", is_active=False)
    user.set_password("StrongPass!1234")
    db.session.add(user)
    db.session.commit()

    found, error = auth_utils.authenticate("inactive@example.com", "StrongPass!1234")
    assert found is None
    assert error == "Account inactive"


def test_register_user_success(app_ctx: None) -> None:
    """register_user creates a new inactive account when data is valid."""
    data = {
        "first_name": "New",
        "last_name": "User",
        "phone": "+1-555-123-4567",
        "company_name": "Example Co",
        "company_phone": "+1-555-765-4321",
        "email": "new@example.com",
        "password": "StrongPass!1234",
    }
    created_user, error = auth_utils.register_user(data)
    assert error is None
    assert created_user is not None
    created = db.session.query(User).filter_by(email="new@example.com").one()
    assert created_user.id == created.id
    assert created.is_active is False
    assert created.first_name == "New"
    assert created.last_name == "User"
    assert created.phone == "+1-555-123-4567"
    assert created.company_name == "Example Co"
    assert created.company_phone == "+1-555-765-4321"
    assert created.role == "customer"
    assert created.employee_approved is False


def test_register_user_requires_contact_fields(app_ctx: None) -> None:
    """register_user validates the presence of contact information."""
    base = {
        "first_name": "New",
        "last_name": "User",
        "phone": "+1-555-123-4567",
        "company_name": "Example Co",
        "company_phone": "+1-555-765-4321",
        "email": "contact@example.com",
        "password": "StrongPass!1234",
    }

    missing_first = base.copy()
    missing_first["first_name"] = ""
    user, error = auth_utils.register_user(missing_first)
    assert user is None
    assert error == "First name is required."

    missing_company_phone = base.copy()
    missing_company_phone["company_phone"] = ""
    user, error = auth_utils.register_user(missing_company_phone)
    assert user is None
    assert error == "Company phone number is required."


def test_register_user_rejects_bad_phone(app_ctx: None) -> None:
    """register_user rejects phone numbers that fail validation."""
    data = {
        "first_name": "New",
        "last_name": "User",
        "phone": "invalid",
        "company_name": "Example Co",
        "company_phone": "+1-555-765-4321",
        "email": "phone@example.com",
        "password": "StrongPass!1234",
    }
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Enter a valid phone number."

    data["phone"] = "+1-555-123-4567"
    data["company_phone"] = "invalid"
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Enter a valid company phone number."


def test_register_user_duplicate_email(app_ctx: None) -> None:
    """register_user fails when the email already exists."""
    user = User(email="dup@example.com", name="Dup", is_active=True)
    user.set_password("StrongPass!1234")
    db.session.add(user)
    db.session.commit()

    data = {
        "first_name": "Dup",
        "last_name": "User",
        "phone": "+1-555-123-0000",
        "company_name": "Example Co",
        "company_phone": "+1-555-765-0000",
        "email": "dup@example.com",
        "password": "StrongPass!1234",
    }
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Email already registered."


def test_register_user_invalid_email(app_ctx: None) -> None:
    """register_user validates email format before proceeding."""
    data = {
        "first_name": "Bad",
        "last_name": "Email",
        "phone": "+1-555-999-9999",
        "company_name": "Example Co",
        "company_phone": "+1-555-888-8888",
        "email": "not-an-email",
        "password": "StrongPass!1234",
    }
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Invalid email address."


def test_register_user_weak_password(app_ctx: None) -> None:
    """register_user enforces password complexity rules."""
    data = {
        "first_name": "Weak",
        "last_name": "Pass",
        "phone": "+1-555-444-4444",
        "company_name": "Example Co",
        "company_phone": "+1-555-333-3333",
        "email": "weak@example.com",
        "password": "weak",
    }
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Password does not meet complexity requirements."


def test_register_user_rejects_invalid_role(app_ctx: None) -> None:
    """register_user prevents unsupported role assignments."""
    data = {
        "first_name": "Role",
        "last_name": "Tester",
        "phone": "+1-555-777-7777",
        "company_name": "Example Co",
        "company_phone": "+1-555-222-2222",
        "email": "role@example.com",
        "password": "StrongPass!1234",
        "role": "manager",
    }
    user, error = auth_utils.register_user(data)
    assert user is None
    assert error == "Invalid role."


def test_register_user_employee_flags(app_ctx: None) -> None:
    """register_user normalizes employee approval flags for each role."""
    employee_data = {
        "first_name": "Emp",
        "last_name": "Loyee",
        "phone": "+1-555-111-1111",
        "company_name": "Example Co",
        "company_phone": "+1-555-666-6666",
        "email": "employee@example.com",
        "password": "StrongPass!1234",
        "role": "employee",
        "employee_approved": "true",
    }
    employee, error = auth_utils.register_user(employee_data, auto_approve=True)
    assert error is None
    assert employee is not None
    assert employee.role == "employee"
    assert employee.employee_approved is True

    customer_data = employee_data.copy()
    customer_data.update(
        {
            "email": "customer@example.com",
            "role": "customer",
            "employee_approved": "true",
        }
    )
    customer, error = auth_utils.register_user(customer_data)
    assert error is None
    assert customer is not None
    assert customer.role == "customer"
    assert customer.employee_approved is False

    admin_data = employee_data.copy()
    admin_data.update(
        {
            "email": "admin@example.com",
            "role": "super_admin",
            "employee_approved": False,
        }
    )
    admin, error = auth_utils.register_user(admin_data, auto_approve=True)
    assert error is None
    assert admin is not None
    assert admin.role == "super_admin"
    assert admin.employee_approved is True


def test_register_user_freight_employee_flagged(
    app_ctx: None, caplog: pytest.LogCaptureFixture
) -> None:
    """register_user auto-assigns Freight Services emails to employee review."""

    data = {
        "first_name": "Fran",
        "last_name": "Freight",
        "phone": "+1-555-212-3434",
        "company_name": "Freight Services",
        "company_phone": "+1-555-121-5656",
        "email": "pending@freightservices.net",
        "password": "StrongPass!1234",
        "role": "customer",
        "employee_approved": True,
    }

    with caplog.at_level(logging.INFO):
        pending, error = auth_utils.register_user(data, auto_approve=True)

    assert error is None
    assert pending is not None
    assert pending.role == "employee"
    assert pending.employee_approved is False
    assert any(
        "pending@freightservices.net" in message
        and "requires approval" in message.lower()
        for message in caplog.messages
    )
