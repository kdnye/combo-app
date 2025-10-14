"""hash password reset tokens

Revision ID: 5a2d3c4b5e6f
Revises: 2f3b1c9ad4e5
Create Date: 2024-05-10 00:00:00.000000

"""

from __future__ import annotations

import hashlib
import string
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5a2d3c4b5e6f"
down_revision: Union[str, Sequence[str], None] = "2f3b1c9ad4e5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _hash_token(value: str) -> str:
    """Return the SHA-256 digest for ``value``."""

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def upgrade() -> None:
    """Store reset tokens as SHA-256 digests.

    The migration widens the ``password_reset_tokens.token`` column and hashes
    any existing values. Tokens already stored as hex-encoded digests are
    normalized to lowercase to match :func:`hashlib.sha256` output.
    """

    # ``batch_alter_table`` is required for SQLite compatibility because the
    # backend does not support ``ALTER COLUMN`` directly. Alembic will instead
    # create a temporary table with the requested schema changes and copy the
    # data over.
    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(length=64),
            type_=sa.String(length=128),
            existing_nullable=False,
        )

    bind = op.get_bind()
    tokens_table = sa.table(
        "password_reset_tokens",
        sa.column("id", sa.Integer),
        sa.column("token", sa.String),
    )

    hex_chars = set(string.hexdigits)
    result = bind.execute(sa.select(tokens_table.c.id, tokens_table.c.token))
    rows = result.fetchall()
    for token_id, raw_value in rows:
        if not raw_value:
            continue
        token_text = str(raw_value)
        is_hex_digest = len(token_text) == 64 and all(
            char in hex_chars for char in token_text
        )
        if is_hex_digest:
            normalized = token_text.lower()
        else:
            normalized = _hash_token(token_text)
        if normalized != token_text:
            bind.execute(
                tokens_table.update()
                .where(tokens_table.c.id == token_id)
                .values(token=normalized)
            )


def downgrade() -> None:
    """Revert the token column size and invalidate digests."""

    bind = op.get_bind()
    tokens_table = sa.table(
        "password_reset_tokens",
        sa.column("id", sa.Integer),
        sa.column("used", sa.Boolean),
    )
    bind.execute(tokens_table.update().values(used=True))

    with op.batch_alter_table("password_reset_tokens") as batch_op:
        batch_op.alter_column(
            "token",
            existing_type=sa.String(length=128),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
