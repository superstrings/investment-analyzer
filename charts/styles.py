"""
Chart style definitions for Investment Analyzer.

Provides predefined color schemes and style configurations for K-line charts.

Usage:
    from charts.styles import ChartStyle, DARK_STYLE, LIGHT_STYLE

    # Use predefined style
    style = DARK_STYLE

    # Or create custom style
    custom_style = ChartStyle(
        name="custom",
        background_color="#1a1a1a",
        up_color="#00ff00",
        down_color="#ff0000",
    )
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChartStyle:
    """
    Chart style configuration.

    Defines colors and appearance for K-line charts.
    """

    name: str = "default"

    # Background colors
    background_color: str = "#1e1e1e"
    grid_color: str = "#333333"

    # Candlestick colors
    up_color: str = "#ef5350"  # Red for up (Chinese convention)
    down_color: str = "#26a69a"  # Green for down
    up_edge_color: str = "#ef5350"
    down_edge_color: str = "#26a69a"

    # Volume colors
    volume_up_color: str = "#ef5350"
    volume_down_color: str = "#26a69a"
    volume_alpha: float = 0.7

    # Moving average colors
    ma_colors: dict = field(
        default_factory=lambda: {
            5: "#ffd700",  # Gold - MA5
            10: "#ff69b4",  # Pink - MA10
            20: "#00bfff",  # DeepSkyBlue - MA20
            60: "#9370db",  # MediumPurple - MA60
            120: "#ff8c00",  # DarkOrange - MA120
            250: "#32cd32",  # LimeGreen - MA250
        }
    )

    # Text colors
    text_color: str = "#cccccc"
    axis_color: str = "#666666"
    title_color: str = "#ffffff"

    # Line widths
    ma_linewidth: float = 1.0
    edge_linewidth: float = 0.8

    # Figure settings
    fig_width: float = 14.0
    fig_height: float = 8.0
    fig_dpi: int = 100

    # Font settings
    font_family: str = "sans-serif"
    title_fontsize: int = 14
    label_fontsize: int = 10

    def to_mpf_style(self) -> dict:
        """
        Convert to mplfinance style dict.

        Returns:
            Dict compatible with mplfinance make_mpf_style()
        """
        return {
            "base_mpf_style": "nightclouds",
            "marketcolors": {
                "candle": {"up": self.up_color, "down": self.down_color},
                "edge": {"up": self.up_edge_color, "down": self.down_edge_color},
                "wick": {"up": self.up_color, "down": self.down_color},
                "ohlc": {"up": self.up_color, "down": self.down_color},
                "volume": {"up": self.volume_up_color, "down": self.volume_down_color},
                "vcedge": {"up": self.up_color, "down": self.down_color},
                "vcdopcod": False,
                "alpha": self.volume_alpha,
            },
            "mavcolors": list(self.ma_colors.values())[:6],
            "facecolor": self.background_color,
            "figcolor": self.background_color,
            "gridcolor": self.grid_color,
            "gridstyle": "--",
            "gridaxis": "both",
            "y_on_right": True,
            "rc": {
                "axes.labelcolor": self.text_color,
                "axes.edgecolor": self.axis_color,
                "xtick.color": self.text_color,
                "ytick.color": self.text_color,
                "text.color": self.text_color,
                "font.family": self.font_family,
                "axes.titlesize": self.title_fontsize,
                "axes.labelsize": self.label_fontsize,
            },
        }

    def get_ma_color(self, period: int) -> str:
        """Get color for a specific MA period."""
        return self.ma_colors.get(period, "#ffffff")


@dataclass
class ChartStyleWestern(ChartStyle):
    """
    Western-style chart (green up, red down).

    Standard convention in US/European markets.
    """

    name: str = "western"
    up_color: str = "#26a69a"  # Green for up
    down_color: str = "#ef5350"  # Red for down
    up_edge_color: str = "#26a69a"
    down_edge_color: str = "#ef5350"
    volume_up_color: str = "#26a69a"
    volume_down_color: str = "#ef5350"


# Predefined styles
DARK_STYLE = ChartStyle(
    name="dark",
    background_color="#1e1e1e",
    grid_color="#333333",
    text_color="#cccccc",
)

LIGHT_STYLE = ChartStyle(
    name="light",
    background_color="#ffffff",
    grid_color="#e0e0e0",
    text_color="#333333",
    axis_color="#999999",
    title_color="#000000",
)

DARK_WESTERN_STYLE = ChartStyleWestern(
    name="dark_western",
    background_color="#1e1e1e",
    grid_color="#333333",
    text_color="#cccccc",
)

# Chinese market style (red up, green down) - default
CHINESE_STYLE = ChartStyle(
    name="chinese",
    background_color="#1a1a2e",
    grid_color="#2d2d44",
    up_color="#ff4757",
    down_color="#2ed573",
    up_edge_color="#ff4757",
    down_edge_color="#2ed573",
    volume_up_color="#ff4757",
    volume_down_color="#2ed573",
)

# Map of available styles
AVAILABLE_STYLES = {
    "dark": DARK_STYLE,
    "light": LIGHT_STYLE,
    "western": DARK_WESTERN_STYLE,
    "chinese": CHINESE_STYLE,
}


def get_style(name: str) -> ChartStyle:
    """
    Get a predefined style by name.

    Args:
        name: Style name ("dark", "light", "western", "chinese")

    Returns:
        ChartStyle instance

    Raises:
        ValueError: If style name not found
    """
    if name not in AVAILABLE_STYLES:
        available = ", ".join(AVAILABLE_STYLES.keys())
        raise ValueError(f"Unknown style '{name}'. Available: {available}")
    return AVAILABLE_STYLES[name]
