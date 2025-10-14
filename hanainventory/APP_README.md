# Hana Table Inventory Flask App

This Flask application seeds an SQLite database with the baseline inventory data that previously lived in Google Sheets and Apps Script. The goal is to provide a foundation for migrating the workflow into a standalone web experience.

## Features

- Loads all form metadata, item expectations, and per-location baselines directly from the original README dataset.
- Stores data in an SQLite database via SQLAlchemy models (`Location`, `Item`, and `LocationItem`).
- Presents a Bootstrap-based dashboard summarising network totals and location-level variances.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
flask --app wsgi run
```

The first run creates `inventory.db` at the repository root and seeds it with the baseline counts from the Google Sheet snapshot. Subsequent runs reuse the existing database.

Open http://127.0.0.1:5000/ to view the dashboard.

## Next steps

- Replace the seeded counts with live form submissions or CSV imports.
- Add authentication and role-based permissions for regional teams.
- Extend the dashboard with trend charts or export utilities.
