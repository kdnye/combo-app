"""Runtime configuration overrides stored in the database."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any, Dict, Optional

from flask import Flask, current_app, has_app_context

from app.models import AppSetting, db


@dataclass(frozen=True)
class SettingRecord:
    """Snapshot of a persisted :class:`AppSetting` row.

    Attributes:
        id: Primary key of the database record.
        key: Normalized setting key (lower-case).
        raw_value: Original string stored in the database.
        parsed_value: Normalised value used within the application.
        is_secret: Flag indicating whether the value should be obfuscated.
        updated_at: Timestamp of the last modification, when available.
    """

    id: int
    key: str
    raw_value: Optional[str]
    parsed_value: Optional[Any]
    is_secret: bool
    updated_at: Optional[datetime]


@dataclass(frozen=True)
class MailSettings:
    """Parsed mail-related override values.

    Attributes:
        server: SMTP server hostname.
        port: SMTP port number.
        use_tls: Whether STARTTLS is enabled.
        use_ssl: Whether implicit TLS is enabled.
        username: SMTP username override.
        password: SMTP password override.
    """

    server: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None


_SETTINGS_CACHE: Dict[str, SettingRecord] = {}
_MAIL_CACHE: Optional[MailSettings] = None


def _parse_bool(value: str) -> Optional[bool]:
    """Convert ``value`` to a boolean when possible.

    Args:
        value: Raw string sourced from the database or configuration.

    Returns:
        Optional[bool]: ``True``/``False`` when parsing succeeds, otherwise
        ``None``.
    """
    truthy = {"true", "1", "yes", "y", "on"}
    falsy = {"false", "0", "no", "n", "off"}
    lower = value.strip().lower()
    if lower in truthy:
        return True
    if lower in falsy:
        return False
    return None


def _parse_setting_value(key: str, value: Optional[str]) -> Optional[Any]:
    """Normalise raw :class:`AppSetting` values for caching.

    Args:
        key: Setting key (e.g. ``"mail_port"``).
        value: Raw string stored in the database, or ``None`` when absent.

    Returns:
        Optional[Any]: Parsed representation used in :class:`SettingRecord`.
    """
    if value is None:
        return None
    if key.endswith("_port"):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    if key.endswith("_use_tls") or key.endswith("_use_ssl"):
        result = _parse_bool(value)
        return result
    return value.strip() or None


def _rebuild_mail_cache() -> None:
    """Refresh :data:`_MAIL_CACHE` using overrides and Flask defaults.

    External dependencies:
        * Reads :data:`flask.current_app.config` for default values.
        * Accesses :data:`_SETTINGS_CACHE` populated from the database.
    """
    global _MAIL_CACHE
    cfg = current_app.config if has_app_context() else {}

    def _setting(key: str) -> Optional[Any]:
        record = _SETTINGS_CACHE.get(key)
        if not record:
            return None
        return (
            record.parsed_value if record.parsed_value is not None else record.raw_value
        )

    raw_port = _setting("mail_port")
    if raw_port is None:
        raw_port = cfg.get("MAIL_PORT")
    try:
        port = int(raw_port) if raw_port is not None else None
    except (TypeError, ValueError):
        port = None

    def _bool_with_fallback(key: str, cfg_key: str) -> Optional[bool]:
        value = _setting(key)
        if value is not None:
            if isinstance(value, bool):
                return value
            parsed = _parse_bool(str(value))
            return parsed if parsed is not None else None
        default = cfg.get(cfg_key)
        if isinstance(default, bool):
            return default
        if default is None:
            return None
        return _parse_bool(str(default))

    _MAIL_CACHE = MailSettings(
        server=str(_setting("mail_server") or cfg.get("MAIL_SERVER", "")).strip()
        or None,
        port=port,
        use_tls=_bool_with_fallback("mail_use_tls", "MAIL_USE_TLS"),
        use_ssl=_bool_with_fallback("mail_use_ssl", "MAIL_USE_SSL"),
        username=(
            str(_setting("mail_username") or cfg.get("MAIL_USERNAME", "")).strip()
            or None
        ),
        password=(
            str(_setting("mail_password") or cfg.get("MAIL_PASSWORD", "")).strip()
            or None
        ),
    )


def _ensure_loaded() -> None:
    """Load overrides into :data:`_SETTINGS_CACHE` when needed.

    Raises:
        RuntimeError: If called outside of an application context.
    """
    if _SETTINGS_CACHE:
        return
    if not has_app_context():
        raise RuntimeError("An application context is required to load settings")
    reload_overrides()


def get_settings_cache() -> Dict[str, SettingRecord]:
    """Return a copy of cached overrides keyed by setting name.

    Returns:
        Dict[str, SettingRecord]: Mapping of normalized keys to cached rows.

    External dependencies:
        * Ensures data is loaded via :func:`reload_overrides` and the database.
    """

    _ensure_loaded()
    return dict(_SETTINGS_CACHE)


def reload_overrides(app: Optional[Flask] = None) -> Dict[str, SettingRecord]:
    """Reload :class:`AppSetting` rows and refresh caches.

    Args:
        app: Optional Flask application used to create a context when one is
            not active.

    Returns:
        Dict[str, SettingRecord]: Fresh mapping of keys to cached settings.

    External dependencies:
        * Queries :class:`AppSetting` via SQLAlchemy.
        * Updates module-level caches consumed by other helpers.
    """

    global _SETTINGS_CACHE
    ctx = None
    if app is not None and not has_app_context():
        ctx = app.app_context()
        ctx.push()
    try:
        rows = AppSetting.query.order_by(AppSetting.key).all()
        new_cache: Dict[str, SettingRecord] = {}
        for row in rows:
            new_cache[row.key] = SettingRecord(
                id=row.id,
                key=row.key,
                raw_value=row.value,
                parsed_value=_parse_setting_value(row.key, row.value),
                is_secret=bool(row.is_secret),
                updated_at=row.updated_at,
            )
        _SETTINGS_CACHE = new_cache
        _rebuild_mail_cache()
        return dict(_SETTINGS_CACHE)
    finally:
        if ctx is not None:
            ctx.pop()


def load_mail_settings() -> MailSettings:
    """Return the current mail override values.

    Returns:
        MailSettings: Dataclass combining overrides and defaults.

    External dependencies:
        * Relies on :func:`_rebuild_mail_cache` which reads Flask configuration.
    """

    _ensure_loaded()
    if _MAIL_CACHE is None:
        _rebuild_mail_cache()
    return replace(_MAIL_CACHE)


def set_setting(
    key: str,
    value: Optional[str],
    *,
    is_secret: bool = False,
) -> Optional[SettingRecord]:
    """Create, update, or delete an :class:`AppSetting` row.

    Args:
        key: Setting key to mutate.
        value: New value to store. ``None`` removes the setting.
        is_secret: Marks whether the value should be hidden in the UI.

    Returns:
        Optional[SettingRecord]: Updated cache entry, or ``None`` if deleted.

    External dependencies:
        * Persists changes via :data:`app.models.db.session`.
    """

    if not key:
        raise ValueError("Setting key cannot be empty")
    normalized = key.strip().lower()
    if not has_app_context():
        raise RuntimeError("set_setting requires an application context")

    record = AppSetting.query.filter_by(key=normalized).one_or_none()
    if value is None:
        if record is not None:
            db.session.delete(record)
        db.session.flush()
        _SETTINGS_CACHE.pop(normalized, None)
        _rebuild_mail_cache()
        return None

    if record is None:
        record = AppSetting(key=normalized)
        db.session.add(record)

    record.value = value
    record.is_secret = bool(is_secret)
    db.session.flush()

    stored = SettingRecord(
        id=record.id,
        key=record.key,
        raw_value=record.value,
        parsed_value=_parse_setting_value(record.key, record.value),
        is_secret=record.is_secret,
        updated_at=record.updated_at,
    )
    _SETTINGS_CACHE[normalized] = stored
    _rebuild_mail_cache()
    return stored
