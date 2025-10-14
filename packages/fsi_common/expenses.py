"""Expense reporting domain models and helper functions.

These dataclasses provide a shared representation of expense reports and
individual expense items. They intentionally avoid persistence concerns
so the models can be used from multiple applications (for example the
Flask UI or background processors).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Dict, Iterable, List, Optional


@dataclass(slots=True)
class ExpenseCategory:
    """Represents a reportable expense category."""

    code: str
    label: str
    description: str = ""


@dataclass(slots=True)
class ExpenseItem:
    """Single expense line item captured on a report."""

    report_id: int
    expense_date: date
    category: str
    description: str
    merchant: str
    amount: Decimal
    currency: str = "USD"
    reimbursable: bool = True
    receipt_filename: Optional[str] = None
    id: Optional[int] = None

    def amount_in_minor_units(self) -> int:
        """Return the amount expressed in the currency's minor units.

        The Expenses app stores monetary values in cents to avoid
        floating point rounding issues. For example, ``Decimal('12.34')``
        becomes ``1234`` when expressed in minor units.
        """

        return int((self.amount * 100).to_integral_value())


@dataclass(slots=True)
class ExpenseReport:
    """Container aggregating metadata and expense line items."""

    title: str
    traveler_name: str
    department: str
    trip_start: date
    trip_end: date
    purpose: str
    policy_acknowledged: bool
    id: Optional[int] = None
    notes: str = ""
    created_at: Optional[date] = None
    expenses: List[ExpenseItem] = field(default_factory=list)

    def reimbursable_total(self) -> Decimal:
        """Compute the reimbursable total for the report."""

        return sum(
            (item.amount for item in self.expenses if item.reimbursable), Decimal()
        )

    def non_reimbursable_total(self) -> Decimal:
        """Compute the non-reimbursable total for the report."""

        return sum(
            (item.amount for item in self.expenses if not item.reimbursable), Decimal()
        )


@dataclass(slots=True)
class ReportSummary:
    """Aggregate totals returned by :func:`summarize_report`."""

    reimbursable_total: Decimal
    non_reimbursable_total: Decimal
    category_totals: Dict[str, Decimal]


def group_expenses_by_category(expenses: Iterable[ExpenseItem]) -> Dict[str, Decimal]:
    """Return total spend per category for the provided expenses."""

    totals: Dict[str, Decimal] = {}
    for item in expenses:
        totals.setdefault(item.category, Decimal())
        totals[item.category] += item.amount
    return totals


def summarize_report(report: ExpenseReport) -> ReportSummary:
    """Build a :class:`ReportSummary` from an :class:`ExpenseReport`."""

    category_totals = group_expenses_by_category(report.expenses)
    return ReportSummary(
        reimbursable_total=report.reimbursable_total(),
        non_reimbursable_total=report.non_reimbursable_total(),
        category_totals=category_totals,
    )
