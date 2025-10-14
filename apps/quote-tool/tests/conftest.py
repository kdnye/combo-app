"""Pytest fixtures and service stubs for the Quote Tool tests."""

from __future__ import annotations

import os
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Lightweight service stubs
# ---------------------------------------------------------------------------
services_module = types.ModuleType("services")
sys.modules.setdefault("services", services_module)


# services.mail stub -------------------------------------------------------
mail_module = types.ModuleType("services.mail")


class MailRateLimitError(RuntimeError):
    """Exception raised when an outbound mail rate limit is exceeded."""


def enforce_mail_rate_limit(_feature: str, _user: object, _recipient: str) -> None:
    """Placeholder rate-limit enforcement used only in tests."""


def log_email_dispatch(_feature: str, _user: object, _recipient: str) -> None:
    """No-op audit helper for the test environment."""


def validate_sender_domain(sender: str) -> None:
    """Ensure the configured sender matches the allowed domain.

    The real application persists the domain in configuration. For the test
    environment we accept any sender unless ``MAIL_ALLOWED_SENDER_DOMAIN`` is
    set explicitly, in which case the domain portion of ``sender`` must match.
    """

    allowed = os.getenv("MAIL_ALLOWED_SENDER_DOMAIN")
    if not allowed:
        return
    if "@" not in sender:
        raise ValueError("Sender address must include a domain")
    domain = sender.split("@", 1)[1].strip().lower()
    if domain != allowed.strip().lower():
        raise ValueError("Sender domain is not permitted")


def user_has_mail_privileges(user: Optional[object]) -> bool:
    """Return ``True`` for approved employee or super admin accounts."""

    if user is None:
        return False
    role = getattr(user, "role", "")
    if role == "super_admin":
        return True
    if role == "employee" and getattr(user, "employee_approved", False):
        return True
    return False


mail_module.MailRateLimitError = MailRateLimitError
mail_module.enforce_mail_rate_limit = enforce_mail_rate_limit
mail_module.log_email_dispatch = log_email_dispatch
mail_module.validate_sender_domain = validate_sender_domain
mail_module.user_has_mail_privileges = user_has_mail_privileges
sys.modules.setdefault("services.mail", mail_module)


# services.auth_utils stub -------------------------------------------------
auth_module = types.ModuleType("services.auth_utils")


def is_valid_password(candidate: str) -> bool:
    """Accept passwords at least 12 characters with mixed character classes."""

    if len(candidate) < 12:
        return False
    has_lower = any(ch.islower() for ch in candidate)
    has_upper = any(ch.isupper() for ch in candidate)
    has_digit = any(ch.isdigit() for ch in candidate)
    has_symbol = any(not ch.isalnum() for ch in candidate)
    return has_lower and has_upper and (has_digit or has_symbol)


def is_valid_email(address: str) -> bool:
    """Very small email validator used in tests."""

    if not address or "@" not in address:
        return False
    local, _, domain = address.partition("@")
    return bool(local.strip()) and "." in domain


def is_valid_phone(value: str) -> bool:
    """Accept phone numbers containing at least 10 digits."""

    digits = [ch for ch in value if ch.isdigit()]
    return len(digits) >= 10


def create_reset_token(_user_id: int) -> str:  # pragma: no cover - unused helper
    return "TESTTOKEN"


def hash_reset_token(token: str) -> str:
    return token[::-1]


def reset_password_with_token(_token: str, _password: str) -> bool:
    return True


auth_module.is_valid_password = is_valid_password
auth_module.is_valid_email = is_valid_email
auth_module.is_valid_phone = is_valid_phone
auth_module.create_reset_token = create_reset_token
auth_module.hash_reset_token = hash_reset_token
auth_module.reset_password_with_token = reset_password_with_token
sys.modules.setdefault("services.auth_utils", auth_module)


# services.settings stub ---------------------------------------------------
settings_module = types.ModuleType("services.settings")


@dataclass
class MailSettings:
    """Structure mirroring the runtime mail override settings."""

    server: Optional[str] = None
    port: Optional[int] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None


_settings_cache: dict[str, MailSettings] = {}


def load_mail_settings() -> MailSettings:
    """Return cached mail override settings for tests."""

    return _settings_cache.get("mail", MailSettings())


def reload_overrides() -> None:
    """Clear cached override data."""

    _settings_cache.pop("mail", None)


def set_setting(key: str, value: Optional[str], *, is_secret: bool = False) -> None:
    """Persist a mock configuration value."""

    settings = _settings_cache.setdefault("mail", MailSettings())
    if key == "mail_username":
        settings.username = value
    elif key == "mail_password":
        settings.password = value
    elif key == "mail_server":
        settings.server = value
    elif key == "mail_port":
        settings.port = int(value) if value is not None else None
    elif key == "mail_use_tls":
        settings.use_tls = value == "true"
    elif key == "mail_use_ssl":
        settings.use_ssl = value == "true"
    else:
        setattr(settings, key, value)


def get_settings_cache() -> dict[str, MailSettings]:
    """Expose the in-memory overrides for inspection in tests."""

    return _settings_cache


settings_module.MailSettings = MailSettings
settings_module.load_mail_settings = load_mail_settings
settings_module.reload_overrides = reload_overrides
settings_module.set_setting = set_setting
settings_module.get_settings_cache = get_settings_cache
sys.modules.setdefault("services.settings", settings_module)


# services.hotshot_rates stub ----------------------------------------------
hotshot_module = types.ModuleType("services.hotshot_rates")


def get_hotshot_zone_by_miles(miles: float) -> str:
    """Return a fake zone based on distance buckets."""

    if miles >= 300:
        return "X"
    if miles >= 150:
        return "B"
    return "A"


@dataclass
class _Rate:
    per_lb: float
    fuel_pct: float
    min_charge: float
    weight_break: Optional[float]
    per_mile: Optional[float] = None


def get_current_hotshot_rate(zone: str) -> _Rate:
    """Provide deterministic rate data for the tests."""

    zone = zone.upper()
    if zone == "X":
        return _Rate(per_lb=0.0, per_mile=5.2, fuel_pct=0.15, min_charge=100.0, weight_break=300)
    if zone == "B":
        return _Rate(per_lb=1.75, fuel_pct=0.12, min_charge=80.0, weight_break=150)
    return _Rate(per_lb=1.25, fuel_pct=0.1, min_charge=60.0, weight_break=120)


hotshot_module.get_hotshot_zone_by_miles = get_hotshot_zone_by_miles
hotshot_module.get_current_hotshot_rate = get_current_hotshot_rate
sys.modules.setdefault("services.hotshot_rates", hotshot_module)

