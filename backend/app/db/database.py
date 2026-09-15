import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from app.config import settings
from app.db.migrations import run_migrations
from app.utils.logger import logger


def get_db_connection() -> sqlite3.Connection:
    """Returns a configured, WAL-mode SQLite connection with row factory."""
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(
        str(db_path),
        timeout=10.0,
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    conn.execute("PRAGMA busy_timeout=5000;")
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager for scoped database operations with automatic commit/rollback."""
    conn = get_db_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_db() -> None:
    """Initializes the database and runs all pending migrations."""
    logger.info(f"Initializing SQLite database at: {settings.db_path}")
    conn = get_db_connection()
    try:
        run_migrations(conn)
        logger.info("Database initialized and schema verified.")
    finally:
        conn.close()
