"""Outbound email helpers and safety checks for the quote tool."""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Deque, DefaultDict, Optional

from flask import current_app

logger = logging.getLogger(__name__)


class MailRateLimitError(RuntimeError):
    """Exception raised when an outbound mail rate limit is exceeded."""


_RateStorage = DefaultDict[str, Deque[datetime]]
_RATE_WINDOWS: dict[str, timedelta] = {
    "user_hour": timedelta(hours=1),
    "user_day": timedelta(days=1),
    "feature_hour": timedelta(hours=1),
    "recipient_day": timedelta(days=1),
}
_RATE_COUNTERS: dict[str, _RateStorage] = {
    name: defaultdict(deque) for name in _RATE_WINDOWS
}


def validate_sender_domain(sender: str) -> None:
    """Ensure the configured sender address belongs to an allowed domain.

    Args:
        sender: Email address configured as the default outbound sender.

    Returns:
        ``None``. The helper raises :class:`ValueError` when validation fails.

    Raises:
        ValueError: When ``sender`` omits an ``@`` symbol or the domain portion
            does not match the policy configured via ``MAIL_ALLOWED_SENDER_DOMAIN``.

    External dependencies:
        Reads ``MAIL_ALLOWED_SENDER_DOMAIN`` from :func:`flask.current_app` and
        environment variables via :func:`current_app.config`.
    """

    allowed = current_app.config.get("MAIL_ALLOWED_SENDER_DOMAIN")
    if allowed is None:
        allowed = current_app.config.get("MAIL_DEFAULT_SENDER")
        if allowed and "@" in allowed:
            allowed = allowed.split("@", 1)[1].strip().lower()
        else:
            allowed = None

    if allowed is None:
        return

    allowed_value = str(allowed).strip().lower()
    if not allowed_value:
        return

    if "@" not in sender:
        raise ValueError("Sender address must include a domain")

    domain = sender.split("@", 1)[1].strip().lower()
    if domain != allowed_value:
        raise ValueError(f"Sender domain '{domain}' is not permitted")


def user_has_mail_privileges(user: Optional[object]) -> bool:
    """Return ``True`` when a user is allowed to send quote-related emails.

    Args:
        user: The current authenticated user or ``None``.

    Returns:
        ``True`` when ``user`` is a super administrator or an approved employee;
        ``False`` otherwise.

    External dependencies:
        Relies on the user object exposing ``role`` and ``employee_approved``
        attributes as defined on :class:`app.models.User`.
    """

    if user is None:
        return False

    role = getattr(user, "role", "") or ""
    if role == "super_admin":
        return True
    if role == "employee" and getattr(user, "employee_approved", False):
        return True
    return False


def enforce_mail_rate_limit(
    feature: str, user: Optional[object], recipient: str
) -> None:
    """Apply per-user, per-feature, and per-recipient mail throttles.

    Args:
        feature: Short label indicating the calling feature (for example,
            ``"quote_email"``).
        user: The authenticated user requesting the send. ``None`` is treated as
            an anonymous caller and is heavily rate limited.
        recipient: Email address of the destination mailbox.

    Raises:
        MailRateLimitError: When any configured rate limit is exceeded.

    External dependencies:
        Consumes configuration from :func:`flask.current_app` including
        ``MAIL_RATE_LIMIT_PER_*`` values established in ``config.Config`` or via
        runtime overrides.
    """

    now = datetime.utcnow()
    normalized_recipient = recipient.strip().lower()
    user_identifier = _resolve_user_identifier(user)
    feature_label = feature.strip().lower() or "general"

    limits = {
        "user_hour": current_app.config.get("MAIL_RATE_LIMIT_PER_USER_PER_HOUR", 10),
        "user_day": current_app.config.get("MAIL_RATE_LIMIT_PER_USER_PER_DAY", 50),
        "feature_hour": current_app.config.get("MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR", 200),
        "recipient_day": current_app.config.get("MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY", 25),
    }

    keys = {
        "user_hour": f"user:{user_identifier}",
        "user_day": f"user:{user_identifier}",
        "feature_hour": f"feature:{feature_label}",
        "recipient_day": f"recipient:{normalized_recipient}",
    }

    for bucket, limit in limits.items():
        if limit is None or limit <= 0:
            continue
        events = _RATE_COUNTERS[bucket][keys[bucket]]
        _prune_expired(events, _RATE_WINDOWS[bucket], now)
        if len(events) >= limit:
            raise MailRateLimitError(
                "Outbound email limit exceeded. Please retry later or contact an administrator."
            )
        events.append(now)


def log_email_dispatch(feature: str, user: Optional[object], recipient: str) -> None:
    """Emit a structured log entry for outbound email activity.

    Args:
        feature: Identifier describing the calling workflow.
        user: The authenticated user initiating the email, if any.
        recipient: Recipient email address.

    Returns:
        ``None``. The helper emits a structured log entry and does not mutate
        the request context.

    External dependencies:
        Uses Python's :mod:`logging` module to emit structured log entries.
    """

    user_identifier = _resolve_user_identifier(user)
    logger.info(
        "mail_dispatch",
        extra={
            "feature": feature,
            "recipient": recipient.strip().lower(),
            "user": user_identifier,
        },
    )


def _resolve_user_identifier(user: Optional[object]) -> str:
    """Return a stable identifier for rate-limiting and logging.

    Args:
        user: Authenticated user instance or ``None``.

    Returns:
        Lowercase identifier derived from ``user.id``, ``user.email``, or the
        class name when neither attribute is available.

    External dependencies:
        Pure helper that only introspects the provided ``user`` object.
    """

    if user is None:
        return "anonymous"
    for attribute in ("id", "email", "username"):
        value = getattr(user, attribute, None)
        if value:
            return str(value).strip().lower()
    return user.__class__.__name__.lower()


def _prune_expired(events: Deque[datetime], window: timedelta, now: datetime) -> None:
    """Remove timestamps older than ``window`` from a deque.

    Args:
        events: Deque of timestamped events for a specific throttle key.
        window: Maximum age retained in ``events``.
        now: Current UTC timestamp.

    Returns:
        ``None``. The helper mutates ``events`` in place.

    External dependencies:
        Operates solely on the provided deque and does not touch global state.
    """

    cutoff = now - window
    while events and events[0] < cutoff:
        events.popleft()


__all__ = [
    "MailRateLimitError",
    "enforce_mail_rate_limit",
    "log_email_dispatch",
    "user_has_mail_privileges",
    "validate_sender_domain",
]
