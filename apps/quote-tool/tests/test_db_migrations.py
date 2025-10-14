"""Tests for database migration orchestration utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

import db


@pytest.fixture
def _mock_alembic(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[MagicMock, MagicMock, MagicMock]:
    """Return mocked Alembic components used by migration helpers."""

    config_instance = MagicMock()
    config_factory = MagicMock(return_value=config_instance)
    monkeypatch.setattr(db, "AlembicConfig", config_factory)

    script_directory = MagicMock()
    script_directory.get_base.return_value = "base_rev"
    directory_factory = MagicMock()
    directory_factory.from_config.return_value = script_directory
    monkeypatch.setattr(db, "ScriptDirectory", directory_factory)

    command = MagicMock()
    monkeypatch.setattr(db, "command", command)

    return config_instance, script_directory, command


def test_run_alembic_upgrade_stamps_existing_schema(
    monkeypatch: pytest.MonkeyPatch, _mock_alembic
) -> None:
    """Stamp legacy databases before upgrading so migrations can proceed."""

    config_instance, script_directory, command = _mock_alembic

    engine = MagicMock()
    engine.url.render_as_string.return_value = "sqlite:///legacy.db"

    inspector = MagicMock()
    inspector.get_table_names.return_value = ["users", "quotes"]
    monkeypatch.setattr(db, "inspect", MagicMock(return_value=inspector))

    db._run_alembic_upgrade(engine)

    script_directory.get_base.assert_called_once()
    command.stamp.assert_called_once_with(config_instance, "base_rev")
    command.upgrade.assert_called_once_with(config_instance, "head")


def test_run_alembic_upgrade_skips_stamp_when_version_present(
    monkeypatch: pytest.MonkeyPatch, _mock_alembic
) -> None:
    """Avoid stamping when the Alembic version table already exists."""

    config_instance, script_directory, command = _mock_alembic

    engine = MagicMock()
    engine.url.render_as_string.return_value = "sqlite:///migrated.db"

    inspector = MagicMock()
    inspector.get_table_names.return_value = ["alembic_version", "users"]
    monkeypatch.setattr(db, "inspect", MagicMock(return_value=inspector))

    db._run_alembic_upgrade(engine)

    script_directory.get_base.assert_not_called()
    command.stamp.assert_not_called()
    command.upgrade.assert_called_once_with(config_instance, "head")
