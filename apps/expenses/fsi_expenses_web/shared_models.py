"""Utilities for importing shared domain models across apps."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys
from types import ModuleType
from typing import Iterable

_PACKAGE_NAME = "packages.fsi_common"


def _ensure_repo_root_on_path() -> None:
    """Add the monorepo root to ``sys.path`` when running from source."""

    for candidate in Path(__file__).resolve().parents:
        packages_dir = candidate / "packages"
        if packages_dir.is_dir():
            root_path = str(candidate)
            if root_path not in sys.path:
                sys.path.insert(0, root_path)
            break


def _load_shared_module() -> ModuleType:
    """Import the shared expenses module, retrying after path adjustment."""

    try:
        return import_module(_PACKAGE_NAME)
    except ModuleNotFoundError:
        _ensure_repo_root_on_path()
        try:
            return import_module(_PACKAGE_NAME)
        except ModuleNotFoundError as exc:  # pragma: no cover - defensive guard
            raise ModuleNotFoundError(
                "Unable to import 'packages.fsi_common'. Install the shared packages "
                "distribution or ensure the repository root is on PYTHONPATH."
            ) from exc


_shared = _load_shared_module()

ExpenseCategory = _shared.ExpenseCategory
ExpenseItem = _shared.ExpenseItem
ExpenseReport = _shared.ExpenseReport
ReportSummary = _shared.ReportSummary
summarize_report = _shared.summarize_report

__all__: Iterable[str] = [
    "ExpenseCategory",
    "ExpenseItem",
    "ExpenseReport",
    "ReportSummary",
    "summarize_report",
]
