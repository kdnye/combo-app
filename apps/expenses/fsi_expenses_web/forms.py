"""Form parsing and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Mapping, Optional, Tuple

from werkzeug.datastructures import FileStorage


@dataclass(slots=True)
class ReportFormData:
    """Validated report metadata returned by :func:`parse_report_form`."""

    title: str
    traveler_name: str
    department: str
    trip_start: date
    trip_end: date
    purpose: str
    notes: str
    policy_acknowledged: bool


@dataclass(slots=True)
class ExpenseItemFormData:
    """Validated expense item form data."""

    expense_date: date
    category: str
    description: str
    merchant: str
    amount: Decimal
    currency: str
    reimbursable: bool
    receipt: Optional[FileStorage]


DATE_INPUT_FORMAT = "%Y-%m-%d"


def parse_report_form(
    form: Mapping[str, str]
) -> Tuple[Optional[ReportFormData], List[str]]:
    """Validate a report form submission.

    Returns a tuple of ``(result, errors)``. ``result`` is ``None`` when
    validation fails.
    """

    errors: List[str] = []
    try:
        trip_start = datetime.strptime(
            form.get("trip_start", ""), DATE_INPUT_FORMAT
        ).date()
    except ValueError:
        errors.append("Trip start date is required and must be YYYY-MM-DD.")
        trip_start = None  # type: ignore[assignment]
    try:
        trip_end = datetime.strptime(form.get("trip_end", ""), DATE_INPUT_FORMAT).date()
    except ValueError:
        errors.append("Trip end date is required and must be YYYY-MM-DD.")
        trip_end = None  # type: ignore[assignment]

    title = form.get("title", "").strip()
    traveler_name = form.get("traveler_name", "").strip()
    department = form.get("department", "").strip()
    purpose = form.get("purpose", "").strip()
    notes = form.get("notes", "").strip()
    policy_acknowledged = form.get("policy_acknowledged") == "on"

    if not title:
        errors.append("Report title is required.")
    if not traveler_name:
        errors.append("Traveler name is required.")
    if not department:
        errors.append("Department is required.")
    if trip_start and trip_end and trip_end < trip_start:
        errors.append("Trip end date must be on or after the start date.")

    if errors:
        return None, errors

    return (
        ReportFormData(
            title=title,
            traveler_name=traveler_name,
            department=department,
            trip_start=trip_start,
            trip_end=trip_end,
            purpose=purpose,
            notes=notes,
            policy_acknowledged=policy_acknowledged,
        ),
        [],
    )


def parse_expense_form(
    form: Mapping[str, str], receipt: Optional[FileStorage]
) -> Tuple[Optional[ExpenseItemFormData], List[str]]:
    """Validate an expense item submission."""

    errors: List[str] = []
    try:
        expense_date = datetime.strptime(
            form.get("expense_date", ""), DATE_INPUT_FORMAT
        ).date()
    except ValueError:
        errors.append("Expense date is required and must be YYYY-MM-DD.")
        expense_date = None  # type: ignore[assignment]

    category = form.get("category", "").strip()
    description = form.get("description", "").strip()
    merchant = form.get("merchant", "").strip()
    currency = form.get("currency", "USD").strip().upper()
    reimbursable = form.get("reimbursable") == "on"

    if not category:
        errors.append("Category is required.")
    if not description:
        errors.append("Description is required.")
    if not merchant:
        errors.append("Merchant is required.")

    amount_raw = form.get("amount", "").strip()
    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            errors.append("Amount must be greater than zero.")
    except (InvalidOperation, ValueError):
        errors.append("Amount must be a valid number.")
        amount = Decimal("0")

    if errors:
        return None, errors

    return (
        ExpenseItemFormData(
            expense_date=expense_date,
            category=category,
            description=description,
            merchant=merchant,
            amount=amount,
            currency=currency,
            reimbursable=reimbursable,
            receipt=receipt,
        ),
        [],
    )
