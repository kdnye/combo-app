"""Tests for the CSV based user seeding utility."""

from __future__ import annotations

from pathlib import Path

from werkzeug.security import generate_password_hash

from app import create_app
from app.models import User
from config import Config
from scripts.seed_users import seed_users_from_csv


def _build_app(db_path: Path):
    """Return a Flask app configured to store data in ``db_path``."""

    class TestConfig(Config):
        SQLALCHEMY_DATABASE_URI = f"sqlite:///{db_path}"
        TESTING = True
        WTF_CSRF_ENABLED = False

    return create_app(TestConfig)


def _write_csv(path: Path, rows: list[str]) -> None:
    """Persist ``rows`` to ``path`` as a CSV file."""

    content = "\n".join(rows) + "\n"
    path.write_text(content, encoding="utf-8")


def test_seed_users_inserts_accounts(tmp_path: Path) -> None:
    """Seed two accounts and verify roles, passwords, and approvals."""

    csv_path = tmp_path / "users.csv"
    _write_csv(
        csv_path,
        [
            "email,name,first_name,last_name,phone,company_name,company_phone,password,role,is_admin,employee_approved,is_active",
            "admin@example.com,Admin User,Admin,User,555-555-0100,Freight Services,555-555-0150,Adm1n!Example2024,super_admin,TRUE,TRUE,TRUE",
            "employee@example.com,Alex Employee,Alex,Employee,555-555-0110,Freight Services,555-555-0160,EmployeE!234567,employee,FALSE,FALSE,TRUE",
        ],
    )

    app = _build_app(tmp_path / "seed.db")
    result = seed_users_from_csv(csv_path, app=app)

    assert result.created == 2
    assert result.updated == 0
    assert result.skipped == 0
    assert result.errors == []

    with app.app_context():
        users = {user.email: user for user in User.query.all()}
        admin = users["admin@example.com"]
        assert admin.role == "super_admin"
        assert admin.is_admin is True
        assert admin.employee_approved is True
        assert admin.check_password("Adm1n!Example2024")

        employee = users["employee@example.com"]
        assert employee.role == "employee"
        assert employee.employee_approved is False
        assert employee.check_password("EmployeE!234567")


def test_seed_users_updates_existing_when_requested(tmp_path: Path) -> None:
    """Existing users are updated when ``update_existing`` is enabled."""

    initial_csv = tmp_path / "initial.csv"
    _write_csv(
        initial_csv,
        [
            "email,name,first_name,last_name,phone,company_name,company_phone,password,role,is_admin,employee_approved,is_active",
            "admin@example.com,Admin User,Admin,User,555-555-0100,Freight Services,555-555-0150,Adm1n!Example2024,super_admin,TRUE,TRUE,TRUE",
        ],
    )

    update_hash = generate_password_hash("N3wAdm1n!Passw0rd")
    updated_csv = tmp_path / "updated.csv"
    _write_csv(
        updated_csv,
        [
            "email,name,first_name,last_name,phone,company_name,company_phone,password,role,is_admin,employee_approved,is_active",
            f"admin@example.com,Updated Admin,Admin,User,555-555-0199,Freight Services Updated,555-555-0250,{update_hash},super_admin,TRUE,TRUE,TRUE",
        ],
    )

    app = _build_app(tmp_path / "update.db")

    first = seed_users_from_csv(initial_csv, app=app)
    assert first.created == 1

    second = seed_users_from_csv(updated_csv, app=app, update_existing=False)
    assert second.created == 0
    assert second.updated == 0
    assert second.skipped == 1

    third = seed_users_from_csv(updated_csv, app=app, update_existing=True)
    assert third.created == 0
    assert third.updated == 1
    assert third.skipped == 0

    with app.app_context():
        admin = User.query.filter_by(email="admin@example.com").one()
        assert admin.name == "Updated Admin"
        assert admin.company_name == "Freight Services Updated"
        assert admin.password_hash == update_hash


def test_seed_users_dry_run(tmp_path: Path) -> None:
    """Dry-run mode reports changes but leaves the database untouched."""

    csv_path = tmp_path / "dry.csv"
    _write_csv(
        csv_path,
        [
            "email,name,first_name,last_name,phone,company_name,company_phone,password,role,is_admin,employee_approved,is_active",
            "user@example.com,User Example,User,Example,555-555-0123,Example Co,555-555-0456,SolidPass!456789,customer,FALSE,FALSE,TRUE",
        ],
    )

    app = _build_app(tmp_path / "dry.db")
    result = seed_users_from_csv(csv_path, app=app, dry_run=True)

    assert result.created == 1
    assert result.updated == 0
    assert result.skipped == 0

    with app.app_context():
        assert User.query.count() == 0
