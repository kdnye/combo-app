"""Tests for mail-related configuration helpers."""

from config import _resolve_mail_allowed_sender_domain


def test_resolve_mail_domain_honours_override(monkeypatch):
    """A configured override should be returned in lowercase."""

    monkeypatch.setenv("MAIL_ALLOWED_SENDER_DOMAIN", "Example.COM")
    result = _resolve_mail_allowed_sender_domain("quote@example.net")
    assert result == "example.com"


def test_resolve_mail_domain_defaults_to_sender(monkeypatch):
    """When unset, derive the domain from the default sender address."""

    monkeypatch.delenv("MAIL_ALLOWED_SENDER_DOMAIN", raising=False)
    result = _resolve_mail_allowed_sender_domain("Quote@Sample.org")
    assert result == "sample.org"


def test_resolve_mail_domain_handles_invalid_sender(monkeypatch):
    """Senders without a domain should disable enforcement by returning empty."""

    monkeypatch.delenv("MAIL_ALLOWED_SENDER_DOMAIN", raising=False)
    result = _resolve_mail_allowed_sender_domain("no-at-symbol")
    assert result == ""
