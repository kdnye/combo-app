"""FSI Expenses Flask application factory."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any

from flask import Flask, current_app, g


def _discover_project_root() -> Path:
    """Return the repository root by walking up the filesystem.

    The Docker image copies the application into ``/app`` which means the
    original ``Path.parents[3]`` lookup fails because ``/app`` does not expose
    enough ancestors. This helper searches parent directories for common
    project markers to keep imports functioning in local and containerised
    environments alike.

    Returns:
        Path: Directory containing ``pyproject.toml`` or ``README.md``. Falls
        back to the package directory when no markers are present.
    """

    current = Path(__file__).resolve().parent
    selected = current
    for candidate in [current] + list(current.parents):
        if any((candidate / marker).exists() for marker in ("pyproject.toml", "README.md")):
            selected = candidate
    return selected


PROJECT_ROOT = _discover_project_root()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


from .config import AppConfig, load_config  # noqa: E402
from .database import create_db_engine, init_schema  # noqa: E402
from .repositories import ExpensesRepository  # noqa: E402


def create_app(config: AppConfig | None = None) -> Flask:
    """Build and configure the Expenses Flask application instance.

    Args:
        config: Optional :class:`AppConfig` override. When ``None`` the helper
            loads configuration via :func:`load_config`, which honours
            environment variables documented in ``README.md``.

    Returns:
        Flask: Fully initialised application ready for registration with
        Gunicorn. The instance carries a SQLAlchemy engine stored on
        ``app.config['DB_ENGINE']`` for downstream repositories.

    External Dependencies:
        * Calls :func:`load_config` to resolve runtime settings.
        * Uses :func:`create_db_engine` and :func:`init_schema` to prepare the
          database schema on startup.
    """

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
    """Return a cached repository bound to the active Flask request.

    Returns:
        ExpensesRepository: Lazily constructed instance stored on
        :mod:`flask.g` so blueprints share a single database connection within
        a request lifecycle.

    External Dependencies:
        * Reads ``current_app.config['DB_ENGINE']`` set during
          :func:`create_app`.
    """

    if not hasattr(g, "expenses_repo"):
        engine = current_app.config["DB_ENGINE"]
        g.expenses_repo = ExpensesRepository(engine)
    return g.expenses_repo


__all__ = ["create_app", "AppConfig", "get_repository"]
