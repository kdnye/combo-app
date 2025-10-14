"""Tests covering secret key resolution behaviour."""

from __future__ import annotations

import importlib

import pytest


def test_secret_key_generated_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Config generates a unique secret key when ``SECRET_KEY`` is absent."""

    config_module = importlib.import_module("config")
    original = config_module.Config.SECRET_KEY
    monkeypatch.delenv("SECRET_KEY", raising=False)
    config_module = importlib.reload(config_module)
    try:
        generated = config_module.Config.SECRET_KEY
        assert generated
        assert generated != original
    finally:
        monkeypatch.setenv("SECRET_KEY", original)
        config_module = importlib.reload(config_module)
