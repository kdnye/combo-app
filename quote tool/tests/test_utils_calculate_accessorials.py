import pandas as pd
from quote.utils import calculate_accessorials


def test_calculate_accessorials_sums_columns():
    df = pd.DataFrame(
        {
            "Liftgate": ["instruction", "$100"],
            "Detention": ["$50", ""],
            "Fuel": ["10%", None],
        }
    )
    total = calculate_accessorials(df, ["Liftgate", "Detention"])
    assert total == 150


def test_calculate_accessorials_ignores_percentage_and_missing():
    df = pd.DataFrame(
        {
            "Guarantee": ["25%"],
            "Other": ["$25"],
        }
    )
    total = calculate_accessorials(df, ["Guarantee", "Other", "Missing"])
    assert total == 25
