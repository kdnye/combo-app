"""rename per_mile to rate in beyond_rates

Revision ID: 4d2f1e8c7b90
Revises: c01ec6a775a4
Create Date: 2025-09-30 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4d2f1e8c7b90"
down_revision: Union[str, Sequence[str], None] = "c01ec6a775a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("beyond_rates", "per_mile", new_column_name="rate")


def downgrade() -> None:
    op.alter_column("beyond_rates", "rate", new_column_name="per_mile")
