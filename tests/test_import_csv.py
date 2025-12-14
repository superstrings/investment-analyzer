"""Tests for CSV import functionality."""

import csv
import tempfile
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.import_csv import (
    POSITION_COLUMN_MAP,
    TRADE_COLUMN_MAP,
    WATCHLIST_COLUMN_MAP,
    ImportResult,
    find_column,
    import_positions,
    import_trades,
    import_watchlist,
    parse_code,
    parse_date,
    parse_datetime,
    parse_decimal,
    parse_int,
    parse_trade_side,
)


class TestParseCode:
    """Tests for parse_code function."""

    def test_parse_hk_with_prefix(self):
        """Test parsing HK code with prefix."""
        market, code = parse_code("HK.00700")
        assert market == "HK"
        assert code == "00700"

    def test_parse_us_with_prefix(self):
        """Test parsing US code with prefix."""
        market, code = parse_code("US.NVDA")
        assert market == "US"
        assert code == "NVDA"

    def test_parse_numeric_defaults_to_hk(self):
        """Test numeric code defaults to HK."""
        market, code = parse_code("00700")
        assert market == "HK"
        assert code == "00700"

    def test_parse_alphabetic_defaults_to_us(self):
        """Test alphabetic code defaults to US."""
        market, code = parse_code("NVDA")
        assert market == "US"
        assert code == "NVDA"

    def test_parse_a_share(self):
        """Test A-share code detection."""
        market, code = parse_code("600519")
        assert market == "A"
        assert code == "600519"

        market, code = parse_code("000001")
        assert market == "A"
        assert code == "000001"

        market, code = parse_code("300750")
        assert market == "A"
        assert code == "300750"

    def test_parse_with_spaces(self):
        """Test parsing code with spaces."""
        market, code = parse_code("  HK.00700  ")
        assert market == "HK"
        assert code == "00700"

    def test_parse_lowercase(self):
        """Test parsing lowercase market."""
        market, code = parse_code("hk.00700")
        assert market == "HK"
        assert code == "00700"


class TestParseDecimal:
    """Tests for parse_decimal function."""

    def test_parse_integer(self):
        """Test parsing integer."""
        assert parse_decimal(100) == Decimal("100")

    def test_parse_float(self):
        """Test parsing float."""
        assert parse_decimal(100.5) == Decimal("100.5")

    def test_parse_string(self):
        """Test parsing string."""
        assert parse_decimal("100.50") == Decimal("100.50")

    def test_parse_string_with_commas(self):
        """Test parsing string with commas."""
        assert parse_decimal("1,000.50") == Decimal("1000.50")

    def test_parse_none(self):
        """Test parsing None."""
        assert parse_decimal(None) is None

    def test_parse_empty_string(self):
        """Test parsing empty string."""
        assert parse_decimal("") is None

    def test_parse_dash(self):
        """Test parsing dash (common empty marker)."""
        assert parse_decimal("-") is None

    def test_parse_invalid(self):
        """Test parsing invalid value."""
        assert parse_decimal("invalid") is None


class TestParseInt:
    """Tests for parse_int function."""

    def test_parse_integer(self):
        """Test parsing integer."""
        assert parse_int(100) == 100

    def test_parse_float(self):
        """Test parsing float (truncates)."""
        assert parse_int(100.7) == 100

    def test_parse_string(self):
        """Test parsing string."""
        assert parse_int("100") == 100

    def test_parse_string_with_commas(self):
        """Test parsing string with commas."""
        assert parse_int("1,000") == 1000

    def test_parse_none(self):
        """Test parsing None."""
        assert parse_int(None) is None

    def test_parse_empty(self):
        """Test parsing empty string."""
        assert parse_int("") is None


