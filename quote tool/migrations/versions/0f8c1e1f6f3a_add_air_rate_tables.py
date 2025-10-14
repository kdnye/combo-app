"""add air rate tables

Revision ID: 0f8c1e1f6f3a
Revises: 9b58f17add8a
Create Date: 2024-05-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0f8c1e1f6f3a"
down_revision: Union[str, Sequence[str], None] = "9b58f17add8a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "zip_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("zipcode", sa.String(length=10), nullable=False, unique=True),
        sa.Column("dest_zone", sa.Integer(), nullable=False),
        sa.Column("beyond", sa.String(length=20), nullable=True),
    )
    op.create_table(
        "cost_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("concat", sa.String(length=5), nullable=False, unique=True),
        sa.Column("cost_zone", sa.String(length=5), nullable=False),
    )
    op.create_table(
        "air_cost_zones",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("zone", sa.String(length=5), nullable=False, unique=True),
        sa.Column("min_charge", sa.Float(), nullable=False),
        sa.Column("per_lb", sa.Float(), nullable=False),
        sa.Column("weight_break", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("air_cost_zones")
    op.drop_table("cost_zones")
    op.drop_table("zip_zones")
