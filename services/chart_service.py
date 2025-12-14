"""
Chart generation service for Investment Analyzer.

Provides high-level chart generation for watchlists and positions.

Usage:
    from services import ChartService
    from fetchers import KlineFetcher
    from charts import ChartGenerator

    # Create service
    kline_fetcher = KlineFetcher()
    chart_generator = ChartGenerator(style="dark")
    service = ChartService(kline_fetcher, chart_generator)

    # Generate watchlist charts
    result = service.generate_watchlist_charts(user_id=1, days=120)

    # Generate position charts
    result = service.generate_position_charts(user_id=1, days=120)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

from charts import ChartConfig, ChartGenerator
from db import Account, Position, WatchlistItem, get_session
from fetchers import KlineFetcher

logger = logging.getLogger(__name__)


@dataclass
class ChartResult:
    """Result of chart generation operation."""

    success: bool
    charts_generated: int = 0
    charts_failed: int = 0
    output_dir: Optional[Path] = None
    generated_files: list[Path] = field(default_factory=list)
    failed_codes: list[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def add_generated(self, path: Path) -> None:
        """Add a successfully generated chart."""
        self.charts_generated += 1
        self.generated_files.append(path)

    def add_failed(self, code: str, reason: str = "") -> None:
        """Add a failed chart generation."""
        self.charts_failed += 1
        self.failed_codes.append(code)
        if reason:
            logger.warning(f"Failed to generate chart for {code}: {reason}")


@dataclass
class BatchChartConfig:
    """Configuration for batch chart generation."""

    days: int = 120
    style: str = "dark"
    ma_periods: list[int] = field(default_factory=lambda: [5, 10, 20, 60])
    show_volume: bool = True
    figsize: tuple[float, float] = (14, 8)
    dpi: int = 100
    output_subdir: Optional[str] = None


class ChartService:
    """
    Service for batch chart generation.

    Generates charts for watchlist items and portfolio positions,
    fetching K-line data and producing PNG chart files.

    Usage:
        service = ChartService(kline_fetcher, chart_generator)

        # Generate charts for user's watchlist
        result = service.generate_watchlist_charts(user_id=1)

        # Generate charts for user's positions
        result = service.generate_position_charts(user_id=1)

        # Generate charts for specific codes
        result = service.generate_charts_for_codes(
            codes=["HK.00700", "US.NVDA"],
            output_dir=Path("charts/output")
        )
    """

    def __init__(
        self,
        kline_fetcher: Optional[KlineFetcher] = None,
        chart_generator: Optional[ChartGenerator] = None,
        output_dir: Optional[Path] = None,
    ):
        """
        Initialize chart service.

        Args:
            kline_fetcher: KlineFetcher instance for fetching K-line data
            chart_generator: ChartGenerator instance for creating charts
            output_dir: Base output directory for charts
        """
        self.kline_fetcher = kline_fetcher or KlineFetcher()
        self.chart_generator = chart_generator or ChartGenerator()
        self.output_dir = output_dir or Path("charts/output")

    def generate_watchlist_charts(
        self,
        user_id: int,
        config: Optional[BatchChartConfig] = None,
        output_dir: Optional[Path] = None,
    ) -> ChartResult:
        """
        Generate charts for all items in a user's watchlist.

        Args:
            user_id: User ID to get watchlist for
            config: Batch chart configuration
            output_dir: Output directory (overrides default)

        Returns:
            ChartResult with generation statistics
        """
        config = config or BatchChartConfig()
        result = ChartResult(success=True)

        try:
            # Get watchlist items
            with get_session() as session:
                items = session.query(WatchlistItem).filter_by(user_id=user_id).all()
                codes = [f"{item.market}.{item.code}" for item in items]

            if not codes:
                result.error_message = "No items in watchlist"
                return result

            # Determine output directory
            out_dir = output_dir or self.output_dir
            if config.output_subdir:
                out_dir = out_dir / config.output_subdir
            out_dir.mkdir(parents=True, exist_ok=True)
            result.output_dir = out_dir

            # Generate charts
            return self._generate_charts_for_codes(codes, out_dir, config, result)

        except Exception as e:
            logger.error(f"Failed to generate watchlist charts: {e}")
            result.success = False
            result.error_message = str(e)
            return result

    def generate_position_charts(
        self,
        user_id: int,
        config: Optional[BatchChartConfig] = None,
        output_dir: Optional[Path] = None,
    ) -> ChartResult:
        """
        Generate charts for all stocks in a user's positions.

        Args:
            user_id: User ID to get positions for
            config: Batch chart configuration
            output_dir: Output directory (overrides default)

        Returns:
            ChartResult with generation statistics
        """
        config = config or BatchChartConfig()
        result = ChartResult(success=True)

        try:
            # Get unique position codes
            with get_session() as session:
                positions = (
                    session.query(Position)
                    .join(Account)
                    .filter(Account.user_id == user_id)
                    .all()
                )
                # Get unique codes with qty > 0
                codes = list(
                    set(
                        f"{p.market}.{p.code}" for p in positions if p.qty and p.qty > 0
                    )
                )

            if not codes:
                result.error_message = "No active positions"
                return result

            # Determine output directory
            out_dir = output_dir or self.output_dir
            if config.output_subdir:
                out_dir = out_dir / config.output_subdir
            out_dir.mkdir(parents=True, exist_ok=True)
            result.output_dir = out_dir

            # Generate charts
            return self._generate_charts_for_codes(codes, out_dir, config, result)

        except Exception as e:
            logger.error(f"Failed to generate position charts: {e}")
            result.success = False
            result.error_message = str(e)
            return result

    def generate_charts_for_codes(
        self,
        codes: list[str],
        config: Optional[BatchChartConfig] = None,
        output_dir: Optional[Path] = None,
    ) -> ChartResult:
        """
        Generate charts for a list of stock codes.

        Args:
            codes: List of stock codes (e.g., ["HK.00700", "US.NVDA"])
            config: Batch chart configuration
            output_dir: Output directory

        Returns:
            ChartResult with generation statistics
        """
        config = config or BatchChartConfig()
        result = ChartResult(success=True)

        if not codes:
            result.error_message = "No codes provided"
            return result

        # Determine output directory
        out_dir = output_dir or self.output_dir
        if config.output_subdir:
            out_dir = out_dir / config.output_subdir
        out_dir.mkdir(parents=True, exist_ok=True)
        result.output_dir = out_dir

        return self._generate_charts_for_codes(codes, out_dir, config, result)

    def _generate_charts_for_codes(
        self,
        codes: list[str],
        output_dir: Path,
        config: BatchChartConfig,
        result: ChartResult,
    ) -> ChartResult:
        """
        Internal method to generate charts for codes.

        Args:
            codes: List of stock codes
            output_dir: Output directory
            config: Batch chart configuration
            result: ChartResult to populate

        Returns:
            Updated ChartResult
        """
        # Create chart config
        chart_config = ChartConfig(
            ma_periods=config.ma_periods,
            show_volume=config.show_volume,
            show_ma=True,
            figsize=config.figsize,
            dpi=config.dpi,
            last_n_days=config.days,
        )

        # Update generator style if needed
        if config.style:
            self.chart_generator.set_style(config.style)

        # Generate charts for each code
        for code in codes:
            try:
                # Fetch K-line data
                fetch_result = self.kline_fetcher.fetch(code, days=config.days)

                if (
                    not fetch_result.success
                    or fetch_result.df is None
                    or fetch_result.df.empty
                ):
                    result.add_failed(code, fetch_result.error_message or "No data")
                    continue

                # Generate chart
                output_path = output_dir / f"{code.replace('.', '_')}.png"
                chart_path = self.chart_generator.generate(
                    df=fetch_result.df,
                    title=code,
                    output_path=output_path,
                    config=chart_config,
                )

                if chart_path:
                    result.add_generated(chart_path)
                else:
                    result.add_failed(code, "Generation failed")

            except Exception as e:
                result.add_failed(code, str(e))

        # Update success status
        if result.charts_generated == 0 and result.charts_failed > 0:
            result.success = False
            result.error_message = f"All {result.charts_failed} charts failed"

        return result


def create_chart_service(
    kline_fetcher: Optional[KlineFetcher] = None,
    chart_generator: Optional[ChartGenerator] = None,
    output_dir: Optional[str] = None,
) -> ChartService:
    """
    Factory function to create a ChartService.

    Args:
        kline_fetcher: KlineFetcher instance
        chart_generator: ChartGenerator instance
        output_dir: Output directory for charts

    Returns:
        ChartService instance
    """
    out_path = Path(output_dir) if output_dir else None
    return ChartService(
        kline_fetcher=kline_fetcher,
        chart_generator=chart_generator,
        output_dir=out_path,
    )
