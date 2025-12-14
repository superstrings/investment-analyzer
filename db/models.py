"""
SQLAlchemy ORM models for Investment Analyzer.

Based on database design from docs/investment-analyzer-design.md
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all models."""

    pass


class User(Base):
    """
    用户表 - 对应富途平台账号

    Each user can have their own FutuOpenD connection settings.
    Trade passwords are stored encrypted or via environment variables.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    display_name: Mapped[Optional[str]] = mapped_column(String(100))
    opend_host: Mapped[str] = mapped_column(
        String(100), nullable=False, default="127.0.0.1"
    )
    opend_port: Mapped[int] = mapped_column(Integer, nullable=False, default=11111)
    trade_password_enc: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    accounts: Mapped[list["Account"]] = relationship(
        "Account", back_populates="user", cascade="all, delete-orphan"
    )
    watchlist_items: Mapped[list["WatchlistItem"]] = relationship(
        "WatchlistItem", back_populates="user", cascade="all, delete-orphan"
    )
    sync_logs: Mapped[list["SyncLog"]] = relationship(
        "SyncLog", back_populates="user", cascade="all, delete-orphan"
    )
    price_alerts: Mapped[list["PriceAlert"]] = relationship(
        "PriceAlert", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class Account(Base):
    """
    交易账户表 - 一个用户可有多个账户

    Supports multiple account types (REAL/SIMULATE) and markets (HK/US/A).
    """

    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint("user_id", "futu_acc_id", name="uq_accounts_user_futu"),
        Index("idx_accounts_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    futu_acc_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    account_name: Mapped[Optional[str]] = mapped_column(String(100))
    account_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # REAL/SIMULATE
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # HK/US/A
    currency: Mapped[str] = mapped_column(String(10), default="HKD")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    positions: Mapped[list["Position"]] = relationship(
        "Position", back_populates="account", cascade="all, delete-orphan"
    )
    trades: Mapped[list["Trade"]] = relationship(
        "Trade", back_populates="account", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["AccountSnapshot"]] = relationship(
        "AccountSnapshot", back_populates="account", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, futu_acc_id={self.futu_acc_id}, market='{self.market}')>"


class Position(Base):
    """
    持仓快照表 - 每日记录

    Stores daily position snapshots for tracking portfolio changes.
    """

    __tablename__ = "positions"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "snapshot_date",
            "market",
            "code",
            name="uq_positions_account_date_code",
        ),
        Index("idx_positions_account_date", "account_id", "snapshot_date"),
        Index("idx_positions_code", "market", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # HK/US/A
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    can_sell_qty: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    cost_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    market_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    market_val: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    pl_val: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))  # 盈亏金额
    pl_ratio: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))  # 盈亏比例
    position_side: Mapped[str] = mapped_column(String(10), default="LONG")  # LONG/SHORT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="positions")

    def __repr__(self) -> str:
        return f"<Position(id={self.id}, code='{self.market}.{self.code}', qty={self.qty})>"


class Trade(Base):
    """
    成交记录表

    Records all executed trades from Futu API.
    """

    __tablename__ = "trades"
    __table_args__ = (
        UniqueConstraint("account_id", "deal_id", name="uq_trades_account_deal"),
        Index("idx_trades_account_time", "account_id", "trade_time"),
        Index("idx_trades_code", "market", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    deal_id: Mapped[str] = mapped_column(String(50), nullable=False)  # 富途成交ID
    order_id: Mapped[Optional[str]] = mapped_column(String(50))
    trade_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    trd_side: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY/SELL
    qty: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 4))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="trades")

    def __repr__(self) -> str:
        return f"<Trade(id={self.id}, deal_id='{self.deal_id}', {self.trd_side} {self.code})>"


class AccountSnapshot(Base):
    """
    账户资金快照表

    Daily snapshots of account balance and assets.
    """

    __tablename__ = "account_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "account_id", "snapshot_date", name="uq_account_snapshots_account_date"
        ),
        Index("idx_account_snapshots_date", "account_id", "snapshot_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_assets: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    market_val: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    frozen_cash: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    buying_power: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    max_power_short: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[Optional[str]] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="snapshots")

    def __repr__(self) -> str:
        return f"<AccountSnapshot(id={self.id}, account_id={self.account_id}, date={self.snapshot_date})>"


class Kline(Base):
    """
    K线数据表 - 全局共享

    Stores daily OHLCV data for all stocks, shared across users.
    Includes pre-calculated technical indicators.
    """

    __tablename__ = "klines"
    __table_args__ = (
        UniqueConstraint(
            "market", "code", "trade_date", name="uq_klines_market_code_date"
        ),
        Index("idx_klines_code_date", "market", "code", "trade_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # HK/US/A
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    open: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    volume: Mapped[Optional[int]] = mapped_column(BigInteger)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    turnover_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    change_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))
    # Pre-calculated technical indicators
    ma5: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    ma10: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    ma20: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    ma60: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    obv: Mapped[Optional[int]] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    def __repr__(self) -> str:
        return f"<Kline(id={self.id}, code='{self.market}.{self.code}', date={self.trade_date})>"

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market}.{self.code}"


class WatchlistItem(Base):
    """
    关注列表表

    Per-user watchlist with optional grouping.
    """

    __tablename__ = "watchlist"
    __table_args__ = (
        UniqueConstraint("user_id", "market", "code", name="uq_watchlist_user_code"),
        Index("idx_watchlist_user", "user_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    group_name: Mapped[Optional[str]] = mapped_column(String(50))  # 分组名称
    notes: Mapped[Optional[str]] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="watchlist_items")

    def __repr__(self) -> str:
        return f"<WatchlistItem(id={self.id}, code='{self.market}.{self.code}')>"

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market}.{self.code}"


class SyncLog(Base):
    """
    数据同步日志表

    Records sync operations for auditing and debugging.
    """

    __tablename__ = "sync_logs"
    __table_args__ = (Index("idx_sync_logs_user_time", "user_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))
    sync_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # POSITIONS/TRADES/KLINES/...
    status: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # SUCCESS/FAILED/PARTIAL
    records_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    # Relationships
    user: Mapped[Optional["User"]] = relationship("User", back_populates="sync_logs")

    def __repr__(self) -> str:
        return (
            f"<SyncLog(id={self.id}, type='{self.sync_type}', status='{self.status}')>"
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate sync duration in seconds."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class PriceAlert(Base):
    """
    价格提醒表

    Stores price alert rules for stocks.
    Alert types:
    - ABOVE: Price goes above target
    - BELOW: Price goes below target
    - CHANGE_UP: Price increases by percentage
    - CHANGE_DOWN: Price decreases by percentage
    """

    __tablename__ = "price_alerts"
    __table_args__ = (
        Index("idx_price_alerts_user", "user_id", "is_active"),
        Index("idx_price_alerts_code", "market", "code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    market: Mapped[str] = mapped_column(String(10), nullable=False)  # HK/US/A
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_name: Mapped[Optional[str]] = mapped_column(String(100))
    alert_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # ABOVE/BELOW/CHANGE_UP/CHANGE_DOWN
    target_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    target_change_pct: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 4)
    )  # For percentage alerts
    base_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 6)
    )  # Reference price for change alerts
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_triggered: Mapped[bool] = mapped_column(Boolean, default=False)
    triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    triggered_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 6))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="price_alerts")

    def __repr__(self) -> str:
        return f"<PriceAlert(id={self.id}, code='{self.market}.{self.code}', type='{self.alert_type}')>"

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market}.{self.code}"

    @property
    def target_description(self) -> str:
        """Get human-readable target description."""
        if self.alert_type in ("ABOVE", "BELOW"):
            return f"{self.alert_type.lower()} {self.target_price}"
        else:  # CHANGE_UP/CHANGE_DOWN
            sign = "+" if self.alert_type == "CHANGE_UP" else "-"
            return f"{sign}{abs(float(self.target_change_pct or 0)):.2%}"
