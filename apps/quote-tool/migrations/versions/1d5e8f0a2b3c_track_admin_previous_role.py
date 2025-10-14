"""Record previous roles for administrator demotions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.engine import Connection


revision: str = "1d5e8f0a2b3c"
down_revision: Union[str, Sequence[str], None] = "b30e345fa99c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ENUM_NAME = "user_admin_previous_role"


def _enum_type_exists(bind: Connection, enum_name: str) -> bool:
    """Return ``True`` when a PostgreSQL enum type named ``enum_name`` exists.

    Uses ``pg_type`` because SQLAlchemy's ``checkfirst`` does not reliably guard
    against duplicate enum creation on PostgreSQL. See
    https://docs.sqlalchemy.org/en/20/core/type_basics.html for background.
    """

    if bind.dialect.name != "postgresql":
        return False
    result = bind.execute(
        sa.text("SELECT 1 FROM pg_type WHERE typname = :name"), {"name": enum_name}
    )
    return result.first() is not None


def _create_enum_if_missing(bind: Connection, enum_type: sa.Enum) -> None:
    """Create ``enum_type`` when the backing PostgreSQL type is absent."""

    if bind.dialect.name == "postgresql":
        if _enum_type_exists(bind, enum_type.name or ENUM_NAME):
            return
        enum_type.create(bind, checkfirst=False)
        return
    enum_type.create(bind, checkfirst=True)


def _drop_enum_if_present(bind: Connection, enum_type: sa.Enum) -> None:
    """Drop ``enum_type`` only when the backing PostgreSQL type exists."""

    if bind.dialect.name == "postgresql":
        if not _enum_type_exists(bind, enum_type.name or ENUM_NAME):
            return
        enum_type.drop(bind, checkfirst=False)
        return
    enum_type.drop(bind, checkfirst=True)


def upgrade() -> None:
    """Add cached role fields that capture pre-admin state."""

    bind = op.get_bind()
    enum_type = sa.Enum("customer", "employee", name=ENUM_NAME)
    _create_enum_if_missing(bind, enum_type)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "admin_previous_role",
                enum_type,
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "admin_previous_employee_approved",
                sa.Boolean(),
                nullable=True,
            )
        )


def downgrade() -> None:
    """Remove cached admin role fields."""

    bind = op.get_bind()
    enum_type = sa.Enum("customer", "employee", name=ENUM_NAME)

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("admin_previous_employee_approved")
        batch_op.drop_column("admin_previous_role")

    _drop_enum_if_present(bind, enum_type)
