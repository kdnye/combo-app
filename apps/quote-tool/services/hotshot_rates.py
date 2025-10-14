"""Helper functions for working with hotshot rate tables."""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models import HotshotRate, db


@dataclass(frozen=True)
class HotshotRateSnapshot:
    """Immutable representation of a :class:`HotshotRate` record."""

    zone: str
    miles: int
    per_lb: float
    per_mile: float | None
    min_charge: float
    weight_break: float | None
    fuel_pct: float


def _normalise_zone(zone: str) -> str:
    """Return an upper-case zone label for lookups.

    Args:
        zone: Raw zone string provided by the caller.

    Returns:
        str: Upper-case zone code defaulting to ``"X"`` when blank.

    External Dependencies:
        None.
    """

    return (zone or "").strip().upper() or "X"


@lru_cache(maxsize=128)
def _lookup_zone_by_miles(distance_bucket: int) -> str:
    """Return the hotshot zone covering ``distance_bucket`` miles.

    Args:
        distance_bucket: Rounded distance in miles used for table lookups.

    Returns:
        str: Zone label sourced from :class:`HotshotRate` or ``"X"`` when no
        matching row exists.

    External Dependencies:
        * Executes :func:`sqlalchemy.select` against :class:`HotshotRate` on
          cache misses.
    """

    try:
        candidate = (
            db.session.execute(
                select(HotshotRate.zone)
                .where(HotshotRate.miles >= distance_bucket)
                .order_by(HotshotRate.miles.asc())
            )
            .scalars()
            .first()
        )
    except SQLAlchemyError:  # pragma: no cover - defensive fallback
        return "X"
    return candidate or "X"


@lru_cache(maxsize=32)
def _snapshot_for_zone(zone: str) -> HotshotRateSnapshot:
    """Return the most recent :class:`HotshotRate` row for ``zone``.

    Args:
        zone: Zone identifier to resolve.

    Returns:
        HotshotRateSnapshot: Cached rate details. Falls back to zone ``X`` when
        the requested zone is missing.

    External Dependencies:
        * Executes :func:`sqlalchemy.select` against :class:`HotshotRate` on
          cache misses.
    """

    normalised = _normalise_zone(zone)
    try:
        row = (
            db.session.execute(
                select(
                    HotshotRate.zone,
                    HotshotRate.miles,
                    HotshotRate.per_lb,
                    HotshotRate.per_mile,
                    HotshotRate.min_charge,
                    HotshotRate.weight_break,
                    HotshotRate.fuel_pct,
                )
                .where(HotshotRate.zone == normalised)
                .order_by(HotshotRate.miles.desc())
            )
            .first()
        )
    except SQLAlchemyError:  # pragma: no cover - defensive fallback
        row = None
    if row is None and normalised != "X":
        return _snapshot_for_zone("X")
    if row is None:
        raise LookupError("No hotshot rate data available for zone X.")
    return HotshotRateSnapshot(*row)


def get_hotshot_zone_by_miles(miles: float) -> str:
    """Return the hotshot zone corresponding to ``miles`` of travel.

    Args:
        miles: Distance between origin and destination ZIP codes.

    Returns:
        str: Zone label used by :mod:`quote.logic_hotshot` for pricing.

    External Dependencies:
        * Queries :class:`HotshotRate` via :func:`sqlalchemy.select` when a cache
          miss occurs.
    """

    if miles is None or math.isnan(miles):
        return "X"
    distance_bucket = max(0, int(math.ceil(miles)))
    return _lookup_zone_by_miles(distance_bucket)


def get_current_hotshot_rate(zone: str) -> HotshotRateSnapshot:
    """Return the latest rate information for ``zone``.

    Args:
        zone: Zone label produced by :func:`get_hotshot_zone_by_miles`.

    Returns:
        HotshotRateSnapshot: Frozen view of the rate row. Falls back to zone ``X``
        when the specific zone is missing to keep pricing operational.

    External Dependencies:
        * Queries :class:`HotshotRate` via :func:`sqlalchemy.select` on cache
          misses.
    """

    return _snapshot_for_zone(zone)


def invalidate_hotshot_rate_cache() -> None:
    """Clear cached zone and rate lookups.

    Returns:
        None. Subsequent calls to :func:`get_hotshot_zone_by_miles` and
        :func:`get_current_hotshot_rate` will refresh data from the database.
    """

    _lookup_zone_by_miles.cache_clear()
    _snapshot_for_zone.cache_clear()


__all__ = [
    "HotshotRateSnapshot",
    "get_current_hotshot_rate",
    "get_hotshot_zone_by_miles",
    "invalidate_hotshot_rate_cache",
]
