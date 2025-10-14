from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from quote import distance


def test_get_api_key_from_flask_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """API key resolves from Flask app config when available."""
    monkeypatch.setattr(distance, "has_app_context", lambda: True)
    app = SimpleNamespace(config={"GOOGLE_MAPS_API_KEY": "cfg"})
    monkeypatch.setattr(distance, "current_app", app)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "env")
    assert distance._get_api_key() == "cfg"


def test_get_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment variable is used when Flask config lacks API key."""
    monkeypatch.setattr(distance, "has_app_context", lambda: False)
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "env")
    assert distance._get_api_key() == "env"


@pytest.mark.parametrize(
    "input_zip,expected",
    [
        ("12345", "12345,USA"),
        (12345, "12345,USA"),
        ("12 345", "12345,USA"),
        (None, None),
        ("", None),
        ("1234", None),
        ("123456", "12345,USA"),
        ("abcde", None),
    ],
)
def test_sanitize_zip(input_zip: str | int | None, expected: str | None) -> None:
    """Sanitize ZIP strings to "ZIP,USA" or return ``None`` for invalid values."""
    assert distance._sanitize_zip(input_zip) == expected


def test_get_distance_miles_ex_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful distance lookup returns miles and ok=True."""
    monkeypatch.setattr(distance, "_get_api_key", lambda: "key")

    mock_resp = Mock()
    mock_resp.json.return_value = {
        "status": "OK",
        "routes": [{"legs": [{"distance": {"value": 1609}}]}],
    }
    mock_session = Mock()
    mock_session.get.return_value = mock_resp
    monkeypatch.setattr(distance, "_session_with_retries", lambda: mock_session)

    result = distance.get_distance_miles_ex("12345", "67890")
    assert result["ok"] is True
    assert result["miles"] == pytest.approx(1609 / 1609.344)


def test_get_distance_miles_ex_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-OK API response returns error details."""
    monkeypatch.setattr(distance, "_get_api_key", lambda: "key")
    mock_resp = Mock()
    mock_resp.json.return_value = {
        "status": "ZERO_RESULTS",
        "error_message": "No route",
    }
    mock_session = Mock()
    mock_session.get.return_value = mock_resp
    monkeypatch.setattr(distance, "_session_with_retries", lambda: mock_session)

    result = distance.get_distance_miles_ex("12345", "67890")
    assert result["ok"] is False
    assert result["status"] == "ZERO_RESULTS"
    assert result["error"] == "No route"
    assert result["miles"] is None
