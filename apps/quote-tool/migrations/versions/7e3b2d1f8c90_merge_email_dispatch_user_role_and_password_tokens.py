"""Merge email dispatch, user role, and password token branches.

Revision ID: 7e3b2d1f8c90
Revises: 1f2e3d4c5b67, 4f9d6f2a9dcb, 5a2d3c4b5e6f
Create Date: 2025-01-14 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op  # noqa: F401
import sqlalchemy as sa  # noqa: F401


# revision identifiers, used by Alembic.
revision: str = "7e3b2d1f8c90"
down_revision: Union[str, Sequence[str], None] = (
    "1f2e3d4c5b67",
    "4f9d6f2a9dcb",
    "5a2d3c4b5e6f",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Do nothing because this revision only merges independent heads.

    The function accepts no parameters and returns ``None``. It simply marks
    the revisions ``1f2e3d4c5b67_add_email_dispatch_log``,
    ``4f9d6f2a9dcb_add_user_role_and_employee_approval``, and
    ``5a2d3c4b5e6f_hash_password_reset_tokens`` as sharing a common descendant
    so Alembic can build a single linear history.
    """

    # No schema changes are required for a merge-only revision.


def downgrade() -> None:
    """Leave the schema untouched when downgrading past the merge.

    This function takes no parameters and returns ``None`` because there is no
    work to undo. Alembic simply reintroduces the independent heads if a
    downgrade skips this merge revision.
    """

    # Merge revisions have no downgrade behavior.
