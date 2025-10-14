"""Configuration helpers for the Expenses web application."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    """Settings loaded from environment variables."""

    database_url: str
    uploads_dir: Path
    secret_key: str
    max_content_length: int


def load_config() -> AppConfig:
    """Create an :class:`AppConfig` instance from environment variables."""

    uploads_dir = Path(os.getenv("EXPENSES_UPLOADS", "instance/uploads"))
    uploads_dir.mkdir(parents=True, exist_ok=True)
    database = os.getenv(
        "EXPENSES_DATABASE", "sqlite:///" + str(Path("instance/expenses.db"))
    )
    max_content_length = int(os.getenv("EXPENSES_MAX_CONTENT_LENGTH", "16777216"))
    secret_key = os.getenv("EXPENSES_SECRET_KEY", "development")
    return AppConfig(
        database_url=database,
        uploads_dir=uploads_dir,
        secret_key=secret_key,
        max_content_length=max_content_length,
    )
