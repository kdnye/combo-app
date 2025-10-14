"""Merge password reset and user column sync migrations.

Revision ID: cc740e9e90bc
Revises: e7ef7795aa3a, e8b3451b6e33
Create Date: 2025-09-11 16:18:04.143681
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "cc740e9e90bc"
down_revision: Union[str, Sequence[str], None] = (
    "e7ef7795aa3a",
    "e8b3451b6e33",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op migration to merge divergent heads."""
    pass


def downgrade() -> None:
    """No-op downgrade for merged heads."""
    pass
