"""Tests for database initialization utility."""

from __future__ import annotations

import os
import socket
import sqlite3
import subprocess
import sys
from pathlib import Path
from typing import List

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

import init_db
from app.models import User, Quote
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def test_initialize_database_creates_missing_tables(tmp_path) -> None:
    """Ensure that ``init_db`` adds new tables to existing databases."""
    db_path = tmp_path / "init.db"
    data_dir = tmp_path / "rates"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    # Pre-create a database containing only user and quote tables to mimic an
    # older installation.
    engine = create_engine(f"sqlite:///{db_path}")
    User.__table__.create(bind=engine)
    Quote.__table__.create(bind=engine)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["RATE_DATA_DIR"] = str(data_dir)

    result = subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Created tables" in result.stdout

    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    assert {
        "zip_zones",
        "cost_zones",
        "air_cost_zones",
        "accessorials",
        "hotshot_rates",
        "beyond_rates",
    } <= tables

    for table in [
        "zip_zones",
        "cost_zones",
        "air_cost_zones",
        "accessorials",
        "hotshot_rates",
        "beyond_rates",
    ]:
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        assert cur.fetchone()[0] > 0

    counts = {
        table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ["accessorials", "hotshot_rates", "beyond_rates"]
    }
    conn.close()

    second = subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Tables already exist" in second.stdout

    conn = sqlite3.connect(db_path)
    for table, count in counts.items():
        cur = conn.execute(f"SELECT COUNT(*) FROM {table}")
        assert cur.fetchone()[0] == count
    conn.close()


def _create_rate_csvs(directory: Path) -> None:
    """Create minimal CSV files containing a single row for each rate table."""
    pd.DataFrame({"ZIPCODE": ["12345"], "DEST ZONE": [1], "BEYOND": [None]}).to_csv(
        directory / "Zipcode_Zones.csv", index=False
    )
    pd.DataFrame({"CONCATENATE": ["123"], "COST ZONE": ["A1"]}).to_csv(
        directory / "cost_zone_table.csv", index=False
    )
    pd.DataFrame(
        {"ZONE": ["A1"], "MIN": [1], "PER LB": [0.5], "WEIGHT BREAK": [10]}
    ).to_csv(directory / "air_cost_zone.csv", index=False)
    pd.DataFrame({"ZONE": ["A1"], "RATE": [2.0], "Up to Miles": [100]}).to_csv(
        directory / "beyond_price.csv", index=False
    )
    pd.DataFrame(
        {
            "Miles": [100, 0],
            "ZONE": ["A1", "X"],
            "PER LB": [0.1, 0.0],
            "MIN": [50, 0],
            "Weight Break": [1000, 0],
            "Fuel": [0.1, 0.0],
        }
    ).to_csv(directory / "Hotshot_Rates.csv", index=False)
    pd.DataFrame({"Liftgate": [50.0]}).to_csv(
        directory / "accessorial_cost.csv", index=False
    )


def test_initialize_database_patches_hotshot_weight_break(tmp_path: Path) -> None:
    """Legacy hotshot tables with ``NOT NULL`` weight breaks are rebuilt."""

    db_path = tmp_path / "legacy.db"
    data_dir = tmp_path / "rates"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE hotshot_rates (
            id INTEGER PRIMARY KEY,
            miles INTEGER NOT NULL,
            zone VARCHAR(5) NOT NULL,
            per_lb FLOAT NOT NULL,
            min_charge FLOAT NOT NULL,
            weight_break FLOAT NOT NULL,
            fuel_pct FLOAT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["RATE_DATA_DIR"] = str(data_dir)

    subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    conn = sqlite3.connect(db_path)
    cur = conn.execute("PRAGMA table_info(hotshot_rates)")
    notnull = {row[1]: row[3] for row in cur.fetchall()}
    conn.close()
    assert notnull["weight_break"] == 0


def test_initialize_database_patches_hotshot_per_mile(tmp_path: Path) -> None:
    """Legacy hotshot tables missing ``per_mile`` are patched with defaults."""

    db_path = tmp_path / "legacy_per_mile.db"
    data_dir = tmp_path / "rates_per_mile"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE hotshot_rates (
            id INTEGER PRIMARY KEY,
            miles INTEGER NOT NULL,
            zone VARCHAR(5) NOT NULL,
            per_lb FLOAT NOT NULL,
            min_charge FLOAT NOT NULL,
            weight_break FLOAT,
            fuel_pct FLOAT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["RATE_DATA_DIR"] = str(data_dir)

    subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    conn = sqlite3.connect(db_path)
    cur = conn.execute("PRAGMA table_info(hotshot_rates)")
    columns = {row[1] for row in cur.fetchall()}
    assert "per_mile" in columns
    cur = conn.execute("SELECT per_lb, per_mile FROM hotshot_rates WHERE zone='X'")
    assert cur.fetchone() == (5.1, 5.2)
    conn.close()


def test_initialize_database_seeds_admin_user_once(tmp_path) -> None:
    """Create admin user on first run and handle existing user gracefully."""
    db_path = tmp_path / "admin.db"
    data_dir = tmp_path / "rates_admin"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    env["RATE_DATA_DIR"] = str(data_dir)
    env["ADMIN_EMAIL"] = "admin@example.com"
    env["ADMIN_PASSWORD"] = "secret"

    result = subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Default admin user created: admin@example.com" in result.stdout
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] == 1
    conn.close()

    second = subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )
    assert "Admin user already exists: admin@example.com" in second.stdout
    conn = sqlite3.connect(db_path)
    cur = conn.execute("SELECT COUNT(*) FROM users")
    assert cur.fetchone()[0] == 1
    conn.close()


