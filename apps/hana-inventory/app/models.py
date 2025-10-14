from __future__ import annotations

from typing import Optional

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


class Location(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False)
    name = db.Column(db.String(128), nullable=False)
    form_url = db.Column(db.String(512))
    sheet_name = db.Column(db.String(128))

    items = db.relationship(
        "LocationItem",
        back_populates="location",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Location {self.code}>"


class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), unique=True, nullable=False)
    expected_total = db.Column(db.Float)
    display_order = db.Column(db.Integer, nullable=False, default=0)

    locations = db.relationship("LocationItem", back_populates="item")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<Item {self.name}>"


class LocationItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey("location.id"), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey("item.id"), nullable=False)
    sheet_column = db.Column(db.String(8))
    baseline_quantity = db.Column(db.Float)
    latest_quantity = db.Column(db.Float)

    location = db.relationship("Location", back_populates="items")
    item = db.relationship("Item", back_populates="locations")

    __table_args__ = (
        db.UniqueConstraint("location_id", "item_id", name="uq_location_item"),
    )

    def delta(self) -> Optional[float]:
        if self.latest_quantity is None or self.baseline_quantity is None:
            return None
        return self.latest_quantity - self.baseline_quantity

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<LocationItem {self.location.code} - {self.item.name}>"
