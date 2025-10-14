"""FSI Expenses Flask application factory."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from flask import Flask, current_app, g

def _discover_project_root(start: Path) -> Path:
    """Return the repository root used for local imports.

    Args:
        start: Absolute path to a file within the project. The helper walks up
            the directory tree from this location.

    Returns:
        The first parent directory containing a repository marker such as
        ``pyproject.toml`` or ``.git``. When no structural markers are found the
        helper returns the closest ancestor that includes one of the known
        marker files.

    External dependencies:
        Relies on :class:`pathlib.Path` for filesystem inspection and does not
        perform any I/O beyond existence checks.
    """

    markers = {"pyproject.toml", "setup.cfg", "requirements.txt", ".git"}
    current = start
    fallback = current
    for parent in (current, *current.parents):
        if (parent / "apps").is_dir() and (parent / "packages").is_dir():
            return parent
        if any((parent / marker).exists() for marker in markers):
            fallback = parent
    return fallback


PROJECT_ROOT = _discover_project_root(Path(__file__).resolve().parent)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from .config import AppConfig, load_config  # noqa: E402
from .database import create_db_engine, init_schema  # noqa: E402
from .repositories import ExpensesRepository  # noqa: E402


def create_app(config: AppConfig | None = None) -> Flask:
    """Return a configured Flask application."""

    app = Flask(__name__, instance_relative_config=True)
    app_config = config or load_config()
    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)
    app.config.update(
        SECRET_KEY=app_config.secret_key,
        UPLOAD_FOLDER=str(app_config.uploads_dir),
        MAX_CONTENT_LENGTH=app_config.max_content_length,
    )
    engine = create_db_engine(app_config.database_url)
    init_schema(engine)
    app.config["DB_ENGINE"] = engine

    from .blueprints.reports import reports_bp

    app.register_blueprint(reports_bp)

    @app.teardown_appcontext
    def teardown(_: Any) -> None:
        g.pop("expenses_repo", None)

    @app.cli.command("init-db")
    def init_db_command() -> None:
        """Initialize the database tables."""

        init_schema(engine)
        import click

        click.echo("Database initialized.")

    return app


def get_repository() -> ExpensesRepository:
    """Return a request-scoped :class:`ExpensesRepository`."""

    if not hasattr(g, "expenses_repo"):
        engine = current_app.config["DB_ENGINE"]
        g.expenses_repo = ExpensesRepository(engine)
    return g.expenses_repo


__all__ = ["create_app", "AppConfig", "get_repository"]
