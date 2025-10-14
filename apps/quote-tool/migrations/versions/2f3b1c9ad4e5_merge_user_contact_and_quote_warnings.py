"""Merge user contact and quote warnings branches.

This migration reconciles the parallel development branches that introduced
`users` contact fields (revision 1c3e84f65d42) and the `quotes.warnings`
column (revision 1bd192a1a2eb). It does not perform any schema changes but
allows Alembic to treat both branches as part of a single linear history.
"""

from typing import Sequence, Union

from alembic import op  # type: ignore
import sqlalchemy as sa  # type: ignore


# revision identifiers, used by Alembic.
revision: str = "2f3b1c9ad4e5"
down_revision: Union[str, Sequence[str], None] = (
    "1c3e84f65d42",
    "1bd192a1a2eb",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op migration that marks both parent revisions as applied."""

    pass


def downgrade() -> None:
    """No-op downgrade because this migration does not alter the schema."""

    pass
