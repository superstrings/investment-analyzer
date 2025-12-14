"""
Support and Resistance level identification.

Identifies key price levels where price tends to reverse or stall.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator


class LevelType(str, Enum):
    """Support/Resistance level type."""

    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"


class LevelStrength(str, Enum):
    """Level strength classification."""

    WEAK = "WEAK"
    MODERATE = "MODERATE"
    STRONG = "STRONG"


@dataclass
class PriceLevel:
    """A support or resistance price level."""

    price: float
    level_type: LevelType
    strength: LevelStrength = LevelStrength.MODERATE
    touches: int = 0  # Number of times price touched this level
    first_touch_idx: int = 0
    last_touch_idx: int = 0
    volume_at_level: float = 0.0  # Average volume at touches
    is_recent: bool = False
    confidence: float = 0.0  # 0-100


@dataclass
class SupportResistanceResult:
    """Result of support/resistance analysis."""

    name: str = "SupportResistance"
    levels: list[PriceLevel] = field(default_factory=list)
    current_support: Optional[float] = None
    current_resistance: Optional[float] = None
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    value: dict = field(default_factory=dict)


@dataclass
class SRConfig:
    """Configuration for Support/Resistance detection."""

    window: int = 5  # Window for local extremes
    tolerance: float = 0.02  # Price tolerance for grouping levels (2%)
    min_touches: int = 2  # Minimum touches to qualify as level
    lookback: int = 120  # Days to look back
    recent_weight: float = 1.5  # Weight for recent touches
    volume_weight: float = 1.2  # Weight for high-volume touches


class SupportResistance(BaseIndicator):
    """Support and Resistance level identifier.

    Identifies price levels based on:
    - Local price extremes (swing highs/lows)
    - Number of touches at each level
    - Volume at level touches
    - Recency of touches
    """

    def __init__(self, config: Optional[SRConfig] = None):
        super().__init__()
        self.config = config or SRConfig()

    def calculate(self, data: pd.DataFrame) -> SupportResistanceResult:
        """Identify support and resistance levels.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            SupportResistanceResult with identified levels
        """
        result = SupportResistanceResult()

        if len(data) < self.config.lookback:
            return result

        # Use recent data
        df = data.tail(self.config.lookback).copy()
        df = df.reset_index(drop=True)

        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        volumes = df["volume"].values if "volume" in df.columns else np.ones(len(df))

        # Find swing highs and lows
        swing_highs = self._find_swing_points(highs, is_high=True)
        swing_lows = self._find_swing_points(lows, is_high=False)

        # Cluster nearby levels
        resistance_levels = self._cluster_levels(swing_highs, volumes, LevelType.RESISTANCE)
        support_levels = self._cluster_levels(swing_lows, volumes, LevelType.SUPPORT)

        # Filter and score levels
        all_levels = []
        current_price = closes[-1]

        for level in resistance_levels + support_levels:
            if level.touches >= self.config.min_touches:
                level.confidence = self._calculate_confidence(level, len(df))
                level.is_recent = level.last_touch_idx > len(df) - 20
                all_levels.append(level)

        # Sort by confidence
        all_levels.sort(key=lambda x: x.confidence, reverse=True)

        # Find current support and resistance
        supports = [l for l in all_levels if l.level_type == LevelType.SUPPORT and l.price < current_price]
        resistances = [l for l in all_levels if l.level_type == LevelType.RESISTANCE and l.price > current_price]

        if supports:
            result.nearest_support = max(supports, key=lambda x: x.price).price
            result.current_support = result.nearest_support
        if resistances:
            result.nearest_resistance = min(resistances, key=lambda x: x.price).price
            result.current_resistance = result.nearest_resistance

        result.levels = all_levels[:10]  # Top 10 levels
        result.value = {
            "support": result.current_support,
            "resistance": result.current_resistance,
            "levels_count": len(all_levels),
        }

        return result

    def _find_swing_points(
        self, prices: np.ndarray, is_high: bool = True
    ) -> list[tuple[int, float]]:
        """Find swing high or low points.

        Args:
            prices: Array of prices
            is_high: True for highs, False for lows

        Returns:
            List of (index, price) tuples
        """
        points = []
        window = self.config.window

        for i in range(window, len(prices) - window):
            local_slice = prices[i - window : i + window + 1]
            if is_high:
                if prices[i] == np.max(local_slice):
                    points.append((i, prices[i]))
            else:
                if prices[i] == np.min(local_slice):
                    points.append((i, prices[i]))

        return points

    def _cluster_levels(
        self,
        points: list[tuple[int, float]],
        volumes: np.ndarray,
        level_type: LevelType,
    ) -> list[PriceLevel]:
        """Cluster nearby price points into levels.

        Args:
            points: List of (index, price) tuples
            volumes: Volume array
            level_type: Support or resistance

        Returns:
            List of PriceLevel objects
        """
        if not points:
            return []

        levels = []
        used = set()

        for i, (idx, price) in enumerate(points):
            if i in used:
                continue

            # Find all points within tolerance
            cluster_idxs = [idx]
            cluster_prices = [price]
            cluster_volumes = [volumes[idx]]

            for j, (other_idx, other_price) in enumerate(points):
                if j != i and j not in used:
                    if abs(other_price - price) / price < self.config.tolerance:
                        cluster_idxs.append(other_idx)
                        cluster_prices.append(other_price)
                        cluster_volumes.append(volumes[other_idx])
                        used.add(j)

            used.add(i)

            # Create level from cluster
            avg_price = np.mean(cluster_prices)
            avg_volume = np.mean(cluster_volumes)
            touches = len(cluster_idxs)

            # Determine strength
            if touches >= 4:
                strength = LevelStrength.STRONG
            elif touches >= 3:
                strength = LevelStrength.MODERATE
            else:
                strength = LevelStrength.WEAK

            level = PriceLevel(
                price=avg_price,
                level_type=level_type,
                strength=strength,
                touches=touches,
                first_touch_idx=min(cluster_idxs),
                last_touch_idx=max(cluster_idxs),
                volume_at_level=avg_volume,
            )
            levels.append(level)

        return levels

    def _calculate_confidence(self, level: PriceLevel, data_len: int) -> float:
        """Calculate confidence score for a level.

        Args:
            level: Price level
            data_len: Length of data

        Returns:
            Confidence score 0-100
        """
        confidence = 40.0

        # Touch count bonus (up to 30 points)
        confidence += min(level.touches - 1, 6) * 5

        # Recent touch bonus (up to 15 points)
        recency = (data_len - level.last_touch_idx) / data_len
        if recency < 0.1:  # Last 10%
            confidence += 15
        elif recency < 0.2:
            confidence += 10
        elif recency < 0.3:
            confidence += 5

        # Strength bonus
        if level.strength == LevelStrength.STRONG:
            confidence += 10
        elif level.strength == LevelStrength.MODERATE:
            confidence += 5

        return min(confidence, 100)


def find_support_resistance(
    data: pd.DataFrame,
    lookback: int = 120,
    min_touches: int = 2,
) -> SupportResistanceResult:
    """Convenience function to find support/resistance levels.

    Args:
        data: DataFrame with OHLCV data
        lookback: Days to analyze
        min_touches: Minimum touches for valid level

    Returns:
        SupportResistanceResult with identified levels
    """
    config = SRConfig(lookback=lookback, min_touches=min_touches)
    detector = SupportResistance(config)
    return detector.calculate(data)


def get_key_levels(
    data: pd.DataFrame,
    n_levels: int = 5,
) -> tuple[list[float], list[float]]:
    """Get top N support and resistance levels.

    Args:
        data: DataFrame with OHLCV data
        n_levels: Number of levels to return

    Returns:
        Tuple of (support_levels, resistance_levels)
    """
    result = find_support_resistance(data)

    supports = sorted(
        [l.price for l in result.levels if l.level_type == LevelType.SUPPORT],
        reverse=True,
    )[:n_levels]

    resistances = sorted(
        [l.price for l in result.levels if l.level_type == LevelType.RESISTANCE],
    )[:n_levels]

    return supports, resistances
