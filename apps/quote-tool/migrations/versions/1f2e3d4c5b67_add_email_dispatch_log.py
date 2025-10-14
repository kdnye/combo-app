"""Add email_dispatch_log table for tracking outbound emails."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "1f2e3d4c5b67"
down_revision: Union[str, Sequence[str], None] = "e8b3451b6e33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the email_dispatch_log audit table."""

    op.create_table(
        "email_dispatch_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("feature", sa.String(length=50), nullable=False),
        sa.Column("recipient", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_email_dispatch_log_user_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_email_dispatch_log_feature",
        "email_dispatch_log",
        ["feature"],
    )
    op.create_index(
        "ix_email_dispatch_log_user_id",
        "email_dispatch_log",
        ["user_id"],
    )
    op.create_index(
        "ix_email_dispatch_log_recipient",
        "email_dispatch_log",
        ["recipient"],
    )


def downgrade() -> None:
    """Drop the email_dispatch_log audit table."""

    op.drop_index("ix_email_dispatch_log_recipient", table_name="email_dispatch_log")
    op.drop_index("ix_email_dispatch_log_user_id", table_name="email_dispatch_log")
    op.drop_index("ix_email_dispatch_log_feature", table_name="email_dispatch_log")
    op.drop_table("email_dispatch_log")
