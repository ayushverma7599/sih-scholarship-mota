"""Database session + engine setup.

Supports SQLite (default, zero-setup) and PostgreSQL via DATABASE_URL.
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    # Needed for SQLite when used across FastAPI's threadpool.
    _connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models so they register on Base.metadata."""
    from app import models  # noqa: F401  (populates metadata)

    Base.metadata.create_all(bind=engine)
