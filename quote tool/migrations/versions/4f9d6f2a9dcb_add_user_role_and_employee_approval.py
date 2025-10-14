"""add user role and employee approval

Revision ID: 4f9d6f2a9dcb
Revises: e8b3451b6e33
Create Date: 2024-03-16 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4f9d6f2a9dcb"
down_revision: Union[str, Sequence[str], None] = "e8b3451b6e33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add role and employee approval columns to the users table."""

    role_enum = sa.Enum("customer", "employee", "super_admin", name="user_role")
    bind = op.get_bind()
    role_enum.create(bind, checkfirst=True)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "role",
                role_enum,
                nullable=False,
                server_default="customer",
            )
        )
        batch_op.add_column(
            sa.Column(
                "employee_approved",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

    users_table = sa.table(
        "users",
        sa.column("is_admin", sa.Boolean()),
        sa.column("role", sa.String(length=20)),
        sa.column("employee_approved", sa.Boolean()),
    )

    op.execute(
        users_table.update()
        .where(users_table.c.role.is_(None))
        .values(role="customer", employee_approved=False)
    )

    op.execute(
        users_table.update()
        .where(users_table.c.is_admin.is_(True))
        .values(role="super_admin", employee_approved=True)
    )


def downgrade() -> None:
    """Remove role and employee approval columns."""

    role_enum = sa.Enum("customer", "employee", "super_admin", name="user_role")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("employee_approved")
        batch_op.drop_column("role")

    bind = op.get_bind()
    role_enum.drop(bind, checkfirst=True)
