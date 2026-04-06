"""
Initialize the EOG Oil Well database.

Creates data/wells.db and all tables defined in src/compiler/schema.py.
Safe to run multiple times — existing tables are left untouched.

Usage:
    python scripts/init_db.py
"""

import sys
from pathlib import Path

# Ensure project root is on the path when running as a script
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.compiler.db import DB_PATH, init_db


def main():
    print(f"Initializing database at: {DB_PATH}")
    summary = init_db()

    if summary:
        print("\nTables created / verified:")
        for table, col_count in summary.items():
            print(f"  {table:30s}  ({col_count} columns)")
    else:
        print("No tables found after initialization — check schema.py.")
        sys.exit(1)

    print(f"\nDatabase ready: {DB_PATH}")


if __name__ == "__main__":
    main()
