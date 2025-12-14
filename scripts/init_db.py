#!/usr/bin/env python3
"""
Database initialization script for Investment Analyzer.

This script provides utilities to:
- Create the database (if it doesn't exist)
- Initialize tables using SQLAlchemy ORM
- Run raw SQL schema file
- Check database connection
- Reset database (drop and recreate)

Usage:
    # Initialize database with SQLAlchemy ORM
    python scripts/init_db.py init

    # Initialize using raw SQL file
    python scripts/init_db.py init --sql

    # Check database connection
    python scripts/init_db.py check

    # Reset database (WARNING: deletes all data)
    python scripts/init_db.py reset

    # Create database (PostgreSQL only)
    python scripts/init_db.py create-db
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import click
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

from config import settings
from db import Base, check_connection, drop_db, engine, init_db


def get_db_name_from_url(url: str) -> str:
    """Extract database name from URL."""
    # postgresql://user:pass@host:port/dbname
    return url.rsplit("/", 1)[-1].split("?")[0]


def get_server_url(url: str) -> str:
    """Get server URL without database name (for creating database)."""
    # Connect to 'postgres' database to create new database
    parts = url.rsplit("/", 1)
    return f"{parts[0]}/postgres"


@click.group()
def cli():
    """Database management commands for Investment Analyzer."""
    pass


@cli.command()
@click.option("--sql", is_flag=True, help="Use raw SQL file instead of ORM")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def init(sql: bool, verbose: bool):
    """Initialize database tables."""
    click.echo("Initializing database...")

    # Check connection first
    if not check_connection():
        click.echo("Error: Cannot connect to database.", err=True)
        click.echo(f"Database URL: {settings.database.url}", err=True)
        click.echo("Make sure PostgreSQL is running and the database exists.", err=True)
        sys.exit(1)

    if sql:
        # Use raw SQL file
        sql_file = project_root / "db" / "migrations" / "init_schema.sql"
        if not sql_file.exists():
            click.echo(f"Error: SQL file not found: {sql_file}", err=True)
            sys.exit(1)

        click.echo(f"Running SQL schema from {sql_file}...")
        with open(sql_file, "r") as f:
            sql_content = f.read()

        with engine.connect() as conn:
            # Split by semicolons and execute each statement
            # Note: This is a simple approach; for complex migrations use Alembic
            conn.execute(text(sql_content))
            conn.commit()

        click.echo("SQL schema applied successfully.")
    else:
        # Use SQLAlchemy ORM
        click.echo("Creating tables from ORM models...")
        init_db()
        click.echo("Tables created successfully.")

    # Verify tables
    with engine.connect() as conn:
        result = conn.execute(
            text(
                """
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
            )
        )
        tables = [row[0] for row in result]

    click.echo(f"\nCreated {len(tables)} tables:")
    for table in tables:
        click.echo(f"  - {table}")


@cli.command()
def check():
    """Check database connection."""
    click.echo("Checking database connection...")
    click.echo(f"Database URL: {settings.database.url}")

    if check_connection():
        click.echo("Connection successful!")

        # Get server version
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            click.echo(f"PostgreSQL version: {version}")

            # Count tables
            result = conn.execute(
                text(
                    """
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            """
                )
            )
            table_count = result.scalar()
            click.echo(f"Tables in database: {table_count}")
    else:
        click.echo("Connection failed!", err=True)
        sys.exit(1)


@cli.command()
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def reset(yes: bool):
    """Reset database (drop all tables and recreate)."""
    if not yes:
        click.confirm(
            "This will DELETE ALL DATA in the database. Continue?", abort=True
        )

    click.echo("Dropping all tables...")
    drop_db()

    click.echo("Recreating tables...")
    init_db()

    click.echo("Database reset complete.")


@cli.command("create-db")
@click.option("--name", default=None, help="Database name (default from DATABASE_URL)")
def create_db(name: str):
    """Create the database (PostgreSQL only)."""
    db_name = name or get_db_name_from_url(settings.database.url)
    server_url = get_server_url(settings.database.url)

    click.echo(f"Creating database '{db_name}'...")

    try:
        # Connect to postgres database to create new database
        temp_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": db_name},
            )
            exists = result.scalar()

            if exists:
                click.echo(f"Database '{db_name}' already exists.")
            else:
                conn.execute(text(f'CREATE DATABASE "{db_name}"'))
                click.echo(f"Database '{db_name}' created successfully.")

        temp_engine.dispose()

    except OperationalError as e:
        click.echo(f"Error connecting to PostgreSQL server: {e}", err=True)
        sys.exit(1)
    except ProgrammingError as e:
        click.echo(f"Error creating database: {e}", err=True)
        sys.exit(1)


