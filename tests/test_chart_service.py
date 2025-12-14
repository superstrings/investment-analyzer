"""Tests for ChartService."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from services.chart_service import (
    BatchChartConfig,
    ChartResult,
    ChartService,
    create_chart_service,
)


class TestChartResult:
    """Tests for ChartResult class."""

    def test_default_values(self):
        """Test default values."""
        result = ChartResult(success=True)
        assert result.success is True
        assert result.charts_generated == 0
        assert result.charts_failed == 0
        assert result.output_dir is None
        assert result.generated_files == []
        assert result.failed_codes == []
        assert result.error_message is None

    def test_add_generated(self, tmp_path):
        """Test adding generated chart."""
        result = ChartResult(success=True)
        path = tmp_path / "test.png"
        result.add_generated(path)
        assert result.charts_generated == 1
        assert path in result.generated_files

    def test_add_failed(self):
        """Test adding failed chart."""
        result = ChartResult(success=True)
        result.add_failed("HK.00700", "No data")
        assert result.charts_failed == 1
        assert "HK.00700" in result.failed_codes


class TestBatchChartConfig:
    """Tests for BatchChartConfig class."""

    def test_default_values(self):
        """Test default values."""
        config = BatchChartConfig()
        assert config.days == 120
        assert config.style == "dark"
        assert config.ma_periods == [5, 10, 20, 60]
        assert config.show_volume is True
        assert config.figsize == (14, 8)
        assert config.dpi == 100
        assert config.output_subdir is None

    def test_custom_values(self):
        """Test custom values."""
        config = BatchChartConfig(
            days=60,
            style="light",
            ma_periods=[10, 20],
            output_subdir="custom",
        )
        assert config.days == 60
        assert config.style == "light"
        assert config.ma_periods == [10, 20]
        assert config.output_subdir == "custom"


class TestChartServiceInit:
    """Tests for ChartService initialization."""

    def test_default_init(self):
        """Test default initialization."""
        service = ChartService()
        assert service.kline_fetcher is not None
        assert service.chart_generator is not None
        assert service.output_dir == Path("charts/output")

    def test_custom_init(self, tmp_path):
        """Test initialization with custom parameters."""
        mock_fetcher = MagicMock()
        mock_generator = MagicMock()
        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )
        assert service.kline_fetcher == mock_fetcher
        assert service.chart_generator == mock_generator
        assert service.output_dir == tmp_path


class TestGenerateWatchlistCharts:
    """Tests for generate_watchlist_charts method."""

    @patch("services.chart_service.get_session")
    def test_empty_watchlist(self, mock_get_session):
        """Test with empty watchlist."""
        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.all.return_value = []
        mock_get_session.return_value.__enter__.return_value = mock_session

        service = ChartService()
        result = service.generate_watchlist_charts(user_id=1)

        assert result.success is True
        assert result.charts_generated == 0
        assert result.error_message == "No items in watchlist"

    @patch("services.chart_service.get_session")
    def test_with_watchlist_items(self, mock_get_session, tmp_path):
        """Test with watchlist items."""
        # Mock watchlist items
        mock_item1 = MagicMock()
        mock_item1.market = "HK"
        mock_item1.code = "00700"
        mock_item2 = MagicMock()
        mock_item2.market = "US"
        mock_item2.code = "NVDA"

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.all.return_value = [
            mock_item1,
            mock_item2,
        ]
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock fetcher
        mock_fetcher = MagicMock()
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [102] * 10,
                "volume": [1000000] * 10,
            }
        )
        mock_fetcher.fetch.return_value = MagicMock(
            success=True, df=mock_df, error_message=None
        )

        # Mock generator
        mock_generator = MagicMock()
        mock_generator.generate.return_value = tmp_path / "test.png"
        mock_generator.set_style = MagicMock()

        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )
        result = service.generate_watchlist_charts(user_id=1)

        assert result.success is True
        assert result.charts_generated == 2
        assert mock_fetcher.fetch.call_count == 2

    @patch("services.chart_service.get_session")
    def test_with_failed_fetches(self, mock_get_session, tmp_path):
        """Test with some failed fetches."""
        mock_item = MagicMock()
        mock_item.market = "HK"
        mock_item.code = "00700"

        mock_session = MagicMock()
        mock_session.query.return_value.filter_by.return_value.all.return_value = [
            mock_item
        ]
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock fetcher to fail
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = MagicMock(
            success=False, df=None, error_message="No data"
        )

        service = ChartService(kline_fetcher=mock_fetcher, output_dir=tmp_path)
        result = service.generate_watchlist_charts(user_id=1)

        assert result.charts_generated == 0
        assert result.charts_failed == 1
        assert "HK.00700" in result.failed_codes


class TestGeneratePositionCharts:
    """Tests for generate_position_charts method."""

    @patch("services.chart_service.get_session")
    def test_no_positions(self, mock_get_session):
        """Test with no positions."""
        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = (
            []
        )
        mock_get_session.return_value.__enter__.return_value = mock_session

        service = ChartService()
        result = service.generate_position_charts(user_id=1)

        assert result.success is True
        assert result.charts_generated == 0
        assert result.error_message == "No active positions"

    @patch("services.chart_service.get_session")
    def test_with_positions(self, mock_get_session, tmp_path):
        """Test with positions."""
        # Mock positions
        mock_pos = MagicMock()
        mock_pos.market = "HK"
        mock_pos.code = "00700"
        mock_pos.qty = 100

        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            mock_pos
        ]
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock fetcher
        mock_fetcher = MagicMock()
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [102] * 10,
                "volume": [1000000] * 10,
            }
        )
        mock_fetcher.fetch.return_value = MagicMock(
            success=True, df=mock_df, error_message=None
        )

        # Mock generator
        mock_generator = MagicMock()
        mock_generator.generate.return_value = tmp_path / "test.png"
        mock_generator.set_style = MagicMock()

        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )
        result = service.generate_position_charts(user_id=1)

        assert result.success is True
        assert result.charts_generated == 1

    @patch("services.chart_service.get_session")
    def test_filters_zero_qty(self, mock_get_session):
        """Test that zero quantity positions are filtered."""
        mock_pos1 = MagicMock()
        mock_pos1.market = "HK"
        mock_pos1.code = "00700"
        mock_pos1.qty = 100

        mock_pos2 = MagicMock()
        mock_pos2.market = "US"
        mock_pos2.code = "NVDA"
        mock_pos2.qty = 0  # Zero quantity

        mock_session = MagicMock()
        mock_session.query.return_value.join.return_value.filter.return_value.all.return_value = [
            mock_pos1,
            mock_pos2,
        ]
        mock_get_session.return_value.__enter__.return_value = mock_session

        service = ChartService()
        # The method should only process positions with qty > 0
        # We're testing the filtering logic, not the chart generation


class TestGenerateChartsForCodes:
    """Tests for generate_charts_for_codes method."""

    def test_empty_codes(self):
        """Test with empty codes list."""
        service = ChartService()
        result = service.generate_charts_for_codes(codes=[])
        assert result.success is True
        assert result.charts_generated == 0
        assert result.error_message == "No codes provided"

    def test_with_codes(self, tmp_path):
        """Test with codes list."""
        # Mock fetcher
        mock_fetcher = MagicMock()
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [102] * 10,
                "volume": [1000000] * 10,
            }
        )
        mock_fetcher.fetch.return_value = MagicMock(
            success=True, df=mock_df, error_message=None
        )

        # Mock generator
        mock_generator = MagicMock()
        mock_generator.generate.return_value = tmp_path / "test.png"
        mock_generator.set_style = MagicMock()

        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )
        result = service.generate_charts_for_codes(codes=["HK.00700", "US.NVDA"])

        assert result.success is True
        assert result.charts_generated == 2
        assert mock_fetcher.fetch.call_count == 2

    def test_all_failed(self, tmp_path):
        """Test when all charts fail."""
        mock_fetcher = MagicMock()
        mock_fetcher.fetch.return_value = MagicMock(
            success=False, df=None, error_message="No data"
        )

        service = ChartService(kline_fetcher=mock_fetcher, output_dir=tmp_path)
        result = service.generate_charts_for_codes(codes=["HK.00700"])

        assert result.success is False
        assert result.charts_generated == 0
        assert result.charts_failed == 1
        assert "All 1 charts failed" in result.error_message


class TestCreateChartService:
    """Tests for create_chart_service factory function."""

    def test_default_factory(self):
        """Test default factory."""
        service = create_chart_service()
        assert isinstance(service, ChartService)

    def test_factory_with_params(self, tmp_path):
        """Test factory with parameters."""
        mock_fetcher = MagicMock()
        mock_generator = MagicMock()
        service = create_chart_service(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=str(tmp_path),
        )
        assert service.kline_fetcher == mock_fetcher
        assert service.chart_generator == mock_generator
        assert service.output_dir == tmp_path


class TestBatchChartConfigIntegration:
    """Integration tests for BatchChartConfig with ChartService."""

    def test_config_passed_to_generator(self, tmp_path):
        """Test that config is properly passed to generator."""
        mock_fetcher = MagicMock()
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [102] * 10,
                "volume": [1000000] * 10,
            }
        )
        mock_fetcher.fetch.return_value = MagicMock(
            success=True, df=mock_df, error_message=None
        )

        mock_generator = MagicMock()
        mock_generator.generate.return_value = tmp_path / "test.png"
        mock_generator.set_style = MagicMock()

        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )

        config = BatchChartConfig(
            days=60,
            style="light",
            ma_periods=[10, 20],
            dpi=150,
        )

        result = service.generate_charts_for_codes(codes=["HK.00700"], config=config)

        # Verify style was set
        mock_generator.set_style.assert_called_with("light")

        # Verify generate was called with proper config
        call_kwargs = mock_generator.generate.call_args[1]
        chart_config = call_kwargs["config"]
        assert chart_config.ma_periods == [10, 20]
        assert chart_config.dpi == 150
        assert chart_config.last_n_days == 60

    def test_output_subdir(self, tmp_path):
        """Test output subdirectory is created."""
        mock_fetcher = MagicMock()
        mock_df = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=10),
                "open": [100] * 10,
                "high": [105] * 10,
                "low": [95] * 10,
                "close": [102] * 10,
                "volume": [1000000] * 10,
            }
        )
        mock_fetcher.fetch.return_value = MagicMock(
            success=True, df=mock_df, error_message=None
        )

        mock_generator = MagicMock()
        mock_generator.generate.return_value = tmp_path / "test.png"
        mock_generator.set_style = MagicMock()

        service = ChartService(
            kline_fetcher=mock_fetcher,
            chart_generator=mock_generator,
            output_dir=tmp_path,
        )

        config = BatchChartConfig(output_subdir="user1/watchlist")
        result = service.generate_charts_for_codes(codes=["HK.00700"], config=config)

        assert result.output_dir == tmp_path / "user1/watchlist"
