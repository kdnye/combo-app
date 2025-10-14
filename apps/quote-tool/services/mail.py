"""Outbound email helpers and safety checks for the Quote Tool."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Optional

from flask import current_app
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from app.models import EmailDispatchLog, db


@dataclass(frozen=True)
class _RateLimitWindow:
    """Represents a configurable rate-limit window."""

    label: str
    limit: int
    interval: timedelta


class MailRateLimitError(RuntimeError):
    """Raised when an outbound email request exceeds configured limits."""


def _now() -> datetime:
    """Return the current UTC timestamp for rate-limit calculations."""

    return datetime.utcnow()


def _normalise_email(value: str) -> str:
    """Return a trimmed, lowercase representation of ``value``.

    Args:
        value: Email address supplied by the caller or stored in the database.

    Returns:
        str: Lowercase string safe for equality comparisons.
    """

    return (value or "").strip().lower()


def _active_windows() -> list[_RateLimitWindow]:
    """Return configured rate-limit windows for outbound email enforcement.

    Returns:
        list[_RateLimitWindow]: Collection of rate-limit policies derived from
        ``current_app.config``.

    External Dependencies:
        * Reads :data:`flask.current_app.config` for ``MAIL_RATE_LIMIT`` values.
    """

    config = current_app.config
    return [
        _RateLimitWindow(
            label="per user per hour",
            limit=int(config.get("MAIL_RATE_LIMIT_PER_USER_PER_HOUR", 0) or 0),
            interval=timedelta(hours=1),
        ),
        _RateLimitWindow(
            label="per user per day",
            limit=int(config.get("MAIL_RATE_LIMIT_PER_USER_PER_DAY", 0) or 0),
            interval=timedelta(days=1),
        ),
        _RateLimitWindow(
            label="per feature per hour",
            limit=int(config.get("MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR", 0) or 0),
            interval=timedelta(hours=1),
        ),
        _RateLimitWindow(
            label="per recipient per day",
            limit=int(config.get("MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY", 0) or 0),
            interval=timedelta(days=1),
        ),
    ]


def _count_dispatches(
    *,
    user_id: Optional[int],
    feature: str,
    recipient: str,
    window: _RateLimitWindow,
) -> int:
    """Return the number of dispatches within ``window`` matching filters.

    Args:
        user_id: Optional database identifier for the requesting user.
        feature: Feature label supplied to :func:`enforce_mail_rate_limit`.
        recipient: Normalised recipient email address.
        window: Rate-limit policy currently being evaluated.

    Returns:
        int: Historical send count that applies to the provided filters.

    External Dependencies:
        * Executes a :mod:`sqlalchemy` query against
          :class:`app.models.EmailDispatchLog`.
    """

    since = _now() - window.interval
    query = db.session.query(func.count(EmailDispatchLog.id)).filter(
        EmailDispatchLog.created_at >= since
    )
    if window.label.startswith("per user") and user_id is not None:
        query = query.filter(EmailDispatchLog.user_id == user_id)
    if window.label == "per feature per hour":
        query = query.filter(EmailDispatchLog.feature == feature)
    if window.label == "per recipient per day":
        query = query.filter(func.lower(EmailDispatchLog.recipient) == recipient)
    return int(query.scalar() or 0)


def enforce_mail_rate_limit(
    feature: str, user: Optional[Any], recipient: str
) -> None:
    """Raise :class:`MailRateLimitError` when the request exceeds policy.

    Args:
        feature: Short label identifying the caller (for example, ``"quote"``).
        user: Authenticated :class:`~app.models.User` requesting the send.
        recipient: Target email address provided by the caller.

    Returns:
        ``None``. The function raises :class:`MailRateLimitError` when a limit is
        exceeded to prevent downstream SMTP dispatch.

    External Dependencies:
        * Queries :class:`EmailDispatchLog` using :mod:`sqlalchemy` to determine
          historical volume.
    """

    normalised_recipient = _normalise_email(recipient)
    user_id = getattr(user, "id", None)

    for window in _active_windows():
        if window.limit <= 0:
            continue

        try:
            count = _count_dispatches(
                user_id=user_id,
                feature=feature,
                recipient=normalised_recipient,
                window=window,
            )
        except SQLAlchemyError as exc:  # pragma: no cover - defensive logging
            current_app.logger.warning(
                "Failed to enforce mail rate limit (%s): %s", window.label, exc
            )
            continue

        if window.label.startswith("per user") and user_id is None:
            continue

        if count >= window.limit:
            raise MailRateLimitError(f"Rate limit exceeded: {window.label}.")


def log_email_dispatch(feature: str, user: Optional[Any], recipient: str) -> None:
    """Persist an audit log entry for a successfully dispatched email.

    Args:
        feature: Feature label responsible for the email send.
        user: Optional :class:`~app.models.User` associated with the dispatch.
        recipient: Recipient email address supplied to :func:`send_email`.

    Returns:
        None. The helper records a new :class:`EmailDispatchLog` row as a side
        effect.

    External Dependencies:
        * Writes to :class:`app.models.EmailDispatchLog` via :data:`db.session`.
    """

    entry = EmailDispatchLog(
        feature=feature,
        recipient=_normalise_email(recipient),
    )
    user_id = getattr(user, "id", None)
    if user_id:
        entry.user_id = user_id

    db.session.add(entry)
    try:
        db.session.commit()
    except SQLAlchemyError as exc:  # pragma: no cover - commit failures are rare
        current_app.logger.error("Failed to commit email dispatch log: %s", exc)
        db.session.rollback()
        raise


def validate_sender_domain(sender: str) -> None:
    """Ensure ``sender`` belongs to the configured allowed domain.

    Args:
        sender: Email address configured as ``MAIL_DEFAULT_SENDER``.

    Returns:
        None. Raises :class:`ValueError` when the sender domain violates policy.

    External Dependencies:
        * Reads :data:`flask.current_app.config['MAIL_ALLOWED_SENDER_DOMAIN']`.
    """

    allowed = (current_app.config.get("MAIL_ALLOWED_SENDER_DOMAIN") or "").strip().lower()
    if not allowed:
        return
    if "@" not in sender:
        raise ValueError("MAIL_DEFAULT_SENDER must include a domain portion")
    domain = sender.split("@", 1)[1].strip().lower()
    if domain != allowed:
        raise ValueError(
            f"Sender domain '{domain}' is not permitted; expected '{allowed}'."
        )


def user_has_mail_privileges(user: Optional[Any]) -> bool:
    """Return ``True`` when ``user`` may send outbound quote emails.

    Args:
        user: Authenticated :class:`~app.models.User` or similar proxy object.

    Returns:
        bool: ``True`` when the caller has either an administrator role, an
        approved employee flag, or an email address within the privileged
        domain configured on the Flask app.

    External Dependencies:
        * Reads :data:`flask.current_app.config['MAIL_PRIVILEGED_DOMAIN']`.
    """

    if user is None:
        return False
    role = getattr(user, "role", "") or ""
    if role == "super_admin" or getattr(user, "is_admin", False):
        return True
    if role == "employee" and getattr(user, "employee_approved", False):
        return True

    email = _normalise_email(getattr(user, "email", ""))
    if not email:
        return False
    privileged_domain = (
        current_app.config.get("MAIL_PRIVILEGED_DOMAIN", "freightservices.net")
        .strip()
        .lower()
    )
    return email.endswith(f"@{privileged_domain}")


__all__ = [
    "MailRateLimitError",
    "enforce_mail_rate_limit",
    "log_email_dispatch",
    "validate_sender_domain",
    "user_has_mail_privileges",
]
