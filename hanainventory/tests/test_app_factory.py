from app.data import ITEMS
from app.data_loader import seed_database
from app.models import Item, Location, LocationItem
from app.latest_inventory import LATEST_INVENTORY


def test_create_app_seeds_reference_data(app_context):
    expected_locations = len(LATEST_INVENTORY)
    assert Item.query.count() == len(ITEMS)
    assert Location.query.count() == expected_locations
    assert LocationItem.query.count() == len(ITEMS) * expected_locations


def test_seed_database_is_idempotent(app_context):
    original_item_ids = {item.id for item in Item.query.all()}

    seed_database()

    expected_locations = len(LATEST_INVENTORY)
    assert Item.query.count() == len(ITEMS)
    assert Location.query.count() == expected_locations
    assert LocationItem.query.count() == len(ITEMS) * expected_locations
    assert {item.id for item in Item.query.all()} == original_item_ids
