# FSI Expenses — Python web client

The Expenses tool is now a Python/Flask application that helps Freight
Services employees assemble reimbursable expense reports, upload
receipts, and generate a copy-ready summary for finance. The
application stores reports in a lightweight SQLite database and serves a
server-rendered user interface so the entire workflow runs without a
browser build step.

## Features

- Guided workflow for creating and editing expense reports.
- Upload receipts per line item and download them later.
- Automatic totals by category and reimbursement status.
- Copy-ready preview that mirrors the information required by the
  accounting template.
- JSON API for exporting reports.

## Getting started

```bash
cd apps/expenses
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
flask --app fsi_expenses_web run --debug
```

The application listens on http://127.0.0.1:5000 by default. Set the
``EXPENSES_DATABASE`` environment variable to point to a different
SQLite database file if you want to keep your dev data between runs.

## Tests

```bash
pytest
```

Tests rely on an in-memory SQLite database and do not touch your local
development data.

## Docker image

A multi-stage Dockerfile is available so the app can be shipped as a
container:

```bash
docker build -t expenses-web:local .
docker run --rm -p 8000:8000 expenses-web:local
```

The container runs the production build with Gunicorn and serves the UI
at http://localhost:8000.

## Configuration

| Environment variable | Default | Description |
| -------------------- | ------- | ----------- |
| ``EXPENSES_DATABASE`` | ``instance/expenses.db`` | SQLite database path. |
| ``EXPENSES_UPLOADS`` | ``instance/uploads`` | Directory that stores receipt uploads. |
| ``EXPENSES_MAX_CONTENT_LENGTH`` | ``16777216`` | Maximum upload size in bytes (16&nbsp;MB). |
| ``EXPENSES_SECRET_KEY`` | ``development`` | Flask secret key used for sessions and CSRF protection. |

When running in production, provide a random `EXPENSES_SECRET_KEY` and
ensure the uploads directory is backed up with the database.
