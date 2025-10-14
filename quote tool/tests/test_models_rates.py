import pytest

from db import (
    Base,
    engine,
    Session,
    Accessorial,
    HotshotRate,
    BeyondRate,
    AirCostZone,
    ZipZone,
    CostZone,
)


def test_rate_models_create_records():
    """Ensure new rate tables can be created and records inserted."""
    # Create tables if they do not exist
    Base.metadata.create_all(engine)
    with Session() as session:
        session.query(Accessorial).delete()
        session.query(HotshotRate).delete()
        session.query(BeyondRate).delete()
        session.query(AirCostZone).delete()
        session.query(ZipZone).delete()
        session.query(CostZone).delete()
        session.commit()
        acc = Accessorial(name="LiftgateTest", amount=75.0)
        hs = HotshotRate(
            miles=1,
            zone="A",
            per_lb=0.2,
            min_charge=50.0,
            weight_break=100.0,
            fuel_pct=0.3,
        )
        br = BeyondRate(zone="A", rate=1.5, up_to_miles=10)
        acz = AirCostZone(zone="C1", min_charge=100.0, per_lb=1.0, weight_break=50.0)
        zz = ZipZone(zipcode="12345", dest_zone=1, beyond="NO")
        cz = CostZone(concat="11", cost_zone="C1")
        session.add_all([acc, hs, br, acz, zz, cz])
        session.commit()
        assert acc.id is not None
        assert hs.id is not None
        assert br.id is not None
        assert acz.id is not None
        assert zz.id is not None
        assert cz.id is not None
