"""FSI Expenses Flask application factory."""

from __future__ import annotations

from pathlib import Path
import os
import sys
from typing import Any

from flask import Flask, current_app, g


def _add_repo_root_to_path() -> None:
    """Ensure shared ``packages`` directory is importable at runtime.

    When the service is installed into a container the application itself is
    imported from ``site-packages``. In that case the monorepo root (which holds
    the ``packages`` directory) is not automatically included on
    :data:`sys.path`. We therefore check a set of likely root locations and
    prepend the first directory that actually contains ``packages``.
    """

    root_marker = "packages"
    current = Path(__file__).resolve()

    candidate_roots: list[Path] = []

    env_root = os.getenv("FSI_MONOREPO_ROOT")
    if env_root:
        try:
            candidate_roots.append(Path(env_root).resolve())
        except OSError:
            pass

    candidate_roots.append(Path("/app"))
    candidate_roots.extend((current.parent, *current.parents))

    seen: set[Path] = set()
    for candidate in candidate_roots:
        if candidate in seen:
            continue
        seen.add(candidate)
        packages_dir = candidate / root_marker
        if packages_dir.exists():
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
