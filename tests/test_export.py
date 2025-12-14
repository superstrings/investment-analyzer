"""
Tests for export service.

Tests data export functionality to CSV, Excel, and JSON formats.
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.export_service import (
    DateRange,
    ExportConfig,
    ExportFormat,
    ExportResult,
    ExportService,
    create_export_service,
    export_all_to_excel,
    export_klines_to_csv,
    export_positions_to_csv,
    export_trades_to_csv,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def export_config(temp_output_dir):
    """Create export config with temp directory."""
    return ExportConfig(output_dir=temp_output_dir)


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = MagicMock()
    return session


@pytest.fixture
def mock_position():
    """Create a mock position object."""
    pos = MagicMock()
    pos.id = 1
    pos.account_id = 1
    pos.snapshot_date = datetime(2024, 1, 15).date()
    pos.market = "HK"
    pos.code = "00700"
    pos.stock_name = "腾讯控股"
    pos.qty = 100
    pos.can_sell_qty = 100
    pos.cost_price = 350.0
    pos.market_price = 380.0
    pos.market_val = 38000.0
    pos.pl_val = 3000.0
    pos.pl_ratio = 0.0857
    pos.position_side = "LONG"
    pos.created_at = datetime(2024, 1, 15, 10, 30, 0)
    return pos


@pytest.fixture
def mock_trade():
    """Create a mock trade object."""
    trade = MagicMock()
    trade.id = 1
    trade.account_id = 1
    trade.deal_id = "D001"
    trade.order_id = "O001"
    trade.trade_time = datetime(2024, 1, 10, 14, 30, 0)
    trade.market = "HK"
    trade.code = "00700"
    trade.stock_name = "腾讯控股"
    trade.trd_side = "BUY"
    trade.qty = 100
    trade.price = 350.0
    trade.amount = 35000.0
    trade.fee = 50.0
    trade.currency = "HKD"
    return trade


@pytest.fixture
def mock_kline():
    """Create a mock kline object."""
    kline = MagicMock()
    kline.trade_date = datetime(2024, 1, 15).date()
    kline.market = "HK"
    kline.code = "00700"
    kline.open = 375.0
    kline.high = 382.0
    kline.low = 372.0
    kline.close = 380.0
    kline.volume = 10000000
    kline.turnover = 3800000000.0
    kline.ma5 = 376.0
    kline.ma10 = 370.0
    kline.ma20 = 365.0
    kline.ma60 = 355.0
    return kline


@pytest.fixture
def mock_watchlist():
    """Create a mock watchlist item."""
    item = MagicMock()
    item.id = 1
    item.market = "HK"
    item.code = "00700"
    item.stock_name = "腾讯控股"
    item.group_name = "Tech"
    item.notes = "Long term hold"
    item.sort_order = 0
    item.is_active = True
    item.created_at = datetime(2024, 1, 1, 9, 0, 0)
    return item


# ============================================================================
# ExportFormat Tests
# ============================================================================


class TestExportFormat:
    """Test ExportFormat enum."""

    def test_format_values(self):
        """Test format enum values."""
        assert ExportFormat.CSV == "csv"
        assert ExportFormat.EXCEL == "xlsx"
        assert ExportFormat.JSON == "json"

    def test_format_from_string(self):
        """Test creating format from string."""
        assert ExportFormat("csv") == ExportFormat.CSV
        assert ExportFormat("xlsx") == ExportFormat.EXCEL
        assert ExportFormat("json") == ExportFormat.JSON


# ============================================================================
# ExportConfig Tests
# ============================================================================


class TestExportConfig:
    """Test ExportConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ExportConfig()

        assert config.output_dir == Path("exports")
        assert config.include_headers is True
        assert config.date_format == "%Y-%m-%d"
        assert config.datetime_format == "%Y-%m-%d %H:%M:%S"
        assert config.decimal_places == 4
        assert config.encoding == "utf-8"

    def test_custom_values(self, temp_output_dir):
        """Test custom configuration values."""
        config = ExportConfig(
            output_dir=temp_output_dir,
            decimal_places=2,
            encoding="utf-16",
        )

        assert config.output_dir == temp_output_dir
        assert config.decimal_places == 2
        assert config.encoding == "utf-16"


