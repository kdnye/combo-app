"""Database-backed helpers for hotshot rate lookups."""

from __future__ import annotations

from math import ceil

from sqlalchemy import select

from app.models import HotshotRate, db


def get_hotshot_zone_by_miles(miles: float) -> str:
    """Return the configured zone for ``miles`` travelled.

    Args:
        miles: Distance between origin and destination.

    Returns:
        str: Hotshot zone label (for example ``"A"`` or ``"X"``).

    External dependencies:
        * Executes a SQLAlchemy query against :class:`HotshotRate`.
    """

    normalized = max(float(miles or 0.0), 0.0)
    target = int(ceil(normalized))
    statement = (
        select(HotshotRate.zone)
        .where(HotshotRate.miles >= target)
        .order_by(HotshotRate.miles.asc())
        .limit(1)
    )
    zone = db.session.execute(statement).scalars().first()
    if zone:
        return str(zone)
    fallback = (
        db.session.execute(
            select(HotshotRate.zone).order_by(HotshotRate.miles.desc()).limit(1)
        )
        .scalars()
        .first()
    )
    return str(fallback or "A")


def get_current_hotshot_rate(zone: str) -> HotshotRate:
    """Return the most recent :class:`HotshotRate` row for ``zone``.

    Args:
        zone: Hotshot zone identifier resolved from mileage.

    Returns:
        HotshotRate: Database record containing pricing details.

    Raises:
        LookupError: If no matching zone data exists.

    External dependencies:
        * Queries :class:`HotshotRate` using SQLAlchemy.
    """

    normalized = (zone or "").strip().upper()
    if not normalized:
        raise LookupError("Zone is required")
    statement = (
        select(HotshotRate)
        .where(HotshotRate.zone == normalized)
        .order_by(HotshotRate.miles.desc())
        .limit(1)
    )
    record = db.session.execute(statement).scalars().first()
    if record is None:
        raise LookupError(f"No hotshot rate found for zone {normalized!r}")
    return record
