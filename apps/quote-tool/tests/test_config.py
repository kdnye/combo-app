"""Configuration helper tests for the Quote Tool application."""

from __future__ import annotations

import os

from config import _resolve_mail_allowed_sender_domain, _resolve_ratelimit_storage_uri, _resolve_secret_key


def test_resolve_secret_key_prefers_env(monkeypatch):
    """SECRET_KEY should respect the environment override."""

    monkeypatch.setenv("SECRET_KEY", "override-key")
    monkeypatch.delenv("SECRET_KEY_FILE", raising=False)
    assert _resolve_secret_key() == "override-key"


def test_resolve_secret_key_generates_ephemeral(monkeypatch):
    """When no env vars exist the helper should create an ephemeral key."""

    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("SECRET_KEY_FILE", raising=False)
    monkeypatch.setattr(os, "getenv", lambda key, default=None: default)
    key = _resolve_secret_key()
    assert isinstance(key, str)
    assert len(key) >= 32


def test_resolve_mail_allowed_sender_domain(monkeypatch):
    """MAIL_ALLOWED_SENDER_DOMAIN should default to the sender domain."""

    monkeypatch.delenv("MAIL_ALLOWED_SENDER_DOMAIN", raising=False)
    assert _resolve_mail_allowed_sender_domain("Quote@Example.com") == "example.com"


def test_resolve_mail_allowed_sender_domain_override(monkeypatch):
    """Explicit overrides should be normalised to lowercase."""

    monkeypatch.setenv("MAIL_ALLOWED_SENDER_DOMAIN", "FREIGHTSERVICES.NET")
    assert _resolve_mail_allowed_sender_domain("Quote@Example.com") == "freightservices.net"


def test_resolve_ratelimit_storage_uri_prefers_env(monkeypatch):
    """RATELIMIT_STORAGE_URI should honour the environment when provided."""

    monkeypatch.setenv("RATELIMIT_STORAGE_URI", "redis://cache:6379/9")
    assert _resolve_ratelimit_storage_uri() == "redis://cache:6379/9"


def test_resolve_ratelimit_storage_uri_defaults_to_memory(monkeypatch):
    """Without an override the helper should default to in-memory storage."""

    monkeypatch.delenv("RATELIMIT_STORAGE_URI", raising=False)
    monkeypatch.delenv("COMPOSE_PROFILES", raising=False)
    assert _resolve_ratelimit_storage_uri() == "memory://"