# ============================================================================
# ExportResult Tests
# ============================================================================


class TestExportResult:
    """Test ExportResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = ExportResult(success=True, format=ExportFormat.CSV)

        assert result.success is True
        assert result.format == ExportFormat.CSV
        assert result.file_path is None
        assert result.records_exported == 0
        assert result.error is None

    def test_success_result(self, temp_output_dir):
        """Test successful export result."""
        file_path = temp_output_dir / "test.csv"
        result = ExportResult(
            success=True,
            format=ExportFormat.CSV,
            file_path=file_path,
            records_exported=100,
        )

        assert result.success is True
        assert result.file_path == file_path
        assert result.records_exported == 100

    def test_error_result(self):
        """Test error export result."""
        result = ExportResult(
            success=False,
            format=ExportFormat.CSV,
            error="Database connection failed",
        )

        assert result.success is False
        assert result.error == "Database connection failed"


# ============================================================================
# DateRange Tests
# ============================================================================


class TestDateRange:
    """Test DateRange dataclass."""

    def test_default_values(self):
        """Test default values."""
        dr = DateRange()

        assert dr.start_date is None
        assert dr.end_date is None

    def test_with_dates(self):
        """Test with specific dates."""
        start = datetime(2024, 1, 1)
        end = datetime(2024, 12, 31)

        dr = DateRange(start_date=start, end_date=end)

        assert dr.start_date == start
        assert dr.end_date == end


# ============================================================================
# ExportService Tests
# ============================================================================


class TestExportService:
    """Test ExportService class."""

    def test_initialization_default(self):
        """Test default initialization."""
        service = ExportService()

        assert service.session is None
        assert service.config is not None
        assert service.config.output_dir == Path("exports")

    def test_initialization_with_config(self, export_config):
        """Test initialization with custom config."""
        service = ExportService(config=export_config)

        assert service.config == export_config

    def test_initialization_creates_output_dir(self, temp_output_dir):
        """Test that output directory is created."""
        output_dir = temp_output_dir / "new_exports"
        config = ExportConfig(output_dir=output_dir)

        ExportService(config=config)

        assert output_dir.exists()


class TestExportPositions:
    """Test export_positions method."""

    def test_export_positions_csv(self, mock_session, mock_position, temp_output_dir):
        """Test exporting positions to CSV."""
        # Setup mock to return account IDs first, then positions
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_session.execute.side_effect = [mock_accounts, mock_positions]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 1
        assert result.file_path is not None
        assert result.file_path.suffix == ".csv"
        assert result.file_path.exists()

        # Verify CSV content
        df = pd.read_csv(result.file_path, dtype={"code": str})
        assert len(df) == 1
        assert df.iloc[0]["code"] == "00700"
        assert df.iloc[0]["market"] == "HK"

    def test_export_positions_json(self, mock_session, mock_position, temp_output_dir):
        """Test exporting positions to JSON."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_session.execute.side_effect = [mock_accounts, mock_positions]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.JSON)

        assert result.success is True
        assert result.file_path.suffix == ".json"

        # Verify JSON content
        with open(result.file_path) as f:
            data = json.load(f)
        assert len(data) == 1
        assert data[0]["code"] == "00700"

    def test_export_positions_excel(self, mock_session, mock_position, temp_output_dir):
        """Test exporting positions to Excel."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_session.execute.side_effect = [mock_accounts, mock_positions]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.EXCEL)

        assert result.success is True
        assert result.file_path.suffix == ".xlsx"
        assert result.file_path.exists()

    def test_export_positions_empty(self, mock_session, temp_output_dir):
        """Test exporting when no accounts exist."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 0
        assert result.error == "No accounts found for user"


