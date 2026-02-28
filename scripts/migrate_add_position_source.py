#!/usr/bin/env python3
"""
Migration: Add 'source' column to positions table.

Distinguishes between Futu-synced and manually added positions.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.database import engine


def migrate():
    """Add source column to positions table."""
    with engine.connect() as conn:
        # Check if column already exists
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'positions' AND column_name = 'source'"
            )
        )
        if result.fetchone():
            print("Column 'source' already exists in positions table.")
            return

        conn.execute(
            text(
                "ALTER TABLE positions ADD COLUMN source VARCHAR(10) DEFAULT 'futu' NOT NULL"
            )
        )
        conn.commit()
        print("Added 'source' column to positions table (default='futu').")


if __name__ == "__main__":
    migrate()
