from app.models import LocationItem


def test_location_item_delta_with_complete_data():
    location_item = LocationItem(baseline_quantity=3, latest_quantity=5)

    assert location_item.delta() == 2


def test_location_item_delta_with_missing_values():
    without_latest = LocationItem(baseline_quantity=3, latest_quantity=None)
    without_baseline = LocationItem(baseline_quantity=None, latest_quantity=5)

    assert without_latest.delta() is None
    assert without_baseline.delta() is None
