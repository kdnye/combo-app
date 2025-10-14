"""Runtime configuration overrides stored in the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, current_app, has_app_context

from app.models import AppSetting, db


@dataclass
class CachedSetting:
    """In-memory representation of an :class:`AppSetting` row."""

    id: int
    key: str
    raw_value: Optional[str]
    parsed_value: Any
    is_secret: bool
    updated_at: Optional[datetime]


@dataclass
class MailSettings:
    """Mail configuration overrides fetched from the settings cache."""

    server: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None


_SETTINGS_CACHE: Dict[str, CachedSetting] = {}
_APPLIED_CONFIG_KEYS: set[str] = set()
_MAIL_FIELDS = {
    "mail_server": "server",
    "mail_port": "port",
    "mail_use_tls": "use_tls",
    "mail_use_ssl": "use_ssl",
    "mail_username": "username",
    "mail_password": "password",
}


def get_settings_cache() -> Dict[str, CachedSetting]:
    """Return the cached :class:`AppSetting` records indexed by key.

    Returns:
        A shallow copy of the internal cache mapping normalized keys to
        :class:`CachedSetting` instances.

    External dependencies:
        Requires an application context when the cache is cold so it can call
        :func:`reload_overrides`.
    """

    if not _SETTINGS_CACHE and has_app_context():
        reload_overrides()
    return dict(_SETTINGS_CACHE)


def load_mail_settings() -> MailSettings:
    """Return typed mail overrides for the application factory.

    Returns:
        :class:`MailSettings` populated from cached overrides.

    External dependencies:
        Pulls data from the cache maintained by :func:`reload_overrides` and
        therefore requires an active application context on the first call.
    """

    cache = get_settings_cache()
    settings = MailSettings()
    for key, field in _MAIL_FIELDS.items():
        record = cache.get(key)
        if not record:
            continue
        value = record.parsed_value
        if field == "port" and value is not None:
            try:
                setattr(settings, field, int(value))
            except (TypeError, ValueError):
                setattr(settings, field, None)
            continue
        setattr(settings, field, value if value is not None else None)
    return settings


def reload_overrides(app: Optional[Flask] = None) -> Dict[str, CachedSetting]:
    """Refresh the cached settings and apply overrides to ``app.config``.

    Args:
        app: Optional :class:`~flask.Flask` instance. When omitted the helper
            falls back to :func:`flask.current_app`.

    Returns:
        Dictionary mirroring the internal cache after the refresh.

    External dependencies:
        Queries the :class:`AppSetting` table using the SQLAlchemy ``db`` session
        and mutates ``app.config`` with the parsed values.
    """

    target_app = app or current_app._get_current_object()
    context_pushed = False
    ctx = None
    if not has_app_context():
        ctx = target_app.app_context()
        ctx.push()
        context_pushed = True

    try:
        _SETTINGS_CACHE.clear()
        new_applied: set[str] = set()
        for record in AppSetting.query.order_by(AppSetting.key).all():
            parsed = _parse_setting_value(record.key, record.value)
            cached = CachedSetting(
                id=record.id,
                key=record.key,
                raw_value=record.value,
                parsed_value=parsed,
                is_secret=record.is_secret,
                updated_at=record.updated_at,
            )
            _SETTINGS_CACHE[record.key] = cached

            upper_key = record.key.upper()
            if parsed is None:
                continue
            target_app.config[upper_key] = parsed
            new_applied.add(upper_key)

        for removed in _APPLIED_CONFIG_KEYS - new_applied:
            target_app.config.pop(removed, None)

        _APPLIED_CONFIG_KEYS.clear()
        _APPLIED_CONFIG_KEYS.update(new_applied)

        return dict(_SETTINGS_CACHE)
    finally:
        if context_pushed and ctx is not None:
            ctx.pop()


def set_setting(key: str, value: Optional[str], *, is_secret: bool = False) -> None:
    """Create, update, or delete an :class:`AppSetting` row.

    Args:
        key: Setting identifier provided by administrators. Normalized to lower
            case before storage.
        value: Optional string payload. ``None`` or an empty string removes the
            record.
        is_secret: Whether the value should be hidden in administrative UIs.

    External dependencies:
        Uses SQLAlchemy's ``db.session`` to persist changes.
    """

    normalized = (key or "").strip().lower()
    if not normalized:
        raise ValueError("Setting key must not be empty.")

    existing = AppSetting.query.filter_by(key=normalized).one_or_none()
    cleaned_value = value.strip() if value is not None else None
    if cleaned_value == "":
        cleaned_value = None

    if cleaned_value is None:
        if existing:
            db.session.delete(existing)
            _SETTINGS_CACHE.pop(normalized, None)
        return

    if existing is None:
        existing = AppSetting(key=normalized)
        db.session.add(existing)

    existing.value = cleaned_value
    existing.is_secret = bool(is_secret)
    _SETTINGS_CACHE.pop(normalized, None)


def _parse_setting_value(key: str, value: Optional[str]) -> Any:
    """Return a typed configuration value based on ``key`` heuristics.

    Args:
        key: Normalized configuration key stored in the database.
        value: Raw string payload persisted for ``key``.

    Returns:
        Either an ``int``, ``bool``, or stripped string depending on the detected
        key suffix.

    External dependencies:
        Pure helper with no side effects beyond parsing the provided inputs.
    """

    if value is None:
        return None
    text = value.strip()
    if not text:
        return None

    lower_key = key.lower()
    if lower_key.endswith(('_per_hour', '_per_day', '_per_minute', '_per_second', '_limit', '_timeout', '_seconds', '_minutes', '_port')):
        try:
            return int(text)
        except ValueError:
            return text

    if lower_key.startswith("mail_use_") or lower_key.endswith("_enabled"):
        lowered = text.lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False

    return text


__all__ = [
    "CachedSetting",
    "MailSettings",
    "get_settings_cache",
    "load_mail_settings",
    "reload_overrides",
    "set_setting",
]
