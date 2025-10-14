import pandas as pd
from quote.utils import normalize_workbook


def test_normalize_workbook_strips_column_names_without_altering_data() -> None:
    """Whitespace in column headers is removed while cell values stay the same."""

    workbook = {
        "Sheet1": pd.DataFrame({" Col1 ": [1, 2], "Col2 ": [3, 4]}),
        "Sheet2": pd.DataFrame({" Col3": ["a", "b"]}),
    }

    normalized = normalize_workbook(workbook)

    assert normalized["Sheet1"].columns.tolist() == ["Col1", "Col2"]
    assert normalized["Sheet2"].columns.tolist() == ["Col3"]

    pd.testing.assert_frame_equal(
        normalized["Sheet1"], pd.DataFrame({"Col1": [1, 2], "Col2": [3, 4]})
    )
    pd.testing.assert_frame_equal(
        normalized["Sheet2"], pd.DataFrame({"Col3": ["a", "b"]})
    )
