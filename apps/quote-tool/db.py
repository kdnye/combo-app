"""Database engine and session configuration utilities."""

from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from google.api_core.exceptions import NotFound
from google.cloud import bigquery
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import scoped_session, sessionmaker

from config import Config
from app.models import (
    db,
    User,
    Quote,
    EmailQuoteRequest,
    EmailDispatchLog,
    Accessorial,
    HotshotRate,
    BeyondRate,
    AirCostZone,
    ZipZone,
    CostZone,
    RateUpload,
)


engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
# Use scoped_session to provide thread-local sessions that are removed
# after each request context. Sessions should be acquired with ``Session()``
# and cleaned up via ``Session.remove()``.
Session = scoped_session(sessionmaker(bind=engine))

# For legacy compatibility, expose Base for metadata operations in tests
Base = db.Model


def ensure_database_schema(active_engine: Engine | None = None) -> None:
    """Provision required tables for the configured database backend.

    The helper inspects the SQLAlchemy engine to determine the active backend.
    When BigQuery is in use it delegates to :func:`_ensure_bigquery_schema`,
    which coordinates with :class:`google.cloud.bigquery.Client` to create the
    dataset and tables. SQLite environments rely on
    :meth:`sqlalchemy.sql.schema.MetaData.create_all` because the test suite
    pre-populates fixtures directly through the ORM. All other backends invoke
    :func:`_run_alembic_upgrade` to ensure Alembic migrations reach the latest
    revision automatically.

    Args:
        active_engine: Optional SQLAlchemy engine. When ``None`` the module's
            global :data:`engine` is used so the function can be invoked from
            application startup as well as tests.

    Returns:
        None. The function performs schema creation as a side effect.
    """

    selected_engine = active_engine or engine
    backend = selected_engine.url.get_backend_name()
    if backend == "bigquery":
        _ensure_bigquery_schema(selected_engine)
        return

    if backend == "sqlite":
        Base.metadata.create_all(bind=selected_engine)
        return

    _run_alembic_upgrade(selected_engine)


def _ensure_bigquery_schema(active_engine: Engine) -> None:
    """Ensure the BigQuery dataset and tables referenced by ``active_engine`` exist.

    The function extracts the project, dataset, and optional location from the
    engine URL before using :class:`google.cloud.bigquery.Client` to verify the
    dataset. Each model table exposed through :data:`Base.metadata` is then
    checked with :meth:`google.cloud.bigquery.Client.get_table`; missing tables
    are created with :meth:`sqlalchemy.sql.schema.Table.create` so the
    application can persist data immediately after startup.

    Args:
        active_engine: SQLAlchemy engine bound to a BigQuery dataset.

    Returns:
        None. Raises :class:`RuntimeError` when the engine URL is incomplete and
        BigQuery cannot be targeted.
    """

    url = active_engine.url
    project = url.host
    dataset_id = url.database
    location = url.query.get("location") if hasattr(url, "query") else None

    if not project or not dataset_id:
        raise RuntimeError(
            "BigQuery engine is missing project or dataset information in the URL."
        )

    client = bigquery.Client(project=project)
    dataset_ref = bigquery.Dataset(f"{project}.{dataset_id}")
    if location:
        dataset_ref.location = location

    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        client.create_dataset(dataset_ref)

    for table in Base.metadata.sorted_tables:
        table_fqdn = f"{project}.{dataset_id}.{table.name}"
        try:
            client.get_table(table_fqdn)
            continue
        except NotFound:
            table.create(bind=active_engine)


def _run_alembic_upgrade(active_engine: Engine) -> None:
    """Apply Alembic migrations for the database bound to ``active_engine``.

    Args:
        active_engine: SQLAlchemy engine configured for the target database.

    Returns:
        ``None``. Executes ``alembic upgrade head`` programmatically so the
        runtime schema always matches the latest migrations. Alembic reads the
        migration scripts from ``migrations/`` and connects using the engine
        URL extracted from ``active_engine``. The helper renders the URL with
        passwords intact by calling :meth:`sqlalchemy.engine.URL.render_as_string`
        when available to avoid relying on environment variables inside the
        container.
    """

    root_path = Path(__file__).resolve().parent
    alembic_config_path = root_path / "alembic.ini"
    migrations_path = root_path / "migrations"
    config = AlembicConfig(str(alembic_config_path))
    config.set_main_option("script_location", str(migrations_path))

    url = active_engine.url
    if hasattr(url, "render_as_string"):
        rendered_url = url.render_as_string(hide_password=False)
    else:  # pragma: no cover - compatibility fallback for older SQLAlchemy
        rendered_url = str(url)

    config.set_main_option("sqlalchemy.url", rendered_url)

    inspector = inspect(active_engine)
    existing_tables = [table for table in inspector.get_table_names() if table]
    has_version_table = "alembic_version" in existing_tables

    if not has_version_table and existing_tables:
        script = ScriptDirectory.from_config(config)
        base_revision = script.get_base()
        if isinstance(base_revision, tuple):  # pragma: no cover - multi-base fallback
            base_revision = base_revision[0]
        stamp_revision = base_revision or "base"
        command.stamp(config, stamp_revision)

    command.upgrade(config, "head")


__all__ = [
    "engine",
    "Session",
    "Base",
    "User",
    "Quote",
    "EmailQuoteRequest",
    "EmailDispatchLog",
    "Accessorial",
    "HotshotRate",
    "BeyondRate",
    "AirCostZone",
    "ZipZone",
    "CostZone",
    "RateUpload",
    "ensure_database_schema",
]


if __name__ == "__main__":
    ensure_database_schema()
