"""HTTP routes for managing expense reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from flask import (
    Blueprint,
    Response,
    abort,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from sqlalchemy.exc import NoResultFound
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from packages.fsi_common import ExpenseItem, ExpenseReport

from .. import get_repository
from ..forms import parse_expense_form, parse_report_form
from ..services import build_preview, categories_for_select

reports_bp = Blueprint("reports", __name__)


@reports_bp.app_context_processor
def inject_categories() -> Dict[str, Any]:
    """Expose category metadata to Jinja templates."""

    return {"expense_categories": list(categories_for_select())}


@reports_bp.get("/")
def list_reports() -> str:
    """Render the list of reports."""

    repo = get_repository()
    reports = repo.list_reports()
    return render_template("reports/index.html", reports=reports)


@reports_bp.get("/reports/new")
def new_report_form() -> str:
    """Render the report creation form."""

    return render_template("reports/new.html", errors=[], form={})


@reports_bp.post("/reports")
def create_report() -> Response:
    """Handle creation of a new report."""

    form_data, errors = parse_report_form(request.form)
    if errors or form_data is None:
        flash("Please correct the highlighted errors.", "danger")
        return (
            render_template("reports/new.html", errors=errors, form=request.form),
            400,
        )

    report = ExpenseReport(
        id=None,
        title=form_data.title,
        traveler_name=form_data.traveler_name,
        department=form_data.department,
        trip_start=form_data.trip_start,
        trip_end=form_data.trip_end,
        purpose=form_data.purpose,
        notes=form_data.notes,
        policy_acknowledged=form_data.policy_acknowledged,
    )
    repo = get_repository()
    saved = repo.create_report(report)
    flash("Report created.", "success")
    return redirect(url_for("reports.view_report", report_id=saved.id))


@reports_bp.get("/reports/<int:report_id>")
def view_report(report_id: int) -> str:
    """Display a single report and its items."""

    repo = get_repository()
    try:
        report = repo.get_report(report_id)
    except NoResultFound:
        abort(404)
    return render_template(
        "reports/detail.html", report=report, form_errors=[], item_errors=[]
    )


@reports_bp.post("/reports/<int:report_id>")
def update_report(report_id: int) -> Response:
    """Update report metadata."""

    repo = get_repository()
    try:
        existing = repo.get_report(report_id)
    except NoResultFound:
        abort(404)

    form_data, errors = parse_report_form(request.form)
    if errors or form_data is None:
        flash("Please correct the highlighted errors.", "danger")
        return (
            render_template(
                "reports/detail.html",
                report=existing,
                form_errors=errors,
                item_errors=[],
            ),
            400,
        )
    repo.update_report(
        report_id,
        title=form_data.title,
        traveler_name=form_data.traveler_name,
        department=form_data.department,
        trip_start=form_data.trip_start,
        trip_end=form_data.trip_end,
        purpose=form_data.purpose,
        notes=form_data.notes,
        policy_acknowledged=form_data.policy_acknowledged,
    )
    flash("Report updated.", "success")
    return redirect(url_for("reports.view_report", report_id=report_id))


@reports_bp.post("/reports/<int:report_id>/expenses")
def add_expense_item(report_id: int) -> Response:
    """Add a new expense item to a report."""

    repo = get_repository()
    try:
        report = repo.get_report(report_id)
    except NoResultFound:
        abort(404)
    form_data, errors = parse_expense_form(request.form, request.files.get("receipt"))
    if errors or form_data is None:
        flash("Please correct the expense information.", "danger")
        return (
            render_template(
                "reports/detail.html",
                report=report,
                form_errors=[],
                item_errors=errors,
            ),
            400,
        )
    item = ExpenseItem(
        id=None,
        report_id=report_id,
        expense_date=form_data.expense_date,
        category=form_data.category,
        description=form_data.description,
        merchant=form_data.merchant,
        amount=form_data.amount,
        currency=form_data.currency,
        reimbursable=form_data.reimbursable,
    )
    saved = repo.add_item(item)
    if form_data.receipt:
        filename = _store_receipt(report_id, saved.id, form_data.receipt)
        repo.update_receipt(saved.id, filename)
    flash("Expense added.", "success")
    return redirect(url_for("reports.view_report", report_id=report_id))


@reports_bp.post("/reports/<int:report_id>/expenses/<int:item_id>/delete")
def delete_expense_item(report_id: int, item_id: int) -> Response:
    """Delete an expense item."""

    repo = get_repository()
    repo.delete_item(report_id, item_id)
    flash("Expense deleted.", "info")
    return redirect(url_for("reports.view_report", report_id=report_id))


@reports_bp.get("/reports/<int:report_id>/preview")
def preview_report(report_id: int) -> str:
    """Render the preview page."""

    repo = get_repository()
    try:
        report = repo.get_report(report_id)
    except NoResultFound:
        abort(404)
    preview_text = build_preview(report)
    return render_template(
        "reports/preview.html", report=report, preview_text=preview_text
    )


@reports_bp.get("/reports/<int:report_id>.json")
def export_report_json(report_id: int) -> Response:
    """Return a JSON representation of a report."""

    repo = get_repository()
    try:
        report = repo.get_report(report_id)
    except NoResultFound:
        abort(404)
    payload = {
        "id": report.id,
        "title": report.title,
        "traveler_name": report.traveler_name,
        "department": report.department,
        "trip_start": report.trip_start.isoformat(),
        "trip_end": report.trip_end.isoformat(),
        "purpose": report.purpose,
        "notes": report.notes,
        "policy_acknowledged": report.policy_acknowledged,
        "expenses": [
            {
                "id": item.id,
                "expense_date": item.expense_date.isoformat(),
                "category": item.category,
                "description": item.description,
                "merchant": item.merchant,
                "amount": float(item.amount),
                "currency": item.currency,
                "reimbursable": item.reimbursable,
                "receipt_filename": item.receipt_filename,
            }
            for item in report.expenses
        ],
    }
    return jsonify(payload)


@reports_bp.get("/receipts/<path:filename>")
def get_receipt(filename: str) -> Response:
    """Serve a previously uploaded receipt."""

    uploads = Path(current_app.config["UPLOAD_FOLDER"]).resolve()
    safe_path = (uploads / filename).resolve()
    if uploads not in safe_path.parents and safe_path != uploads:
        abort(404)
    if not safe_path.exists():
        abort(404)
    relative = safe_path.relative_to(uploads)
    return send_from_directory(uploads, relative.as_posix(), as_attachment=True)


def _store_receipt(report_id: int, item_id: int, receipt: FileStorage) -> str:
    """Persist a receipt upload and return its relative filename."""

    uploads = Path(current_app.config["UPLOAD_FOLDER"])
    report_dir = uploads / f"report_{report_id}"
    report_dir.mkdir(parents=True, exist_ok=True)
    original_name = receipt.filename or f"receipt-{item_id}.bin"
    filename = secure_filename(original_name)
    unique_name = f"{item_id}_{filename}"
    path = report_dir / unique_name
    receipt.save(path)
    relative = Path(f"report_{report_id}") / unique_name
    return relative.as_posix()
