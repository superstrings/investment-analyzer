"""Tests for data fetchers module.

Tests the base classes, data types, and FutuFetcher functionality.
Since FutuOpenD may not be running, we test with mocks where appropriate.
"""

from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fetchers import (
    AccountInfo,
    AccountType,
    FetchResult,
    FutuFetcher,
    Market,
    PositionInfo,
    PositionSide,
    TradeInfo,
    TradeSide,
)
from fetchers.futu_fetcher import _parse_code, _parse_market


class TestMarketEnum:
    """Tests for Market enum."""

    def test_market_values(self):
        """Test market enum values."""
        assert Market.HK.value == "HK"
        assert Market.US.value == "US"
        assert Market.A.value == "A"


class TestTradeSideEnum:
    """Tests for TradeSide enum."""

    def test_trade_side_values(self):
        """Test trade side enum values."""
        assert TradeSide.BUY.value == "BUY"
        assert TradeSide.SELL.value == "SELL"


class TestAccountTypeEnum:
    """Tests for AccountType enum."""

    def test_account_type_values(self):
        """Test account type enum values."""
        assert AccountType.REAL.value == "REAL"
        assert AccountType.SIMULATE.value == "SIMULATE"


class TestFetchResult:
    """Tests for FetchResult class."""

    def test_ok_result(self):
        """Test creating successful result."""
        data = [1, 2, 3]
        result = FetchResult.ok(data)
        assert result.success is True
        assert result.data == data
        assert result.records_count == 3
        assert result.error_message == ""

    def test_error_result(self):
        """Test creating error result."""
        result = FetchResult.error("Something went wrong")
        assert result.success is False
        assert result.data == []
        assert result.error_message == "Something went wrong"

    def test_empty_ok_result(self):
        """Test successful result with empty data."""
        result = FetchResult.ok([])
        assert result.success is True
        assert result.records_count == 0


class TestAccountInfo:
    """Tests for AccountInfo dataclass."""

    def test_account_info_creation(self):
        """Test creating AccountInfo."""
        acc = AccountInfo(
            acc_id=123456,
            account_type=AccountType.REAL,
            market=Market.HK,
            currency="HKD",
            total_assets=Decimal("100000.00"),
            cash=Decimal("20000.00"),
        )
        assert acc.acc_id == 123456
        assert acc.account_type == AccountType.REAL
        assert acc.market == Market.HK
        assert acc.total_assets == Decimal("100000.00")

    def test_account_info_defaults(self):
        """Test AccountInfo default values."""
        acc = AccountInfo(acc_id=1, account_type=AccountType.SIMULATE, market=Market.US)
        assert acc.currency == "HKD"
        assert acc.total_assets == Decimal("0")


class TestPositionInfo:
    """Tests for PositionInfo dataclass."""

    def test_position_info_creation(self):
        """Test creating PositionInfo."""
        pos = PositionInfo(
            market=Market.HK,
            code="00700",
            stock_name="腾讯控股",
            qty=Decimal("100"),
            cost_price=Decimal("350.00"),
            market_price=Decimal("380.00"),
            pl_val=Decimal("3000.00"),
            pl_ratio=Decimal("0.0857"),
        )
        assert pos.code == "00700"
        assert pos.qty == Decimal("100")
        assert pos.pl_ratio == Decimal("0.0857")

    def test_position_full_code(self):
        """Test full_code property."""
        pos = PositionInfo(
            market=Market.US,
            code="NVDA",
            stock_name="NVIDIA",
            qty=Decimal("10"),
        )
        assert pos.full_code == "US.NVDA"

    def test_position_defaults(self):
        """Test PositionInfo default values."""
        pos = PositionInfo(
            market=Market.HK, code="00700", stock_name="腾讯", qty=Decimal("100")
        )
        assert pos.position_side == PositionSide.LONG
        assert pos.can_sell_qty == Decimal("0")


class TestTradeInfo:
    """Tests for TradeInfo dataclass."""

    def test_trade_info_creation(self):
        """Test creating TradeInfo."""
        trade = TradeInfo(
            deal_id="DEAL123",
            market=Market.HK,
            code="00700",
            stock_name="腾讯控股",
            trd_side=TradeSide.BUY,
            qty=Decimal("100"),
            price=Decimal("350.00"),
            trade_time=datetime(2025, 12, 14, 10, 30, 0),
        )
        assert trade.deal_id == "DEAL123"
        assert trade.trd_side == TradeSide.BUY
        assert trade.qty == Decimal("100")

    def test_trade_full_code(self):
        """Test full_code property."""
        trade = TradeInfo(
            deal_id="DEAL1",
            market=Market.US,
            code="AAPL",
            stock_name="Apple",
            trd_side=TradeSide.SELL,
            qty=Decimal("5"),
            price=Decimal("190.00"),
            trade_time=datetime.now(),
        )
        assert trade.full_code == "US.AAPL"


class TestParseMarket:
    """Tests for _parse_market helper function."""

    def test_parse_hk_market(self):
        """Test parsing HK market."""
        assert _parse_market("HK") == Market.HK
        assert _parse_market("hk") == Market.HK
        assert _parse_market("HKEX") == Market.HK

    def test_parse_us_market(self):
        """Test parsing US market."""
        assert _parse_market("US") == Market.US
        assert _parse_market("NYSE") == Market.US
        assert _parse_market("NASDAQ") == Market.US

    def test_parse_a_market(self):
        """Test parsing A-share market."""
        assert _parse_market("A") == Market.A
        assert _parse_market("SH") == Market.A
        assert _parse_market("SZ") == Market.A
        assert _parse_market("CN") == Market.A

    def test_parse_unknown_defaults_to_hk(self):
        """Test unknown market defaults to HK."""
        assert _parse_market("UNKNOWN") == Market.HK


