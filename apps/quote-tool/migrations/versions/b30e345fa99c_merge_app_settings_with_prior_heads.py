"""Merge the ``app_settings`` branch with earlier user management merges."""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "b30e345fa99c"
down_revision: Union[str, Sequence[str], None] = ("7e3b2d1f8c90", "9f2d1c3a4b5e")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Do nothing because this revision only resolves parallel heads.

    Alembic identifies the ``7e3b2d1f8c90_merge_email_dispatch_user_role_and_``
    ``password_tokens`` merge and the ``9f2d1c3a4b5e_add_app_settings_table``
    migration as separate heads. Calling :func:`upgrade` records that both
    revisions now share the current merge revision as a common descendant, which
    allows ``alembic upgrade head`` to run without ambiguity. No schema changes
    are performed.
    """

    # Merge revisions do not apply DDL operations.


def downgrade() -> None:
    """Leave the schema untouched when downgrading past the merge revision.

    Alembic automatically reinstates the independent heads if a downgrade skips
    this revision, so the function intentionally contains no logic.
    """

    # Merge revisions also have no downgrade behavior.
