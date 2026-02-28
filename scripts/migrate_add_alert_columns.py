#!/usr/bin/env python3
"""
Migration: Add stop_loss_price and take_profit_price columns to price_alerts.

Supports new alert types: STOP_LOSS, TAKE_PROFIT, OCO.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from db.database import engine


def migrate():
    """Add stop_loss_price and take_profit_price to price_alerts."""
    with engine.connect() as conn:
        # Check if columns already exist
        result = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'price_alerts' AND column_name = 'stop_loss_price'"
            )
        )
        if result.fetchone():
            print("Columns already exist in 'price_alerts'.")
            return

        conn.execute(
            text(
                "ALTER TABLE price_alerts "
                "ADD COLUMN stop_loss_price NUMERIC(18, 6), "
                "ADD COLUMN take_profit_price NUMERIC(18, 6)"
            )
        )
        conn.commit()
        print("Added stop_loss_price and take_profit_price columns to price_alerts.")


if __name__ == "__main__":
    migrate()
