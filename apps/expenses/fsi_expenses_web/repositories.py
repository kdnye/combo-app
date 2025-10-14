"""Database access layer for the Expenses web app."""

from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import List

from sqlalchemy import delete, insert, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import NoResultFound

from packages.fsi_common import ExpenseItem, ExpenseReport

from .database import expense_items, expense_reports, session_scope


class ExpensesRepository:
    """Provides CRUD operations for expense reports and items."""

    def __init__(self, engine: Engine):
        self._engine = engine

    def create_report(self, report: ExpenseReport) -> ExpenseReport:
        """Persist a new expense report and return it with an ID."""

        payload = {
            "title": report.title,
            "traveler_name": report.traveler_name,
            "department": report.department,
            "trip_start": report.trip_start,
            "trip_end": report.trip_end,
            "purpose": report.purpose,
            "notes": report.notes,
            "policy_acknowledged": report.policy_acknowledged,
        }
        with session_scope(self._engine) as session:
            result = session.execute(
                insert(expense_reports)
                .values(**payload)
                .returning(expense_reports.c.id)
            )
            report_id = result.scalar_one()
        return replace(report, id=report_id)

    def update_report(
        self,
        report_id: int,
        *,
        title: str,
        traveler_name: str,
        department: str,
        trip_start: date,
        trip_end: date,
        purpose: str,
        notes: str,
        policy_acknowledged: bool,
    ) -> None:
        """Update editable report metadata."""

        with session_scope(self._engine) as session:
            session.execute(
                update(expense_reports)
                .where(expense_reports.c.id == report_id)
                .values(
                    title=title,
                    traveler_name=traveler_name,
                    department=department,
                    trip_start=trip_start,
                    trip_end=trip_end,
                    purpose=purpose,
                    notes=notes,
                    policy_acknowledged=policy_acknowledged,
                )
            )

    def add_item(self, item: ExpenseItem) -> ExpenseItem:
        """Insert a new expense item."""

        payload = {
            "report_id": item.report_id,
            "expense_date": item.expense_date,
            "category": item.category,
            "description": item.description,
            "merchant": item.merchant,
            "amount_cents": item.amount_in_minor_units(),
            "currency": item.currency,
            "reimbursable": item.reimbursable,
            "receipt_filename": item.receipt_filename,
        }
        with session_scope(self._engine) as session:
            result = session.execute(
                insert(expense_items).values(**payload).returning(expense_items.c.id)
            )
            item_id = result.scalar_one()
        return replace(item, id=item_id)

    def list_reports(self) -> List[ExpenseReport]:
        """Return all reports ordered by creation date."""

        with session_scope(self._engine) as session:
            rows = session.execute(
                select(expense_reports).order_by(expense_reports.c.created_at.desc())
            ).all()
        return [self._row_to_report(row) for row in rows]

    def get_report(self, report_id: int) -> ExpenseReport:
        """Fetch a single report including its items."""

        with session_scope(self._engine) as session:
            report_row = session.execute(
                select(expense_reports).where(expense_reports.c.id == report_id)
            ).one_or_none()
            if report_row is None:
                raise NoResultFound(f"Report {report_id} not found")
            item_rows = session.execute(
                select(expense_items)
                .where(expense_items.c.report_id == report_id)
                .order_by(expense_items.c.expense_date)
            ).all()
        report = self._row_to_report(report_row)
        report.expenses = [self._row_to_item(row) for row in item_rows]
        return report

    def delete_item(self, report_id: int, item_id: int) -> None:
        """Remove an expense item from a report."""

        with session_scope(self._engine) as session:
            session.execute(
                delete(expense_items).where(
                    expense_items.c.id == item_id,
                    expense_items.c.report_id == report_id,
                )
            )

    def delete_report(self, report_id: int) -> None:
        """Remove a report and all associated items."""

        with session_scope(self._engine) as session:
            session.execute(
                delete(expense_items).where(expense_items.c.report_id == report_id)
            )
            session.execute(
                delete(expense_reports).where(expense_reports.c.id == report_id)
            )

    def update_receipt(self, item_id: int, filename: str) -> None:
        """Attach a receipt file to an expense item."""

        with session_scope(self._engine) as session:
            session.execute(
                update(expense_items)
                .where(expense_items.c.id == item_id)
                .values(receipt_filename=filename)
            )

    @staticmethod
    def _row_to_report(row) -> ExpenseReport:
        """Convert a SQLAlchemy row to an :class:`ExpenseReport`."""

        values = row._mapping
        return ExpenseReport(
            id=values["id"],
            title=values["title"],
            traveler_name=values["traveler_name"],
            department=values["department"],
            trip_start=values["trip_start"],
            trip_end=values["trip_end"],
            purpose=values["purpose"],
            notes=values["notes"],
            policy_acknowledged=values["policy_acknowledged"],
            created_at=values["created_at"].date() if values["created_at"] else None,
        )

    @staticmethod
    def _row_to_item(row) -> ExpenseItem:
        """Convert a SQLAlchemy row to an :class:`ExpenseItem`."""

        values = row._mapping
        amount = Decimal(values["amount_cents"]) / Decimal(100)
        return ExpenseItem(
            id=values["id"],
            report_id=values["report_id"],
            expense_date=values["expense_date"],
            category=values["category"],
            description=values["description"],
            merchant=values["merchant"],
            amount=amount,
            currency=values["currency"],
            reimbursable=values["reimbursable"],
            receipt_filename=values["receipt_filename"],
        )
