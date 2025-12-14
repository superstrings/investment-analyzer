"""
VCP (Volatility Contraction Pattern) indicator.

Implements Mark Minervini's Volatility Contraction Pattern detection.

VCP characteristics:
1. Price contractions: Series of decreasing pullbacks (e.g., 25% → 15% → 8% → 3%)
2. Volume dry-up: Volume decreases during consolidation
3. Tight price action: Decreasing range between highs and lows
4. Pivot point: Price near breakout level

Usage:
    from analysis.indicators import VCP, VCPScanner

    # Detect VCP pattern
    vcp = VCP()
    result = vcp.calculate(df)

    # Scan for VCP with scoring
    scanner = VCPScanner()
    scan_result = scanner.scan(df)
    print(f"VCP Score: {scan_result.score}")
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult

logger = logging.getLogger(__name__)


@dataclass
class Contraction:
    """Represents a single price contraction in VCP pattern."""

    start_idx: int  # Start index (swing high)
    end_idx: int  # End index (swing low)
    high_price: float  # Swing high price
    low_price: float  # Swing low price
    depth_pct: float  # Contraction depth percentage
    duration: int  # Number of bars
    avg_volume: float  # Average volume during contraction


@dataclass
class VCPResult:
    """Result of VCP pattern detection."""

    is_vcp: bool = False
    contractions: list[Contraction] = field(default_factory=list)
    contraction_count: int = 0
    depth_sequence: list[float] = field(default_factory=list)
    volume_trend: float = 0.0  # Negative = decreasing volume (good)
    range_contraction: float = 0.0  # How much range contracted
    pivot_price: Optional[float] = None  # Potential breakout level
    pivot_distance_pct: float = 0.0  # Distance from current price to pivot
    score: float = 0.0  # Overall VCP quality score (0-100)
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "is_vcp": self.is_vcp,
            "contraction_count": self.contraction_count,
            "depth_sequence": self.depth_sequence,
            "volume_trend": self.volume_trend,
            "range_contraction": self.range_contraction,
            "pivot_price": self.pivot_price,
            "pivot_distance_pct": self.pivot_distance_pct,
            "score": self.score,
            "signals": self.signals,
        }


@dataclass
class VCPConfig:
    """Configuration for VCP detection."""

    # Contraction detection
    min_contractions: int = 2  # Minimum number of contractions
    max_contractions: int = 5  # Maximum contractions to detect
    min_depth_pct: float = 3.0  # Minimum contraction depth (%)
    max_first_depth_pct: float = 35.0  # Maximum first contraction (%)
    depth_decrease_ratio: float = 0.7  # Each contraction should be <= this * previous

    # Swing detection
    swing_period: int = 5  # Period for swing high/low detection
    min_swing_distance: int = 3  # Minimum bars between swings

    # Volume analysis
    volume_lookback: int = 20  # Bars for volume comparison
    volume_dry_up_threshold: float = -0.2  # Volume should decrease by at least 20%

    # Range analysis
    atr_period: int = 14  # ATR period for range analysis
    range_contraction_threshold: float = 0.5  # Range should contract by at least 50%

    # Pivot detection
    pivot_distance_threshold: float = 5.0  # Max % distance from pivot to be valid

    # Scoring weights
    weight_contractions: float = 25.0
    weight_depth_decrease: float = 25.0
    weight_volume: float = 20.0
    weight_range: float = 15.0
    weight_pivot: float = 15.0


class VCP(BaseIndicator):
    """
    VCP (Volatility Contraction Pattern) indicator.

    Detects Mark Minervini's VCP pattern which signals potential breakouts.

    The pattern is characterized by:
    - Multiple price contractions with decreasing depth
    - Decreasing volume during consolidation
    - Tightening price range
    - Price near a pivot/breakout level

    Usage:
        vcp = VCP()
        result = vcp.calculate(df)
        vcp_result = result.values  # VCPResult dataclass

        if vcp_result.is_vcp:
            print(f"VCP detected! Score: {vcp_result.score}")
            print(f"Pivot price: {vcp_result.pivot_price}")
    """

    name = "VCP"

    def __init__(self, config: Optional[VCPConfig] = None):
        """
        Initialize VCP indicator.

        Args:
            config: VCP configuration parameters
        """
        self.config = config or VCPConfig()

    def calculate(self, df: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate VCP pattern.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            IndicatorResult with VCPResult as values
        """
        self._validate_dataframe(df, ["high", "low", "close", "volume"])

        high = self._get_column(df, "high")
        low = self._get_column(df, "low")
        close = self._get_column(df, "close")
        volume = self._get_column(df, "volume")

        # Detect VCP pattern
        vcp_result = self._detect_vcp(high, low, close, volume)

        return IndicatorResult(
            name=self.name,
            values=vcp_result,
            params={"config": self.config.__dict__},
        )

    def _detect_vcp(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
    ) -> VCPResult:
        """
        Detect VCP pattern in the data.

        Args:
            high: High prices
            low: Low prices
            close: Close prices
            volume: Volume

        Returns:
            VCPResult with detection results
        """
        result = VCPResult()

        if len(close) < 50:  # Need enough data
            result.signals.append("Insufficient data for VCP detection")
            return result

        # Step 1: Find swing highs and lows
        swing_highs = self._find_swing_highs(high)
        swing_lows = self._find_swing_lows(low)

        if len(swing_highs) < 2 or len(swing_lows) < 1:
            result.signals.append("Not enough swing points detected")
            return result

        # Step 2: Detect contractions
        contractions = self._detect_contractions(
            high, low, close, volume, swing_highs, swing_lows
        )

        if len(contractions) < self.config.min_contractions:
            result.signals.append(
                f"Only {len(contractions)} contractions found "
                f"(need {self.config.min_contractions})"
            )
            return result

        result.contractions = contractions
        result.contraction_count = len(contractions)
        result.depth_sequence = [c.depth_pct for c in contractions]

        # Step 3: Analyze depth progression
        depth_decreasing = self._check_depth_decrease(contractions)

        # Step 4: Analyze volume
        result.volume_trend = self._analyze_volume_trend(volume, contractions)

        # Step 5: Analyze range contraction
        result.range_contraction = self._analyze_range_contraction(
            high, low, contractions
        )

        # Step 6: Find pivot price
        result.pivot_price = self._find_pivot_price(high, contractions)
        if result.pivot_price:
            current_price = close.iloc[-1]
            result.pivot_distance_pct = (
                (result.pivot_price - current_price) / current_price * 100
            )

        # Step 7: Determine if valid VCP
        is_valid_vcp = self._validate_vcp(result, depth_decreasing)
        result.is_vcp = is_valid_vcp

        # Step 8: Calculate score
        result.score = self._calculate_score(result, depth_decreasing)

        # Add analysis signals
        self._add_signals(result, depth_decreasing)

        return result

    def _find_swing_highs(self, high: pd.Series) -> list[int]:
        """Find swing high indices."""
        swing_highs = []
        period = self.config.swing_period

        for i in range(period, len(high) - period):
            if high.iloc[i] == high.iloc[i - period : i + period + 1].max():
                # Ensure minimum distance from previous swing
                if (
                    not swing_highs
                    or i - swing_highs[-1] >= self.config.min_swing_distance
                ):
                    swing_highs.append(i)

        return swing_highs

    def _find_swing_lows(self, low: pd.Series) -> list[int]:
        """Find swing low indices."""
        swing_lows = []
        period = self.config.swing_period

        for i in range(period, len(low) - period):
            if low.iloc[i] == low.iloc[i - period : i + period + 1].min():
                if (
                    not swing_lows
                    or i - swing_lows[-1] >= self.config.min_swing_distance
                ):
                    swing_lows.append(i)

        return swing_lows

    def _detect_contractions(
        self,
        high: pd.Series,
        low: pd.Series,
        close: pd.Series,
        volume: pd.Series,
        swing_highs: list[int],
        swing_lows: list[int],
    ) -> list[Contraction]:
        """
        Detect price contractions from swing points.

        A contraction is a pullback from a swing high to a swing low.
        """
        contractions = []

        # Start from the highest point in the lookback period
        lookback_start = max(0, len(close) - 120)  # Look at last ~6 months
        relevant_highs = [h for h in swing_highs if h >= lookback_start]

        if not relevant_highs:
            return contractions

        # Find the base high (highest swing high)
        base_high_idx = max(relevant_highs, key=lambda x: high.iloc[x])
        base_high_price = high.iloc[base_high_idx]

        # Track contractions after the base high
        current_high_idx = base_high_idx
        current_high_price = base_high_price

        for i in range(len(swing_lows)):
            low_idx = swing_lows[i]

            # Only consider lows after current high
            if low_idx <= current_high_idx:
                continue

            low_price = low.iloc[low_idx]

            # Calculate contraction depth
            depth_pct = (current_high_price - low_price) / current_high_price * 100

            # Check if valid contraction
            if depth_pct >= self.config.min_depth_pct:
                # Calculate average volume during contraction
                avg_vol = volume.iloc[current_high_idx : low_idx + 1].mean()

                contraction = Contraction(
                    start_idx=current_high_idx,
                    end_idx=low_idx,
                    high_price=current_high_price,
                    low_price=low_price,
                    depth_pct=depth_pct,
                    duration=low_idx - current_high_idx,
                    avg_volume=avg_vol,
                )
                contractions.append(contraction)

                # Find next swing high after this low
                next_highs = [h for h in swing_highs if h > low_idx]
                if next_highs:
                    # Use the first swing high that's higher than previous lows
                    for next_high_idx in next_highs:
                        next_high_price = high.iloc[next_high_idx]
                        # The next high should be above the current low
                        if next_high_price > low_price:
                            current_high_idx = next_high_idx
                            current_high_price = next_high_price
                            break

                if len(contractions) >= self.config.max_contractions:
                    break

        return contractions

    def _check_depth_decrease(self, contractions: list[Contraction]) -> bool:
        """Check if contraction depths are decreasing."""
        if len(contractions) < 2:
            return False

        for i in range(1, len(contractions)):
            ratio = contractions[i].depth_pct / contractions[i - 1].depth_pct
            if ratio > self.config.depth_decrease_ratio:
                return False

        return True

    def _analyze_volume_trend(
        self, volume: pd.Series, contractions: list[Contraction]
    ) -> float:
        """
        Analyze volume trend during contractions.

        Returns negative value if volume is decreasing (good for VCP).
        """
        if len(contractions) < 2:
            return 0.0

        # Compare average volume of each contraction
        volumes = [c.avg_volume for c in contractions]

        # Calculate linear regression slope of volumes
        x = np.arange(len(volumes))
        if np.std(volumes) > 0:
            correlation = np.corrcoef(x, volumes)[0, 1]
            # Negative correlation means decreasing volume
            return correlation
        return 0.0

    def _analyze_range_contraction(
        self,
        high: pd.Series,
        low: pd.Series,
        contractions: list[Contraction],
    ) -> float:
        """
        Analyze how much the trading range has contracted.

        Returns the ratio of range contraction (0 to 1).
        Higher values indicate more contraction (good for VCP).
        """
        if len(contractions) < 2:
            return 0.0

        # Calculate range for each contraction period
        ranges = []
        for c in contractions:
            period_high = high.iloc[c.start_idx : c.end_idx + 1].max()
            period_low = low.iloc[c.start_idx : c.end_idx + 1].min()
            range_pct = (period_high - period_low) / period_high * 100
            ranges.append(range_pct)

        # Calculate range contraction ratio
        if ranges[0] > 0:
            contraction_ratio = 1 - (ranges[-1] / ranges[0])
            return max(0, contraction_ratio)

        return 0.0

    def _find_pivot_price(
        self, high: pd.Series, contractions: list[Contraction]
    ) -> Optional[float]:
        """
        Find the pivot/breakout price level.

        The pivot is typically the highest point in the pattern.
        """
        if not contractions:
            return None

        # Pivot is the highest price among all contraction starting points
        pivot_prices = [c.high_price for c in contractions]
        return max(pivot_prices)

    def _validate_vcp(
        self,
        result: VCPResult,
        depth_decreasing: bool,
    ) -> bool:
        """
        Validate if the pattern is a valid VCP.

        Returns True if pattern meets VCP criteria.
        """
        # Must have enough contractions
        if result.contraction_count < self.config.min_contractions:
            return False

        # First contraction shouldn't be too deep
        if (
            result.depth_sequence
            and result.depth_sequence[0] > self.config.max_first_depth_pct
        ):
            return False

        # Depths should generally decrease
        if not depth_decreasing:
            # Allow some flexibility - check if overall trend is decreasing
            if len(result.depth_sequence) >= 2:
                if result.depth_sequence[-1] >= result.depth_sequence[0]:
                    return False

        # Volume should be decreasing or stable
        if result.volume_trend > 0.3:  # Strongly increasing volume is bad
            return False

        # Should be near pivot
        if (
            result.pivot_distance_pct > self.config.pivot_distance_threshold
            or result.pivot_distance_pct < -self.config.pivot_distance_threshold
        ):
            return False

        return True

    def _calculate_score(
        self,
        result: VCPResult,
        depth_decreasing: bool,
    ) -> float:
        """
        Calculate VCP quality score (0-100).

        Higher scores indicate stronger VCP patterns.
        """
        score = 0.0

        cfg = self.config

        # 1. Contraction count score (25 points)
        if result.contraction_count >= cfg.min_contractions:
            # More contractions = better (up to a point)
            contraction_score = (
                min(result.contraction_count, 4) / 4 * cfg.weight_contractions
            )
            score += contraction_score

        # 2. Depth decrease score (25 points)
        if len(result.depth_sequence) >= 2:
            if depth_decreasing:
                score += cfg.weight_depth_decrease
            else:
                # Partial credit if last depth is less than first
                if result.depth_sequence[-1] < result.depth_sequence[0]:
                    reduction_ratio = 1 - (
                        result.depth_sequence[-1] / result.depth_sequence[0]
                    )
                    score += reduction_ratio * cfg.weight_depth_decrease

        # 3. Volume score (20 points)
        # Negative trend is good (volume drying up)
        if result.volume_trend < cfg.volume_dry_up_threshold:
            score += cfg.weight_volume
        elif result.volume_trend < 0:
            score += abs(result.volume_trend) * cfg.weight_volume
        else:
            # Small penalty for increasing volume
            score += max(0, cfg.weight_volume - result.volume_trend * 10)

        # 4. Range contraction score (15 points)
        if result.range_contraction >= cfg.range_contraction_threshold:
            score += cfg.weight_range
        else:
            score += (
                result.range_contraction / cfg.range_contraction_threshold
            ) * cfg.weight_range

        # 5. Pivot proximity score (15 points)
        if abs(result.pivot_distance_pct) <= cfg.pivot_distance_threshold:
            proximity_score = (
                1 - abs(result.pivot_distance_pct) / cfg.pivot_distance_threshold
            )
            score += proximity_score * cfg.weight_pivot

        return min(100, max(0, score))

    def _add_signals(self, result: VCPResult, depth_decreasing: bool) -> None:
        """Add analysis signals to result."""
        if result.is_vcp:
            result.signals.append(
                f"VCP detected with {result.contraction_count} contractions"
            )

            if result.score >= 80:
                result.signals.append("Strong VCP setup")
            elif result.score >= 60:
                result.signals.append("Moderate VCP setup")
            else:
                result.signals.append("Weak VCP setup")

            if depth_decreasing:
                result.signals.append("Ideal depth progression")

            if result.volume_trend < -0.3:
                result.signals.append("Good volume dry-up")

            if result.range_contraction > 0.5:
                result.signals.append("Significant range contraction")

            if result.pivot_price and abs(result.pivot_distance_pct) < 3:
                result.signals.append(f"Near pivot point (${result.pivot_price:.2f})")
        else:
            # Add signals explaining why not detected as VCP
            if result.contraction_count < self.config.min_contractions:
                result.signals.append(
                    f"Only {result.contraction_count} contractions "
                    f"(need {self.config.min_contractions})"
                )
            if result.volume_trend > 0.3:
                result.signals.append("Volume increasing - not ideal for VCP")
            if result.pivot_distance_pct > self.config.pivot_distance_threshold:
                result.signals.append(
                    f"Price too far from pivot ({result.pivot_distance_pct:.1f}% away)"
                )
            elif result.pivot_distance_pct < -self.config.pivot_distance_threshold:
                result.signals.append(
                    f"Price above pivot ({abs(result.pivot_distance_pct):.1f}% above)"
                )
            if result.depth_sequence:
                if (
                    len(result.depth_sequence) >= 2
                    and result.depth_sequence[-1] >= result.depth_sequence[0]
                ):
                    result.signals.append("Contractions not decreasing in depth")
                if result.depth_sequence[0] > self.config.max_first_depth_pct:
                    result.signals.append(
                        f"First contraction too deep ({result.depth_sequence[0]:.1f}%)"
                    )

            # If we have contractions but didn't pass validation, add summary
            if result.contraction_count >= self.config.min_contractions:
                result.signals.append(
                    f"Pattern has {result.contraction_count} contractions with "
                    f"score {result.score:.1f} but failed validation"
                )


