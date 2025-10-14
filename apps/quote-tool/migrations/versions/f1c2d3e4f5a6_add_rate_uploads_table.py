"""add rate uploads table

Revision ID: f1c2d3e4f5a6
Revises: e8b3451b6e33
Create Date: 2024-06-06 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "e8b3451b6e33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rate_uploads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("table_name", sa.String(length=50), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rate_uploads")
