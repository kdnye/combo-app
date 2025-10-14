"""Add contact fields to users

Revision ID: 1c3e84f65d42
Revises: 4d2f1e8c7b90
Create Date: 2024-06-01 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c3e84f65d42"
down_revision: Union[str, Sequence[str], None] = "4d2f1e8c7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add individual contact columns to the users table."""

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("first_name", sa.String(length=80), nullable=True)
        )
        batch_op.add_column(sa.Column("last_name", sa.String(length=80), nullable=True))
        batch_op.add_column(sa.Column("phone", sa.String(length=50), nullable=True))
        batch_op.add_column(
            sa.Column("company_name", sa.String(length=120), nullable=True)
        )
        batch_op.add_column(
            sa.Column("company_phone", sa.String(length=50), nullable=True)
        )


def downgrade() -> None:
    """Remove contact columns from the users table."""

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("company_phone")
        batch_op.drop_column("company_name")
        batch_op.drop_column("phone")
        batch_op.drop_column("last_name")
        batch_op.drop_column("first_name")
