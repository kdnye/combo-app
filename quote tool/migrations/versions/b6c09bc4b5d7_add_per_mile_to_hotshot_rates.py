"""add per_mile to hotshot_rates

Revision ID: b6c09bc4b5d7
Revises: a42a1c24b2b1
Create Date: 2025-09-24 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "b6c09bc4b5d7"
down_revision: Union[str, Sequence[str], None] = "a42a1c24b2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional per-mile rate column to hotshot_rates."""
    with op.batch_alter_table("hotshot_rates", schema=None) as batch_op:
        batch_op.add_column(sa.Column("per_mile", sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove per-mile rate column from hotshot_rates."""
    with op.batch_alter_table("hotshot_rates", schema=None) as batch_op:
        batch_op.drop_column("per_mile")
