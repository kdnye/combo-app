import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pandas as pd

from quote.logic_hotshot import ZONE_X_PER_LB_RATE, ZONE_X_PER_MILE_RATE

ROOT = Path(__file__).resolve().parents[1]


def _create_rate_csvs(directory: Path) -> None:
    """Create CSV files with minimal data for quote generation."""
    pd.DataFrame(
        {"ZIPCODE": ["12345", "67890"], "DEST ZONE": [1, 2], "BEYOND": [None, "B1"]}
    ).to_csv(directory / "Zipcode_Zones.csv", index=False)
    pd.DataFrame({"CONCATENATE": ["12"], "COST ZONE": ["C1"]}).to_csv(
        directory / "cost_zone_table.csv", index=False
    )
    pd.DataFrame(
        {"ZONE": ["C1"], "MIN": [100], "PER LB": [1.0], "WEIGHT BREAK": [50]}
    ).to_csv(directory / "air_cost_zone.csv", index=False)
    pd.DataFrame({"ZONE": ["B1"], "RATE": [20.0], "Up to Miles": [0]}).to_csv(
        directory / "beyond_price.csv", index=False
    )
    pd.DataFrame(
        {
            "Miles": [100],
            "ZONE": ["A"],
            "PER LB": [2.0],
            "MIN": [50],
            "Weight Break": [100],
            "Fuel": [0.1],
        }
    ).to_csv(directory / "Hotshot_Rates.csv", index=False)
    pd.DataFrame({"Liftgate": [50.0]}).to_csv(
        directory / "accessorial_cost.csv", index=False
    )


def test_initialize_database_supports_quote_creation(tmp_path) -> None:
    """init_db seeds rate tables so quotes can be calculated."""
    db_path = tmp_path / "app.db"
    data_dir = tmp_path / "rates"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["RATE_DATA_DIR"] = str(data_dir)

    subprocess.run([sys.executable, "init_db.py"], cwd=ROOT, env=env, check=True)

    conn = sqlite3.connect(db_path)
    try:
        counts = {
            "zip_zones": conn.execute("SELECT COUNT(*) FROM zip_zones").fetchone()[0],
            "cost_zones": conn.execute("SELECT COUNT(*) FROM cost_zones").fetchone()[0],
            "air_cost_zones": conn.execute(
                "SELECT COUNT(*) FROM air_cost_zones"
            ).fetchone()[0],
            "accessorials": conn.execute(
                "SELECT COUNT(*) FROM accessorials"
            ).fetchone()[0],
            "hotshot_rates": conn.execute(
                "SELECT COUNT(*) FROM hotshot_rates"
            ).fetchone()[0],
            "beyond_rates": conn.execute(
                "SELECT COUNT(*) FROM beyond_rates"
            ).fetchone()[0],
        }
        for table, count in counts.items():
            assert count > 0, f"Expected seeded rows in {table}, got {count}"

        zone_row = conn.execute(
            """
            SELECT per_lb, per_mile
            FROM hotshot_rates
            WHERE zone='X'
            ORDER BY miles ASC
            LIMIT 1
            """
        ).fetchone()
        assert zone_row is not None, "Missing fallback hotshot zone X rate"
        assert abs(zone_row[0] - ZONE_X_PER_LB_RATE) < 1e-6
        assert abs(zone_row[1] - ZONE_X_PER_MILE_RATE) < 1e-6
    finally:
        conn.close()

    code = (
        "import quote.logic_hotshot, services.quote as qs;"
        "quote.logic_hotshot.get_distance_miles=lambda o,d:50;"
        "q,_=qs.create_quote(1,'user@example.com','Hotshot','12345','67890',10);"
        "assert q.zone=='A';"
        "assert abs(q.total-55.0)<1e-6;"
        "q2,_=qs.create_quote(1,'user@example.com','Air','12345','67890',60);"
        "assert q2.zone=='12';"
        "assert abs(q2.total-130.0)<1e-6;"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, check=True)
