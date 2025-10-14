import pytest
from jinja2 import Environment, TemplateNotFound
from flask_app import create_app
from app.models import db


def test_missing_template_triggers_500(monkeypatch):
    """If a required template is absent, the app should return a 500 page."""
    original = Environment.get_or_select_template

    def fake_get(self, name_or_list, parent=None, globals=None):
        if name_or_list == "index.html":
            raise TemplateNotFound(name_or_list)
        return original(self, name_or_list, parent, globals)

    monkeypatch.setattr(Environment, "get_or_select_template", fake_get)

    app = create_app()
    app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite:///:memory:")
    with app.app_context():
        db.create_all()

    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 500
    assert b"misconfigured" in resp.data.lower()