class VCPScanner(BaseIndicator):
    """
    Scanner for finding VCP patterns across multiple timeframes.

    Provides a simplified interface for scanning stocks for VCP setups.

    Usage:
        scanner = VCPScanner()
        result = scanner.scan(df)

        if result.is_vcp:
            print(f"VCP found! Score: {result.score}")
    """

    name = "VCPScanner"

    def __init__(
        self,
        config: Optional[VCPConfig] = None,
        min_score: float = 60.0,
    ):
        """
        Initialize VCP Scanner.

        Args:
            config: VCP configuration
            min_score: Minimum score to consider as valid VCP
        """
        self.config = config or VCPConfig()
        self.min_score = min_score
        self._vcp = VCP(config=self.config)

    def calculate(self, df: pd.DataFrame, **kwargs) -> IndicatorResult:
        """
        Calculate VCP scan result.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            IndicatorResult with VCPResult
        """
        result = self._vcp.calculate(df, **kwargs)
        # Override name to reflect scanner
        return IndicatorResult(
            name=self.name,
            values=result.values,
            params=result.params,
        )

    def scan(self, df: pd.DataFrame) -> VCPResult:
        """
        Scan for VCP pattern.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            VCPResult with scan results
        """
        result = self._vcp.calculate(df)
        vcp_result = result.values

        # Apply minimum score filter
        if vcp_result.score < self.min_score:
            vcp_result.is_vcp = False
            vcp_result.signals.append(
                f"Score {vcp_result.score:.1f} below threshold {self.min_score}"
            )

        return vcp_result


def detect_vcp(
    df: pd.DataFrame,
    config: Optional[VCPConfig] = None,
) -> VCPResult:
    """
    Convenience function to detect VCP pattern.

    Args:
        df: DataFrame with OHLCV data
        config: Optional VCP configuration

    Returns:
        VCPResult with detection results

    Example:
        result = detect_vcp(df)
        if result.is_vcp:
            print(f"VCP Score: {result.score}")
    """
    vcp = VCP(config=config)
    indicator_result = vcp.calculate(df)
    return indicator_result.values


def scan_vcp(
    df: pd.DataFrame,
    min_score: float = 60.0,
    config: Optional[VCPConfig] = None,
) -> VCPResult:
    """
    Convenience function to scan for VCP pattern.

    Args:
        df: DataFrame with OHLCV data
        min_score: Minimum score threshold
        config: Optional VCP configuration

    Returns:
        VCPResult with scan results

    Example:
        result = scan_vcp(df, min_score=70)
        if result.is_vcp:
            print(f"High quality VCP! Score: {result.score}")
    """
    scanner = VCPScanner(config=config, min_score=min_score)
    return scanner.scan(df)