class TestExportTrades:
    """Test export_trades method."""

    def test_export_trades_csv(self, mock_session, mock_trade, temp_output_dir):
        """Test exporting trades to CSV."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_trades = MagicMock()
        mock_trades.scalars.return_value.all.return_value = [mock_trade]
        mock_session.execute.side_effect = [mock_accounts, mock_trades]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_trades(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 1
        assert result.file_path.exists()

    def test_export_trades_with_date_range(self, mock_session, mock_trade, temp_output_dir):
        """Test exporting trades with date range filter."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_trades = MagicMock()
        mock_trades.scalars.return_value.all.return_value = [mock_trade]
        mock_session.execute.side_effect = [mock_accounts, mock_trades]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        date_range = DateRange(
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
        )

        result = service.export_trades(
            user_id=1, format=ExportFormat.CSV, date_range=date_range
        )

        assert result.success is True

    def test_export_trades_empty(self, mock_session, temp_output_dir):
        """Test exporting when no accounts exist."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_trades(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 0
        assert result.error == "No accounts found for user"


class TestExportKlines:
    """Test export_klines method."""

    def test_export_klines_csv(self, mock_session, mock_kline, temp_output_dir):
        """Test exporting klines to CSV."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_kline]
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_klines(code="HK.00700", format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 1

    def test_export_klines_with_limit(self, mock_session, mock_kline, temp_output_dir):
        """Test exporting klines with limit."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_kline]
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_klines(
            code="HK.00700", format=ExportFormat.CSV, limit=100
        )

        assert result.success is True

    def test_export_klines_no_market_prefix(self, mock_session, mock_kline, temp_output_dir):
        """Test exporting klines without market prefix."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_kline]
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_klines(code="00700", format=ExportFormat.CSV)

        assert result.success is True


class TestExportWatchlist:
    """Test export_watchlist method."""

    def test_export_watchlist_csv(self, mock_session, mock_watchlist, temp_output_dir):
        """Test exporting watchlist to CSV."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = [mock_watchlist]
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_watchlist(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 1

    def test_export_watchlist_empty(self, mock_session, temp_output_dir):
        """Test exporting empty watchlist."""
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_watchlist(user_id=1, format=ExportFormat.CSV)

        assert result.success is True
        assert result.records_exported == 0


class TestExportAll:
    """Test export_all method."""

    def test_export_all_excel(
        self, mock_session, mock_position, mock_trade, mock_watchlist, temp_output_dir
    ):
        """Test exporting all data to Excel."""
        # Setup mock to return data in order: account_ids, positions, trades, watchlist
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_trades = MagicMock()
        mock_trades.scalars.return_value.all.return_value = [mock_trade]
        mock_watchlists = MagicMock()
        mock_watchlists.scalars.return_value.all.return_value = [mock_watchlist]

        mock_session.execute.side_effect = [
            mock_accounts,
            mock_positions,
            mock_trades,
            mock_watchlists,
        ]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_all(user_id=1, format=ExportFormat.EXCEL)

        assert result.success is True
        assert result.file_path.suffix == ".xlsx"
        assert result.records_exported == 3  # 1 position + 1 trade + 1 watchlist

    def test_export_all_no_data(self, mock_session, temp_output_dir):
        """Test exporting when no data exists."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = []  # No accounts
        mock_watchlists = MagicMock()
        mock_watchlists.scalars.return_value.all.return_value = []  # No watchlist

        mock_session.execute.side_effect = [mock_accounts, mock_watchlists]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_all(user_id=1, format=ExportFormat.EXCEL)

        assert result.success is True
        assert result.records_exported == 0


# ============================================================================
# Factory Function Tests
# ============================================================================


class TestCreateExportService:
    """Test create_export_service factory function."""

    def test_default_creation(self):
        """Test creating service with defaults."""
        service = create_export_service()

        assert service is not None
        assert service.session is None

    def test_with_output_dir(self, temp_output_dir):
        """Test creating service with custom output dir."""
        service = create_export_service(output_dir=temp_output_dir)

        assert service.config.output_dir == temp_output_dir


# ============================================================================
# Convenience Function Tests
# ============================================================================


class TestConvenienceFunctions:
    """Test convenience export functions."""

    @patch("services.export_service.get_session")
    def test_export_positions_to_csv(self, mock_get_session, temp_output_dir):
        """Test export_positions_to_csv function."""
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute
        mock_get_session.return_value = mock_session

        result = export_positions_to_csv(user_id=1, output_dir=temp_output_dir)

        assert result.format == ExportFormat.CSV

    @patch("services.export_service.get_session")
    def test_export_trades_to_csv(self, mock_get_session, temp_output_dir):
        """Test export_trades_to_csv function."""
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute
        mock_get_session.return_value = mock_session

        result = export_trades_to_csv(
            user_id=1,
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            output_dir=temp_output_dir,
        )

        assert result.format == ExportFormat.CSV

    @patch("services.export_service.get_session")
    def test_export_klines_to_csv(self, mock_get_session, temp_output_dir):
        """Test export_klines_to_csv function."""
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute
        mock_get_session.return_value = mock_session

        result = export_klines_to_csv(
            code="HK.00700",
            output_dir=temp_output_dir,
        )

        assert result.format == ExportFormat.CSV

    @patch("services.export_service.get_session")
    def test_export_all_to_excel(self, mock_get_session, temp_output_dir):
        """Test export_all_to_excel function."""
        mock_session = MagicMock()
        mock_execute = MagicMock()
        mock_execute.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_execute
        mock_get_session.return_value = mock_session

        result = export_all_to_excel(user_id=1, output_dir=temp_output_dir)

        assert result.format == ExportFormat.EXCEL


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error handling in export service."""

    def test_export_handles_exception(self, temp_output_dir):
        """Test that export handles exceptions gracefully."""
        mock_session = MagicMock()
        mock_session.execute.side_effect = Exception("Database error")

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.CSV)

        assert result.success is False
        assert "Database error" in result.error


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for export service."""

    def test_imports_from_services(self):
        """Test that export service can be imported from services."""
        from services import (
            DateRange,
            ExportConfig,
            ExportFormat,
            ExportResult,
            ExportService,
            create_export_service,
        )

        assert ExportService is not None
        assert ExportFormat is not None
        assert create_export_service is not None

    def test_export_csv_content_format(self, mock_session, mock_position, temp_output_dir):
        """Test CSV content format."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_session.execute.side_effect = [mock_accounts, mock_positions]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.CSV)

        # Read and verify CSV structure
        df = pd.read_csv(result.file_path)
        expected_columns = [
            "id", "account_id", "snapshot_date", "market", "code", "stock_name",
            "qty", "can_sell_qty", "cost_price", "market_price", "market_val",
            "pl_val", "pl_ratio", "position_side", "created_at"
        ]
        assert list(df.columns) == expected_columns

    def test_export_json_content_format(self, mock_session, mock_position, temp_output_dir):
        """Test JSON content format."""
        mock_accounts = MagicMock()
        mock_accounts.scalars.return_value.all.return_value = [1]
        mock_positions = MagicMock()
        mock_positions.scalars.return_value.all.return_value = [mock_position]
        mock_session.execute.side_effect = [mock_accounts, mock_positions]

        config = ExportConfig(output_dir=temp_output_dir)
        service = ExportService(session=mock_session, config=config)

        result = service.export_positions(user_id=1, format=ExportFormat.JSON)

        # Read and verify JSON structure
        with open(result.file_path) as f:
            data = json.load(f)

        assert isinstance(data, list)
        assert len(data) == 1
        assert "market" in data[0]
        assert "code" in data[0]
        assert "stock_name" in data[0]
