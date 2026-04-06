"""
SQLAlchemy table definitions for the EOG Oil Well Information Compiler.

This module defines the database schema. It is the single source of truth
for table structure — all DB operations reference these definitions.
"""

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    String,
    Table,
)

metadata = MetaData()

wells = Table(
    "wells",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    # Identifiers
    Column("well_id", String(50), unique=True, nullable=False),
    Column("api_number", String(14), unique=True, nullable=True),
    Column("lease_code", String(100), nullable=True),
    # Descriptive
    Column("well_name", String(200), nullable=False),
    Column("operator", String(200), nullable=True),
    Column("status", String(50), nullable=True),
    # Location
    Column("county", String(100), nullable=False),
    Column("state", String(2), nullable=False),
    Column("lat", Float, nullable=True),
    Column("lon", Float, nullable=True),
)
