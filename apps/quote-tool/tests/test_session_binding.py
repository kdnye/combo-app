import importlib

import pytest


def test_session_rebinds_to_flask_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service queries should use the same engine as the Flask app."""
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")

    import config as config_module

    importlib.reload(config_module)
    import db as db_module

    importlib.reload(db_module)

    from app import create_app

    app = create_app()

    from services import hotshot_rates as hs_service

    importlib.reload(hs_service)

    with app.app_context():
        hs = db_module.HotshotRate(
            miles=0,
            zone="A",
            per_lb=1.0,
            min_charge=1.0,
            weight_break=1.0,
            fuel_pct=0.0,
        )
        db_module.db.session.add(hs)
        db_module.db.session.commit()
        assert hs_service.get_hotshot_zone_by_miles(0) == "A"

    monkeypatch.delenv("DATABASE_URL", raising=False)
    importlib.reload(config_module)
    importlib.reload(db_module)
    importlib.reload(hs_service)
