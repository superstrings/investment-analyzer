"""Tests for K-line data fetcher module.

Tests the KlineFetcher class and related data types.
Since akshare fetches real market data, we use mocks for testing.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fetchers import KlineData, KlineFetchResult, KlineFetcher, Market, create_kline_fetcher


class TestKlineData:
    """Tests for KlineData dataclass."""

    def test_kline_data_creation(self):
        """Test creating KlineData."""
        kline = KlineData(
            market=Market.HK,
            code="00700",
            trade_date=date(2025, 12, 14),
            open=Decimal("380.00"),
            high=Decimal("385.00"),
            low=Decimal("378.00"),
            close=Decimal("382.50"),
            volume=10000000,
            amount=Decimal("3825000000"),
            turnover_rate=Decimal("0.25"),
            change_pct=Decimal("1.50"),
        )
        assert kline.market == Market.HK
        assert kline.code == "00700"
        assert kline.trade_date == date(2025, 12, 14)
        assert kline.close == Decimal("382.50")

    def test_kline_data_defaults(self):
        """Test KlineData default values."""
        kline = KlineData(
            market=Market.US,
            code="NVDA",
            trade_date=date(2025, 12, 14),
            open=Decimal("140.00"),
            high=Decimal("145.00"),
            low=Decimal("139.00"),
            close=Decimal("143.50"),
        )
        assert kline.volume == 0
        assert kline.amount == Decimal("0")
        assert kline.turnover_rate == Decimal("0")
        assert kline.change_pct == Decimal("0")

    def test_kline_full_code(self):
        """Test full_code property."""
        kline = KlineData(
            market=Market.HK,
            code="00700",
            trade_date=date(2025, 12, 14),
            open=Decimal("380.00"),
            high=Decimal("385.00"),
            low=Decimal("378.00"),
            close=Decimal("382.50"),
        )
        assert kline.full_code == "HK.00700"

    def test_kline_full_code_us(self):
        """Test full_code property for US stocks."""
        kline = KlineData(
            market=Market.US,
            code="AAPL",
            trade_date=date(2025, 12, 14),
            open=Decimal("190.00"),
            high=Decimal("192.00"),
            low=Decimal("189.00"),
            close=Decimal("191.50"),
        )
        assert kline.full_code == "US.AAPL"


class TestKlineFetchResult:
    """Tests for KlineFetchResult class."""

    def test_ok_with_df(self):
        """Test creating successful result with DataFrame."""
        klines = [
            KlineData(
                market=Market.HK,
                code="00700",
                trade_date=date(2025, 12, 14),
                open=Decimal("380.00"),
                high=Decimal("385.00"),
                low=Decimal("378.00"),
                close=Decimal("382.50"),
            )
        ]
        df = pd.DataFrame(
            {
                "trade_date": [date(2025, 12, 14)],
                "open": [380.0],
                "high": [385.0],
                "low": [378.0],
                "close": [382.5],
            }
        )
        result = KlineFetchResult.ok_with_df(klines, df)
        assert result.success is True
        assert result.records_count == 1
        assert result.df is not None
        assert len(result.df) == 1

    def test_error_result(self):
        """Test creating error result."""
        result = KlineFetchResult.error("Network error")
        assert result.success is False
        assert result.error_message == "Network error"
        assert result.df is None


class TestKlineFetcherInit:
    """Tests for KlineFetcher initialization."""

    def test_default_init(self):
        """Test default initialization."""
        fetcher = KlineFetcher()
        assert fetcher.default_days == 120

    def test_custom_init(self):
        """Test custom initialization."""
        fetcher = KlineFetcher(default_days=60)
        assert fetcher.default_days == 60


class TestKlineFetcherParseCode:
    """Tests for KlineFetcher._parse_code method."""

    def test_parse_hk_with_prefix(self):
        """Test parsing HK code with prefix."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("HK.00700")
        assert market == Market.HK
        assert code == "00700"

    def test_parse_us_with_prefix(self):
        """Test parsing US code with prefix."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("US.NVDA")
        assert market == Market.US
        assert code == "NVDA"

    def test_parse_a_share_with_prefix(self):
        """Test parsing A-share code with prefix."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("A.600519")
        assert market == Market.A
        assert code == "600519"

    def test_parse_a_share_sh_prefix(self):
        """Test parsing A-share code with SH prefix."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("SH.600519")
        assert market == Market.A
        assert code == "600519"

    def test_parse_a_share_sz_prefix(self):
        """Test parsing A-share code with SZ prefix."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("SZ.000001")
        assert market == Market.A
        assert code == "000001"

    def test_parse_hk_auto_detect(self):
        """Test auto-detecting HK code (5 digits)."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("00700")
        assert market == Market.HK
        assert code == "00700"

    def test_parse_us_auto_detect(self):
        """Test auto-detecting US code (letters)."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("NVDA")
        assert market == Market.US
        assert code == "NVDA"

    def test_parse_a_share_sh_auto_detect(self):
        """Test auto-detecting Shanghai A-share (starts with 6)."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("600519")
        assert market == Market.A
        assert code == "600519"

    def test_parse_a_share_sz_auto_detect(self):
        """Test auto-detecting Shenzhen A-share (starts with 0 or 3)."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("000001")
        assert market == Market.A
        assert code == "000001"

    def test_parse_chinext_auto_detect(self):
        """Test auto-detecting ChiNext (starts with 3)."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("300750")
        assert market == Market.A
        assert code == "300750"

    def test_parse_numeric_defaults_to_hk(self):
        """Test numeric code without pattern defaults to HK."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("1234")
        assert market == Market.HK
        assert code == "01234"  # Padded to 5 digits


