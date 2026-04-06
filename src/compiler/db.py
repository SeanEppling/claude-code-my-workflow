"""
Database connection management for the EOG Oil Well Information Compiler.

Usage:
    from src.compiler.db import get_engine, get_connection, init_db

    init_db()                    # Create tables if they don't exist
    with get_connection() as conn:
        result = conn.execute(...)
"""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, inspect, text

from src.compiler.schema import metadata

# Path to the SQLite database file, relative to project root
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = _PROJECT_ROOT / "data" / "wells.db"

_engine = None


def get_engine():
    """Return the SQLAlchemy engine, creating it once and reusing it."""
    global _engine
    if _engine is None:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        _engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
    return _engine


@contextmanager
def get_connection():
    """Context manager that yields an open database connection."""
    engine = get_engine()
    with engine.connect() as conn:
        yield conn


def init_db():
    """
    Create all tables defined in schema.py if they do not already exist.
    Safe to call multiple times (idempotent).

    Returns a dict with table names and their column counts.
    """
    engine = get_engine()
    metadata.create_all(engine)

    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    summary = {t: len(inspector.get_columns(t)) for t in table_names}
    return summary
