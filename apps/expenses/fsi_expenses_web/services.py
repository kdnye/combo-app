"""Business logic helpers for the Expenses UI."""

from __future__ import annotations

from typing import Iterable, List

from .shared_models import (
    ExpenseCategory,
    ExpenseReport,
    ReportSummary,
    summarize_report,
)

DEFAULT_CATEGORIES: List[ExpenseCategory] = [
    ExpenseCategory(
        code="travel",
        label="Travel",
        description="Flights, rail, rideshare, and taxis.",
    ),
    ExpenseCategory(
        code="lodging", label="Lodging", description="Hotels and overnight stays."
    ),
    ExpenseCategory(
        code="meals", label="Meals", description="Meals during business travel."
    ),
    ExpenseCategory(
        code="mileage", label="Mileage", description="Personal vehicle mileage."
    ),
    ExpenseCategory(
        code="supplies", label="Supplies", description="Office or field supplies."
    ),
    ExpenseCategory(
        code="training",
        label="Training",
        description="Registration fees and materials.",
    ),
]


def build_preview(report: ExpenseReport) -> str:
    """Render a copy-ready preview for an expense report."""

    summary: ReportSummary = summarize_report(report)
    lines = [
        f"Expense Report: {report.title}",
        f"Traveler: {report.traveler_name} ({report.department})",
        f"Travel Dates: {report.trip_start:%Y-%m-%d} to {report.trip_end:%Y-%m-%d}",
        f"Purpose: {report.purpose or 'N/A'}",
        "",
        "Line Items:",
    ]
    if not report.expenses:
        lines.append("  - No expenses recorded yet.")
    else:
        for item in report.expenses:
            receipt = (
                f" (receipt: {item.receipt_filename})" if item.receipt_filename else ""
            )
            reimbursable = "Reimbursable" if item.reimbursable else "Non-reimbursable"
            lines.append(
                "  - "
                f"{item.expense_date:%Y-%m-%d} | {item.category} | {item.description} | {item.merchant} | "
                f"${item.amount:.2f} {item.currency} | {reimbursable}{receipt}"
            )
    lines.extend(
        [
            "",
            "Totals:",
            f"  - Reimbursable: ${summary.reimbursable_total:.2f}",
            f"  - Non-reimbursable: ${summary.non_reimbursable_total:.2f}",
        ]
    )
    if summary.category_totals:
        lines.append("  - By category:")
        for category, total in summary.category_totals.items():
            lines.append(f"      * {category}: ${total:.2f}")
    if report.notes:
        lines.extend(["", f"Notes: {report.notes}"])
    return "\n".join(lines)


def categories_for_select() -> Iterable[ExpenseCategory]:
    """Return categories presented in the new expense form."""

    return DEFAULT_CATEGORIES
