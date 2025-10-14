"""sync user columns

Revision ID: e8b3451b6e33
Revises: 0f8c1e1f6f3a
Create Date: 2025-09-10 22:02:50.694611

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e8b3451b6e33"
down_revision: Union[str, Sequence[str], None] = "0f8c1e1f6f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Synchronize `users` table with the current SQLAlchemy model."""

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("phone")
        batch_op.drop_column("business_name")
        batch_op.drop_column("business_phone")
        batch_op.drop_column("role")
        batch_op.drop_column("is_approved")
        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=100),
            type_=sa.String(length=120),
            nullable=True,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=100),
            type_=sa.String(length=255),
            nullable=False,
        )


def downgrade() -> None:
    """Revert `users` table to the previous schema."""

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("is_admin")
        batch_op.drop_column("is_active")
        batch_op.add_column(sa.Column("phone", sa.String(length=50)))
        batch_op.add_column(sa.Column("business_name", sa.String(length=100)))
        batch_op.add_column(sa.Column("business_phone", sa.String(length=50)))
        batch_op.add_column(sa.Column("role", sa.String(length=20)))
        batch_op.add_column(sa.Column("is_approved", sa.Boolean()))
        batch_op.alter_column(
            "name",
            existing_type=sa.String(length=120),
            type_=sa.String(length=100),
            nullable=False,
        )
        batch_op.alter_column(
            "email",
            existing_type=sa.String(length=255),
            type_=sa.String(length=100),
            nullable=False,
        )
