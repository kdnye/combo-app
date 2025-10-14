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
    QUOTE_TOOL_WORKSPACE_URL = os.environ.get(
        "QUOTE_TOOL_WORKSPACE_URL",
        "http://localhost:5000/workspace/",
    )
