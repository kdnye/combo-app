"""Tests for the runtime debug flag configuration."""

from pathlib import Path

import pytest

import flask_app


def test_resolve_debug_flag_defaults_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """``FLASK_DEBUG`` missing from the environment disables debug mode by default.

    Uses :class:`pytest.MonkeyPatch` to temporarily clear the environment so
    :func:`flask_app.resolve_debug_flag` falls back to its hardened
    :data:`flask_app.DEFAULT_DEBUG` value (``False``).
    """

    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    assert flask_app.resolve_debug_flag() is False


def test_resolve_debug_flag_false_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production-style values disable debugging via :func:`flask_app.resolve_debug_flag`.

    Sets ``FLASK_DEBUG`` to ``"0"`` using :class:`pytest.MonkeyPatch` to mimic a
    production deployment and asserts the helper returns ``False``.
    """

    monkeypatch.setenv("FLASK_DEBUG", "0")
    assert flask_app.resolve_debug_flag() is False


def test_dockerfile_disables_debug_in_production() -> None:
    """The Docker runtime image sets ``FLASK_DEBUG=0`` for hardened builds.

    Reads the top-level ``Dockerfile`` via :class:`pathlib.Path` to confirm the
    runtime stage hard-codes ``FLASK_DEBUG=0`` so production containers do not
    expose the Werkzeug debugger.
    """

    dockerfile_path = Path(__file__).resolve().parents[1] / "Dockerfile"
    dockerfile_text = dockerfile_path.read_text(encoding="utf-8")
    assert "FLASK_DEBUG=0" in dockerfile_text
