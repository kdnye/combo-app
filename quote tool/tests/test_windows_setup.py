"""Tests for the Windows setup launcher."""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path

from dotenv import dotenv_values

import windows_setup


def _install_dummy_flask_app(monkeypatch):
    """Install a lightweight stand-in for :mod:`flask_app` during tests."""

    class DummyApp:
        def __init__(self) -> None:
            self.run_called = False

        def run(self) -> None:
            self.run_called = True

    dummy_app = DummyApp()
    dummy_module = types.SimpleNamespace(app=dummy_app)
    monkeypatch.setitem(sys.modules, "flask_app", dummy_module)
    return dummy_app


def _clear_env(monkeypatch) -> None:
    """Ensure configuration environment variables do not leak between tests."""

    for key in [
        "ADMIN_EMAIL",
        "ADMIN_PASSWORD",
        "GOOGLE_MAPS_API_KEY",
        "SECRET_KEY",
    ]:
        monkeypatch.delenv(key, raising=False)


def test_first_run_creates_env_and_initializes_db(monkeypatch, tmp_path: Path) -> None:
    """The launcher prompts for configuration and seeds the database on first run."""

    exec_dir = tmp_path
    rates_dir = exec_dir / "rates"
    rates_dir.mkdir()
    for filename in windows_setup.REQUIRED_RATE_FILES:
        (rates_dir / filename).write_text("placeholder", encoding="utf-8")

    responses = iter(
        ["admin@example.com", "maps-key", ""]
    )  # SECRET_KEY blank -> generate

    def fake_input(prompt: str) -> str:
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(windows_setup, "getpass", lambda prompt: "SuperSecure!1")
    monkeypatch.setattr(windows_setup, "get_execution_dir", lambda: exec_dir)
    monkeypatch.setattr(
        windows_setup, "generate_secret_key", lambda: "generated-secret"
    )

    init_calls: list[Path] = []

    def fake_initialize_database(path: Path) -> None:
        init_calls.append(path)

    monkeypatch.setattr("init_db.initialize_database", fake_initialize_database)
    dummy_app = _install_dummy_flask_app(monkeypatch)
    _clear_env(monkeypatch)

    windows_setup.main([])

    env_path = exec_dir / ".env"
    assert env_path.exists()
    env_values = dotenv_values(env_path)
    assert env_values["ADMIN_EMAIL"] == "admin@example.com"
    assert env_values["ADMIN_PASSWORD"] == "SuperSecure!1"
    assert env_values["GOOGLE_MAPS_API_KEY"] == "maps-key"
    assert env_values["SECRET_KEY"] == "generated-secret"

    assert init_calls == [rates_dir]
    assert (exec_dir / windows_setup.SENTINEL_FILENAME).exists()
    assert dummy_app.run_called

    # Environment variables are loaded for downstream tooling.
    assert os.environ["ADMIN_EMAIL"] == "admin@example.com"
    assert os.environ["SECRET_KEY"] == "generated-secret"


def test_first_run_uses_meipass_resources(monkeypatch, tmp_path: Path) -> None:
    """PyInstaller's ``_MEIPASS`` extraction directory is used for rate files."""

    exec_dir = tmp_path / "exec"
    exec_dir.mkdir()
    bundle_root = tmp_path / "bundle"
    rates_dir = bundle_root / "rates"
    rates_dir.mkdir(parents=True)
    for filename in windows_setup.REQUIRED_RATE_FILES:
        (rates_dir / filename).write_text("placeholder", encoding="utf-8")

    responses = iter(["admin@example.com", "maps-key", ""])

    monkeypatch.setattr("builtins.input", lambda prompt: next(responses))
    monkeypatch.setattr(windows_setup, "getpass", lambda prompt: "SuperSecure!1")
    monkeypatch.setattr(windows_setup, "get_execution_dir", lambda: exec_dir)
    monkeypatch.setattr(
        windows_setup, "generate_secret_key", lambda: "generated-secret"
    )
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_root), raising=False)

    init_calls: list[Path] = []

    def fake_initialize_database(path: Path) -> None:
        init_calls.append(path)

    monkeypatch.setattr("init_db.initialize_database", fake_initialize_database)
    dummy_app = _install_dummy_flask_app(monkeypatch)
    _clear_env(monkeypatch)

    windows_setup.main([])

    env_path = exec_dir / ".env"
    assert env_path.exists()
    env_values = dotenv_values(env_path)
    assert env_values["ADMIN_EMAIL"] == "admin@example.com"
    assert env_values["SECRET_KEY"] == "generated-secret"

    assert init_calls == [rates_dir]
    assert dummy_app.run_called
    assert (exec_dir / windows_setup.SENTINEL_FILENAME).exists()


