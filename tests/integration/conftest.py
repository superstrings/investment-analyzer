"""Shared fixtures for integration tests."""

import os
import tempfile
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Generator
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from db.models import (
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


@pytest.fixture(scope="module")
def integration_engine():
    """Create an in-memory SQLite database for integration tests."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def integration_session(integration_engine) -> Generator[Session, None, None]:
    """Create a new session for each test."""
    SessionLocal = sessionmaker(bind=integration_engine)
    session = SessionLocal()

    # Clear all data before each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session
    session.close()


@pytest.fixture
def sample_user(integration_session) -> User:
    """Create a sample user."""
    user = User(username="test_user")
    integration_session.add(user)
    integration_session.commit()
    integration_session.refresh(user)
    return user


@pytest.fixture
def sample_account(integration_session, sample_user) -> Account:
    """Create a sample account."""
    account = Account(
        user_id=sample_user.id,
        futu_acc_id=12345678,
        account_name="测试账户",
        account_type="REAL",
        market="HK",
        currency="HKD",
    )
    integration_session.add(account)
    integration_session.commit()
    integration_session.refresh(account)
    return account


@pytest.fixture
def sample_positions(integration_session, sample_account) -> list[Position]:
    """Create sample positions."""
    today = date.today()
    positions_data = [
        {
            "code": "00700",
            "market": "HK",
            "stock_name": "腾讯控股",
            "snapshot_date": today,
            "qty": Decimal("100"),
            "can_sell_qty": Decimal("100"),
            "cost_price": Decimal("350.00"),
            "market_price": Decimal("380.00"),
            "market_val": Decimal("38000.00"),
            "pl_val": Decimal("3000.00"),
            "pl_ratio": Decimal("0.0857"),
            "position_side": "LONG",
        },
        {
            "code": "09988",
            "market": "HK",
            "stock_name": "阿里巴巴-SW",
            "snapshot_date": today,
            "qty": Decimal("200"),
            "can_sell_qty": Decimal("200"),
            "cost_price": Decimal("85.00"),
            "market_price": Decimal("78.00"),
            "market_val": Decimal("15600.00"),
            "pl_val": Decimal("-1400.00"),
            "pl_ratio": Decimal("-0.0824"),
            "position_side": "LONG",
        },
        {
            "code": "03690",
            "market": "HK",
            "stock_name": "美团-W",
            "snapshot_date": today,
            "qty": Decimal("50"),
            "can_sell_qty": Decimal("50"),
            "cost_price": Decimal("120.00"),
            "market_price": Decimal("135.00"),
            "market_val": Decimal("6750.00"),
            "pl_val": Decimal("750.00"),
            "pl_ratio": Decimal("0.125"),
            "position_side": "LONG",
        },
    ]

    positions = []
    for data in positions_data:
        position = Position(account_id=sample_account.id, **data)
        integration_session.add(position)
        positions.append(position)

    integration_session.commit()
    for p in positions:
        integration_session.refresh(p)
    return positions


@pytest.fixture
def sample_trades(integration_session, sample_account) -> list[Trade]:
    """Create sample trades."""
    base_time = datetime.now() - timedelta(days=30)
    trades_data = [
        {
            "deal_id": "DEAL_001",
            "order_id": "ORDER_001",
            "code": "00700",
            "market": "HK",
            "stock_name": "腾讯控股",
            "trd_side": "BUY",
            "qty": Decimal("100"),
            "price": Decimal("350.00"),
            "amount": Decimal("35000.00"),
            "trade_time": base_time,
        },
        {
            "deal_id": "DEAL_002",
            "order_id": "ORDER_002",
            "code": "09988",
            "market": "HK",
            "stock_name": "阿里巴巴-SW",
            "trd_side": "BUY",
            "qty": Decimal("200"),
            "price": Decimal("85.00"),
            "amount": Decimal("17000.00"),
            "trade_time": base_time + timedelta(days=5),
        },
        {
            "deal_id": "DEAL_003",
            "order_id": "ORDER_003",
            "code": "03690",
            "market": "HK",
            "stock_name": "美团-W",
            "trd_side": "BUY",
            "qty": Decimal("50"),
            "price": Decimal("120.00"),
            "amount": Decimal("6000.00"),
            "trade_time": base_time + timedelta(days=10),
        },
    ]

    trades = []
    for data in trades_data:
        trade = Trade(account_id=sample_account.id, **data)
        integration_session.add(trade)
        trades.append(trade)

    integration_session.commit()
    for t in trades:
        integration_session.refresh(t)
    return trades


@pytest.fixture
def sample_klines() -> pd.DataFrame:
    """Generate sample K-line data for testing."""
    days = 120
    end_date = date.today()
    dates = [end_date - timedelta(days=i) for i in range(days)]
    dates.reverse()

    # Generate realistic price data with some volatility
    import random

    random.seed(42)

    base_price = 350.0
    prices = []
    current_price = base_price

    for _ in range(days):
        change = random.uniform(-0.03, 0.035) * current_price
        current_price = max(current_price + change, 100)

        high = current_price * (1 + random.uniform(0.005, 0.02))
        low = current_price * (1 - random.uniform(0.005, 0.02))
        open_price = random.uniform(low, high)

        prices.append(
            {
                "open": round(open_price, 2),
                "high": round(high, 2),
                "low": round(low, 2),
                "close": round(current_price, 2),
            }
        )

    df = pd.DataFrame(
        {
            "trade_date": dates,
            "open": [p["open"] for p in prices],
            "high": [p["high"] for p in prices],
            "low": [p["low"] for p in prices],
            "close": [p["close"] for p in prices],
            "volume": [random.randint(1000000, 5000000) for _ in range(days)],
            "turnover": [random.uniform(350000000, 1750000000) for _ in range(days)],
        }
    )

    # Set trade_date as index for mplfinance compatibility
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df.set_index("trade_date", inplace=True)

    return df


@pytest.fixture
def sample_klines_db(integration_session, sample_klines) -> list[Kline]:
    """Store sample K-lines in database."""
    klines = []
    df = sample_klines.reset_index()

    for _, row in df.iterrows():
        kline = Kline(
            code="00700",
            market="HK",
            trade_date=row["trade_date"].date(),
            open=Decimal(str(row["open"])),
            high=Decimal(str(row["high"])),
            low=Decimal(str(row["low"])),
            close=Decimal(str(row["close"])),
            volume=int(row["volume"]),
            amount=Decimal(str(row["turnover"])),
        )
        integration_session.add(kline)
        klines.append(kline)

    integration_session.commit()
    return klines


@pytest.fixture
def sample_watchlist(integration_session, sample_user) -> list[WatchlistItem]:
    """Create sample watchlist."""
    watchlist_data = [
        {
            "code": "00700",
            "market": "HK",
            "stock_name": "腾讯控股",
            "notes": "核心持仓",
        },
        {"code": "09988", "market": "HK", "stock_name": "阿里巴巴-SW", "notes": "观察"},
        {"code": "NVDA", "market": "US", "stock_name": "NVIDIA", "notes": "AI龙头"},
    ]

    watchlist = []
    for data in watchlist_data:
        item = WatchlistItem(user_id=sample_user.id, **data)
        integration_session.add(item)
        watchlist.append(item)

    integration_session.commit()
    for w in watchlist:
        integration_session.refresh(w)
    return watchlist


@pytest.fixture
def sample_snapshot(integration_session, sample_account) -> AccountSnapshot:
    """Create sample account snapshot."""
    snapshot = AccountSnapshot(
        account_id=sample_account.id,
        snapshot_date=date.today(),
        total_assets=Decimal("100000.00"),
        cash=Decimal("39650.00"),
        market_val=Decimal("60350.00"),
        frozen_cash=Decimal("0"),
        buying_power=Decimal("79300.00"),
        max_withdraw=Decimal("39650.00"),
        currency="HKD",
    )
    integration_session.add(snapshot)
    integration_session.commit()
    integration_session.refresh(snapshot)
    return snapshot


@pytest.fixture
def mock_kline_fetcher(sample_klines):
    """Create a mock KlineFetcher that returns sample data."""
    from fetchers.base import FetchResult
    from fetchers.kline_fetcher import KlineFetcher, KlineFetchResult

    mock_fetcher = MagicMock(spec=KlineFetcher)

    def mock_fetch(code, days=120, **kwargs):
        return KlineFetchResult(
            success=True,
            data=None,
            df=sample_klines.copy(),
            code=code,
            market="HK" if code.startswith("0") else "US",
            records_count=len(sample_klines),
        )

    mock_fetcher.fetch.side_effect = mock_fetch
    mock_fetcher.fetch_batch.return_value = {
        "00700": mock_fetch("00700"),
        "09988": mock_fetch("09988"),
    }

    return mock_fetcher


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for test outputs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def temp_chart_dir(temp_output_dir):
    """Create a temporary directory for chart outputs."""
    chart_dir = os.path.join(temp_output_dir, "charts")
    os.makedirs(chart_dir, exist_ok=True)
    return chart_dir


@pytest.fixture
def temp_report_dir(temp_output_dir):
    """Create a temporary directory for report outputs."""
    report_dir = os.path.join(temp_output_dir, "reports")
    os.makedirs(report_dir, exist_ok=True)
    return report_dir
