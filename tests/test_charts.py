"""Tests for chart generation module.

Tests the ChartGenerator, ChartStyle, and related functionality.
"""

import tempfile
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from charts import (
    AVAILABLE_STYLES,
    CHINESE_STYLE,
    DARK_STYLE,
    DARK_WESTERN_STYLE,
    LIGHT_STYLE,
    ChartConfig,
    ChartGenerator,
    ChartStyle,
    ChartStyleWestern,
    create_chart_generator,
    get_style,
)
from fetchers import Market
from fetchers.kline_fetcher import KlineData


class TestChartStyle:
    """Tests for ChartStyle class."""

    def test_default_style(self):
        """Test default style values."""
        style = ChartStyle()
        assert style.name == "default"
        assert style.background_color == "#1e1e1e"
        assert style.up_color == "#ef5350"
        assert style.down_color == "#26a69a"

    def test_custom_style(self):
        """Test creating custom style."""
        style = ChartStyle(
            name="custom",
            background_color="#000000",
            up_color="#00ff00",
            down_color="#ff0000",
        )
        assert style.name == "custom"
        assert style.background_color == "#000000"
        assert style.up_color == "#00ff00"

    def test_to_mpf_style(self):
        """Test converting to mplfinance style dict."""
        style = ChartStyle()
        mpf_style = style.to_mpf_style()

        assert "marketcolors" in mpf_style
        assert "facecolor" in mpf_style
        assert "rc" in mpf_style
        assert mpf_style["facecolor"] == style.background_color

    def test_get_ma_color(self):
        """Test getting MA color for period."""
        style = ChartStyle()
        assert style.get_ma_color(5) == "#ffd700"
        assert style.get_ma_color(20) == "#00bfff"
        # Unknown period returns white
        assert style.get_ma_color(999) == "#ffffff"


class TestChartStyleWestern:
    """Tests for ChartStyleWestern class."""

    def test_western_colors(self):
        """Test western style has inverted colors."""
        style = ChartStyleWestern()
        assert style.up_color == "#26a69a"  # Green for up
        assert style.down_color == "#ef5350"  # Red for down


class TestPredefinedStyles:
    """Tests for predefined styles."""

    def test_dark_style(self):
        """Test DARK_STYLE."""
        assert DARK_STYLE.name == "dark"
        assert DARK_STYLE.background_color == "#1e1e1e"

    def test_light_style(self):
        """Test LIGHT_STYLE."""
        assert LIGHT_STYLE.name == "light"
        assert LIGHT_STYLE.background_color == "#ffffff"

    def test_chinese_style(self):
        """Test CHINESE_STYLE (red up, green down)."""
        assert CHINESE_STYLE.name == "chinese"
        assert CHINESE_STYLE.up_color == "#ff4757"
        assert CHINESE_STYLE.down_color == "#2ed573"

    def test_available_styles(self):
        """Test AVAILABLE_STYLES dict."""
        assert "dark" in AVAILABLE_STYLES
        assert "light" in AVAILABLE_STYLES
        assert "western" in AVAILABLE_STYLES
        assert "chinese" in AVAILABLE_STYLES


class TestGetStyle:
    """Tests for get_style function."""

    def test_get_dark_style(self):
        """Test getting dark style."""
        style = get_style("dark")
        assert style.name == "dark"

    def test_get_light_style(self):
        """Test getting light style."""
        style = get_style("light")
        assert style.name == "light"

    def test_get_unknown_style(self):
        """Test error for unknown style."""
        with pytest.raises(ValueError) as exc_info:
            get_style("nonexistent")
        assert "Unknown style" in str(exc_info.value)


class TestChartConfig:
    """Tests for ChartConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = ChartConfig()
        assert config.ma_periods == [5, 10, 20, 60]
        assert config.show_volume is True
        assert config.show_ma is True
        assert config.figsize == (14, 8)
        assert config.dpi == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = ChartConfig(
            ma_periods=[10, 20],
            show_volume=False,
            figsize=(10, 6),
            last_n_days=30,
        )
        assert config.ma_periods == [10, 20]
        assert config.show_volume is False
        assert config.figsize == (10, 6)
        assert config.last_n_days == 30


class TestChartGeneratorInit:
    """Tests for ChartGenerator initialization."""

    def test_default_init(self):
        """Test default initialization."""
        generator = ChartGenerator()
        assert generator.style.name == "dark"
        assert generator.output_dir.exists()

    def test_init_with_style_name(self):
        """Test initialization with style name."""
        generator = ChartGenerator(style="light")
        assert generator.style.name == "light"

    def test_init_with_style_object(self):
        """Test initialization with ChartStyle object."""
        custom_style = ChartStyle(name="custom")
        generator = ChartGenerator(style=custom_style)
        assert generator.style.name == "custom"

    def test_init_with_output_dir(self):
        """Test initialization with output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            assert generator.output_dir == Path(tmpdir)


