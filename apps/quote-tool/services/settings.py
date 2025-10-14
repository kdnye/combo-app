"""Runtime configuration overrides sourced from the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from flask import Flask, current_app
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import AppSetting, db


@dataclass(frozen=True)
class SettingRecord:
    """Serializable view of an :class:`AppSetting` database row."""

    key: str
    value: Optional[str]
    is_secret: bool
    updated_at: datetime


@dataclass(frozen=True)
class MailSettings:
    """Container for SMTP-related configuration overrides."""

    server: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None


_settings_cache: Dict[str, SettingRecord] = {}
_mail_settings: Optional[MailSettings] = None


def _normalise_key(key: str) -> str:
    """Return a lower-case key suitable for consistent lookups.

    Args:
        key: Raw key provided by the caller or stored in the database.

    Returns:
        str: Trimmed, lower-case representation of ``key``.
    """

    return (key or "").strip().lower()


def _parse_bool(value: Optional[str]) -> Optional[bool]:
    """Convert textual truthy values to :class:`bool` where possible.

    Args:
        value: String representation retrieved from :class:`AppSetting`.

    Returns:
        Optional[bool]: ``True`` or ``False`` for recognised tokens; ``None``
        when the string is blank or cannot be parsed.
    """

    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"true", "1", "yes", "y"}:
        return True
    if lowered in {"false", "0", "no", "n"}:
        return False
    return None


def _build_mail_settings(records: Iterable[SettingRecord]) -> MailSettings:
    """Create :class:`MailSettings` from cached :class:`SettingRecord` items.

    Args:
        records: Iterable containing the latest database snapshot.

    Returns:
        MailSettings: Parsed mail override values with appropriate types.
    """

    mapping = {record.key: record for record in records}

    def _value(key: str) -> Optional[str]:
        stored = mapping.get(key)
        return stored.value if stored else None

    port_value = _value("mail_port")
    try:
        port = int(port_value) if port_value is not None else None
    except ValueError:
        port = None

    return MailSettings(
        server=_value("mail_server"),
        port=port,
        use_tls=_parse_bool(_value("mail_use_tls")),
        use_ssl=_parse_bool(_value("mail_use_ssl")),
        username=_value("mail_username"),
        password=_value("mail_password"),
    )


def _apply_mail_settings(app: Flask, settings: MailSettings) -> None:
    """Update ``app.config`` with overrides stored in ``settings``.

    Args:
        app: Flask application being configured.
        settings: Mail override values calculated by :func:`_build_mail_settings`.

    Returns:
        None. ``app.config`` is mutated as a side effect.
    """

    if settings.server is not None:
        app.config["MAIL_SERVER"] = settings.server
    if settings.port is not None:
        app.config["MAIL_PORT"] = settings.port
    if settings.use_tls is not None:
        app.config["MAIL_USE_TLS"] = settings.use_tls
    if settings.use_ssl is not None:
        app.config["MAIL_USE_SSL"] = settings.use_ssl
    if settings.username is not None:
        app.config["MAIL_USERNAME"] = settings.username
    if settings.password is not None:
        app.config["MAIL_PASSWORD"] = settings.password


def _update_cache(records: Iterable[AppSetting]) -> List[SettingRecord]:
    """Refresh the in-memory caches with ``records`` from the database.

    Args:
        records: Collection of :class:`AppSetting` ORM instances.

    Returns:
        list[SettingRecord]: Serialised snapshot suitable for templates and
        diagnostics.
    """

    global _settings_cache, _mail_settings
    snapshot: Dict[str, SettingRecord] = {}
    for row in records:
        normalised = _normalise_key(row.key)
        record = SettingRecord(
            key=row.key.strip(),
            value=row.value,
            is_secret=row.is_secret,
            updated_at=row.updated_at or datetime.utcnow(),
        )
        snapshot[normalised] = record
    _settings_cache = snapshot
    _mail_settings = _build_mail_settings(snapshot.values())
    return list(snapshot.values())


def get_settings_cache() -> Dict[str, SettingRecord]:
    """Return a copy of the cached application settings.

    Returns:
        dict[str, SettingRecord]: Mapping of setting keys to cached metadata.

    External Dependencies:
        * Calls :func:`reload_overrides` when the cache is empty, which queries
          the database via :mod:`sqlalchemy`.
    """

    if not _settings_cache:
        reload_overrides()
    return dict(_settings_cache)


def load_mail_settings() -> MailSettings:
    """Return SMTP override values pulled from :class:`AppSetting` rows.

    Returns:
        MailSettings: Cached mail overrides, defaulting to empty values when no
        database records are present.
    """

    if _mail_settings is None:
        reload_overrides()
    return _mail_settings or MailSettings()


def reload_overrides(app: Optional[Flask] = None) -> List[SettingRecord]:
    """Reload runtime overrides from the database and apply them to ``app``.

    Args:
        app: Optional Flask application. Defaults to :data:`flask.current_app`.

    Returns:
        list[SettingRecord]: Serialised settings snapshot used for logging and
        UI rendering. Returns an empty list when the database query fails.

    External Dependencies:
        * Executes :func:`sqlalchemy.select` against :class:`AppSetting`.
    """

    target_app = app or current_app
    try:
        rows = db.session.execute(select(AppSetting)).scalars().all()
    except SQLAlchemyError as exc:
        try:
            default_logger = current_app.logger
        except RuntimeError:  # pragma: no cover - outside application context
            default_logger = None
        logger = getattr(target_app, "logger", None) or default_logger
        if logger is not None:
            logger.warning("Failed to load settings: %s", exc)
        return []

    records = _update_cache(rows)
    if target_app:
        for record in records:
            config_key = record.key.upper()
            if record.value is None:
                target_app.config.pop(config_key, None)
            else:
                target_app.config[config_key] = record.value
        _apply_mail_settings(target_app, _mail_settings or MailSettings())
    return records


def set_setting(key: str, value: Optional[str], *, is_secret: bool = False) -> None:
    """Create, update, or delete an :class:`AppSetting` row.

    Args:
        key: Unique identifier for the setting.
        value: New string payload or ``None`` to delete the setting.
        is_secret: Whether the value should be hidden in administrative views.

    Returns:
        None. The ORM session is mutated in-place and callers are responsible
        for committing the transaction.

    External Dependencies:
        * Uses :mod:`sqlalchemy` ORM queries via :data:`db.session`.
    """

    global _mail_settings
    normalised_key = _normalise_key(key)
    existing = AppSetting.query.filter_by(key=normalised_key).one_or_none()
    if value is None:
        if existing:
            db.session.delete(existing)
        _settings_cache.pop(normalised_key, None)
        _mail_settings = None
        return

    if existing is None:
        existing = AppSetting(key=normalised_key)
        db.session.add(existing)
    existing.value = value
    existing.is_secret = bool(is_secret)
    _settings_cache.pop(normalised_key, None)
    _mail_settings = None


def get_settings_cache_snapshot() -> List[SettingRecord]:
    """Return the cached settings as a list for diagnostics and tests.

    Returns:
        list[SettingRecord]: Cached settings ordered by key insertion.

    External Dependencies:
        * Delegates to :func:`get_settings_cache`, which may trigger a database
          query via :func:`reload_overrides`.
    """

    return list(get_settings_cache().values())


__all__ = [
    "MailSettings",
    "SettingRecord",
    "get_settings_cache",
    "get_settings_cache_snapshot",
    "load_mail_settings",
    "reload_overrides",
    "set_setting",
]
