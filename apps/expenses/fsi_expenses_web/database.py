"""Database setup utilities for the Expenses web app."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

metadata = MetaData()

expense_reports = Table(
    "expense_reports",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("title", String(255), nullable=False),
    Column("traveler_name", String(255), nullable=False),
    Column("department", String(255), nullable=False),
    Column("trip_start", Date, nullable=False),
    Column("trip_end", Date, nullable=False),
    Column("purpose", Text, nullable=False),
    Column("notes", Text, nullable=False, default=""),
    Column("policy_acknowledged", Boolean, nullable=False, default=False),
    Column(
        "created_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    ),
)

expense_items = Table(
    "expense_items",
    metadata,
    Column("id", Integer, primary_key=True),
    Column(
        "report_id",
        ForeignKey("expense_reports.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column("expense_date", Date, nullable=False),
    Column("category", String(120), nullable=False),
    Column("description", Text, nullable=False),
    Column("merchant", String(255), nullable=False),
    Column("amount_cents", Integer, nullable=False),
    Column("currency", String(8), nullable=False, default="USD"),
    Column("reimbursable", Boolean, nullable=False, default=True),
    Column("receipt_filename", String(255), nullable=True),
    Column(
        "created_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    ),
)


def create_db_engine(database_url: str) -> Engine:
    """Return a SQLAlchemy engine for the provided URL."""

    return create_engine(database_url, future=True)


def init_schema(engine: Engine) -> None:
    """Create database tables if they do not exist."""

    metadata.create_all(engine)


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Context manager that yields a SQLAlchemy :class:`Session`."""

    with Session(engine, future=True) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
