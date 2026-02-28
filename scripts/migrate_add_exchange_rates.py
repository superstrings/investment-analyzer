#!/usr/bin/env python3
"""
Migration: Create 'exchange_rates' table with initial fallback values.

Stores currency-to-CNY exchange rates for portfolio valuation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.database import engine


def migrate():
    """Create exchange_rates table and insert initial fallback values."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = 'exchange_rates'"
            )
        )
        if result.fetchone():
            print("Table 'exchange_rates' already exists.")
            return

        conn.execute(
            text("""
                CREATE TABLE exchange_rates (
                    id SERIAL PRIMARY KEY,
                    currency VARCHAR(10) NOT NULL UNIQUE,
                    rate_to_cny NUMERIC(12, 6) NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                )
            """)
        )

        # Insert initial fallback values
        conn.execute(
            text("""
                INSERT INTO exchange_rates (currency, rate_to_cny)
                VALUES
                    ('USD', 7.250000),
                    ('HKD', 0.930000),
                    ('JPY', 0.048000)
            """)
        )

        conn.commit()
        print("Created 'exchange_rates' table with initial fallback values.")


if __name__ == "__main__":
    migrate()
