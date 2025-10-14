import os
import sqlite3
import subprocess
import sys
import importlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_script(script: str, env: dict) -> None:
    """Execute a maintenance script in a subprocess."""
    subprocess.run([sys.executable, script], cwd=REPO_ROOT, check=True, env=env)


def test_migrate_quotes_adds_columns_and_populates(tmp_path) -> None:
    """Ensure migrate_quotes adds missing columns and populates data."""
    db_path = tmp_path / "mig.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE quotes (id INTEGER PRIMARY KEY, weight REAL)")
    conn.execute("INSERT INTO quotes (weight) VALUES (?)", (123.0,))
    conn.commit()
    conn.close()
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    _run_script("migrate_quotes.py", env)
    conn = sqlite3.connect(db_path)
    columns = {row[1] for row in conn.execute("PRAGMA table_info(quotes)")}
    assert {"quote_id", "weight_method"}.issubset(columns)
    quote_id, weight_method = conn.execute(
        "SELECT quote_id, weight_method FROM quotes"
    ).fetchone()
    assert quote_id
    assert weight_method == "actual"
    conn.close()


def test_run_app_exposes_flask_app() -> None:
    """run_app should expose the same Flask app as flask_app."""
    run_app_module = importlib.import_module("run_app")
    flask_app_module = importlib.import_module("flask_app")
    assert run_app_module.app is flask_app_module.app
