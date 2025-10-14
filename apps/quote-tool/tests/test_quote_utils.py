"""Tests for helpers in :mod:`quote.utils`."""

from __future__ import annotations

import pandas as pd

from quote.utils import calculate_accessorials, normalize_workbook


def test_normalize_workbook_trims_columns():
    """Whitespace surrounding column headers should be stripped."""

    df = pd.DataFrame({"  Column A  ": [1, 2], "Column B": [3, 4]})
    workbook = {"Sheet1": df}
    normalized = normalize_workbook(workbook)
    assert list(normalized["Sheet1"].columns) == ["Column A", "Column B"]


def test_calculate_accessorials_matches_selected_options():
    """Totals should include the first numeric value for each selected column."""

    df = pd.DataFrame({
        "Liftgate": ["$25"],
        "Guarantee": ["10%"],
        "Inside Delivery": [" 15 "],
    })
    total = calculate_accessorials(df, ["Liftgate", "Inside Delivery"])
    assert total == 40.0


def test_calculate_accessorials_handles_missing_columns():
    """Unknown accessorials should be ignored gracefully."""

    df = pd.DataFrame({"Storage": ["$5"], "Hazmat": ["$12"]})
    total = calculate_accessorials(df, ["Liftgate", "Hazmat"])
    assert total == 12.0

