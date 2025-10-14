"""add password reset tokens

Revision ID: e7ef7795aa3a
Revises: 0f8c1e1f6f3a
Create Date: 2025-09-10 22:01:57.327368

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e7ef7795aa3a"
down_revision: Union[str, Sequence[str], None] = "0f8c1e1f6f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the ``password_reset_tokens`` table."""
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("used", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Drop the ``password_reset_tokens`` table."""
    op.drop_table("password_reset_tokens")
