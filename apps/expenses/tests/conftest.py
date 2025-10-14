"""Test fixtures for the Expenses app."""

from __future__ import annotations

from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from fsi_expenses_web import AppConfig, create_app


@pytest.fixture()
def app(tmp_path: Path):
    """Return a Flask app configured for testing."""

    db_path = tmp_path / "test.db"
    uploads = tmp_path / "uploads"
    config = AppConfig(
        database_url=f"sqlite:///{db_path}",
        uploads_dir=uploads,
        secret_key="testing",
        max_content_length=1024 * 1024,
    )
    application = create_app(config)
    application.config.update(TESTING=True)
    yield application


@pytest.fixture()
def client(app):
    """Return a Flask test client."""

    return app.test_client()
