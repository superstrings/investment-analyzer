"""
Chart generation module for Investment Analyzer.

Provides K-line chart generation with customizable styles.

Usage:
    from charts import ChartGenerator, ChartConfig, ChartStyle
    from fetchers import KlineFetcher

    # Create generator with style
    generator = ChartGenerator(style="dark")

    # Fetch and generate chart
    fetcher = KlineFetcher()
    result = fetcher.fetch("HK.00700", days=120)
    if result.success and result.df is not None:
        generator.generate(
            result.df,
            title="腾讯控股",
            output_path="tencent.png"
        )

    # Custom configuration
    config = ChartConfig(
        ma_periods=[5, 10, 20, 60],
        show_volume=True,
        last_n_days=60,
    )
    generator.generate(df, title="Chart", config=config)
"""

from .generator import ChartConfig, ChartGenerator, create_chart_generator
from .styles import (
    AVAILABLE_STYLES,
    CHINESE_STYLE,
    DARK_STYLE,
    DARK_WESTERN_STYLE,
    LIGHT_STYLE,
    ChartStyle,
    ChartStyleWestern,
    get_style,
)

__all__ = [
    # Generator
    "ChartGenerator",
    "ChartConfig",
    "create_chart_generator",
    # Styles
    "ChartStyle",
    "ChartStyleWestern",
    "get_style",
    # Predefined styles
    "DARK_STYLE",
    "LIGHT_STYLE",
    "DARK_WESTERN_STYLE",
    "CHINESE_STYLE",
    "AVAILABLE_STYLES",
]
