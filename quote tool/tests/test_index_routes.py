import pytest
from flask import url_for
from flask_app import create_app
from app.models import db


@pytest.fixture
def app():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_map_and_send_routes_exist(app):
    with app.test_request_context():
        assert url_for("map_view") == "/map"
        assert url_for("send_email_route") == "/send"