@cli.command("drop-db")
@click.option("--name", default=None, help="Database name (default from DATABASE_URL)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def drop_database(name: str, yes: bool):
    """Drop the database (PostgreSQL only)."""
    db_name = name or get_db_name_from_url(settings.database.url)

    if not yes:
        click.confirm(
            f"This will DELETE the entire database '{db_name}'. Continue?", abort=True
        )

    server_url = get_server_url(settings.database.url)

    try:
        temp_engine = create_engine(server_url, isolation_level="AUTOCOMMIT")
        with temp_engine.connect() as conn:
            # Terminate existing connections
            conn.execute(
                text(
                    f"""
                SELECT pg_terminate_backend(pg_stat_activity.pid)
                FROM pg_stat_activity
                WHERE pg_stat_activity.datname = '{db_name}'
                AND pid <> pg_backend_pid()
            """
                )
            )
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))

        temp_engine.dispose()
        click.echo(f"Database '{db_name}' dropped successfully.")

    except Exception as e:
        click.echo(f"Error dropping database: {e}", err=True)
        sys.exit(1)


@cli.command()
def status():
    """Show database status and statistics."""
    click.echo("Database Status")
    click.echo("=" * 50)

    if not check_connection():
        click.echo("Status: DISCONNECTED", err=True)
        sys.exit(1)

    click.echo("Status: CONNECTED")
    click.echo(f"URL: {settings.database.url}")

    with engine.connect() as conn:
        # Get table statistics
        result = conn.execute(
            text(
                """
            SELECT
                table_name,
                (SELECT COUNT(*) FROM information_schema.columns
                 WHERE table_name = t.table_name) as column_count
            FROM information_schema.tables t
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
            )
        )
        tables = list(result)

        click.echo(f"\nTables ({len(tables)}):")
        for table_name, col_count in tables:
            # Get row count
            try:
                row_result = conn.execute(text(f'SELECT COUNT(*) FROM "{table_name}"'))
                row_count = row_result.scalar()
            except Exception:
                row_count = "?"

            click.echo(f"  {table_name}: {row_count} rows, {col_count} columns")


@cli.command("seed")
@click.option("--user", default="dyson", help="Username for seed data")
def seed_data(user: str):
    """Add sample seed data for testing."""
    from datetime import date, datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from db import Account, User, WatchlistItem

    click.echo("Adding seed data...")

    with Session(engine) as session:
        # Check if user exists
        existing = session.query(User).filter_by(username=user).first()
        if existing:
            click.echo(f"User '{user}' already exists (id={existing.id})")
            return

        # Create user
        new_user = User(
            username=user,
            display_name=user.title(),
            opend_host="127.0.0.1",
            opend_port=11111,
        )
        session.add(new_user)
        session.flush()

        # Create sample accounts
        hk_account = Account(
            user_id=new_user.id,
            futu_acc_id=1234567890,
            account_name="港股真实账户",
            account_type="REAL",
            market="HK",
            currency="HKD",
        )
        us_account = Account(
            user_id=new_user.id,
            futu_acc_id=1234567891,
            account_name="美股真实账户",
            account_type="REAL",
            market="US",
            currency="USD",
        )
        session.add_all([hk_account, us_account])

        # Create sample watchlist
        watchlist_items = [
            WatchlistItem(
                user_id=new_user.id,
                market="HK",
                code="00700",
                stock_name="腾讯控股",
                group_name="科技股",
            ),
            WatchlistItem(
                user_id=new_user.id,
                market="HK",
                code="09988",
                stock_name="阿里巴巴-SW",
                group_name="科技股",
            ),
            WatchlistItem(
                user_id=new_user.id,
                market="US",
                code="NVDA",
                stock_name="NVIDIA",
                group_name="美股",
            ),
            WatchlistItem(
                user_id=new_user.id,
                market="US",
                code="AAPL",
                stock_name="Apple",
                group_name="美股",
            ),
        ]
        session.add_all(watchlist_items)

        session.commit()

        click.echo(f"Created user '{user}' with:")
        click.echo(f"  - 2 accounts (HK, US)")
        click.echo(f"  - 4 watchlist items")


if __name__ == "__main__":
    cli()
