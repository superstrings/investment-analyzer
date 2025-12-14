"""
K-line chart generator for Investment Analyzer.

Generates candlestick charts with moving averages and volume using mplfinance.

Usage:
    from charts import ChartGenerator
    from fetchers import KlineFetcher

    # Create generator
    generator = ChartGenerator()

    # Generate chart from fetcher result
    fetcher = KlineFetcher()
    result = fetcher.fetch("HK.00700", days=120)
    if result.success and result.df is not None:
        generator.generate(result.df, title="腾讯控股", output_path="tencent.png")

    # Or generate from DataFrame directly
    generator.generate(df, title="Stock Chart", ma_periods=[5, 10, 20])
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional, Union

import mplfinance as mpf
import pandas as pd

from .styles import DARK_STYLE, ChartStyle, get_style

logger = logging.getLogger(__name__)


@dataclass
class ChartConfig:
    """Configuration for chart generation."""

    # Moving averages to display
    ma_periods: list[int] = field(default_factory=lambda: [5, 10, 20, 60])

    # Chart components
    show_volume: bool = True
    show_ma: bool = True

    # Chart size
    figsize: tuple[float, float] = (14, 8)
    dpi: int = 100

    # Output settings
    tight_layout: bool = True

    # Date range (optional, filters data)
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    # Number of days to show (alternative to date range)
    last_n_days: Optional[int] = None


class ChartGenerator:
    """
    K-line chart generator using mplfinance.

    Generates candlestick charts with:
    - OHLCV candlesticks
    - Moving average overlays (MA5, MA10, MA20, MA60, etc.)
    - Volume panel
    - Customizable styles

    Usage:
        generator = ChartGenerator(style="dark")

        # Generate from DataFrame
        generator.generate(df, title="Stock Chart", output_path="chart.png")

        # Generate with custom config
        config = ChartConfig(ma_periods=[5, 20, 60], show_volume=True)
        generator.generate(df, title="Chart", config=config, output_path="chart.png")
    """

    def __init__(
        self,
        style: Union[str, ChartStyle] = "dark",
        output_dir: Optional[Union[str, Path]] = None,
    ):
        """
        Initialize chart generator.

        Args:
            style: Chart style name or ChartStyle instance
            output_dir: Default output directory for charts
        """
        if isinstance(style, str):
            self.style = get_style(style)
        else:
            self.style = style

        self.output_dir = Path(output_dir) if output_dir else Path("charts/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Create mplfinance style
        self._mpf_style = mpf.make_mpf_style(**self.style.to_mpf_style())

    def generate(
        self,
        df: pd.DataFrame,
        title: str = "",
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[ChartConfig] = None,
        show: bool = False,
    ) -> Optional[Path]:
        """
        Generate a K-line chart from DataFrame.

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            title: Chart title
            output_path: Output file path (if None, uses default naming)
            config: Chart configuration
            show: Whether to display chart interactively

        Returns:
            Path to saved chart file, or None if only showing

        Raises:
            ValueError: If DataFrame is empty or missing required columns
        """
        config = config or ChartConfig()

        # Validate and prepare data
        df = self._prepare_dataframe(df, config)

        if df.empty:
            raise ValueError("DataFrame is empty after filtering")

        # Calculate moving averages if needed
        add_plots = []
        if config.show_ma:
            add_plots.extend(self._create_ma_plots(df, config.ma_periods))

        # Build plot kwargs
        plot_kwargs = {
            "type": "candle",
            "style": self._mpf_style,
            "title": title,
            "figsize": config.figsize,
            "volume": config.show_volume,
            "tight_layout": config.tight_layout,
            "warn_too_much_data": 500,
        }

        if add_plots:
            plot_kwargs["addplot"] = add_plots

        # Generate chart
        if output_path:
            output_path = Path(output_path)
            plot_kwargs["savefig"] = {
                "fname": str(output_path),
                "dpi": config.dpi,
                "bbox_inches": "tight",
            }
            mpf.plot(df, **plot_kwargs)
            logger.info(f"Chart saved to {output_path}")
            return output_path
        elif show:
            mpf.plot(df, **plot_kwargs)
            return None
        else:
            # Generate with default filename
            filename = self._generate_filename(df, title)
            output_path = self.output_dir / filename
            plot_kwargs["savefig"] = {
                "fname": str(output_path),
                "dpi": config.dpi,
                "bbox_inches": "tight",
            }
            mpf.plot(df, **plot_kwargs)
            logger.info(f"Chart saved to {output_path}")
            return output_path

    def generate_from_klines(
        self,
        klines: list,
        title: str = "",
        output_path: Optional[Union[str, Path]] = None,
        config: Optional[ChartConfig] = None,
    ) -> Optional[Path]:
        """
        Generate chart from list of KlineData objects.

        Args:
            klines: List of KlineData objects
            title: Chart title
            output_path: Output file path
            config: Chart configuration

        Returns:
            Path to saved chart file
        """
        df = self._klines_to_dataframe(klines)
        return self.generate(df, title=title, output_path=output_path, config=config)

    def generate_batch(
        self,
        data_dict: dict[str, pd.DataFrame],
        config: Optional[ChartConfig] = None,
        output_dir: Optional[Union[str, Path]] = None,
    ) -> dict[str, Path]:
        """
        Generate charts for multiple stocks.

        Args:
            data_dict: Dict mapping stock code to DataFrame
            config: Chart configuration
            output_dir: Output directory for charts

        Returns:
            Dict mapping stock code to output path
        """
        output_dir = Path(output_dir) if output_dir else self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        results = {}
        for code, df in data_dict.items():
            try:
                output_path = output_dir / f"{code.replace('.', '_')}.png"
                path = self.generate(
                    df,
                    title=code,
                    output_path=output_path,
                    config=config,
                )
                if path:
                    results[code] = path
            except Exception as e:
                logger.error(f"Failed to generate chart for {code}: {e}")
                continue

        return results

    def _prepare_dataframe(
        self,
        df: pd.DataFrame,
        config: ChartConfig,
    ) -> pd.DataFrame:
        """
        Prepare DataFrame for mplfinance.

        Ensures proper column names, index, and data types.
        """
        if df.empty:
            return df

        df = df.copy()

        # Standardize column names (lowercase)
        df.columns = df.columns.str.lower()

        # Check for required columns
        required = {"open", "high", "low", "close"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing required columns: {missing}")

        # Handle date column/index
        if "trade_date" in df.columns:
            df["date"] = pd.to_datetime(df["trade_date"])
            df.set_index("date", inplace=True)
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df.set_index("date", inplace=True)
        elif not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("DataFrame must have date column or DatetimeIndex")

        # Sort by date
        df.sort_index(inplace=True)

        # Filter by date range
        if config.start_date:
            df = df[df.index >= pd.Timestamp(config.start_date)]
        if config.end_date:
            df = df[df.index <= pd.Timestamp(config.end_date)]

        # Filter by last N days
        if config.last_n_days and len(df) > config.last_n_days:
            df = df.tail(config.last_n_days)

        # Ensure numeric types
        for col in ["open", "high", "low", "close"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        if "volume" in df.columns:
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)

        # Drop rows with NaN in OHLC
        df = df.dropna(subset=["open", "high", "low", "close"])

        return df

    def _create_ma_plots(
        self,
        df: pd.DataFrame,
        ma_periods: list[int],
    ) -> list:
        """Create moving average plot overlays."""
        add_plots = []

        for period in ma_periods:
            if len(df) < period:
                continue

            ma_col = f"ma{period}"

            # Calculate MA if not present
            if ma_col not in df.columns:
                df[ma_col] = df["close"].rolling(window=period).mean()

            # Skip if all NaN
            if df[ma_col].isna().all():
                continue

            color = self.style.get_ma_color(period)
            add_plots.append(
                mpf.make_addplot(
                    df[ma_col],
                    color=color,
                    width=self.style.ma_linewidth,
                    label=f"MA{period}",
                )
            )

        return add_plots

    def _klines_to_dataframe(self, klines: list) -> pd.DataFrame:
        """Convert list of KlineData to DataFrame."""
        if not klines:
            return pd.DataFrame()

        data = []
        for k in klines:
            data.append(
                {
                    "date": k.trade_date,
                    "open": float(k.open),
                    "high": float(k.high),
                    "low": float(k.low),
                    "close": float(k.close),
                    "volume": k.volume,
                }
            )

        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        return df.sort_index()

    def _generate_filename(self, df: pd.DataFrame, title: str) -> str:
        """Generate default filename for chart."""
        # Use title or date range
        if title:
            safe_title = title.replace(" ", "_").replace(".", "_")
            safe_title = "".join(c for c in safe_title if c.isalnum() or c == "_")
        else:
            safe_title = "chart"

        # Add date range
        if not df.empty:
            start = df.index.min().strftime("%Y%m%d")
            end = df.index.max().strftime("%Y%m%d")
            return f"{safe_title}_{start}_{end}.png"

        return f"{safe_title}.png"

    def set_style(self, style: Union[str, ChartStyle]) -> None:
        """
        Change the chart style.

        Args:
            style: Style name or ChartStyle instance
        """
        if isinstance(style, str):
            self.style = get_style(style)
        else:
            self.style = style
        self._mpf_style = mpf.make_mpf_style(**self.style.to_mpf_style())


def create_chart_generator(
    style: str = "dark",
    output_dir: Optional[str] = None,
) -> ChartGenerator:
    """
    Factory function to create a ChartGenerator.

    Args:
        style: Chart style name
        output_dir: Output directory for charts

    Returns:
        ChartGenerator instance
    """
    return ChartGenerator(style=style, output_dir=output_dir)
