import logging
from pathlib import Path

import pandas as pd
import pytest

from app import create_app
from app.models import db, ZipZone, CostZone, AirCostZone, BeyondRate
from scripts.import_air_rates import (
    load_zip_zones,
    load_cost_zones,
    load_air_cost_zones,
    load_beyond_rates,
    import_csvs,
)


def test_load_zip_zones() -> None:
    df = pd.DataFrame(
        {
            "Zipcode": ["12345", "12345"],
            "Dest Zone": [1, 2],
            "BEYOND": ["B1", "B2"],
            "City": ["Town", "Town"],
        }
    )
    objs = load_zip_zones(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, ZipZone)
    assert obj.zipcode == "12345"
    assert obj.dest_zone == 1
    assert obj.beyond == "B1"


def test_load_zip_zones_handles_numeric_and_missing_zips() -> None:
    """Numeric ZIPs are normalized and missing rows are ignored."""

    df = pd.DataFrame(
        {
            "Zipcode": [85001.0, float("nan"), 85002],
            "Dest Zone": [1, 2, 3],
            "BEYOND": ["B1", "B2", "B3"],
        }
    )
    objs = load_zip_zones(df)
    assert {o.zipcode for o in objs} == {"85001", "85002"}


def test_load_zip_zones_missing_headers() -> None:
    df = pd.DataFrame({"Zipcode": ["12345"], "Dest Zone": [1]})
    with pytest.raises(ValueError) as exc:
        load_zip_zones(df)
    assert "Missing expected columns" in str(exc.value)


def test_load_zip_zones_transposed_sheet() -> None:
    df = pd.DataFrame(
        [
            ["Zipcode", "Dest Zone", "BEYOND"],
            ["12345", 1, "B1"],
            ["23456", 2, "B2"],
        ]
    )
    objs = load_zip_zones(df)
    assert {o.zipcode for o in objs} == {"12345", "23456"}


def test_load_cost_zones() -> None:
    df = pd.DataFrame({"Concatenate ": ["12"], "Cost Zone": ["C1"], "Ignore": ["x"]})
    objs = load_cost_zones(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, CostZone)
    assert obj.concat == "12"
    assert obj.cost_zone == "C1"


def test_load_cost_zones_handles_floats() -> None:
    """Float values are converted to integer strings."""

    df = pd.DataFrame({"Concatenate": [41.0], "Cost Zone": ["A"]})
    objs = load_cost_zones(df)
    assert [o.concat for o in objs] == ["41"]


def test_load_air_cost_zones() -> None:
    df = pd.DataFrame(
        {
            "zone": ["C1"],
            "min": ["100"],
            "per lb": ["1.0"],
            "weight break": ["50"],
            "extra": ["y"],
        }
    )
    objs = load_air_cost_zones(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, AirCostZone)
    assert obj.zone == "C1"
    assert obj.min_charge == 100
    assert obj.per_lb == 1.0
    assert obj.weight_break == 50


def test_load_air_cost_zones_ignores_missing_rows() -> None:
    df = pd.DataFrame(
        {
            "zone": ["C1", None],
            "min": ["100", None],
            "per lb": ["1.0", None],
            "weight break": ["50", None],
        }
    )
    objs = load_air_cost_zones(df)
    assert len(objs) == 1
    assert objs[0].zone == "C1"


def test_load_beyond_rates() -> None:
    df = pd.DataFrame(
        {
            "zone": ["A", None],
            "Rate": [1.5, 2.0],
            "Up To Miles": [100, 200],
            "unused": [0, 0],
        }
    )
    objs = load_beyond_rates(df)
    assert len(objs) == 1
    obj = objs[0]
    assert isinstance(obj, BeyondRate)
    assert obj.zone == "A"
    assert obj.rate == 1.5
    assert obj.up_to_miles == 100


def test_import_csvs_skips_duplicates(tmp_path, caplog, capsys) -> None:
    data_dir = tmp_path
    pd.DataFrame(
        {"Zipcode": ["11111", "22222"], "Dest Zone": [1, 2], "BEYOND": ["B1", "B2"]}
    ).to_csv(data_dir / "Zipcode_Zones.csv", index=False)
    pd.DataFrame({"Concatenate": [11, 22], "Cost Zone": ["C1", "C2"]}).to_csv(
        data_dir / "cost_zone_table.csv", index=False
    )
    pd.DataFrame(
        {
            "Zone": ["Z1", "Z2"],
            "Min": [1, 2],
            "Per LB": [1.0, 2.0],
            "Weight Break": [1, 2],
        }
    ).to_csv(data_dir / "air_cost_zone.csv", index=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        session = db.session
        session.query(ZipZone).delete()
        session.query(CostZone).delete()
        session.query(AirCostZone).delete()
        session.add_all(
            [
                ZipZone(zipcode="11111", dest_zone=1, beyond="B1"),
                CostZone(concat="11", cost_zone="C1"),
                AirCostZone(zone="Z1", min_charge=1.0, per_lb=1.0, weight_break=1.0),
            ]
        )
        session.commit()

        with caplog.at_level(logging.INFO):
            import_csvs(data_dir)
        stdout = capsys.readouterr().out
        assert "Inserted 1 ZipZone rows" in stdout

        assert session.query(ZipZone).count() == 2
        assert session.query(CostZone).count() == 2
        assert session.query(AirCostZone).count() == 2

        session.query(ZipZone).delete()
        session.query(CostZone).delete()
        session.query(AirCostZone).delete()
        session.commit()

    assert "Inserted ZipZone: 22222" in caplog.text
    assert "Skipped existing ZipZone: 11111" in caplog.text
    assert "Inserted CostZone: 22" in caplog.text
    assert "Skipped existing CostZone: 11" in caplog.text
    assert "Inserted AirCostZone: Z2" in caplog.text
    assert "Skipped existing AirCostZone: Z1" in caplog.text


def test_import_csvs_raises_when_no_new_zips(tmp_path) -> None:
    data_dir = tmp_path
    pd.DataFrame({"Zipcode": ["11111"], "Dest Zone": [1], "BEYOND": ["B1"]}).to_csv(
        data_dir / "Zipcode_Zones.csv", index=False
    )

    app = create_app()
    with app.app_context():
        db.create_all()
        db.session.add(ZipZone(zipcode="11111", dest_zone=1, beyond="B1"))
        db.session.commit()

        with pytest.raises(RuntimeError):
            import_csvs(data_dir)


def test_import_csvs_handles_large_zip_zones(tmp_path) -> None:
    """All ZIP code rows are imported even for large datasets."""

    data_dir = tmp_path
    zips = [f"{i:05d}" for i in range(1200)]
    pd.DataFrame(
        {"Zipcode": zips, "Dest Zone": [1] * len(zips), "BEYOND": ["NO"] * len(zips)}
    ).to_csv(data_dir / "Zipcode_Zones.csv", index=False)

    app = create_app()
    with app.app_context():
        db.create_all()
        ZipZone.query.delete()
        db.session.commit()
        import_csvs(data_dir)
        assert ZipZone.query.count() == len(zips)
