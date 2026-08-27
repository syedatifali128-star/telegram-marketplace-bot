from __future__ import annotations

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings
from app.models import Base

# check_same_thread=False is needed because FastAPI/APScheduler will touch
# the SQLite connection from more than one thread. timeout=30 makes SQLite
# wait up to 30s for a lock instead of immediately raising "database is
# locked" — important here because the dashboard and bot run as separate
# processes writing to the same file.
_connect_args = {"check_same_thread": False, "timeout": 30} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=_connect_args, future=True)

if settings.database_url.startswith("sqlite"):
    from sqlalchemy import event

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, connection_record) -> None:
        cursor = dbapi_connection.cursor()
        # WAL lets readers and a writer work concurrently instead of the
        # default mode blocking everyone on a single writer — matters here
        # since dashboard + bot are separate processes on the same file.
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """
    Create all tables if they don't already exist. Safe to call on every
    startup — SQLAlchemy's create_all() is a no-op for existing tables.
    This is what "the application creates/manages the SQLite database
    automatically" (spec section 14) means in practice for V1; a real
    migrations tool (Alembic) can be layered in later without changing
    this call site.
    """
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency: yields a session, always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for use OUTSIDE FastAPI request handlers — bot handlers,
    scheduler jobs, scripts. Commits on success, rolls back on exception.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
