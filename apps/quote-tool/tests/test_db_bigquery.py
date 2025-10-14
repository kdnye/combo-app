"""Tests covering BigQuery schema provisioning helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from google.api_core.exceptions import NotFound

import db


class _DummyUrl(SimpleNamespace):
    """Lightweight helper that mimics the SQLAlchemy URL interface."""

    backend: str

    def get_backend_name(self) -> str:  # pragma: no cover - simple delegation
        """Return the configured backend name."""

        return self.backend


def test_ensure_database_schema_bigquery_creates_missing_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ensure BigQuery datasets and tables are created when missing.

    The test simulates a BigQuery backend by monkeypatching the SQLAlchemy URL
    to report ``"bigquery"`` and configuring :class:`google.cloud.bigquery.Client`
    to raise :class:`google.api_core.exceptions.NotFound` for datasets and tables.
    ``db.ensure_database_schema`` should create the dataset and call
    :meth:`sqlalchemy.sql.schema.Table.create` for the fake table.
    """

    dummy_engine = MagicMock()
    dummy_engine.url = _DummyUrl(
        backend="bigquery", host="quote-project", database="quote_dataset", query={}
    )

    dummy_table = MagicMock()
    dummy_table.name = "users"
    dummy_metadata = SimpleNamespace(sorted_tables=[dummy_table])
    monkeypatch.setattr(db, "Base", SimpleNamespace(metadata=dummy_metadata))

    client = MagicMock()
    client.get_dataset.side_effect = NotFound("dataset missing")
    client.get_table.side_effect = NotFound("table missing")
    client_ctor = MagicMock(return_value=client)
    monkeypatch.setattr(db.bigquery, "Client", client_ctor)

    upgrade = MagicMock()
    monkeypatch.setattr(db, "_run_alembic_upgrade", upgrade)

    db.ensure_database_schema(dummy_engine)

    client_ctor.assert_called_once_with(project="quote-project")
    client.create_dataset.assert_called_once()
    client.get_table.assert_called_once_with("quote-project.quote_dataset.users")
    dummy_table.create.assert_called_once_with(bind=dummy_engine)
    upgrade.assert_not_called()


def test_ensure_database_schema_uses_create_all_for_sqlite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use ``MetaData.create_all`` when the backend is SQLite."""

    dummy_engine = MagicMock()
    dummy_engine.url = _DummyUrl(backend="sqlite", host=None, database=None)

    create_all = MagicMock()
    dummy_metadata = SimpleNamespace(create_all=create_all)
    monkeypatch.setattr(db, "Base", SimpleNamespace(metadata=dummy_metadata))
    upgrade = MagicMock()
    monkeypatch.setattr(db, "_run_alembic_upgrade", upgrade)

    db.ensure_database_schema(dummy_engine)

    create_all.assert_called_once_with(bind=dummy_engine)
    upgrade.assert_not_called()


def test_ensure_database_schema_runs_migrations_for_postgres(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invoke Alembic migrations for non-SQLite relational backends."""

    dummy_engine = MagicMock()
    dummy_engine.url = _DummyUrl(backend="postgresql", host=None, database=None)

    upgrade = MagicMock()
    monkeypatch.setattr(db, "_run_alembic_upgrade", upgrade)

    db.ensure_database_schema(dummy_engine)

    upgrade.assert_called_once_with(dummy_engine)
