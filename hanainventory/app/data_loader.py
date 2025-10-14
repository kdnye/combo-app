from __future__ import annotations

from typing import Dict

from .data import BASELINE_INVENTORY, FORMS, ITEMS
from .latest_inventory import LATEST_INVENTORY
from .models import Item, Location, LocationItem, db


def seed_database() -> None:
    """Populate the database with reference data extracted from the README."""
    if Item.query.first():
        # Assume database already seeded.
        return

    items_by_name: Dict[str, Item] = {}
    for item_data in ITEMS:
        item = Item(
            name=item_data['label'],
            expected_total=item_data['expected_total'],
            display_order=item_data['display_order'],
        )
        db.session.add(item)
        items_by_name[item.name] = item

    db.session.flush()

    for form in FORMS:
        if form['code'] not in LATEST_INVENTORY:
            # The training kit and any auxiliary forms are not part of the
            # production dashboard. Skip them during the initial seed.
            continue
        location = Location(
            code=form['code'],
            name=form['code'],
            form_url=form.get('form_url'),
            sheet_name=form['sheet_name'],
        )
        db.session.add(location)
        baseline = BASELINE_INVENTORY.get(form['code'], {})
        latest = LATEST_INVENTORY.get(form['code'], {})

        for item_name, item in items_by_name.items():
            location_item = LocationItem(
                item=item,
                sheet_column=form['item_columns'].get(item_name),
                baseline_quantity=baseline.get(item_name),
                latest_quantity=latest.get(item_name),
            )
            location.items.append(location_item)

    db.session.commit()
