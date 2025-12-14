"""
Automatic trendline detection and analysis.

Identifies and validates trendlines based on price action.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator


class TrendDirection(str, Enum):
    """Trendline direction."""

    UP = "UP"
    DOWN = "DOWN"
    FLAT = "FLAT"


class TrendlineType(str, Enum):
    """Type of trendline."""

    SUPPORT = "SUPPORT"  # Connects lows
    RESISTANCE = "RESISTANCE"  # Connects highs


@dataclass
class Trendline:
    """A detected trendline."""

    trendline_type: TrendlineType
    direction: TrendDirection
    slope: float  # Price change per bar
    intercept: float  # Y-intercept (at x=0)
    start_idx: int
    end_idx: int
    touches: int = 0  # Number of price touches
    touch_indices: list[int] = field(default_factory=list)
    current_price: float = 0.0  # Current trendline price
    strength: float = 0.0  # 0-100 strength score
    is_valid: bool = True
    broken: bool = False  # Has price broken through

    def get_price_at(self, idx: int) -> float:
        """Get trendline price at given index."""
        return self.slope * idx + self.intercept


@dataclass
class TrendlineResult:
    """Result of trendline analysis."""

    name: str = "Trendline"
    trendlines: list[Trendline] = field(default_factory=list)
    primary_support: Optional[Trendline] = None
    primary_resistance: Optional[Trendline] = None
    overall_trend: TrendDirection = TrendDirection.FLAT
    value: dict = field(default_factory=dict)


@dataclass
class TrendlineConfig:
    """Configuration for trendline detection."""

    window: int = 5  # Window for swing point detection
    min_touches: int = 2  # Minimum touches for valid trendline
    max_deviation: float = 0.02  # Max price deviation from line (2%)
    lookback: int = 60  # Bars to analyze
    min_slope: float = 0.0001  # Minimum slope for non-flat
    max_trendlines: int = 4  # Max trendlines to return


class TrendlineDetector(BaseIndicator):
    """Automatic trendline detector.

    Identifies trendlines by:
    1. Finding swing high/low points
    2. Fitting lines through multiple points
    3. Validating by price action
    4. Scoring by touches and consistency
    """

    def __init__(self, config: Optional[TrendlineConfig] = None):
        super().__init__()
        self.config = config or TrendlineConfig()

    def calculate(self, data: pd.DataFrame) -> TrendlineResult:
        """Detect trendlines in price data.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            TrendlineResult with detected trendlines
        """
        result = TrendlineResult()

        if len(data) < self.config.lookback:
            return result

        # Use recent data
        df = data.tail(self.config.lookback).copy()
        df = df.reset_index(drop=True)

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values

        # Find swing points
        swing_highs = self._find_swings(highs, is_high=True)
        swing_lows = self._find_swings(lows, is_high=False)

        # Find resistance trendlines (connecting highs)
        resistance_lines = self._find_trendlines(
            swing_highs, highs, TrendlineType.RESISTANCE
        )

        # Find support trendlines (connecting lows)
        support_lines = self._find_trendlines(
            swing_lows, lows, TrendlineType.SUPPORT
        )

        # Check for broken trendlines
        current_close = closes[-1]
        for line in resistance_lines + support_lines:
            line.current_price = line.get_price_at(len(df) - 1)
            if line.trendline_type == TrendlineType.RESISTANCE:
                line.broken = current_close > line.current_price * 1.01
            else:
                line.broken = current_close < line.current_price * 0.99

        # Score and sort
        all_lines = resistance_lines + support_lines
        all_lines.sort(key=lambda x: x.strength, reverse=True)

        # Select best lines
        result.trendlines = all_lines[: self.config.max_trendlines]

        # Find primary support and resistance
        valid_support = [
            l for l in all_lines
            if l.trendline_type == TrendlineType.SUPPORT and not l.broken
        ]
        valid_resistance = [
            l for l in all_lines
            if l.trendline_type == TrendlineType.RESISTANCE and not l.broken
        ]

        if valid_support:
            result.primary_support = valid_support[0]
        if valid_resistance:
            result.primary_resistance = valid_resistance[0]

        # Determine overall trend
        avg_slope = np.mean([l.slope for l in all_lines]) if all_lines else 0
        if avg_slope > self.config.min_slope:
            result.overall_trend = TrendDirection.UP
        elif avg_slope < -self.config.min_slope:
            result.overall_trend = TrendDirection.DOWN
        else:
            result.overall_trend = TrendDirection.FLAT

        result.value = {
            "trend": result.overall_trend.value,
            "support_count": len([l for l in all_lines if l.trendline_type == TrendlineType.SUPPORT]),
            "resistance_count": len([l for l in all_lines if l.trendline_type == TrendlineType.RESISTANCE]),
        }

        return result

    def _find_swings(
        self, prices: np.ndarray, is_high: bool = True
    ) -> list[tuple[int, float]]:
        """Find swing points.

        Args:
            prices: Price array
            is_high: True for swing highs, False for swing lows

        Returns:
            List of (index, price) tuples
        """
        points = []
        window = self.config.window

        for i in range(window, len(prices) - window):
            local = prices[i - window : i + window + 1]
            if is_high and prices[i] == np.max(local):
                points.append((i, prices[i]))
            elif not is_high and prices[i] == np.min(local):
                points.append((i, prices[i]))

        return points

    def _find_trendlines(
        self,
        points: list[tuple[int, float]],
        all_prices: np.ndarray,
        line_type: TrendlineType,
    ) -> list[Trendline]:
        """Find valid trendlines through swing points.

        Args:
            points: List of swing points
            all_prices: All prices for validation
            line_type: Support or resistance

        Returns:
            List of valid Trendline objects
        """
        if len(points) < 2:
            return []

        trendlines = []

        # Try all combinations of points
        for i in range(len(points)):
            for j in range(i + 1, len(points)):
                idx1, price1 = points[i]
                idx2, price2 = points[j]

                if idx2 - idx1 < 5:  # Minimum distance between points
                    continue

                # Calculate line equation
                slope = (price2 - price1) / (idx2 - idx1)
                intercept = price1 - slope * idx1

                # Validate and count touches
                touches = 0
                touch_indices = []
                valid = True

                for k in range(len(all_prices)):
                    line_price = slope * k + intercept
                    actual_price = all_prices[k]
                    deviation = (actual_price - line_price) / line_price if line_price != 0 else 0

                    if abs(deviation) < self.config.max_deviation:
                        touches += 1
                        touch_indices.append(k)

                    # Check if line is violated (for support, price shouldn't go below)
                    if line_type == TrendlineType.SUPPORT:
                        if deviation < -self.config.max_deviation * 2:
                            valid = False
                            break
                    else:  # Resistance
                        if deviation > self.config.max_deviation * 2:
                            valid = False
                            break

                if not valid or touches < self.config.min_touches:
                    continue

                # Determine direction
                if slope > self.config.min_slope:
                    direction = TrendDirection.UP
                elif slope < -self.config.min_slope:
                    direction = TrendDirection.DOWN
                else:
                    direction = TrendDirection.FLAT

                # Calculate strength
                strength = self._calculate_strength(
                    touches, touch_indices, len(all_prices)
                )

                trendline = Trendline(
                    trendline_type=line_type,
                    direction=direction,
                    slope=slope,
                    intercept=intercept,
                    start_idx=idx1,
                    end_idx=idx2,
                    touches=touches,
                    touch_indices=touch_indices,
                    strength=strength,
                    is_valid=valid,
                )
                trendlines.append(trendline)

        # Remove duplicates (similar lines)
        unique_lines = []
        for line in trendlines:
            is_unique = True
            for existing in unique_lines:
                if abs(line.slope - existing.slope) < 0.001 and abs(line.intercept - existing.intercept) < 1:
                    # Similar line, keep the stronger one
                    if line.strength > existing.strength:
                        unique_lines.remove(existing)
                    else:
                        is_unique = False
                    break
            if is_unique:
                unique_lines.append(line)

        return unique_lines

    def _calculate_strength(
        self, touches: int, touch_indices: list[int], data_len: int
    ) -> float:
        """Calculate trendline strength.

        Args:
            touches: Number of touches
            touch_indices: Indices of touches
            data_len: Total data length

        Returns:
            Strength score 0-100
        """
        strength = 30.0

        # Touch count bonus (up to 35 points)
        strength += min(touches - 1, 7) * 5

        # Recent touch bonus (up to 20 points)
        if touch_indices:
            last_touch_recency = (data_len - max(touch_indices)) / data_len
            if last_touch_recency < 0.1:
                strength += 20
            elif last_touch_recency < 0.2:
                strength += 15
            elif last_touch_recency < 0.3:
                strength += 10
            elif last_touch_recency < 0.5:
                strength += 5

        # Span bonus (longer trendlines are stronger, up to 15 points)
        if len(touch_indices) >= 2:
            span = max(touch_indices) - min(touch_indices)
            span_ratio = span / data_len
            if span_ratio > 0.7:
                strength += 15
            elif span_ratio > 0.5:
                strength += 10
            elif span_ratio > 0.3:
                strength += 5

        return min(strength, 100)


def detect_trendlines(
    data: pd.DataFrame,
    lookback: int = 60,
) -> TrendlineResult:
    """Convenience function to detect trendlines.

    Args:
        data: DataFrame with OHLCV data
        lookback: Bars to analyze

    Returns:
        TrendlineResult with detected trendlines
    """
    config = TrendlineConfig(lookback=lookback)
    detector = TrendlineDetector(config)
    return detector.calculate(data)


def get_trend_direction(data: pd.DataFrame) -> TrendDirection:
    """Get overall trend direction from trendlines.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        TrendDirection
    """
    result = detect_trendlines(data)
    return result.overall_trend
