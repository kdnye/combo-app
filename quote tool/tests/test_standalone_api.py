import pytest
from types import SimpleNamespace

import standalone_flask_app as api


@pytest.fixture
def client():
    return api.app.test_client()


def test_api_quote_returns_weight_fields(monkeypatch, client):
    fake_quote = SimpleNamespace(
        quote_id="abc123",
        quote_type="Hotshot",
        origin="12345",
        destination="67890",
        weight=50,
        weight_method="Actual",
        actual_weight=50,
        dim_weight=40,
        pieces=2,
        total=100,
    )
    monkeypatch.setattr(api.quote_service, "create_quote", lambda *a, **k: fake_quote)

    resp = client.post(
        "/api/quote",
        json={
            "user_id": 1,
            "user_email": "a@example.com",
            "quote_type": "Hotshot",
            "origin": "12345",
            "destination": "67890",
            "weight": 50,
            "pieces": 2,
            "length": 10,
            "width": 10,
            "height": 10,
        },
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["quote_type"] == "Hotshot"
    assert data["actual_weight"] == 50
    assert data["dim_weight"] == 40
    assert data["pieces"] == 2


def test_api_get_quote_returns_weight_fields(monkeypatch, client):
    fake_quote = SimpleNamespace(
        quote_id="xyz789",
        quote_type="Air",
        origin="12345",
        destination="67890",
        weight=60,
        weight_method="Dimensional",
        actual_weight=50,
        dim_weight=60,
        pieces=1,
        total=120,
        quote_metadata="{}",
    )
    monkeypatch.setattr(api.quote_service, "get_quote", lambda qid: fake_quote if qid == "xyz789" else None)

    resp = client.get("/api/quote/xyz789")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["quote_type"] == "Air"
    assert data["actual_weight"] == 50
    assert data["dim_weight"] == 60
    assert data["pieces"] == 1


def test_api_quote_includes_metadata(monkeypatch, client):
    fake_quote = SimpleNamespace(
        quote_id="abc123",
        quote_type="Hotshot",
        origin="12345",
        destination="67890",
        weight=50,
        weight_method="Actual",
        actual_weight=50,
        dim_weight=40,
        pieces=2,
        total=100,
    )

    def fake_create(*args, **kwargs):
        return fake_quote, {"miles": 150}

    monkeypatch.setattr(api.quote_service, "create_quote", fake_create)

    resp = client.post(
        "/api/quote",
        json={
            "user_id": 1,
            "user_email": "a@example.com",
            "quote_type": "Hotshot",
            "origin": "12345",
            "destination": "67890",
            "weight": 50,
        },
    )

    assert resp.status_code == 201
    data = resp.get_json()
    assert data["metadata"]["miles"] == 150