class TestParseDatetime:
    """Tests for parse_datetime function."""

    def test_parse_iso_format(self):
        """Test parsing ISO format."""
        result = parse_datetime("2024-01-15 10:30:00")
        assert result == datetime(2024, 1, 15, 10, 30, 0)

    def test_parse_date_only(self):
        """Test parsing date only."""
        result = parse_datetime("2024-01-15")
        assert result == datetime(2024, 1, 15, 0, 0, 0)

    def test_parse_slash_format(self):
        """Test parsing slash format."""
        result = parse_datetime("2024/01/15")
        assert result == datetime(2024, 1, 15, 0, 0, 0)

    def test_parse_datetime_object(self):
        """Test parsing datetime object."""
        dt = datetime(2024, 1, 15, 10, 30)
        assert parse_datetime(dt) == dt

    def test_parse_date_object(self):
        """Test parsing date object."""
        d = date(2024, 1, 15)
        result = parse_datetime(d)
        assert result == datetime(2024, 1, 15, 0, 0, 0)

    def test_parse_none(self):
        """Test parsing None."""
        assert parse_datetime(None) is None

    def test_parse_empty(self):
        """Test parsing empty string."""
        assert parse_datetime("") is None

    def test_parse_invalid(self):
        """Test parsing invalid value."""
        assert parse_datetime("invalid") is None


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_date(self):
        """Test parsing date."""
        result = parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_datetime_string(self):
        """Test parsing datetime string returns date."""
        result = parse_date("2024-01-15 10:30:00")
        assert result == date(2024, 1, 15)


class TestParseTradeSide:
    """Tests for parse_trade_side function."""

    def test_parse_buy(self):
        """Test parsing BUY."""
        assert parse_trade_side("BUY") == "BUY"
        assert parse_trade_side("buy") == "BUY"
        assert parse_trade_side("B") == "BUY"
        assert parse_trade_side("买") == "BUY"
        assert parse_trade_side("买入") == "BUY"
        assert parse_trade_side("LONG") == "BUY"

    def test_parse_sell(self):
        """Test parsing SELL."""
        assert parse_trade_side("SELL") == "SELL"
        assert parse_trade_side("sell") == "SELL"
        assert parse_trade_side("S") == "SELL"
        assert parse_trade_side("卖") == "SELL"
        assert parse_trade_side("卖出") == "SELL"
        assert parse_trade_side("SHORT") == "SELL"

    def test_parse_none(self):
        """Test parsing None defaults to BUY."""
        assert parse_trade_side(None) == "BUY"

    def test_parse_unknown(self):
        """Test parsing unknown value defaults to BUY."""
        assert parse_trade_side("unknown") == "BUY"


class TestFindColumn:
    """Tests for find_column function."""

    def test_find_exact_match(self):
        """Test finding exact match."""
        headers = ["code", "name", "qty"]
        result = find_column(headers, ["code"])
        assert result == "code"

    def test_find_alias(self):
        """Test finding by alias."""
        headers = ["股票代码", "名称", "数量"]
        result = find_column(headers, ["code", "股票代码", "代码"])
        assert result == "股票代码"

    def test_find_case_insensitive(self):
        """Test case insensitive matching."""
        headers = ["CODE", "NAME"]
        result = find_column(headers, ["code"])
        assert result == "CODE"

    def test_find_not_found(self):
        """Test column not found."""
        headers = ["foo", "bar"]
        result = find_column(headers, ["code"])
        assert result is None

    def test_find_with_spaces(self):
        """Test matching with spaces."""
        headers = ["  code  ", "name"]
        result = find_column(headers, ["code"])
        assert result == "  code  "


class TestImportResult:
    """Tests for ImportResult class."""

    def test_default_values(self):
        """Test default values."""
        result = ImportResult(success=True)
        assert result.success is True
        assert result.imported == 0
        assert result.skipped == 0
        assert result.errors == 0
        assert result.error_messages == []

    def test_add_error(self):
        """Test adding error."""
        result = ImportResult(success=True)
        result.add_error("Error 1")
        result.add_error("Error 2")
        assert result.errors == 2
        assert len(result.error_messages) == 2
        assert "Error 1" in result.error_messages


