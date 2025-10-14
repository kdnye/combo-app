"""Repository integration tests."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from packages.fsi_common import ExpenseItem, ExpenseReport

from fsi_expenses_web.repositories import ExpensesRepository


def test_repository_crud(app):
    """Exercise CRUD paths on the repository abstraction."""

    repo = ExpensesRepository(app.config["DB_ENGINE"])
    report = ExpenseReport(
        id=None,
        title="Sample",
        traveler_name="Jamie",
        department="Logistics",
        trip_start=date(2024, 2, 1),
        trip_end=date(2024, 2, 3),
        purpose="Conference",
        notes="",
        policy_acknowledged=True,
    )
    saved = repo.create_report(report)
    assert saved.id is not None

    repo.update_report(
        saved.id,
        title="Updated",
        traveler_name="Jamie",
        department="Logistics",
        trip_start=date(2024, 2, 1),
        trip_end=date(2024, 2, 3),
        purpose="Conference",
        notes="Updated",
        policy_acknowledged=True,
    )

    fetched = repo.get_report(saved.id)
    assert fetched.title == "Updated"

    item = ExpenseItem(
        id=None,
        report_id=saved.id,
        expense_date=date(2024, 2, 1),
        category="travel",
        description="Flight",
        merchant="Delta",
        amount=Decimal("120.50"),
        currency="USD",
        reimbursable=True,
    )
    saved_item = repo.add_item(item)
    repo.update_receipt(saved_item.id, "report_1/receipt.pdf")

    fetched = repo.get_report(saved.id)
    assert len(fetched.expenses) == 1
    assert fetched.expenses[0].receipt_filename == "report_1/receipt.pdf"

    repo.delete_item(saved.id, fetched.expenses[0].id)
    repo.delete_report(saved.id)

    assert repo.list_reports() == []
