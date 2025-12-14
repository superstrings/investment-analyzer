"""
Database module for Investment Analyzer.

This module provides:
- SQLAlchemy ORM models for all database tables
- Database connection and session management
- Database initialization utilities

Usage:
    from db import get_session, User, Account, Position

    # Query example
    with get_session() as session:
        user = session.query(User).filter_by(username="dyson").first()
        for account in user.accounts:
            print(account.market, account.futu_acc_id)

    # Initialize database
    from db import init_db
    init_db()
"""

from .database import (
    SessionLocal,
    check_connection,
    drop_db,
    engine,
    get_db,
    get_engine,
    get_session,
    init_db,
)
from .models import (
    Account,
    AccountSnapshot,
    Base,
    Kline,
    Position,
    SyncLog,
    Trade,
    User,
    WatchlistItem,
)

__all__ = [
    # Database utilities
    "engine",
    "SessionLocal",
    "get_session",
    "get_db",
    "init_db",
    "drop_db",
    "check_connection",
    "get_engine",
    # Models
    "Base",
    "User",
    "Account",
    "Position",
    "Trade",
    "AccountSnapshot",
    "Kline",
    "WatchlistItem",
    "SyncLog",
]
