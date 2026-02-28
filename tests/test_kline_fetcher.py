"""Tests for K-line data fetcher module.

Tests the KlineFetcher class and related data types.
Uses mocks for both Futu API and akshare to avoid external dependencies.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from fetchers import (
    KlineData,
    KlineFetcher,
    KlineFetchResult,
    Market,
    create_kline_fetcher,
)


def _make_futu_fetch_fail(fetcher):
    """Helper to make Futu path raise so akshare fallback is tested."""
    fetcher._get_futu_ctx = MagicMock(side_effect=Exception("Futu not available"))


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
        assert fetcher.default_days == 250
        assert fetcher.futu_host == "127.0.0.1"
        assert fetcher.futu_port == 11111
        assert fetcher._futu_ctx is None

    def test_custom_init(self):
        """Test custom initialization."""
        fetcher = KlineFetcher(
            default_days=60, futu_host="192.168.1.1", futu_port=22222
        )
        assert fetcher.default_days == 60
        assert fetcher.futu_host == "192.168.1.1"
        assert fetcher.futu_port == 22222


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

    def test_parse_4digit_detects_jp(self):
        """Test 4-digit numeric code detects as JP market."""
        fetcher = KlineFetcher()
        market, code = fetcher._parse_code("7203")
        assert market == Market.JP
        assert code == "7203"

    def test_parse_numeric_defaults_to_hk(self):
        """Test numeric code without pattern defaults to HK."""
        fetcher = KlineFetcher()
        # 3-digit or other non-pattern numeric codes default to HK
        market, code = fetcher._parse_code("123")
        assert market == Market.HK
        assert code == "00123"  # Padded to 5 digits


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
    """Tests for KlineFetcher with mocked APIs (akshare fallback path)."""

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_akshare_fallback(self, mock_ak):
        """Test HK stock fetch via akshare when Futu fails."""
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
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch(
            "HK.00700",
            start_date=date(2025, 12, 10),
            end_date=date(2025, 12, 15),
        )

        assert result.success is True
        assert result.records_count == 3
        mock_ak.stock_hk_daily.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_empty_result(self, mock_ak):
        """Test HK stock fetch with empty result from akshare."""
        mock_ak.stock_hk_daily.return_value = pd.DataFrame()

        fetcher = KlineFetcher()
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is False
        assert "No data returned" in result.error_message

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_hk_none_result(self, mock_ak):
        """Test HK stock fetch with None result from akshare."""
        mock_ak.stock_hk_daily.return_value = None

        fetcher = KlineFetcher()
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is False
        assert "No data returned" in result.error_message

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_us_success(self, mock_ak):
        """Test successful US stock fetch (always via akshare)."""
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
        result = fetcher.fetch(
            "US.NVDA",
            start_date=date(2025, 12, 10),
            end_date=date(2025, 12, 15),
        )

        assert result.success is True
        assert result.records_count == 2
        mock_ak.stock_us_daily.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_a_share_akshare_fallback(self, mock_ak):
        """Test A-share fetch via akshare when Futu fails."""
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
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch("A.600519", days=5)

        assert result.success is True
        assert result.records_count == 3
        mock_ak.stock_zh_a_hist.assert_called_once()

    @patch("fetchers.kline_fetcher.ak")
    def test_fetch_exception_handling(self, mock_ak):
        """Test exception handling when both Futu and akshare fail."""
        mock_ak.stock_hk_daily.side_effect = Exception("Network error")

        fetcher = KlineFetcher()
        _make_futu_fetch_fail(fetcher)
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
        _make_futu_fetch_fail(fetcher)
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
        _make_futu_fetch_fail(fetcher)
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
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch(
            "HK.00700",
            start_date=date(2025, 12, 13),
            end_date=date(2025, 12, 15),
        )

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
        _make_futu_fetch_fail(fetcher)
        result = fetcher.fetch(
            "HK.00700",
            start_date=date(2025, 12, 13),
            end_date=date(2025, 12, 15),
        )

        assert result.success is True
        kline = result.data[0]
        assert isinstance(kline.trade_date, date)
        assert kline.trade_date == date(2025, 12, 14)


class TestToFutuCode:
    """Tests for _to_futu_code method."""

    def test_hk_code(self):
        fetcher = KlineFetcher()
        assert fetcher._to_futu_code(Market.HK, "00700") == "HK.00700"
        assert fetcher._to_futu_code(Market.HK, "01378") == "HK.01378"

    def test_a_share_shanghai(self):
        fetcher = KlineFetcher()
        assert fetcher._to_futu_code(Market.A, "600519") == "SH.600519"
        assert fetcher._to_futu_code(Market.A, "601318") == "SH.601318"
        assert fetcher._to_futu_code(Market.A, "688981") == "SH.688981"

    def test_a_share_shenzhen(self):
        fetcher = KlineFetcher()
        assert fetcher._to_futu_code(Market.A, "000975") == "SZ.000975"
        assert fetcher._to_futu_code(Market.A, "002594") == "SZ.002594"
        assert fetcher._to_futu_code(Market.A, "300750") == "SZ.300750"

    def test_us_code(self):
        fetcher = KlineFetcher()
        assert fetcher._to_futu_code(Market.US, "NVDA") == "US.NVDA"


class TestFutuFetchPath:
    """Tests for Futu API fetch path."""

    def test_fetch_hk_via_futu(self):
        """Test HK fetch succeeds via Futu without touching akshare."""
        futu_df = pd.DataFrame(
            {
                "code": ["HK.00700"] * 3,
                "time_key": ["2025-12-12", "2025-12-13", "2025-12-14"],
                "open": [378.0, 380.0, 382.0],
                "high": [382.0, 385.0, 388.0],
                "low": [376.0, 378.0, 380.0],
                "close": [380.0, 382.0, 385.0],
                "volume": [1000000, 1200000, 1100000],
                "turnover": [380000000, 460000000, 420000000],
                "turnover_rate": [0.1, 0.12, 0.11],
                "change_rate": [0.5, 0.53, 0.79],
            }
        )

        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.return_value = (0, futu_df, None)  # RET_OK=0
        fetcher._futu_ctx = mock_ctx

        with patch("fetchers.kline_fetcher.ak") as mock_ak:
            result = fetcher.fetch("HK.00700", days=5)
            mock_ak.stock_hk_daily.assert_not_called()

        assert result.success is True
        assert result.records_count == 3
        assert result.data[0].market == Market.HK
        assert result.data[0].code == "00700"

    def test_fetch_a_share_via_futu(self):
        """Test A-share fetch succeeds via Futu without touching akshare."""
        futu_df = pd.DataFrame(
            {
                "code": ["SH.600519"] * 2,
                "time_key": ["2025-12-13", "2025-12-14"],
                "open": [1820.0, 1835.0],
                "high": [1850.0, 1860.0],
                "low": [1810.0, 1825.0],
                "close": [1840.0, 1855.0],
                "volume": [12000, 11000],
                "turnover": [21600000, 20350000],
                "turnover_rate": [0.6, 0.55],
                "change_rate": [1.1, 0.82],
            }
        )

        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.return_value = (0, futu_df, None)
        fetcher._futu_ctx = mock_ctx

        with patch("fetchers.kline_fetcher.ak") as mock_ak:
            result = fetcher.fetch("A.600519", days=5)
            mock_ak.stock_zh_a_hist.assert_not_called()

        assert result.success is True
        assert result.records_count == 2
        assert result.data[0].market == Market.A

    def test_futu_pagination(self):
        """Test Futu pagination with page_req_key."""
        page1_df = pd.DataFrame(
            {
                "code": ["HK.00700"],
                "time_key": ["2025-12-12"],
                "open": [378.0],
                "high": [382.0],
                "low": [376.0],
                "close": [380.0],
                "volume": [1000000],
                "turnover": [380000000],
            }
        )
        page2_df = pd.DataFrame(
            {
                "code": ["HK.00700"],
                "time_key": ["2025-12-13"],
                "open": [380.0],
                "high": [385.0],
                "low": [378.0],
                "close": [382.0],
                "volume": [1200000],
                "turnover": [460000000],
            }
        )

        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.side_effect = [
            (0, page1_df, "next_page_key"),
            (0, page2_df, None),
        ]
        fetcher._futu_ctx = mock_ctx

        result = fetcher.fetch("HK.00700", days=5)

        assert result.success is True
        assert result.records_count == 2
        assert mock_ctx.request_history_kline.call_count == 2

    def test_futu_api_error_falls_back_to_akshare(self):
        """Test that Futu API error triggers akshare fallback."""
        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.return_value = (
            -1,  # RET_ERROR
            "Request timeout",
            None,
        )
        fetcher._futu_ctx = mock_ctx

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

        with patch("fetchers.kline_fetcher.ak") as mock_ak:
            mock_ak.stock_hk_daily.return_value = mock_hk_df
            result = fetcher.fetch(
                "HK.00700",
                start_date=date(2025, 12, 13),
                end_date=date(2025, 12, 15),
            )
            mock_ak.stock_hk_daily.assert_called_once()

        assert result.success is True
        assert result.records_count == 1

    def test_us_falls_back_to_akshare(self):
        """Test that US stocks fall back to akshare when Futu fails."""
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

        fetcher = KlineFetcher()
        # Set a _futu_ctx that fails (simulating Futu unavailable)
        mock_ctx = MagicMock()
        mock_ctx.request_history_kline.return_value = (1, "error", None)
        fetcher._futu_ctx = mock_ctx

        with patch("fetchers.kline_fetcher.ak") as mock_ak:
            mock_ak.stock_us_daily.return_value = mock_us_df
            result = fetcher.fetch("US.NVDA", days=5)

        assert result.success is True


class TestFutuContextLifecycle:
    """Tests for Futu context management."""

    def test_close_futu_ctx(self):
        """Test _close_futu_ctx properly closes and nullifies."""
        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        fetcher._futu_ctx = mock_ctx

        fetcher._close_futu_ctx()

        mock_ctx.close.assert_called_once()
        assert fetcher._futu_ctx is None

    def test_close_futu_ctx_handles_error(self):
        """Test _close_futu_ctx handles close() errors gracefully."""
        fetcher = KlineFetcher()
        mock_ctx = MagicMock()
        mock_ctx.close.side_effect = Exception("Already closed")
        fetcher._futu_ctx = mock_ctx

        fetcher._close_futu_ctx()
        assert fetcher._futu_ctx is None

    def test_close_futu_ctx_when_none(self):
        """Test _close_futu_ctx is a no-op when context is None."""
        fetcher = KlineFetcher()
        fetcher._close_futu_ctx()  # Should not raise
        assert fetcher._futu_ctx is None


class TestCreateKlineFetcher:
    """Tests for create_kline_fetcher factory function."""

    def test_create_with_default_days(self):
        """Test creating fetcher with default days."""
        fetcher = create_kline_fetcher()
        assert fetcher.default_days == 250

    def test_create_with_custom_days(self):
        """Test creating fetcher with custom days."""
        fetcher = create_kline_fetcher(default_days=60)
        assert fetcher.default_days == 60

    def test_create_reads_futu_settings(self):
        """Test that factory reads Futu settings from config."""
        fetcher = create_kline_fetcher()
        assert fetcher.futu_host == "127.0.0.1"
        assert fetcher.futu_port == 11111

    def test_create_with_custom_futu_params(self):
        """Test factory with explicit Futu params."""
        fetcher = create_kline_fetcher(futu_host="10.0.0.1", futu_port=22222)
        assert fetcher.futu_host == "10.0.0.1"
        assert fetcher.futu_port == 22222
