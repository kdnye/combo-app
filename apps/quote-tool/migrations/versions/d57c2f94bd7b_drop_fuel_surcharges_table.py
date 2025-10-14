"""drop fuel_surcharges table

Revision ID: d57c2f94bd7b
Revises: b6c09bc4b5d7
Create Date: 2025-10-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d57c2f94bd7b"
down_revision: Union[str, Sequence[str], None] = "b6c09bc4b5d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("fuel_surcharges")


def downgrade() -> None:
    op.create_table(
        "fuel_surcharges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fuel_price", sa.Float(), nullable=False),
        sa.Column("fuel_pct", sa.Float(), nullable=False),
    )