class TestImportWatchlistUnit:
    """Unit tests for import_watchlist function."""

    def test_missing_code_column(self, tmp_path):
        """Test error when code column is missing."""
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text("name,group\nTest Stock,Group1")

        with patch("scripts.import_csv.get_session"):
            result = import_watchlist(1, csv_path)
            assert result.success is False
            assert "Missing required column: code" in result.error_messages[0]

    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        result = import_watchlist(1, tmp_path / "nonexistent.csv")
        assert result.success is False
        assert "File not found" in result.error_messages[0]


class TestImportPositionsUnit:
    """Unit tests for import_positions function."""

    def test_missing_required_columns(self, tmp_path):
        """Test error when required columns are missing."""
        csv_path = tmp_path / "positions.csv"
        csv_path.write_text("name,price\nTest Stock,100")

        with patch("scripts.import_csv.get_session"):
            result = import_positions(1, csv_path)
            assert result.success is False
            assert "Missing required columns" in result.error_messages[0]

    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        result = import_positions(1, tmp_path / "nonexistent.csv")
        assert result.success is False
        assert "File not found" in result.error_messages[0]


class TestImportTradesUnit:
    """Unit tests for import_trades function."""

    def test_missing_required_columns(self, tmp_path):
        """Test error when required columns are missing."""
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text("name,side\nTest Stock,BUY")

        with patch("scripts.import_csv.get_session"):
            result = import_trades(1, csv_path)
            assert result.success is False
            assert "Missing required columns" in result.error_messages[0]

    def test_file_not_found(self, tmp_path):
        """Test error when file doesn't exist."""
        result = import_trades(1, tmp_path / "nonexistent.csv")
        assert result.success is False
        assert "File not found" in result.error_messages[0]


class TestColumnMaps:
    """Tests for column mapping configurations."""

    def test_watchlist_column_map(self):
        """Test watchlist column map has required keys."""
        assert "code" in WATCHLIST_COLUMN_MAP
        assert "name" in WATCHLIST_COLUMN_MAP
        assert "group" in WATCHLIST_COLUMN_MAP
        assert "notes" in WATCHLIST_COLUMN_MAP

    def test_position_column_map(self):
        """Test position column map has required keys."""
        assert "code" in POSITION_COLUMN_MAP
        assert "qty" in POSITION_COLUMN_MAP
        assert "cost_price" in POSITION_COLUMN_MAP
        assert "market_price" in POSITION_COLUMN_MAP

    def test_trade_column_map(self):
        """Test trade column map has required keys."""
        assert "code" in TRADE_COLUMN_MAP
        assert "qty" in TRADE_COLUMN_MAP
        assert "price" in TRADE_COLUMN_MAP
        assert "side" in TRADE_COLUMN_MAP

    def test_chinese_aliases(self):
        """Test Chinese aliases are included."""
        assert "股票代码" in WATCHLIST_COLUMN_MAP["code"]
        assert "数量" in POSITION_COLUMN_MAP["qty"]
        assert "成交价" in TRADE_COLUMN_MAP["price"]


class TestImportWatchlistMocked:
    """Mocked tests for import_watchlist function."""

    @patch("scripts.import_csv.get_session")
    def test_import_new_items(self, mock_get_session, tmp_path):
        """Test importing new watchlist items."""
        # Create CSV
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text(
            "code,name,group,notes\n"
            "HK.00700,腾讯控股,科技股,核心持仓\n"
            "US.NVDA,英伟达,AI概念,关注\n"
        )

        # Mock session
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_watchlist(1, csv_path)

        assert result.success is True
        assert result.imported == 2
        assert result.skipped == 0
        assert mock_session.add.call_count == 2

    @patch("scripts.import_csv.get_session")
    def test_import_skips_existing(self, mock_get_session, tmp_path):
        """Test importing skips existing items."""
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text("code,name\nHK.00700,腾讯控股\n")

        mock_session = MagicMock()
        # Return existing item
        mock_session.query.return_value.filter_by.return_value.first.return_value = (
            MagicMock()
        )
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_watchlist(1, csv_path)

        assert result.success is True
        assert result.imported == 0
        assert result.skipped == 1

    @patch("scripts.import_csv.get_session")
    def test_import_empty_code_skipped(self, mock_get_session, tmp_path):
        """Test rows with empty code are skipped."""
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text("code,name\n,Empty Code\nHK.00700,腾讯控股\n")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_watchlist(1, csv_path)

        assert result.success is True
        assert result.imported == 1
        assert result.skipped == 1


