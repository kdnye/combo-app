import os
from pathlib import Path


class Config:
    """Default configuration for the Flask application."""

    BASE_DIR = Path(__file__).resolve().parent.parent
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'inventory.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    APP_DIRECTORY = [
        {
            "slug": "hana-inventory",
            "name": "Hana Table Inventory",
            "description": (
                "Audit nationwide Hana operating table kits and identify "
                "inventory variances before the weekly review."
            ),
            "endpoint": "main.inventory_dashboard",
        },
        {
            "slug": "expenses",
            "name": "Expenses",
            "description": (
                "Assemble reimbursable expense reports, attach receipts, "
                "and send them for approval in one workflow."
            ),
            "url": os.environ.get("EXPENSES_APP_URL", "http://localhost:8080/"),
            "external": True,
        },
        {
            "slug": "quote-tool",
            "name": "Hotshot Quote Tool",
            "description": (
                "Build and track hotshot freight quotes with automated "
                "margin checks and status updates."
            ),
            "url": os.environ.get("QUOTE_TOOL_APP_URL", "http://localhost:5000/"),
            "external": True,
        },
    ]