def test_initialize_database_defaults_to_app_db(tmp_path: Path) -> None:
    """init_db uses ``app.db`` when ``DATABASE_URL`` is unset."""
    data_dir = tmp_path / "rates_default"
    data_dir.mkdir()
    _create_rate_csvs(data_dir)

    env = os.environ.copy()
    env.pop("DATABASE_URL", None)
    env["RATE_DATA_DIR"] = str(data_dir)

    db_file = ROOT / "instance" / "app.db"
    if db_file.exists():
        db_file.unlink()

    subprocess.run(
        [sys.executable, "init_db.py"],
        cwd=ROOT,
        env=env,
        check=True,
        text=True,
        capture_output=True,
    )

    assert db_file.exists()
    db_file.unlink()


def test_initialize_database_dns_failure(monkeypatch) -> None:
    """Fallback to ``localhost`` when ``postgres`` cannot be resolved."""

    class DummyEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    captured_urls: list[str] = []
    dummy_engine = DummyEngine()

    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:password@postgres:5432/quote_tool",
    )

    def fake_getaddrinfo(*_args, **_kwargs):
        raise socket.gaierror("name or service not known")

    def fake_create_engine(url: str) -> DummyEngine:
        captured_urls.append(url)
        return dummy_engine

    class DummyInspector:
        def get_table_names(self) -> List[str]:
            return []

    def fake_inspect(_engine: DummyEngine) -> DummyInspector:
        return DummyInspector()

    class BoomApp:
        def app_context(self):
            raise RuntimeError("stop before heavy operations")

    monkeypatch.setattr(init_db.socket, "getaddrinfo", fake_getaddrinfo)
    monkeypatch.setattr(init_db, "create_engine", fake_create_engine)
    monkeypatch.setattr(init_db, "inspect", fake_inspect)
    monkeypatch.setattr(init_db, "create_app", lambda: BoomApp())

    with pytest.raises(RuntimeError, match="stop before heavy operations"):
        init_db.initialize_database()

    assert len(captured_urls) == 1
    fallback_url = make_url(captured_urls[0])
    assert fallback_url.host == "localhost"
    assert fallback_url.username == "postgres"
    assert fallback_url.database == "quote_tool"
    assert os.getenv("POSTGRES_HOST") == "localhost"
    assert dummy_engine.disposed


def test_initialize_database_propagates_operational_error(monkeypatch) -> None:
    """Leave non-DNS ``OperationalError`` exceptions untouched."""

    class DummyEngine:
        def __init__(self) -> None:
            self.disposed = False

        def dispose(self) -> None:
            self.disposed = True

    dummy_engine = DummyEngine()

    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://postgres:password@postgres/quote_tool"
    )

    connection_error = OperationalError(
        "SELECT 1",
        None,
        Exception("could not connect to server: Connection refused"),
    )

    def fake_create_engine(_url: str) -> DummyEngine:
        return dummy_engine

    class DummyInspector:
        def get_table_names(self) -> List[str]:
            raise connection_error

    def fake_inspect(_engine: DummyEngine) -> DummyInspector:
        return DummyInspector()

    monkeypatch.setattr(init_db, "create_engine", fake_create_engine)
    monkeypatch.setattr(init_db, "inspect", fake_inspect)
    monkeypatch.setattr(
        init_db,
        "create_app",
        lambda: pytest.fail("initialize_database should abort before create_app"),
    )

    with pytest.raises(OperationalError) as excinfo:
        init_db.initialize_database()

    assert excinfo.value is connection_error
    assert dummy_engine.disposed


def test_hostname_fallback_sets_localhost(monkeypatch) -> None:
    """Helper rewrites unresolved ``postgres`` hostnames to ``localhost``."""

    monkeypatch.delenv("POSTGRES_HOST", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)

    database_url = "postgresql+psycopg2://user:secret@postgres:5432/example"

    def fake_getaddrinfo(*_args, **_kwargs):
        raise socket.gaierror("name or service not known")

    monkeypatch.setattr(init_db.socket, "getaddrinfo", fake_getaddrinfo)

    rewritten = init_db._ensure_resolvable_hostname(database_url)
    rewritten_url = make_url(rewritten)

    assert rewritten_url.host == "localhost"
    assert rewritten_url.username == "user"
    assert os.getenv("POSTGRES_HOST") == "localhost"
    assert os.getenv("DATABASE_URL") == str(rewritten_url)
