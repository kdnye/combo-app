"""add warnings column to quotes

Revision ID: 1bd192a1a2eb
Revises: 4d2f1e8c7b90
Create Date: 2025-09-12 21:22:16.115882

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1bd192a1a2eb"
down_revision: Union[str, Sequence[str], None] = "4d2f1e8c7b90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the ``warnings`` column to the ``quotes`` table.

    This function has no parameters or return value and uses
    :func:`alembic.op.add_column` to alter the schema.
    """
    op.add_column("quotes", sa.Column("warnings", sa.Text(), nullable=True))


def downgrade() -> None:
    """Remove the ``warnings`` column from the ``quotes`` table.

    This function has no parameters or return value and uses
    :func:`alembic.op.drop_column` to revert the schema change.
    """
    op.drop_column("quotes", "warnings")
