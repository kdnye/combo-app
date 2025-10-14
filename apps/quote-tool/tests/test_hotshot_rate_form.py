import pytest
from flask import Flask

from app.admin import HotshotRateForm


def _base_form_data(**kwargs):
    data = {
        "miles": 100,
        "zone": "A",
        "per_lb": 0.0,
        "per_mile": 0.0,
        "min_charge": 50.0,
        "weight_break": 500.0,
        "fuel_pct": 0.1,
    }
    data.update(kwargs)
    return data


@pytest.fixture
def app() -> Flask:
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "test"
    return app


def test_requires_either_per_lb_or_per_mile(app: Flask) -> None:
    with app.test_request_context():
        form = HotshotRateForm(data=_base_form_data(), meta={"csrf": False})
        assert not form.validate()
        msg = "Either Per LB or Per Mile must be provided and greater than zero."
        assert msg in form.per_lb.errors
        assert msg in form.per_mile.errors


def test_accepts_per_mile_without_per_lb(app: Flask) -> None:
    with app.test_request_context():
        form = HotshotRateForm(
            data=_base_form_data(per_mile=1.5),
            meta={"csrf": False},
        )
        assert form.validate()


def test_accepts_per_lb_without_per_mile(app: Flask) -> None:
    with app.test_request_context():
        form = HotshotRateForm(
            data=_base_form_data(per_lb=1.5),
            meta={"csrf": False},
        )
        assert form.validate()
