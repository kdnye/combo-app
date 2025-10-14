"""FSI Expenses Flask application factory."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from flask import Flask, current_app, g


def _add_repo_root_to_path() -> None:
    """Ensure the monorepo root is on ``sys.path`` when running in Docker.

    The expenses service imports shared utilities from ``packages/``. When the
    application is installed as a wheel inside the container the package lives
    under ``/app/fsi_expenses_web`` which is only two levels deep, so the
    previous ``parents[3]`` lookup raised :class:`IndexError`. This helper walks
    upward from the current module until it finds a directory containing the
    ``packages`` folder and appends that path to ``sys.path`` if it is missing.

    External dependencies:
        * Relies on :mod:`pathlib` to traverse parent directories.
        * Mutates :data:`sys.path` so imports such as ``packages.fsi_common``
          continue to work inside the Docker runtime.
    """

    root_marker = "packages"
    current = Path(__file__).resolve()
    for candidate in (current.parent, *current.parents):
        if (candidate / root_marker).exists():
            root = str(candidate)
            if root not in sys.path:
                sys.path.insert(0, root)
            return


_add_repo_root_to_path()


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