class TestChartGeneratorPrepareDataframe:
    """Tests for DataFrame preparation."""

    def test_prepare_basic_dataframe(self):
        """Test preparing basic OHLCV DataFrame."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=10),
                "open": [100 + i for i in range(10)],
                "high": [105 + i for i in range(10)],
                "low": [95 + i for i in range(10)],
                "close": [102 + i for i in range(10)],
                "volume": [1000000] * 10,
            }
        )

        generator = ChartGenerator()
        config = ChartConfig()
        prepared = generator._prepare_dataframe(df, config)

        assert isinstance(prepared.index, pd.DatetimeIndex)
        assert "open" in prepared.columns
        assert "close" in prepared.columns

    def test_prepare_with_trade_date_column(self):
        """Test preparing DataFrame with trade_date column."""
        df = pd.DataFrame(
            {
                "trade_date": pd.date_range("2025-01-01", periods=5),
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],
            }
        )

        generator = ChartGenerator()
        config = ChartConfig()
        prepared = generator._prepare_dataframe(df, config)

        assert isinstance(prepared.index, pd.DatetimeIndex)

    def test_prepare_missing_columns(self):
        """Test error when missing required columns."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=5),
                "open": [100, 101, 102, 103, 104],
                # Missing high, low, close
            }
        )

        generator = ChartGenerator()
        config = ChartConfig()

        with pytest.raises(ValueError) as exc_info:
            generator._prepare_dataframe(df, config)
        assert "Missing required columns" in str(exc_info.value)

    def test_prepare_with_date_filter(self):
        """Test preparing DataFrame with date filtering."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=30),
                "open": range(30),
                "high": range(30),
                "low": range(30),
                "close": range(30),
            }
        )

        generator = ChartGenerator()
        config = ChartConfig(
            start_date=date(2025, 1, 10),
            end_date=date(2025, 1, 20),
        )
        prepared = generator._prepare_dataframe(df, config)

        assert len(prepared) == 11  # Jan 10-20 inclusive

    def test_prepare_with_last_n_days(self):
        """Test preparing DataFrame with last_n_days filter."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=100),
                "open": range(100),
                "high": range(100),
                "low": range(100),
                "close": range(100),
            }
        )

        generator = ChartGenerator()
        config = ChartConfig(last_n_days=20)
        prepared = generator._prepare_dataframe(df, config)

        assert len(prepared) == 20


class TestChartGeneratorMAPlots:
    """Tests for moving average plot creation."""

    def test_create_ma_plots(self):
        """Test creating MA plot overlays."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=100),
                "open": [100 + i * 0.1 for i in range(100)],
                "high": [105 + i * 0.1 for i in range(100)],
                "low": [95 + i * 0.1 for i in range(100)],
                "close": [102 + i * 0.1 for i in range(100)],
            }
        )
        df.set_index("date", inplace=True)

        generator = ChartGenerator()
        add_plots = generator._create_ma_plots(df, [5, 10, 20])

        # Should create 3 MA plots
        assert len(add_plots) == 3

    def test_create_ma_plots_insufficient_data(self):
        """Test MA plots with insufficient data."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=5),
                "open": [100, 101, 102, 103, 104],
                "high": [105, 106, 107, 108, 109],
                "low": [95, 96, 97, 98, 99],
                "close": [102, 103, 104, 105, 106],
            }
        )
        df.set_index("date", inplace=True)

        generator = ChartGenerator()
        # Request MA20 with only 5 data points
        add_plots = generator._create_ma_plots(df, [5, 20])

        # Should only create MA5 (MA20 needs more data)
        assert len(add_plots) == 1


class TestChartGeneratorKlinesToDataframe:
    """Tests for converting KlineData to DataFrame."""

    def test_klines_to_dataframe(self):
        """Test converting KlineData list to DataFrame."""
        klines = [
            KlineData(
                market=Market.HK,
                code="00700",
                trade_date=date(2025, 1, 1) + timedelta(days=i),
                open=Decimal("100") + i,
                high=Decimal("105") + i,
                low=Decimal("95") + i,
                close=Decimal("102") + i,
                volume=1000000,
            )
            for i in range(10)
        ]

        generator = ChartGenerator()
        df = generator._klines_to_dataframe(klines)

        assert len(df) == 10
        assert "open" in df.columns
        assert "close" in df.columns
        assert isinstance(df.index, pd.DatetimeIndex)

    def test_klines_to_dataframe_empty(self):
        """Test converting empty klines list."""
        generator = ChartGenerator()
        df = generator._klines_to_dataframe([])

        assert df.empty


