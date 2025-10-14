"""End-to-end tests for the Expenses HTTP routes."""

from __future__ import annotations

from io import BytesIO

from fsi_expenses_web.repositories import ExpensesRepository


def _create_report(client):
    """Submit a valid report creation request and return the response."""

    return client.post(
        "/reports",
        data={
            "title": "Conference",
            "traveler_name": "Sam",
            "department": "Logistics",
            "trip_start": "2024-03-01",
            "trip_end": "2024-03-05",
            "purpose": "Industry expo",
            "notes": "Bring marketing collateral",
            "policy_acknowledged": "on",
        },
        follow_redirects=False,
    )


def test_full_report_flow(client, app):
    """Ensure creating a report and adding an expense works end-to-end."""

    response = _create_report(client)
    assert response.status_code == 302
    location = response.headers["Location"]

    add_expense = client.post(
        f"{location}/expenses",
        data={
            "expense_date": "2024-03-02",
            "category": "travel",
            "description": "Flight",
            "merchant": "Delta",
            "amount": "320.10",
            "currency": "USD",
            "reimbursable": "on",
            "receipt": (BytesIO(b"pdf"), "receipt.pdf"),
        },
        content_type="multipart/form-data",
        follow_redirects=False,
    )
    assert add_expense.status_code == 302

    preview = client.get(f"{location}/preview")
    assert preview.status_code == 200
    assert b"Copy-ready preview" in preview.data

    json_resp = client.get(f"{location}.json")
    payload = json_resp.get_json()
    assert payload["title"] == "Conference"
    assert len(payload["expenses"]) == 1
    assert payload["expenses"][0]["receipt_filename"] is not None

    repo = ExpensesRepository(app.config["DB_ENGINE"])
    reports = repo.list_reports()
    assert len(reports) == 1
