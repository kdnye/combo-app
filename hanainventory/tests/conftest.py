import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db
from app.config import Config


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = "sqlite:///{path}"
    TESTING = True
    SECRET_KEY = "test-secret-key"

    def __init__(self, path: Path) -> None:
        # Override URI with the runtime path for the sqlite database.
        self.SQLALCHEMY_DATABASE_URI = f"sqlite:///{path}"


@pytest.fixture()
def app(tmp_path):
    db_path = tmp_path / "test.db"
    config = TestConfig(db_path)
    application = create_app(config)

    yield application

    with application.app_context():
        db.drop_all()
        db.session.remove()
    if db_path.exists():
        os.remove(db_path)


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def app_context(app):
    with app.app_context():
        yield