def test_existing_env_skips_initialization_without_reconfigure(
    monkeypatch, tmp_path: Path
) -> None:
    """If ``.env`` already exists and ``--reconfigure`` is absent, prompts are skipped."""

    exec_dir = tmp_path
    env_path = exec_dir / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ADMIN_EMAIL=existing@example.com",
                "ADMIN_PASSWORD=OldPassword123",
                "GOOGLE_MAPS_API_KEY=old-maps-key",
                "SECRET_KEY=old-secret",
            ]
        ),
        encoding="utf-8",
    )
    (exec_dir / windows_setup.SENTINEL_FILENAME).touch()

    def unexpected(*_args, **_kwargs):  # pragma: no cover - defensive
        raise AssertionError("Prompts should not be triggered when .env exists")

    monkeypatch.setattr("builtins.input", unexpected)
    monkeypatch.setattr(windows_setup, "getpass", unexpected)
    monkeypatch.setattr(windows_setup, "get_execution_dir", lambda: exec_dir)

    init_called = False

    def fake_initialize_database(_path: Path) -> None:
        nonlocal init_called
        init_called = True

    monkeypatch.setattr("init_db.initialize_database", fake_initialize_database)
    dummy_app = _install_dummy_flask_app(monkeypatch)
    _clear_env(monkeypatch)

    windows_setup.main([])

    assert not init_called
    assert dummy_app.run_called
    assert dotenv_values(env_path)["ADMIN_EMAIL"] == "existing@example.com"


def test_reconfigure_updates_env(monkeypatch, tmp_path: Path) -> None:
    """``--reconfigure`` triggers prompts and updates persisted values."""

    exec_dir = tmp_path
    env_path = exec_dir / ".env"
    env_path.write_text(
        "\n".join(
            [
                "ADMIN_EMAIL=old@example.com",
                "ADMIN_PASSWORD=OldPassword123",
                "GOOGLE_MAPS_API_KEY=old-maps-key",
                "SECRET_KEY=old-secret",
            ]
        ),
        encoding="utf-8",
    )
    (exec_dir / windows_setup.SENTINEL_FILENAME).touch()

    responses = iter(["new@example.com", "new-maps-key", "manual-secret"])

    def fake_input(prompt: str) -> str:
        return next(responses)

    monkeypatch.setattr("builtins.input", fake_input)
    monkeypatch.setattr(windows_setup, "getpass", lambda prompt: "NewPassword!2")
    monkeypatch.setattr(windows_setup, "get_execution_dir", lambda: exec_dir)

    init_called = False

    def fake_initialize_database(_path: Path) -> None:
        nonlocal init_called
        init_called = True

    monkeypatch.setattr("init_db.initialize_database", fake_initialize_database)
    dummy_app = _install_dummy_flask_app(monkeypatch)
    _clear_env(monkeypatch)

    windows_setup.main(["--reconfigure"])

    env_values = dotenv_values(env_path)
    assert env_values["ADMIN_EMAIL"] == "new@example.com"
    assert env_values["ADMIN_PASSWORD"] == "NewPassword!2"
    assert env_values["GOOGLE_MAPS_API_KEY"] == "new-maps-key"
    assert env_values["SECRET_KEY"] == "manual-secret"

    assert not init_called
    assert dummy_app.run_called
    assert os.environ["ADMIN_EMAIL"] == "new@example.com"
    assert os.environ["ADMIN_PASSWORD"] == "NewPassword!2"