class TestParseCode:
    """Tests for _parse_code helper function."""

    def test_parse_full_code(self):
        """Test parsing full stock code."""
        market, code = _parse_code("HK.00700")
        assert market == Market.HK
        assert code == "00700"

    def test_parse_us_code(self):
        """Test parsing US stock code."""
        market, code = _parse_code("US.NVDA")
        assert market == Market.US
        assert code == "NVDA"

    def test_parse_code_without_market(self):
        """Test parsing code without market prefix."""
        market, code = _parse_code("00700")
        assert market == Market.HK  # Default
        assert code == "00700"


class TestFutuFetcherInit:
    """Tests for FutuFetcher initialization."""

    def test_default_init(self):
        """Test default initialization."""
        fetcher = FutuFetcher()
        assert fetcher.host == "127.0.0.1"
        assert fetcher.port == 11111
        assert fetcher.is_connected is False
        assert fetcher.is_unlocked is False

    def test_custom_init(self):
        """Test custom initialization."""
        fetcher = FutuFetcher(host="192.168.1.100", port=22222)
        assert fetcher.host == "192.168.1.100"
        assert fetcher.port == 22222


class TestFutuFetcherWithMock:
    """Tests for FutuFetcher with mocked Futu API."""

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_connect_success(self, mock_ctx_class):
        """Test successful connection."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        result = fetcher.connect()

        assert result is True
        assert fetcher.is_connected is True
        mock_ctx_class.assert_called_once()

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_connect_failure(self, mock_ctx_class):
        """Test connection failure."""
        mock_ctx_class.side_effect = Exception("Connection refused")

        fetcher = FutuFetcher()
        result = fetcher.connect()

        assert result is False
        assert fetcher.is_connected is False

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_disconnect(self, mock_ctx_class):
        """Test disconnection."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        fetcher.connect()
        fetcher.disconnect()

        assert fetcher.is_connected is False
        mock_ctx.close.assert_called_once()

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_unlock_trade_success(self, mock_ctx_class):
        """Test successful trade unlock."""
        mock_ctx = MagicMock()
        mock_ctx.unlock_trade.return_value = (0, None)  # RET_OK = 0
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        fetcher.connect()
        result = fetcher.unlock_trade("password123")

        assert result.success is True
        assert fetcher.is_unlocked is True

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_get_account_list(self, mock_ctx_class):
        """Test getting account list."""
        mock_ctx = MagicMock()
        mock_data = pd.DataFrame(
            {
                "acc_id": [123456, 789012],
                "trd_env": ["REAL", "SIMULATE"],
                "trd_market_auth": [[], []],
                "currency": ["HKD", "USD"],
            }
        )
        mock_ctx.get_acc_list.return_value = (0, mock_data)
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        fetcher.connect()
        result = fetcher.get_account_list()

        assert result.success is True
        assert result.records_count == 2
        assert result.data[0].acc_id == 123456
        assert result.data[1].account_type == AccountType.SIMULATE

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_get_positions(self, mock_ctx_class):
        """Test getting positions."""
        mock_ctx = MagicMock()
        mock_data = pd.DataFrame(
            {
                "code": ["HK.00700", "US.NVDA"],
                "stock_name": ["腾讯控股", "NVIDIA"],
                "qty": [100, 50],
                "can_sell_qty": [100, 50],
                "cost_price": [350.0, 140.0],
                "nominal_price": [380.0, 145.0],
                "market_val": [38000.0, 7250.0],
                "pl_val": [3000.0, 250.0],
                "pl_ratio": [0.0857, 0.0357],
                "position_side": ["LONG", "LONG"],
            }
        )
        mock_ctx.position_list_query.return_value = (0, mock_data)
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        fetcher.connect()
        result = fetcher.get_positions(acc_id=123456)

        assert result.success is True
        assert result.records_count == 2
        assert result.data[0].code == "00700"
        assert result.data[0].market == Market.HK
        assert result.data[1].code == "NVDA"
        assert result.data[1].market == Market.US

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_get_account_info(self, mock_ctx_class):
        """Test getting account info."""
        mock_ctx = MagicMock()
        mock_data = pd.DataFrame(
            {
                "trd_market": [1],  # HK
                "currency": ["HKD"],
                "total_assets": [100000.0],
                "cash": [20000.0],
                "market_val": [80000.0],
                "frozen_cash": [0.0],
                "avl_withdrawal_cash": [15000.0],
                "max_power_short": [0.0],
            }
        )
        mock_ctx.accinfo_query.return_value = (0, mock_data)
        mock_ctx_class.return_value = mock_ctx

        fetcher = FutuFetcher()
        fetcher.connect()
        result = fetcher.get_account_info(acc_id=123456)

        assert result.success is True
        assert result.data[0].total_assets == Decimal("100000.0")
        assert result.data[0].cash == Decimal("20000.0")

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_context_manager(self, mock_ctx_class):
        """Test using FutuFetcher as context manager."""
        mock_ctx = MagicMock()
        mock_ctx_class.return_value = mock_ctx

        with FutuFetcher() as fetcher:
            assert fetcher.is_connected is True

        mock_ctx.close.assert_called_once()

    @patch("fetchers.futu_fetcher.OpenSecTradeContext")
    def test_not_connected_error(self, mock_ctx_class):
        """Test error when not connected."""
        mock_ctx_class.side_effect = Exception("Connection refused")

        fetcher = FutuFetcher()
        result = fetcher.get_account_list()

        assert result.success is False
        assert "Not connected" in result.error_message
