"""Authentication helper functions shared across blueprints."""

from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Optional, Tuple

from flask import current_app
from sqlalchemy import func

from app.models import PasswordResetToken, User, db

_PASSWORD_RE = re.compile(
    r"^(?:(?=.*[a-z])(?=.*[A-Z])(?:(?=.*\d)|(?=.*\W)).{14,}|.{24,})$"
)
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_password(candidate: str) -> bool:
    """Validate password complexity for registration and resets.

    Args:
        candidate: Plain-text password provided by the user.

    Returns:
        bool: ``True`` when the password meets length and complexity checks.
    """

    if not candidate:
        return False
    return bool(_PASSWORD_RE.match(candidate))


def is_valid_email(address: str) -> bool:
    """Return whether ``address`` resembles a valid email.

    Args:
        address: Email supplied by a user.

    Returns:
        bool: ``True`` when the address matches a minimal regex.
    """

    if not address:
        return False
    return bool(_EMAIL_RE.match(address.strip()))


def is_valid_phone(value: str) -> bool:
    """Return whether ``value`` contains at least ten digits.

    Args:
        value: Phone number captured from a form field.

    Returns:
        bool: ``True`` when the digit count threshold is satisfied.
    """

    digits = [ch for ch in str(value) if ch.isdigit()]
    return len(digits) >= 10


def hash_reset_token(token: str) -> str:
    """Return a SHA-256 digest for ``token``.

    Args:
        token: Raw reset token string.

    Returns:
        str: Hex-encoded SHA-256 digest for storage.

    External dependencies:
        * Uses :mod:`hashlib` for hashing.
    """

    return sha256(token.encode("utf-8")).hexdigest()


def create_reset_token(email: str) -> Tuple[Optional[str], Optional[str]]:
    """Create a password reset token for ``email`` if allowed.

    Args:
        email: Email address requesting the reset.

    Returns:
        tuple: ``(token, error_message)``. ``token`` is ``None`` when creation
        fails. ``error_message`` is populated for user-facing failures.

    External dependencies:
        * Queries :class:`User` and :class:`PasswordResetToken` via SQLAlchemy.
        * Reads :data:`flask.current_app.config` for rate-limit and TTL values.
        * Persists new tokens with :data:`app.models.db.session`.
    """

    normalized = (email or "").strip().lower()
    if not normalized:
        return None, "Email address is required."

    user = User.query.filter(func.lower(User.email) == normalized).first()
    if user is None:
        return None, None

    interval = int(current_app.config.get("AUTH_RESET_TOKEN_MIN_INTERVAL", 900))
    window_start = datetime.utcnow() - timedelta(seconds=interval)
    recent = (
        PasswordResetToken.query.filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.created_at >= window_start,
            PasswordResetToken.used.is_(False),
        )
        .order_by(PasswordResetToken.created_at.desc())
        .first()
    )
    if recent is not None:
        return None, "Reset already requested recently. Please wait."

    raw_token = secrets.token_urlsafe(32)
    hashed = hash_reset_token(raw_token)
    ttl = int(current_app.config.get("AUTH_RESET_TOKEN_TTL", 3600))
    expires_at = datetime.utcnow() + timedelta(seconds=ttl)

    record = PasswordResetToken(
        user_id=user.id,
        token=hashed,
        expires_at=expires_at,
        used=False,
    )
    db.session.add(record)
    db.session.commit()
    return raw_token, None


def reset_password_with_token(token: str, password: str) -> Optional[str]:
    """Update the password for the user associated with ``token``.

    Args:
        token: One-time password reset token supplied by the user.
        password: New password to persist.

    Returns:
        Optional[str]: ``None`` on success or an error message for display.

    External dependencies:
        * Interacts with :class:`PasswordResetToken`, :class:`User`, and
          :data:`app.models.db.session`.
    """

    if not is_valid_password(password):
        return "Password does not meet complexity requirements."

    hashed = hash_reset_token(token)
    reset = PasswordResetToken.query.filter_by(token=hashed, used=False).first()
    if reset is None or reset.expires_at < datetime.utcnow():
        return "Invalid or expired token."

    user = db.session.get(User, reset.user_id)
    if user is None:
        return "Account is no longer available."

    user.set_password(password)
    reset.used = True
    db.session.commit()
    return None
