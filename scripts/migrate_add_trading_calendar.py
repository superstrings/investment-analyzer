#!/usr/bin/env python3
"""
Migration: Create 'trading_calendar' table.

Stores trading day data for HK/US/A/JP markets.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.database import engine


def migrate():
    """Create trading_calendar table."""
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_name = 'trading_calendar'"
            )
        )
        if result.fetchone():
            print("Table 'trading_calendar' already exists.")
            return

        conn.execute(
            text("""
                CREATE TABLE trading_calendar (
                    id SERIAL PRIMARY KEY,
                    market VARCHAR(10) NOT NULL,
                    trade_date DATE NOT NULL,
                    trade_date_type VARCHAR(20) DEFAULT 'WHOLE',
                    source VARCHAR(20) DEFAULT 'futu',
                    created_at TIMESTAMP DEFAULT NOW(),
                    CONSTRAINT uq_calendar_market_date UNIQUE (market, trade_date)
                )
            """)
        )
        conn.execute(
            text("CREATE INDEX ix_calendar_market ON trading_calendar (market)")
        )
        conn.commit()
        print("Created 'trading_calendar' table.")


if __name__ == "__main__":
    migrate()
