"""Outbound email helpers for the quote tool."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app
from sqlalchemy import func

from app.models import EmailDispatchLog, User, db

logger = logging.getLogger(__name__)


class MailRateLimitError(RuntimeError):
    """Raised when an outbound email attempt exceeds configured thresholds."""


@dataclass(frozen=True)
class MailRateLimitPolicy:
    """Configuration describing how outbound mail is throttled.

    Attributes:
        per_user_per_hour: Maximum emails a single user may send per hour.
        per_user_per_day: Daily cap for a single user.
        per_feature_per_hour: Hourly limit shared by a feature label.
        per_recipient_per_day: Daily cap per recipient address.
        window_hours: Sliding-window size (hours) for hourly checks.
        window_days: Sliding-window size (days) for daily checks.
    """

    per_user_per_hour: int
    per_user_per_day: int
    per_feature_per_hour: int
    per_recipient_per_day: int
    window_hours: int = 1
    window_days: int = 1


def _policy_from_config() -> MailRateLimitPolicy:
    """Return the active mail throttling policy.

    Returns:
        MailRateLimitPolicy: Structured limits derived from
        :data:`flask.current_app.config`.

    External dependencies:
        * Reads :data:`flask.current_app.config` for limit values.
    """

    cfg = current_app.config
    return MailRateLimitPolicy(
        per_user_per_hour=int(cfg.get("MAIL_RATE_LIMIT_PER_USER_PER_HOUR", 10)),
        per_user_per_day=int(cfg.get("MAIL_RATE_LIMIT_PER_USER_PER_DAY", 50)),
        per_feature_per_hour=int(cfg.get("MAIL_RATE_LIMIT_PER_FEATURE_PER_HOUR", 200)),
        per_recipient_per_day=int(cfg.get("MAIL_RATE_LIMIT_PER_RECIPIENT_PER_DAY", 25)),
    )


def _coerce_user_id(user: Optional[User]) -> Optional[int]:
    """Return ``user.id`` if present without assuming a concrete type.

    Args:
        user: Object that may expose an ``id`` attribute.

    Returns:
        Optional[int]: ``user.id`` when accessible, otherwise ``None``.
    """

    if user is None:
        return None
    return getattr(user, "id", None)


def _count_dispatches(
    *,
    user_id: Optional[int] = None,
    recipient: Optional[str] = None,
    feature: Optional[str] = None,
    since: Optional[datetime] = None,
) -> int:
    """Return the number of email dispatches matching the supplied filters.

    Args:
        user_id: Optional user identifier to scope the query.
        recipient: Email recipient to match exactly.
        feature: Feature label tracked by :class:`EmailDispatchLog`.
        since: Lower bound timestamp limiting results.

    Returns:
        int: Count of matching dispatch rows.

    External dependencies:
        * Executes a SQLAlchemy query against :class:`EmailDispatchLog`.
    """

    query = db.session.query(func.count(EmailDispatchLog.id))
    if user_id is not None:
        query = query.filter(EmailDispatchLog.user_id == user_id)
    if recipient is not None:
        query = query.filter(EmailDispatchLog.recipient == recipient)
    if feature is not None:
        query = query.filter(EmailDispatchLog.feature == feature)
    if since is not None:
        query = query.filter(EmailDispatchLog.created_at >= since)
    return int(query.scalar() or 0)


def validate_sender_domain(sender: str) -> None:
    """Ensure the sender email address aligns with configuration.

    Args:
        sender: Email address configured for outbound messages.

    Raises:
        ValueError: When the domain does not match
            ``MAIL_ALLOWED_SENDER_DOMAIN``.

    External dependencies:
        * Reads :data:`flask.current_app.config` for the allowed domain.
    """

    allowed = (current_app.config.get("MAIL_ALLOWED_SENDER_DOMAIN") or "").strip()
    if not allowed:
        return
    if "@" not in sender:
        raise ValueError("Sender address must include a domain")
    domain = sender.split("@", 1)[1].strip().lower()
    if domain != allowed.lower():
        raise ValueError("Sender domain is not permitted")


def user_has_mail_privileges(user: Optional[User]) -> bool:
    """Return whether ``user`` may dispatch quote emails.

    Args:
        user: Authenticated user requesting to send mail.

    Returns:
        bool: ``True`` when the user meets role or domain requirements.

    External dependencies:
        * Consults :data:`flask.current_app.config` for privileged domains.
    """

    if user is None:
        return False
    role = getattr(user, "role", "") or ""
    if role == "super_admin":
        return True
    if role == "employee" and getattr(user, "employee_approved", False):
        return True
    privileged_domain = (current_app.config.get("MAIL_PRIVILEGED_DOMAIN") or "").lower()
    email = (getattr(user, "email", "") or "").lower()
    if privileged_domain and email.endswith(f"@{privileged_domain}"):
        return True
    return False


def enforce_mail_rate_limit(
    feature: str,
    user: Optional[User],
    recipient: str,
) -> None:
    """Guard outbound email sends against configured thresholds.

    Args:
        feature: Label identifying the caller (e.g. ``"quote_email"``).
        user: Authenticated user requesting the send, if any.
        recipient: Target email address.

    Raises:
        MailRateLimitError: When any configured rate limit has been exceeded.

    External dependencies:
        * Uses :func:`_policy_from_config` to read Flask configuration.
        * Issues SQLAlchemy queries against :class:`EmailDispatchLog`.
    """

    policy = _policy_from_config()
    now = datetime.utcnow()
    user_id = _coerce_user_id(user)

    if user_id is not None and policy.per_user_per_hour:
        hourly = _count_dispatches(
            user_id=user_id, since=now - timedelta(hours=policy.window_hours)
        )
        if hourly >= policy.per_user_per_hour:
            raise MailRateLimitError("Hourly per-user mail limit exceeded")

    if user_id is not None and policy.per_user_per_day:
        daily = _count_dispatches(
            user_id=user_id, since=now - timedelta(days=policy.window_days)
        )
        if daily >= policy.per_user_per_day:
            raise MailRateLimitError("Daily per-user mail limit exceeded")

    if policy.per_feature_per_hour:
        feature_count = _count_dispatches(
            feature=feature, since=now - timedelta(hours=policy.window_hours)
        )
        if feature_count >= policy.per_feature_per_hour:
            raise MailRateLimitError("Hourly feature mail limit exceeded")

    recipient_clean = recipient.strip().lower()
    if policy.per_recipient_per_day and recipient_clean:
        recipient_count = _count_dispatches(
            recipient=recipient_clean,
            since=now - timedelta(days=policy.window_days),
        )
        if recipient_count >= policy.per_recipient_per_day:
            raise MailRateLimitError("Daily recipient mail limit exceeded")


def log_email_dispatch(feature: str, user: Optional[User], recipient: str) -> None:
    """Persist an email dispatch audit record.

    Args:
        feature: Feature label associated with the email send.
        user: User responsible for the dispatch, if authenticated.
        recipient: Recipient email address.

    Returns:
        None. Commits an :class:`EmailDispatchLog` row for auditing.

    External dependencies:
        * Persists state via :data:`app.models.db.session`.
        * Logs failures with :mod:`logging`.
    """

    record = EmailDispatchLog(
        feature=feature,
        recipient=recipient.strip().lower(),
        user_id=_coerce_user_id(user),
        created_at=datetime.utcnow(),
    )
    db.session.add(record)
    try:
        db.session.commit()
    except Exception:  # pragma: no cover - defensive rollback
        db.session.rollback()
        logger.exception("Failed to log email dispatch")
        raise