class TestKlineFetcherDetectMarket:
    """Tests for KlineFetcher.detect_market method."""

    def test_detect_hk_market(self):
        """Test detecting HK market."""
        fetcher = KlineFetcher()
        assert fetcher.detect_market("00700") == Market.HK
        assert fetcher.detect_market("HK.00700") == Market.HK

    def test_detect_us_market(self):
        """Test detecting US market."""
        fetcher = KlineFetcher()
        assert fetcher.detect_market("NVDA") == Market.US
        assert fetcher.detect_market("US.AAPL") == Market.US

    def test_detect_a_market(self):
        """Test detecting A-share market."""
        fetcher = KlineFetcher()
        assert fetcher.detect_market("600519") == Market.A
        assert fetcher.detect_market("000001") == Market.A
        assert fetcher.detect_market("A.600519") == Market.A


class TestKlineFetcherWithMock:
    """Tests for KlineFetcher with mocked akshare API."""

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_success(self, mock_ak):
        """Test successful HK stock fetch."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-12", "2025-12-13", "2025-12-14"]),
                "open": [378.0, 380.0, 382.0],
                "high": [382.0, 385.0, 388.0],
                "low": [376.0, 378.0, 380.0],
                "close": [380.0, 382.0, 385.0],
                "volume": [1000000, 1200000, 1100000],
            }
        )
        mock_ak.stock_hk_daily.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is True
        assert result.records_count == 3
        mock_ak.stock_hk_daily.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_empty_result(self, mock_ak):
        """Test HK stock fetch with empty result."""
        mock_ak.stock_hk_daily.return_value = pd.DataFrame()

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is False
        assert "No data returned" in result.error_message

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_none_result(self, mock_ak):
        """Test HK stock fetch with None result."""
        mock_ak.stock_hk_daily.return_value = None

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is False
        assert "No data returned" in result.error_message

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_us_success(self, mock_ak):
        """Test successful US stock fetch."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-12", "2025-12-13"]),
                "open": [140.0, 142.0],
                "high": [145.0, 148.0],
                "low": [139.0, 141.0],
                "close": [143.0, 146.0],
                "volume": [50000000, 45000000],
            }
        )
        mock_ak.stock_us_daily.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch("US.NVDA", days=5)

        assert result.success is True
        assert result.records_count == 2
        mock_ak.stock_us_daily.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_a_share_success(self, mock_ak):
        """Test successful A-share fetch."""
        mock_df = pd.DataFrame(
            {
                "日期": pd.to_datetime(["2025-12-12", "2025-12-13", "2025-12-14"]),
                "开盘": [1800.0, 1820.0, 1835.0],
                "最高": [1830.0, 1850.0, 1860.0],
                "最低": [1790.0, 1810.0, 1825.0],
                "收盘": [1820.0, 1840.0, 1855.0],
                "成交量": [10000, 12000, 11000],
                "成交额": [18000000, 21600000, 20350000],
                "换手率": [0.5, 0.6, 0.55],
                "涨跌幅": [1.1, 1.1, 0.82],
            }
        )
        mock_ak.stock_zh_a_hist.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch("A.600519", days=5)

        assert result.success is True
        assert result.records_count == 3
        mock_ak.stock_zh_a_hist.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_exception_handling(self, mock_ak):
        """Test exception handling during fetch."""
        mock_ak.stock_hk_daily.side_effect = Exception("Network error")

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is False
        assert "Network error" in result.error_message

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_batch(self, mock_ak):
        """Test batch fetching multiple stocks."""
        mock_hk_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-14"]),
                "open": [380.0],
                "high": [385.0],
                "low": [378.0],
                "close": [382.0],
                "volume": [1000000],
            }
        )
        mock_us_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-14"]),
                "open": [140.0],
                "high": [145.0],
                "low": [139.0],
                "close": [143.0],
                "volume": [50000000],
            }
        )
        mock_ak.stock_hk_daily.return_value = mock_hk_df
        mock_ak.stock_us_daily.return_value = mock_us_df

        fetcher = KlineFetcher()
        results = fetcher.fetch_batch(["HK.00700", "US.NVDA"], days=5)

        assert "HK.00700" in results
        assert "US.NVDA" in results
        assert results["HK.00700"].success is True
        assert results["US.NVDA"].success is True

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_with_date_range(self, mock_ak):
        """Test fetching with explicit date range."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-10", "2025-12-11", "2025-12-12"]),
                "open": [375.0, 378.0, 380.0],
                "high": [380.0, 382.0, 385.0],
                "low": [373.0, 376.0, 378.0],
                "close": [378.0, 380.0, 382.0],
                "volume": [900000, 1000000, 1100000],
            }
        )
        mock_ak.stock_hk_daily.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch(
            "HK.00700",
            start_date=date(2025, 12, 10),
            end_date=date(2025, 12, 12),
        )

        assert result.success is True
        assert result.records_count == 3


class TestKlineFetcherDataConversion:
    """Tests for data conversion in KlineFetcher."""

    @patch("fetchers.kline_fetcher.ak")
    def test_decimal_conversion(self, mock_ak):
        """Test that prices are converted to Decimal."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-14"]),
                "open": [380.123],
                "high": [385.456],
                "low": [378.789],
                "close": [382.012],
                "volume": [1000000],
            }
        )
        mock_ak.stock_hk_daily.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is True
        kline = result.data[0]
        assert isinstance(kline.open, Decimal)
        assert isinstance(kline.high, Decimal)
        assert isinstance(kline.low, Decimal)
        assert isinstance(kline.close, Decimal)
        assert kline.open == Decimal("380.123")

    @patch("fetchers.kline_fetcher.ak")
    def test_date_conversion(self, mock_ak):
        """Test that trade_date is converted to date object."""
        mock_df = pd.DataFrame(
            {
                "date": pd.to_datetime(["2025-12-14"]),
                "open": [380.0],
                "high": [385.0],
                "low": [378.0],
                "close": [382.0],
                "volume": [1000000],
            }
        )
        mock_ak.stock_hk_daily.return_value = mock_df

        fetcher = KlineFetcher()
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is True
        kline = result.data[0]
        assert isinstance(kline.trade_date, date)
        assert kline.trade_date == date(2025, 12, 14)


class TestCreateKlineFetcher:
    """Tests for create_kline_fetcher factory function."""

    def test_create_with_default_days(self):
        """Test creating fetcher with default days."""
        fetcher = create_kline_fetcher()
        assert fetcher.default_days == 120

    def test_create_with_custom_days(self):
        """Test creating fetcher with custom days."""
        fetcher = create_kline_fetcher(default_days=60)
        assert fetcher.default_days == 60
