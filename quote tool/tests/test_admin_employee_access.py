import csv
import re
from io import StringIO

import pytest
from flask.testing import FlaskClient

from app import create_app
from app.models import Quote, User, db
from quote.theme import init_fsi_theme


@pytest.fixture
def app():
    """Set up an application with admin and employee accounts."""

    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        init_fsi_theme(app)
        db.create_all()
        admin = User(
            name="Admin",
            email="admin@freightservices.net",
            role="super_admin",
            employee_approved=True,
        )
        admin.set_password("StrongPass!1234")
        employee = User(
            name="Employee",
            email="employee@freightservices.net",
            role="employee",
            employee_approved=False,
        )
        employee.set_password("StrongPass!1234")
        quote = Quote(
            quote_type="Hotshot",
            origin="12345",
            destination="67890",
            total=100.0,
            user=admin,
        )
        db.session.add_all([admin, employee, quote])
        db.session.commit()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app) -> FlaskClient:
    """Provide a Flask test client bound to the in-memory app."""

    return app.test_client()


def _login(client: FlaskClient, email: str) -> None:
    """Authenticate ``email`` using the default strong password."""

    resp = client.get("/login")
    token = re.search(
        r'name="csrf_token" value="([^"]+)"',
        resp.get_data(as_text=True),
    ).group(1)
    client.post(
        "/login",
        data={
            "email": email,
            "password": "StrongPass!1234",
            "csrf_token": token,
        },
        follow_redirects=False,
    )


def _logout(client: FlaskClient) -> None:
    """End the authenticated session if one exists."""

    client.get("/logout", follow_redirects=False)


def _get_csrf(client: FlaskClient, path: str) -> str:
    """Return the CSRF token embedded in ``path``."""

    resp = client.get(path)
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        resp.get_data(as_text=True),
    )
    return match.group(1) if match else ""


def test_unapproved_employee_blocked(client: FlaskClient) -> None:
    """Unapproved employees receive 403s for admin pages."""

    _login(client, "employee@freightservices.net")
    resp = client.get("/admin/")
    assert resp.status_code == 403
    resp = client.get("/admin/quotes")
    assert resp.status_code == 403


def test_super_admin_can_approve_employee(client: FlaskClient, app) -> None:
    """Super admins can flip ``employee_approved`` via the new route."""

    _login(client, "admin@freightservices.net")
    token = _get_csrf(client, "/admin/")
    with app.app_context():
        employee = User.query.filter_by(email="employee@freightservices.net").one()
    resp = client.post(
        f"/admin/approve_employee/{employee.id}",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    with app.app_context():
        refreshed = db.session.get(User, employee.id)
        assert refreshed.employee_approved is True


def test_approved_employee_limited_access(client: FlaskClient, app) -> None:
    """Approved employees see the limited dashboard and quote listings."""

    _login(client, "admin@freightservices.net")
    token = _get_csrf(client, "/admin/")
    with app.app_context():
        employee = User.query.filter_by(email="employee@freightservices.net").one()
        quote = Quote.query.first()
    client.post(
        f"/admin/approve_employee/{employee.id}",
        data={"csrf_token": token},
        follow_redirects=False,
    )
    _logout(client)

    _login(client, "employee@freightservices.net")
    resp = client.get("/admin/")
    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "Team Quote Access" in html
    assert "/admin/quotes" in html

    resp = client.get("/admin/quotes")
    assert resp.status_code == 200
    resp = client.get("/admin/quotes.csv")
    assert resp.status_code == 200
    resp = client.get("/admin/hotshot_rates")
    assert resp.status_code == 403
    resp = client.get(f"/admin/quotes/{quote.quote_id}/email")
    assert resp.status_code == 403


def test_quotes_csv_escapes_formula_prefixes(client: FlaskClient, app) -> None:
    """Quote exports escape values that could trigger CSV formulas."""

    _login(client, "admin@freightservices.net")
    evil_email = "=cmd@example.com"
    evil_type = "@Hotshot"
    evil_origin = "=1+1"
    evil_destination = "+SUM(A1:A2)"
    evil_method = "-weight"
    evil_zone = "@Z1"
    evil_metadata = "=json"
    with app.app_context():
        quote = Quote.query.first()
        quote.user_email = evil_email
        quote.quote_type = evil_type
        quote.origin = evil_origin
        quote.destination = evil_destination
        quote.weight_method = evil_method
        quote.zone = evil_zone
        quote.quote_metadata = evil_metadata
        db.session.commit()

    resp = client.get("/admin/quotes.csv")
    assert resp.status_code == 200
    rows = list(csv.reader(StringIO(resp.get_data(as_text=True))))
    assert rows[1][2] == f"'{evil_email}"
    assert rows[1][3] == f"'{evil_type}"
    assert rows[1][4] == f"'{evil_origin}"
    assert rows[1][5] == f"'{evil_destination}"
    assert rows[1][7] == f"'{evil_method}"
    assert rows[1][8] == f"'{evil_zone}"
    assert rows[1][10] == f"'{evil_metadata}"
