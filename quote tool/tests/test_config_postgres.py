"""Tests for PostgreSQL configuration helpers."""

from __future__ import annotations

import pytest

from config import build_postgres_database_uri_from_env


@pytest.mark.usefixtures("monkeypatch")
def test_build_postgres_database_uri_encodes_special_characters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_postgres_database_uri_from_env percent-encodes credentials.

    The password includes characters that would otherwise terminate the URI. The
    helper now uses :func:`urllib.parse.quote_plus` so SQLAlchemy receives a
    valid connection string without manual escaping.
    """

    monkeypatch.setenv("POSTGRES_USER", "quote-tool")
    monkeypatch.setenv("POSTGRES_PASSWORD", "?;Mieb?]@K8pMj+O")
    monkeypatch.setenv("POSTGRES_DB", "quote-tool")
    monkeypatch.setenv("POSTGRES_HOST", "34.132.95.126")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    monkeypatch.delenv("POSTGRES_OPTIONS", raising=False)

    uri = build_postgres_database_uri_from_env()
    assert (
        uri
        == "postgresql+psycopg2://quote-tool:%3F%3BMieb%3F%5D%40K8pMj%2BO@34.132.95.126:5432/quote-tool"
    )


@pytest.mark.usefixtures("monkeypatch")
def test_build_postgres_database_uri_appends_query_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """build_postgres_database_uri_from_env includes query parameters.

    ``POSTGRES_OPTIONS`` accepts a query-string-style value. The helper parses
    the pairs and feeds them back to :func:`urllib.parse.urlencode`, ensuring the
    resulting URI contains the encoded options in the same order.
    """

    monkeypatch.setenv("POSTGRES_USER", "quote_tool")
    monkeypatch.setenv("POSTGRES_PASSWORD", "secret")
    monkeypatch.setenv("POSTGRES_DB", "quote_tool")
    monkeypatch.setenv("POSTGRES_HOST", "db.example.com")
    monkeypatch.setenv("POSTGRES_PORT", "6543")
    monkeypatch.setenv(
        "POSTGRES_OPTIONS", "sslmode=require&application_name=quote-tool"
    )

    uri = build_postgres_database_uri_from_env()
    assert uri.endswith("/quote_tool?sslmode=require&application_name=quote-tool")
