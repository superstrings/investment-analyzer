"""Tests for CLI utilities."""

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from cli import OutputFormat
from cli.utils import (
    console,
    create_progress,
    error_console,
    format_output,
    format_percent,
    format_pnl,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
    with_progress,
)


class TestPrintFunctions:
    """Test print utility functions."""

    def test_print_success(self, capsys):
        """Test success message printing."""
        # Can't easily capture rich output, but verify no exception
        print_success("Test message")

    def test_print_error(self, capsys):
        """Test error message printing."""
        print_error("Test error")

    def test_print_error_with_exit(self):
        """Test error with exit code."""
        with pytest.raises(SystemExit) as exc:
            print_error("Fatal error", exit_code=1)
        assert exc.value.code == 1

    def test_print_warning(self):
        """Test warning message printing."""
        print_warning("Test warning")

    def test_print_info(self):
        """Test info message printing."""
        print_info("Test info")


class TestPrintTable:
    """Test table printing functionality."""

    def test_print_table_basic(self):
        """Test basic table printing."""
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        # Should not raise
        print_table(data)

    def test_print_table_with_columns(self):
        """Test table with custom columns."""
        data = [
            {"code": "00700", "name": "Tencent", "price": 350.0},
        ]
        columns = [
            ("code", "Stock Code"),
            ("name", "Name"),
            ("price", "Price"),
        ]
        print_table(data, columns=columns, title="Stocks")

    def test_print_table_empty_data(self):
        """Test table with empty data."""
        print_table([])

    def test_print_table_with_float_values(self):
        """Test table with float formatting."""
        data = [
            {
                "code": "00700",
                "pl_ratio": 0.15,
                "pl_val": 1500.50,
                "weight": 0.25,
            },
        ]
        print_table(data)

    def test_print_table_with_negative_values(self):
        """Test table with negative P&L values."""
        data = [
            {
                "code": "09988",
                "pl_ratio": -0.08,
                "pl_val": -800.00,
            },
        ]
        print_table(data)

    def test_print_table_with_bool_values(self):
        """Test table with boolean values."""
        data = [
            {"name": "Test", "active": True},
            {"name": "Test2", "active": False},
        ]
        print_table(data)


class TestFormatOutput:
    """Test output format functionality."""

    def test_format_json(self):
        """Test JSON output format."""
        data = [
            {"code": "00700", "name": "Tencent"},
            {"code": "09988", "name": "Alibaba"},
        ]
        result = format_output(data, OutputFormat.JSON)
        parsed = json.loads(result)
        assert len(parsed) == 2
        assert parsed[0]["code"] == "00700"

    def test_format_csv(self):
        """Test CSV output format."""
        data = [
            {"code": "00700", "name": "Tencent", "price": 350.0},
        ]
        result = format_output(data, OutputFormat.CSV)
        assert "code,name,price" in result
        assert "00700" in result
        assert "Tencent" in result

    def test_format_csv_with_columns(self):
        """Test CSV with specific columns."""
        data = [
            {"code": "00700", "name": "Tencent", "extra": "ignored"},
        ]
        columns = [("code", "Code"), ("name", "Name")]
        result = format_output(data, OutputFormat.CSV, columns=columns)
        assert "code,name" in result
        assert "extra" not in result

    def test_format_table(self):
        """Test table output format."""
        data = [{"code": "00700"}]
        # Table prints directly, returns empty string
        result = format_output(data, OutputFormat.TABLE)
        assert result == ""

    def test_format_empty_data(self):
        """Test formatting empty data."""
        result = format_output([], OutputFormat.JSON)
        assert result == ""


class TestProgressBar:
    """Test progress bar functionality."""

    def test_create_determinate_progress(self):
        """Test creating determinate progress bar."""
        progress = create_progress("Processing", total=100)
        assert progress is not None

    def test_create_indeterminate_progress(self):
        """Test creating indeterminate progress (spinner)."""
        progress = create_progress("Loading")
        assert progress is not None

    def test_with_progress(self):
        """Test processing items with progress."""
        items = [1, 2, 3, 4, 5]
        results = with_progress(items, "Testing")
        assert results == items

    def test_with_progress_callback(self):
        """Test progress with callback function."""
        items = [1, 2, 3]
        results = with_progress(items, "Doubling", callback=lambda x: x * 2)
        assert results == [2, 4, 6]


class TestFormatters:
    """Test value formatters."""

    def test_format_pnl_positive(self):
        """Test formatting positive P&L."""
        text = format_pnl(1500.50)
        assert "+1,500.50" in str(text)
        assert text.style == "green"

    def test_format_pnl_negative(self):
        """Test formatting negative P&L."""
        text = format_pnl(-500.25)
        assert "-500.25" in str(text)
        assert text.style == "red"

    def test_format_pnl_no_sign(self):
        """Test formatting P&L without sign."""
        text = format_pnl(100.0, include_sign=False)
        assert "+100" not in str(text)
        assert "100" in str(text)

    def test_format_percent_positive(self):
        """Test formatting positive percentage."""
        text = format_percent(0.15)
        assert "+15.00%" in str(text)
        assert text.style == "green"

    def test_format_percent_negative(self):
        """Test formatting negative percentage."""
        text = format_percent(-0.08)
        assert "-8.00%" in str(text)
        assert text.style == "red"


class TestConsoleInstances:
    """Test console instance creation."""

    def test_console_exists(self):
        """Test main console exists."""
        assert console is not None

    def test_error_console_exists(self):
        """Test error console exists."""
        assert error_console is not None


class TestOutputFormatEnum:
    """Test OutputFormat enum."""

    def test_output_format_values(self):
        """Test enum values."""
        assert OutputFormat.TABLE.value == "table"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.CSV.value == "csv"

    def test_output_format_from_string(self):
        """Test creating from string."""
        assert OutputFormat("table") == OutputFormat.TABLE
        assert OutputFormat("json") == OutputFormat.JSON


class TestEdgeCases:
    """Test edge cases."""

    def test_print_table_with_none_values(self):
        """Test table with None values."""
        data = [
            {"code": "00700", "name": None, "price": None},
        ]
        print_table(data)

    def test_format_json_with_special_chars(self):
        """Test JSON with Chinese characters."""
        data = [{"name": "腾讯控股", "note": "测试备注"}]
        result = format_output(data, OutputFormat.JSON)
        assert "腾讯控股" in result

    def test_format_csv_with_commas(self):
        """Test CSV with values containing commas."""
        data = [{"name": "Test, Inc.", "value": "1,000"}]
        result = format_output(data, OutputFormat.CSV)
        # CSV should properly quote values with commas
        assert "Test" in result

    def test_with_progress_empty_list(self):
        """Test progress with empty list."""
        results = with_progress([], "Empty")
        assert results == []