class TestImportPositionsMocked:
    """Mocked tests for import_positions function."""

    @patch("scripts.import_csv.get_session")
    def test_import_new_positions(self, mock_get_session, tmp_path):
        """Test importing new positions."""
        csv_path = tmp_path / "positions.csv"
        csv_path.write_text(
            "code,name,qty,cost_price,market_price\n"
            "HK.00700,腾讯控股,100,350.00,380.00\n"
            "US.NVDA,英伟达,50,500.00,550.00\n"
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_positions(1, csv_path)

        assert result.success is True
        assert result.imported == 2
        assert result.skipped == 0

    @patch("scripts.import_csv.get_session")
    def test_import_zero_qty_skipped(self, mock_get_session, tmp_path):
        """Test rows with zero quantity are skipped."""
        csv_path = tmp_path / "positions.csv"
        csv_path.write_text("code,qty\nHK.00700,0\nUS.NVDA,100\n")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_positions(1, csv_path)

        assert result.success is True
        assert result.imported == 1
        assert result.skipped == 1

    @patch("scripts.import_csv.get_session")
    def test_import_with_custom_date(self, mock_get_session, tmp_path):
        """Test importing with custom snapshot date."""
        csv_path = tmp_path / "positions.csv"
        csv_path.write_text("code,qty\nHK.00700,100\n")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        custom_date = date(2024, 1, 15)
        result = import_positions(1, csv_path, snapshot_date=custom_date)

        assert result.success is True
        # Verify the snapshot_date was used in the filter
        call_args = mock_session.query.return_value.filter_by.call_args
        assert call_args[1]["snapshot_date"] == custom_date


class TestImportTradesMocked:
    """Mocked tests for import_trades function."""

    @patch("scripts.import_csv.get_session")
    def test_import_new_trades(self, mock_get_session, tmp_path):
        """Test importing new trades."""
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text(
            "deal_id,trade_time,code,name,side,qty,price,amount,fee\n"
            "D123456,2024-01-15 10:30:00,HK.00700,腾讯控股,BUY,100,350.00,35000.00,50.00\n"
            "D123457,2024-01-15 11:00:00,US.NVDA,英伟达,SELL,50,500.00,25000.00,30.00\n"
        )

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_trades(1, csv_path)

        assert result.success is True
        assert result.imported == 2
        assert result.skipped == 0

    @patch("scripts.import_csv.get_session")
    def test_import_generates_deal_id(self, mock_get_session, tmp_path):
        """Test that deal_id is generated if not provided."""
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text("code,qty,price,side\nHK.00700,100,350.00,BUY\n")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_trades(1, csv_path)

        assert result.success is True
        assert result.imported == 1

    @patch("scripts.import_csv.get_session")
    def test_import_chinese_side(self, mock_get_session, tmp_path):
        """Test importing trades with Chinese side values."""
        csv_path = tmp_path / "trades.csv"
        csv_path.write_text("code,qty,price,side\nHK.00700,100,350.00,买入\n")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_trades(1, csv_path)

        assert result.success is True
        assert result.imported == 1


class TestEncodingSupport:
    """Tests for encoding support."""

    @patch("scripts.import_csv.get_session")
    def test_utf8_encoding(self, mock_get_session, tmp_path):
        """Test UTF-8 encoding (default)."""
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text("code,name\nHK.00700,腾讯控股\n", encoding="utf-8")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_watchlist(1, csv_path, encoding="utf-8")

        assert result.success is True
        assert result.imported == 1

    @patch("scripts.import_csv.get_session")
    def test_gbk_encoding(self, mock_get_session, tmp_path):
        """Test GBK encoding."""
        csv_path = tmp_path / "watchlist.csv"
        csv_path.write_text("code,name\nHK.00700,腾讯控股\n", encoding="gbk")

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = import_watchlist(1, csv_path, encoding="gbk")

        assert result.success is True
        assert result.imported == 1
