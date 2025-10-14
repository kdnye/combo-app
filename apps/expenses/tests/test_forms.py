"""Unit tests for form parsing helpers."""

from __future__ import annotations

from decimal import Decimal

from werkzeug.datastructures import MultiDict

from fsi_expenses_web.forms import parse_expense_form, parse_report_form


def test_parse_report_form_success():
    """Validate that a well-formed report submission passes."""

    form = MultiDict(
        {
            "title": "January Travel",
            "traveler_name": "Alex Rider",
            "department": "Operations",
            "trip_start": "2024-01-03",
            "trip_end": "2024-01-05",
            "purpose": "Client meetings",
            "notes": "Visited HQ",
            "policy_acknowledged": "on",
        }
    )
    result, errors = parse_report_form(form)
    assert not errors
    assert result is not None
    assert result.policy_acknowledged is True


def test_parse_report_form_errors():
    """Ensure missing report fields surface validation errors."""

    form = MultiDict({})
    result, errors = parse_report_form(form)
    assert result is None
    assert errors


def test_parse_expense_form_success():
    """Check that a complete expense passes validation."""

    form = MultiDict(
        {
            "expense_date": "2024-01-04",
            "category": "travel",
            "description": "Flight",
            "merchant": "Delta",
            "amount": "123.45",
            "currency": "USD",
            "reimbursable": "on",
        }
    )
    result, errors = parse_expense_form(form, None)
    assert not errors
    assert result is not None
    assert result.amount == Decimal("123.45")


def test_parse_expense_form_validation_errors():
    """Verify invalid amounts trigger an error."""

    form = MultiDict({"amount": "abc"})
    result, errors = parse_expense_form(form, None)
    assert result is None
    assert errors
