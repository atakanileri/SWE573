"""SQLite setup.

The database file path comes from DATABASE_URL. If that variable is missing
we use backend/data/crafts.db, which is gitignored. Docker sets DATABASE_URL
to a file on the named volume so the posts survive a container restart.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "crafts.db"

engine = None
SessionLocal = None


class Base(DeclarativeBase):
    pass


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        return url
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH}"


def init_db() -> None:
    """Create the engine, turn on SQLite foreign keys, and create tables."""
    global engine, SessionLocal
    url = database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        # The request runs on a different thread from the one that opened the
        # connection (uvicorn, and the test client). SQLite refuses that unless
        # we turn this check off. Writes are still one-at-a-time.
        connect_args["check_same_thread"] = False
    if engine is not None:
        engine.dispose()
    engine = create_engine(url, connect_args=connect_args)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Import models so they are registered on Base before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


def get_db():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
