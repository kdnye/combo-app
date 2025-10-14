import pandas as pd
import pytest

from scripts.import_hotshot_rates import (
    import_csvs,
    load_accessorials,
    load_beyond_rates,
    load_hotshot_rates,
    verify_csvs,
)
from app.models import Accessorial, BeyondRate, HotshotRate
from db import Session


def test_load_hotshot_rates() -> None:
    df = pd.DataFrame(
        {
            "Miles": [1],
            "ZONE": ["A"],
            "PER LB": [0.2],
            "MIN": [79.5],
            "Weight Break": [382.5],
            "Fuel": [0.3],
        }
    )
    objs = load_hotshot_rates(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, HotshotRate)
    assert obj.miles == 1
    assert obj.zone == "A"
    assert obj.per_lb == 0.2
    assert obj.min_charge == 79.5
    assert obj.weight_break == 382.5
    assert obj.fuel_pct == 0.3


def test_load_hotshot_rates_with_per_mile() -> None:
    df = pd.DataFrame(
        {
            "Miles": [1],
            "ZONE": ["A"],
            "PER MILE": [1.5],
            "PER LB": [0.2],
            "MIN": [79.5],
            "Weight Break": [382.5],
            "Fuel": [0.3],
        }
    )
    objs = load_hotshot_rates(df)
    assert len(objs) == 1
    assert objs[0].per_mile == 1.5


def test_load_hotshot_rates_handles_missing_weight_break() -> None:
    """load_hotshot_rates should convert missing weight breaks to None."""

    df = pd.DataFrame(
        {
            "Miles": [10],
            "ZONE": ["X"],
            "PER LB": [1.0],
            "MIN": [5.0],
            "Weight Break": [float("nan")],
            "Fuel": [0.1],
        }
    )
    objs = load_hotshot_rates(df)
    assert len(objs) == 1
    assert objs[0].weight_break is None


def test_load_hotshot_rates_missing_miles_column() -> None:
    """Missing required columns should raise a clear ValueError."""

    df = pd.DataFrame({"ZONE": ["A"], "PER LB": [0.2], "MIN": [50], "Fuel": [0.1]})
    with pytest.raises(ValueError):
        load_hotshot_rates(df)


def test_load_beyond_rates() -> None:
    df = pd.DataFrame({"ZONE": ["B"], "RATE": [1.5], "Up to Miles": [10]})
    objs = load_beyond_rates(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, BeyondRate)
    assert obj.zone == "B"
    assert obj.rate == 1.5
    assert obj.up_to_miles == 10


def test_load_beyond_rates_ignores_missing_zone() -> None:
    """Rows missing a ZONE value are skipped and do not raise errors."""

    df = pd.DataFrame(
        {
            "ZONE": ["B", None],
            "RATE": [1.5, 2.0],
            "Up to Miles": [10, 20],
        }
    )
    objs = load_beyond_rates(df)
    assert len(objs) == 1
    assert objs[0].zone == "B"

    with Session() as session:
        session.query(BeyondRate).delete()
        session.bulk_save_objects(objs)
        session.commit()
        assert session.query(BeyondRate).count() == 1
        session.query(BeyondRate).delete()
        session.commit()


def test_load_beyond_rates_parses_currency() -> None:
    df = pd.DataFrame({"ZONE": ["B"], "RATE": ["$1,050.40"], "Up to Miles": ["1,000"]})
    objs = load_beyond_rates(df)
    assert len(objs) == 1
    obj = objs[0]
    assert obj.rate == pytest.approx(1050.40)
    assert obj.up_to_miles == pytest.approx(1000)


def test_load_accessorials() -> None:
    df = pd.DataFrame([{"Liftgate": 50, "Guarantee": "multiply total by 1.25"}])
    objs = load_accessorials(df)
    by_name = {o.name: o for o in objs}
    liftgate = by_name["Liftgate"]
    guarantee = by_name["Guarantee"]
    assert isinstance(liftgate, Accessorial)
    assert liftgate.amount == 50
    assert not liftgate.is_percentage
    assert isinstance(guarantee, Accessorial)
    assert guarantee.is_percentage
    assert guarantee.amount == pytest.approx(0.25)


def test_load_accessorials_column_oriented() -> None:
    df = pd.DataFrame(
        {
            "Accessorial": ["Liftgate", "Guarantee"],
            "Amount": [50, "multiply total by 1.25"],
        }
    )
    objs = load_accessorials(df)
    by_name = {o.name: o for o in objs}
    liftgate = by_name["Liftgate"]
    guarantee = by_name["Guarantee"]
    assert isinstance(liftgate, Accessorial)
    assert liftgate.amount == 50
    assert not liftgate.is_percentage
    assert isinstance(guarantee, Accessorial)
    assert guarantee.is_percentage
    assert guarantee.amount == pytest.approx(0.25)


def test_load_accessorials_parses_currency() -> None:
    df = pd.DataFrame({"Accessorial": ["Detention"], "Amount": ["$95.00"]})
    objs = load_accessorials(df)
    assert len(objs) == 1
    obj = objs[0]
    assert obj.name == "Detention"
    assert obj.amount == pytest.approx(95.0)


def test_load_accessorials_skips_blank_rows() -> None:
    df = pd.DataFrame({"Accessorial": ["Liftgate", None], "Amount": [50, None]})
    objs = load_accessorials(df)
    assert len(objs) == 1
    assert objs[0].name == "Liftgate"


def test_verify_csvs(tmp_path) -> None:
    """verify_csvs returns True only when tables match the CSV sources."""

    hotshot_df = pd.DataFrame(
        {
            "Miles": [1],
            "ZONE": ["A"],
            "PER LB": [0.2],
            "MIN": [79.5],
            "Weight Break": [382.5],
            "Fuel": [0.3],
        }
    )
    beyond_df = pd.DataFrame({"ZONE": ["B"], "RATE": [1.5], "Up to Miles": [10]})
    access_df = pd.DataFrame([{"Liftgate": 50}])
    data_dir = tmp_path
    hotshot_df.to_csv(data_dir / "Hotshot_Rates.csv", index=False)
    beyond_df.to_csv(data_dir / "beyond_price.csv", index=False)
    access_df.to_csv(data_dir / "accessorial_cost.csv", index=False)

    with Session() as session:
        session.query(HotshotRate).delete()
        session.query(BeyondRate).delete()
        session.query(Accessorial).delete()
        session.commit()

    import_csvs(data_dir)
    assert verify_csvs(data_dir)

    # Introduce mismatch
    with Session() as session:
        session.query(HotshotRate).delete()
        session.commit()
    assert not verify_csvs(data_dir)
