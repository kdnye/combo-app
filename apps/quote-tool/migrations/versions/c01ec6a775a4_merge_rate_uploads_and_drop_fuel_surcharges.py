"""Merge rate uploads and fuel surcharge removal branches.

Revision ID: c01ec6a775a4
Revises: d57c2f94bd7b, f1c2d3e4f5a6
Create Date: 2025-09-15 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


revision: str = "c01ec6a775a4"
down_revision: Union[str, Sequence[str], None] = (
    "d57c2f94bd7b",
    "f1c2d3e4f5a6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op migration to merge divergent heads."""
    pass


def downgrade() -> None:
    """No-op downgrade for merged heads."""
    pass
