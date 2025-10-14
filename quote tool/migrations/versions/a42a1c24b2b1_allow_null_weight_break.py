"""allow null weight_break

Revision ID: a42a1c24b2b1
Revises: cc740e9e90bc
Create Date: 2025-09-20 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a42a1c24b2b1"
down_revision: Union[str, Sequence[str], None] = "cc740e9e90bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow ``weight_break`` column in ``hotshot_rates`` to be nullable."""
    with op.batch_alter_table("hotshot_rates", schema=None) as batch_op:
        batch_op.alter_column(
            "weight_break",
            existing_type=sa.Float(),
            nullable=True,
        )


def downgrade() -> None:
    """Revert ``weight_break`` column to be non-nullable."""
    with op.batch_alter_table("hotshot_rates", schema=None) as batch_op:
        batch_op.alter_column(
            "weight_break",
            existing_type=sa.Float(),
            nullable=False,
        )