class TestChartGeneratorGenerate:
    """Tests for chart generation."""

    @patch("charts.generator.mpf.plot")
    def test_generate_basic_chart(self, mock_plot):
        """Test generating basic chart."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=50),
                "open": [100 + i * 0.1 for i in range(50)],
                "high": [105 + i * 0.1 for i in range(50)],
                "low": [95 + i * 0.1 for i in range(50)],
                "close": [102 + i * 0.1 for i in range(50)],
                "volume": [1000000] * 50,
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            output_path = Path(tmpdir) / "test_chart.png"

            result = generator.generate(df, title="Test", output_path=output_path)

            mock_plot.assert_called_once()
            assert result == output_path

    @patch("charts.generator.mpf.plot")
    def test_generate_without_volume(self, mock_plot):
        """Test generating chart without volume."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=30),
                "open": range(30),
                "high": range(30),
                "low": range(30),
                "close": range(30),
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            config = ChartConfig(show_volume=False)

            generator.generate(
                df,
                title="No Volume",
                output_path=Path(tmpdir) / "test.png",
                config=config,
            )

            call_kwargs = mock_plot.call_args[1]
            assert call_kwargs["volume"] is False

    @patch("charts.generator.mpf.plot")
    def test_generate_without_ma(self, mock_plot):
        """Test generating chart without MA."""
        df = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=30),
                "open": range(30),
                "high": range(30),
                "low": range(30),
                "close": range(30),
            }
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            config = ChartConfig(show_ma=False)

            generator.generate(
                df,
                title="No MA",
                output_path=Path(tmpdir) / "test.png",
                config=config,
            )

            call_kwargs = mock_plot.call_args[1]
            assert "addplot" not in call_kwargs

    def test_generate_empty_dataframe(self):
        """Test error with empty DataFrame."""
        df = pd.DataFrame()

        generator = ChartGenerator()

        with pytest.raises(ValueError):
            generator.generate(df, title="Empty")

    @patch("charts.generator.mpf.plot")
    def test_generate_from_klines(self, mock_plot):
        """Test generating chart from KlineData list."""
        klines = [
            KlineData(
                market=Market.HK,
                code="00700",
                trade_date=date(2025, 1, 1) + timedelta(days=i),
                open=Decimal("100") + i,
                high=Decimal("105") + i,
                low=Decimal("95") + i,
                close=Decimal("102") + i,
                volume=1000000,
            )
            for i in range(30)
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            result = generator.generate_from_klines(
                klines,
                title="From KLines",
                output_path=Path(tmpdir) / "klines.png",
            )

            mock_plot.assert_called_once()


class TestChartGeneratorBatch:
    """Tests for batch chart generation."""

    @patch("charts.generator.mpf.plot")
    def test_generate_batch(self, mock_plot):
        """Test batch chart generation."""
        df1 = pd.DataFrame(
            {
                "date": pd.date_range("2025-01-01", periods=30),
                "open": range(30),
                "high": range(30),
                "low": range(30),
                "close": range(30),
            }
        )
        df2 = df1.copy()

        data_dict = {"HK.00700": df1, "US.NVDA": df2}

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ChartGenerator(output_dir=tmpdir)
            results = generator.generate_batch(data_dict)

            assert len(results) == 2
            assert mock_plot.call_count == 2


class TestChartGeneratorSetStyle:
    """Tests for changing chart style."""

    def test_set_style_by_name(self):
        """Test changing style by name."""
        generator = ChartGenerator(style="dark")
        assert generator.style.name == "dark"

        generator.set_style("light")
        assert generator.style.name == "light"

    def test_set_style_by_object(self):
        """Test changing style by object."""
        generator = ChartGenerator()
        custom = ChartStyle(name="custom")

        generator.set_style(custom)
        assert generator.style.name == "custom"


class TestCreateChartGenerator:
    """Tests for create_chart_generator factory function."""

    def test_create_default(self):
        """Test creating with defaults."""
        generator = create_chart_generator()
        assert generator.style.name == "dark"

    def test_create_with_style(self):
        """Test creating with custom style."""
        generator = create_chart_generator(style="chinese")
        assert generator.style.name == "chinese"

    def test_create_with_output_dir(self):
        """Test creating with output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = create_chart_generator(output_dir=tmpdir)
            assert generator.output_dir == Path(tmpdir)
