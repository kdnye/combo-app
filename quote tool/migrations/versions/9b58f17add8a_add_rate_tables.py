"""add rate tables

Revision ID: 9b58f17add8a
Revises: 4c6faa67f3c2
Create Date: 2025-08-19 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "9b58f17add8a"
down_revision: Union[str, Sequence[str], None] = "4c6faa67f3c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accessorials",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False, unique=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column(
            "is_percentage", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_table(
        "hotshot_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("miles", sa.Integer(), nullable=False),
        sa.Column("zone", sa.String(length=5), nullable=False),
        sa.Column("per_lb", sa.Float(), nullable=False),
        sa.Column("min_charge", sa.Float(), nullable=False),
        sa.Column("weight_break", sa.Float(), nullable=False),
        sa.Column("fuel_pct", sa.Float(), nullable=False),
    )
    op.create_table(
        "fuel_surcharges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("fuel_price", sa.Float(), nullable=False),
        sa.Column("fuel_pct", sa.Float(), nullable=False),
    )
    op.create_table(
        "beyond_rates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("zone", sa.String(length=5), nullable=False),
        sa.Column("per_mile", sa.Float(), nullable=False),
        sa.Column("up_to_miles", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("beyond_rates")
    op.drop_table("fuel_surcharges")
    op.drop_table("hotshot_rates")
    op.drop_table("accessorials")
