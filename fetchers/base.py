"""
Base class for data fetchers.

Provides common interface and utilities for all data fetchers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class Market(Enum):
    """Supported markets."""

    HK = "HK"  # Hong Kong
    US = "US"  # United States
    A = "A"  # China A-shares


class TradeSide(Enum):
    """Trade direction."""

    BUY = "BUY"
    SELL = "SELL"


class AccountType(Enum):
    """Account type."""

    REAL = "REAL"
    SIMULATE = "SIMULATE"


class PositionSide(Enum):
    """Position direction."""

    LONG = "LONG"
    SHORT = "SHORT"


@dataclass
class AccountInfo:
    """Account information from broker."""

    acc_id: int
    account_type: AccountType
    market: Market
    currency: str = "HKD"
    total_assets: Decimal = Decimal("0")
    cash: Decimal = Decimal("0")
    market_val: Decimal = Decimal("0")
    frozen_cash: Decimal = Decimal("0")
    buying_power: Decimal = Decimal("0")
    max_power_short: Decimal = Decimal("0")


@dataclass
class PositionInfo:
    """Position information from broker."""

    market: Market
    code: str
    stock_name: str
    qty: Decimal
    can_sell_qty: Decimal = Decimal("0")
    cost_price: Decimal = Decimal("0")
    market_price: Decimal = Decimal("0")
    market_val: Decimal = Decimal("0")
    pl_val: Decimal = Decimal("0")
    pl_ratio: Decimal = Decimal("0")
    position_side: PositionSide = PositionSide.LONG

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market.value}.{self.code}"


@dataclass
class TradeInfo:
    """Trade/deal information from broker."""

    deal_id: str
    market: Market
    code: str
    stock_name: str
    trd_side: TradeSide
    qty: Decimal
    price: Decimal
    trade_time: datetime
    order_id: str = ""
    amount: Decimal = Decimal("0")
    fee: Decimal = Decimal("0")
    currency: str = "HKD"

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market.value}.{self.code}"


@dataclass
class FetchResult:
    """Result container for fetch operations."""

    success: bool
    data: list = field(default_factory=list)
    error_message: str = ""
    records_count: int = 0

    @classmethod
    def ok(cls, data: list) -> "FetchResult":
        """Create successful result."""
        return cls(success=True, data=data, records_count=len(data))

    @classmethod
    def error(cls, message: str) -> "FetchResult":
        """Create error result."""
        return cls(success=False, error_message=message)


class BaseFetcher(ABC):
    """
    Abstract base class for data fetchers.

    All data fetchers should inherit from this class and implement
    the abstract methods.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 11111):
        """
        Initialize fetcher.

        Args:
            host: Server host address
            port: Server port number
        """
        self.host = host
        self.port = port
        self._connected = False

    @property
    def is_connected(self) -> bool:
        """Check if connected to server."""
        return self._connected

    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the data source.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the data source."""
        pass

    @abstractmethod
    def get_account_list(self) -> FetchResult:
        """
        Get list of trading accounts.

        Returns:
            FetchResult containing list of AccountInfo
        """
        pass

    @abstractmethod
    def get_positions(self, acc_id: int) -> FetchResult:
        """
        Get positions for an account.

        Args:
            acc_id: Account ID

        Returns:
            FetchResult containing list of PositionInfo
        """
        pass

    @abstractmethod
    def get_account_info(self, acc_id: int) -> FetchResult:
        """
        Get account balance and asset information.

        Args:
            acc_id: Account ID

        Returns:
            FetchResult containing AccountInfo
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        return False
