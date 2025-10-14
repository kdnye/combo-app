"""Air freight quote calculations using database rate tables."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from sqlalchemy.exc import OperationalError

from db import Session, ZipZone, CostZone, AirCostZone, BeyondRate


def get_zip_zone(zipcode: str) -> Optional[ZipZone]:
    """Return the :class:`db.ZipZone` record for a given ZIP code.

    Returns ``None`` if the table is missing or the lookup fails.
    """
    try:
        with Session() as db:
            return db.query(ZipZone).filter_by(zipcode=str(zipcode)).first()
    except OperationalError:
        return None


def get_cost_zone(concat: str) -> Optional[CostZone]:
    """Return the :class:`db.CostZone` mapping for concatenated origin/dest zones.

    Returns ``None`` if the table is missing or the lookup fails.
    """
    try:
        with Session() as db:
            return db.query(CostZone).filter_by(concat=str(concat)).first()
    except OperationalError:
        return None


def get_air_cost_zone(zone: str) -> Optional[AirCostZone]:
    """Return the :class:`db.AirCostZone` record for a given cost zone.

    Returns ``None`` if the table is missing or the lookup fails.
    """
    try:
        with Session() as db:
            return db.query(AirCostZone).filter_by(zone=str(zone)).first()
    except OperationalError:
        return None


def get_beyond_rate(zone: Optional[str]) -> float:
    """Return the beyond charge for a given zone code.

    Returns ``0.0`` if the table is missing, the lookup fails, or ``zone`` is
    falsy.
    """
    if not zone:
        return 0.0
    try:
        with Session() as db:
            record = db.query(BeyondRate).filter_by(zone=str(zone)).first()
            return float(record.rate) if record else 0.0
    except OperationalError:
        return 0.0


def calculate_air_quote(
    origin: str,
    destination: str,
    weight: float,
    accessorial_total: float,
    zip_lookup: Callable[[str], Optional[ZipZone]] = get_zip_zone,
    cost_zone_lookup: Callable[[str], Optional[CostZone]] = get_cost_zone,
    air_cost_lookup: Callable[[str], Optional[AirCostZone]] = get_air_cost_zone,
    beyond_rate_lookup: Callable[[Optional[str]], float] = get_beyond_rate,
) -> Dict[str, Any]:
    """Compute an air quote using rate tables stored in the database.

    If a cost zone mapping is missing for the origin/destination pair, the
    lookup is retried with the zones reversed. This allows tables that only
    define one direction of a route to still resolve correctly.

    Parameters
    ----------
    origin : str
        Origin ZIP code used for the lookup.
    destination : str
        Destination ZIP code used for the lookup.
    weight : float
        Total shipment weight in pounds.
    accessorial_total : float
        Sum of any additional charges to be applied.
    zip_lookup : Callable[[str], Optional[ZipZone]]
        Lookup function for retrieving :class:`db.ZipZone` records.
    cost_zone_lookup : Callable[[str], Optional[CostZone]]
        Function retrieving :class:`db.CostZone` mappings.
    air_cost_lookup : Callable[[str], Optional[AirCostZone]]
        Function retrieving :class:`db.AirCostZone` rate records.
    beyond_rate_lookup : Callable[[Optional[str]], float]
        Function retrieving beyond charges from :class:`db.BeyondRate`.

    Returns
    -------
    Dict[str, Any]
        Quote details or an error structure when validation fails.
    """

    def _error_result(msg: str) -> Dict[str, Any]:
        return {
            "zone": None,
            "quote_total": 0,
            "min_charge": None,
            "per_lb": None,
            "weight_break": None,
            "origin_beyond": None,
            "dest_beyond": None,
            "origin_charge": 0,
            "dest_charge": 0,
            "beyond_total": 0,
            "error": msg,
        }

    origin_row = zip_lookup(str(origin))
    if origin_row is None:
        return _error_result(f"Origin ZIP code {origin} not found")
    if not hasattr(origin_row, "dest_zone") or origin_row.dest_zone is None:
        return _error_result(f"Origin ZIP code {origin} missing dest_zone")
    if not hasattr(origin_row, "beyond"):
        return _error_result(f"Origin ZIP code {origin} missing beyond")

    dest_row = zip_lookup(str(destination))
    if dest_row is None:
        return _error_result(f"Destination ZIP code {destination} not found")
    if not hasattr(dest_row, "dest_zone") or dest_row.dest_zone is None:
        return _error_result(f"Destination ZIP code {destination} missing dest_zone")
    if not hasattr(dest_row, "beyond"):
        return _error_result(f"Destination ZIP code {destination} missing beyond")

    orig_zone = int(origin_row.dest_zone)
    dest_zone = int(dest_row.dest_zone)
    concat = f"{orig_zone}{dest_zone}"

    cost_zone_row = cost_zone_lookup(concat)
    if cost_zone_row is None:
        reverse_concat = f"{dest_zone}{orig_zone}"
        cost_zone_row = cost_zone_lookup(reverse_concat)
        if cost_zone_row is None:
            return _error_result(
                f"Cost zone not found for concatenated zone {concat} or {reverse_concat}"
            )
    cost_zone = cost_zone_row.cost_zone

    air_cost_row = air_cost_lookup(cost_zone)
    if air_cost_row is None:
        return _error_result(f"Air cost zone {cost_zone} not found")

    min_charge = float(air_cost_row.min_charge)
    per_lb = float(air_cost_row.per_lb)
    weight_break = float(air_cost_row.weight_break)

    if weight > weight_break:
        base = ((weight - weight_break) * per_lb) + min_charge
    else:
        base = min_charge

    def _parse_beyond(value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        val = str(value).strip().upper()
        if val in ("", "N/A", "NO", "NONE", "NAN"):
            return None
        return val.split()[-1]

    origin_beyond = _parse_beyond(origin_row.beyond)
    dest_beyond = _parse_beyond(dest_row.beyond)

    origin_charge = beyond_rate_lookup(origin_beyond)
    dest_charge = beyond_rate_lookup(dest_beyond)
    beyond_total = origin_charge + dest_charge

    quote_total = base + accessorial_total + beyond_total

    return {
        "zone": concat,
        "quote_total": quote_total,
        "min_charge": min_charge,
        "per_lb": per_lb,
        "weight_break": weight_break,
        "origin_beyond": origin_beyond,
        "dest_beyond": dest_beyond,
        "origin_charge": origin_charge,
        "dest_charge": dest_charge,
        "beyond_total": beyond_total,
        "error": None,
    }
