"""Database setup.

DATABASE_URL decides which database we talk to.

- If it is missing (or blank), we use a SQLite file at backend/data/crafts.db.
  That file is gitignored. This is the local default.
- Docker Compose sets it to sqlite:////data/crafts.db, on a named volume.
- On Render it is a Postgres URL, filled in from the database in render.yaml.
  The password in that URL is created by Render. It is not in this repo.

Tables are created on startup. There is no migration tool. If a column
changes during development, delete the local file (or the Render database)
and let startup create it again. seed.py puts the sample crafts back.
Drafts did not add a column. A draft is a crafts row with status "draft".
"""

import logging
import os
import time
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger("crafts")

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "crafts.db"

# The first deploy can try to connect before Postgres is accepting connections.
POSTGRES_CONNECT_TRIES = 5
POSTGRES_CONNECT_WAIT_SECONDS = 3

engine = None
SessionLocal = None


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """Turn a Render Postgres URL into one SQLAlchemy can open.

    Render gives postgresql:// or postgres://. That names the database, not
    the Python driver. We installed psycopg, so the URL has to start with
    postgresql+psycopg://. A SQLite URL is returned unchanged.
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        return normalize_database_url(url)
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{DEFAULT_DB_PATH}"


def _create_tables(url: str) -> None:
    """Create tables. Retry a few times for Postgres; SQLite is local."""
    if url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
        return

    last_error: OperationalError | None = None
    for attempt in range(1, POSTGRES_CONNECT_TRIES + 1):
        try:
            Base.metadata.create_all(bind=engine)
            return
        except OperationalError as exc:
            last_error = exc
            if attempt == POSTGRES_CONNECT_TRIES:
                break
            logger.warning(
                "Database is not ready (attempt %s/%s): %s",
                attempt,
                POSTGRES_CONNECT_TRIES,
                exc,
            )
            time.sleep(POSTGRES_CONNECT_WAIT_SECONDS)
    assert last_error is not None
    raise last_error


def init_db() -> None:
    """Open the database and create tables that are not there yet.

    SQLite refuses a connection used from another thread unless we turn that
    check off. Uvicorn and the test client both do that. Writes are still
    one at a time. SQLite also leaves foreign keys off unless we ask.

    Postgres checks foreign keys itself. pool_pre_ping replaces connections
    that died while the free Render service was asleep.
    """
    global engine, SessionLocal
    url = database_url()
    options: dict = {}
    if url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    else:
        options["pool_pre_ping"] = True
        # One web process. Stay well under the database's connection limit.
        options["pool_size"] = 5
        options["max_overflow"] = 0

    if engine is not None:
        engine.dispose()
    engine = create_engine(url, **options)

    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    # Import models so they are registered on Base before create_all.
    from app import models  # noqa: F401

    _create_tables(url)


def get_db():
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
