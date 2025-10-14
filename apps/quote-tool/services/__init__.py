"""Shared service utilities for the Quote Tool application."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Final

__all__: Final[list[str]] = ["mail", "settings", "auth_utils", "hotshot_rates", "quote"]


def __getattr__(name: str) -> ModuleType:
    """Dynamically expose lazily imported service modules.

    The legacy codebase imports ``services.quote`` even though the concrete
    implementation lives in the top-level :mod:`quote` package. This shim keeps
    those imports working while still providing explicit modules such as
    :mod:`services.mail` and :mod:`services.settings` implemented in this
    directory.

    Args:
        name: Attribute requested from the package.

    Returns:
        ModuleType: Resolved module for ``mail``, ``settings``,
        ``auth_utils``, ``hotshot_rates``, or a proxy to the top-level
        :mod:`quote` package when ``name`` equals ``"quote"``.

    Raises:
        AttributeError: If an unknown attribute is requested.

    External Dependencies:
        * Delegates to :func:`importlib.import_module` for module loading.
    """

    if name == "quote":
        return import_module("quote")
    if name in {"mail", "settings", "auth_utils", "hotshot_rates"}:
        return import_module(f"{__name__}.{name}")
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
