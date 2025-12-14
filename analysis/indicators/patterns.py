"""
Technical chart pattern recognition.

Implements detection for common chart patterns:
- Cup and Handle (杯柄形态)
- Head and Shoulders (头肩形态)
- Double Top/Bottom (双顶/双底)
- Triangle patterns (三角形整理)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult


class PatternType(str, Enum):
    """Pattern type enumeration."""

    CUP_AND_HANDLE = "CUP_AND_HANDLE"
    INVERSE_CUP_AND_HANDLE = "INVERSE_CUP_AND_HANDLE"
    HEAD_AND_SHOULDERS = "HEAD_AND_SHOULDERS"
    INVERSE_HEAD_AND_SHOULDERS = "INVERSE_HEAD_AND_SHOULDERS"
    DOUBLE_TOP = "DOUBLE_TOP"
    DOUBLE_BOTTOM = "DOUBLE_BOTTOM"
    ASCENDING_TRIANGLE = "ASCENDING_TRIANGLE"
    DESCENDING_TRIANGLE = "DESCENDING_TRIANGLE"
    SYMMETRICAL_TRIANGLE = "SYMMETRICAL_TRIANGLE"


class PatternBias(str, Enum):
    """Pattern directional bias."""

    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class PatternResult:
    """Result of pattern detection."""

    pattern_type: PatternType
    is_detected: bool = False
    confidence: float = 0.0  # 0-100
    bias: PatternBias = PatternBias.NEUTRAL
    start_idx: int = 0
    end_idx: int = 0
    breakout_price: Optional[float] = None
    target_price: Optional[float] = None
    stop_price: Optional[float] = None
    description: str = ""
    key_points: dict = field(default_factory=dict)


@dataclass
class CupHandleConfig:
    """Configuration for Cup and Handle detection."""

    min_cup_depth: float = 0.12  # Minimum 12% cup depth
    max_cup_depth: float = 0.35  # Maximum 35% cup depth
    min_cup_length: int = 20  # Minimum bars for cup
    max_cup_length: int = 60  # Maximum bars for cup
    handle_depth_ratio: float = 0.5  # Handle should be <50% of cup depth
    min_handle_length: int = 5  # Minimum handle length
    max_handle_length: int = 20  # Maximum handle length


class CupAndHandle(BaseIndicator):
    """Cup and Handle pattern detector.

    A bullish continuation pattern consisting of:
    1. Cup: A U-shaped price pattern forming a rounded bottom
    2. Handle: A small consolidation/pullback after the cup
    """

    def __init__(self, config: Optional[CupHandleConfig] = None):
        super().__init__()
        self.config = config or CupHandleConfig()

    def calculate(self, data: pd.DataFrame) -> PatternResult:
        """Detect Cup and Handle pattern.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            PatternResult with detection details
        """
        result = PatternResult(pattern_type=PatternType.CUP_AND_HANDLE)

        if len(data) < self.config.min_cup_length + self.config.min_handle_length:
            return result

        highs = data["high"].values
        lows = data["low"].values
        closes = data["close"].values

        # Find potential cup left rim (high before decline)
        for left_rim_idx in range(len(data) - self.config.min_cup_length - 5, 0, -1):
            left_rim = highs[left_rim_idx]

            # Look for cup bottom and right rim
            for cup_length in range(
                self.config.min_cup_length,
                min(self.config.max_cup_length, len(data) - left_rim_idx - 5),
            ):
                cup_end_idx = left_rim_idx + cup_length

                # Find cup bottom
                cup_data = lows[left_rim_idx : cup_end_idx + 1]
                cup_bottom_idx = left_rim_idx + np.argmin(cup_data)
                cup_bottom = lows[cup_bottom_idx]

                # Calculate cup depth
                cup_depth = (left_rim - cup_bottom) / left_rim

                if not (self.config.min_cup_depth <= cup_depth <= self.config.max_cup_depth):
                    continue

                # Check if cup is roughly U-shaped (bottom in middle third)
                cup_third = cup_length // 3
                if not (cup_third <= cup_bottom_idx - left_rim_idx <= cup_length - cup_third):
                    continue

                # Check right rim is close to left rim
                right_rim = highs[cup_end_idx]
                rim_diff = abs(right_rim - left_rim) / left_rim
                if rim_diff > 0.05:  # Allow 5% difference
                    continue

                # Look for handle
                handle_found = False
                for handle_length in range(
                    self.config.min_handle_length,
                    min(self.config.max_handle_length, len(data) - cup_end_idx),
                ):
                    handle_end_idx = cup_end_idx + handle_length
                    if handle_end_idx >= len(data):
                        break

                    handle_data = lows[cup_end_idx : handle_end_idx + 1]
                    handle_low = np.min(handle_data)
                    handle_depth = (right_rim - handle_low) / right_rim

                    # Handle should be shallower than cup
                    if handle_depth <= cup_depth * self.config.handle_depth_ratio:
                        handle_found = True

                        # Calculate confidence
                        confidence = 60.0
                        # Bonus for symmetrical cup
                        if rim_diff < 0.02:
                            confidence += 10
                        # Bonus for proper depth
                        if 0.15 <= cup_depth <= 0.30:
                            confidence += 10
                        # Bonus for handle in upper half
                        if handle_depth < cup_depth * 0.3:
                            confidence += 10
                        # Bonus for recent completion
                        if handle_end_idx >= len(data) - 5:
                            confidence += 10

                        result.is_detected = True
                        result.confidence = min(confidence, 100)
                        result.bias = PatternBias.BULLISH
                        result.start_idx = left_rim_idx
                        result.end_idx = handle_end_idx
                        result.breakout_price = max(left_rim, right_rim)
                        result.target_price = result.breakout_price + (
                            result.breakout_price - cup_bottom
                        )
                        result.stop_price = handle_low * 0.98
                        result.description = (
                            f"杯柄形态: 杯深{cup_depth:.1%}, 柄深{handle_depth:.1%}"
                        )
                        result.key_points = {
                            "left_rim": left_rim,
                            "cup_bottom": cup_bottom,
                            "right_rim": right_rim,
                            "handle_low": handle_low,
                        }

                        return result

        return result


@dataclass
class HeadShouldersConfig:
    """Configuration for Head and Shoulders detection."""

    min_pattern_length: int = 30
    max_pattern_length: int = 100
    shoulder_tolerance: float = 0.05  # Shoulders can differ by 5%
    head_min_diff: float = 0.03  # Head must be 3% above shoulders
    neckline_tolerance: float = 0.05  # Neckline can slope 5%


class HeadAndShoulders(BaseIndicator):
    """Head and Shoulders pattern detector.

    A reversal pattern consisting of:
    - Left shoulder, head, right shoulder (for bearish)
    - Inverse for bullish
    """

    def __init__(self, config: Optional[HeadShouldersConfig] = None):
        super().__init__()
        self.config = config or HeadShouldersConfig()

    def calculate(self, data: pd.DataFrame) -> PatternResult:
        """Detect Head and Shoulders pattern.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            PatternResult with detection details
        """
        # Try regular H&S first, then inverse
        result = self._detect_hs(data, inverse=False)
        if not result.is_detected:
            result = self._detect_hs(data, inverse=True)
        return result

    def _detect_hs(self, data: pd.DataFrame, inverse: bool = False) -> PatternResult:
        """Detect regular or inverse H&S."""
        pattern_type = (
            PatternType.INVERSE_HEAD_AND_SHOULDERS
            if inverse
            else PatternType.HEAD_AND_SHOULDERS
        )
        result = PatternResult(pattern_type=pattern_type)

        if len(data) < self.config.min_pattern_length:
            return result

        prices = data["low"].values if inverse else data["high"].values
        closes = data["close"].values

        # Find local extremes (potential shoulders and head)
        window = 5
        extremes = []

        for i in range(window, len(data) - window):
            if inverse:
                # Looking for lows
                if prices[i] == min(prices[i - window : i + window + 1]):
                    extremes.append((i, prices[i]))
            else:
                # Looking for highs
                if prices[i] == max(prices[i - window : i + window + 1]):
                    extremes.append((i, prices[i]))

        if len(extremes) < 3:
            return result

        # Look for H&S pattern in extremes
        for i in range(len(extremes) - 2):
            ls_idx, ls_price = extremes[i]
            head_idx, head_price = extremes[i + 1]
            rs_idx, rs_price = extremes[i + 2]

            # Pattern length check
            pattern_len = rs_idx - ls_idx
            if not (
                self.config.min_pattern_length
                <= pattern_len
                <= self.config.max_pattern_length
            ):
                continue

            # Shoulders should be similar height
            shoulder_diff = abs(ls_price - rs_price) / max(ls_price, rs_price)
            if shoulder_diff > self.config.shoulder_tolerance:
                continue

            # Head should be more extreme than shoulders
            if inverse:
                head_diff = (min(ls_price, rs_price) - head_price) / head_price
            else:
                head_diff = (head_price - max(ls_price, rs_price)) / max(
                    ls_price, rs_price
                )

            if head_diff < self.config.head_min_diff:
                continue

            # Find neckline (connect troughs/peaks between shoulders and head)
            if inverse:
                left_neck = max(data["high"].values[ls_idx:head_idx])
                right_neck = max(data["high"].values[head_idx:rs_idx])
            else:
                left_neck = min(data["low"].values[ls_idx:head_idx])
                right_neck = min(data["low"].values[head_idx:rs_idx])

            neckline_slope = (right_neck - left_neck) / left_neck
            if abs(neckline_slope) > self.config.neckline_tolerance:
                continue

            # Pattern found
            neckline = (left_neck + right_neck) / 2
            pattern_height = abs(head_price - neckline)

            confidence = 60.0
            # Bonus for symmetrical shoulders
            if shoulder_diff < 0.02:
                confidence += 15
            # Bonus for prominent head
            if head_diff > 0.05:
                confidence += 10
            # Bonus for flat neckline
            if abs(neckline_slope) < 0.02:
                confidence += 10
            # Recent pattern
            if rs_idx >= len(data) - 10:
                confidence += 5

            result.is_detected = True
            result.confidence = min(confidence, 100)
            result.bias = PatternBias.BULLISH if inverse else PatternBias.BEARISH
            result.start_idx = ls_idx
            result.end_idx = rs_idx
            result.breakout_price = neckline

            if inverse:
                result.target_price = neckline + pattern_height
                result.stop_price = head_price * 0.98
            else:
                result.target_price = neckline - pattern_height
                result.stop_price = head_price * 1.02

            result.description = (
                f"{'倒置' if inverse else ''}头肩{'底' if inverse else '顶'}: "
                f"颈线{neckline:.2f}, 高度{pattern_height:.2f}"
            )
            result.key_points = {
                "left_shoulder": ls_price,
                "head": head_price,
                "right_shoulder": rs_price,
                "neckline": neckline,
            }

            return result

        return result


@dataclass
class DoubleTopBottomConfig:
    """Configuration for Double Top/Bottom detection."""

    min_pattern_length: int = 15
    max_pattern_length: int = 60
    peak_tolerance: float = 0.03  # Peaks can differ by 3%
    min_valley_depth: float = 0.05  # Valley must be 5% from peaks


class DoubleTopBottom(BaseIndicator):
    """Double Top/Bottom pattern detector.

    - Double Top: Two peaks at similar levels (bearish)
    - Double Bottom: Two troughs at similar levels (bullish)
    """

    def __init__(self, config: Optional[DoubleTopBottomConfig] = None):
        super().__init__()
        self.config = config or DoubleTopBottomConfig()

    def calculate(self, data: pd.DataFrame) -> PatternResult:
        """Detect Double Top or Double Bottom.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            PatternResult with detection details
        """
        # Try double top first, then double bottom
        result = self._detect_double(data, is_top=True)
        if not result.is_detected:
            result = self._detect_double(data, is_top=False)
        return result

    def _detect_double(
        self, data: pd.DataFrame, is_top: bool = True
    ) -> PatternResult:
        """Detect double top or bottom."""
        pattern_type = PatternType.DOUBLE_TOP if is_top else PatternType.DOUBLE_BOTTOM
        result = PatternResult(pattern_type=pattern_type)

        if len(data) < self.config.min_pattern_length:
            return result

        prices = data["high"].values if is_top else data["low"].values
        closes = data["close"].values

        # Find local extremes
        window = 5
        extremes = []

        for i in range(window, len(data) - window):
            if is_top:
                if prices[i] == max(prices[i - window : i + window + 1]):
                    extremes.append((i, prices[i]))
            else:
                if prices[i] == min(prices[i - window : i + window + 1]):
                    extremes.append((i, prices[i]))

        if len(extremes) < 2:
            return result

        # Look for double pattern
        for i in range(len(extremes) - 1):
            first_idx, first_price = extremes[i]
            second_idx, second_price = extremes[i + 1]

            # Pattern length check
            pattern_len = second_idx - first_idx
            if not (
                self.config.min_pattern_length
                <= pattern_len
                <= self.config.max_pattern_length
            ):
                continue

            # Peaks/troughs should be similar
            peak_diff = abs(first_price - second_price) / max(first_price, second_price)
            if peak_diff > self.config.peak_tolerance:
                continue

            # Find the valley/peak between them
            between_prices = (
                data["low"].values[first_idx:second_idx]
                if is_top
                else data["high"].values[first_idx:second_idx]
            )

            if is_top:
                valley_price = np.min(between_prices)
                valley_depth = (first_price - valley_price) / first_price
            else:
                valley_price = np.max(between_prices)
                valley_depth = (valley_price - first_price) / first_price

            if valley_depth < self.config.min_valley_depth:
                continue

            # Pattern found
            avg_peak = (first_price + second_price) / 2
            pattern_height = abs(avg_peak - valley_price)

            confidence = 60.0
            # Bonus for equal peaks
            if peak_diff < 0.01:
                confidence += 20
            # Bonus for sufficient depth
            if valley_depth > 0.08:
                confidence += 10
            # Recent pattern
            if second_idx >= len(data) - 10:
                confidence += 10

            result.is_detected = True
            result.confidence = min(confidence, 100)
            result.bias = PatternBias.BEARISH if is_top else PatternBias.BULLISH
            result.start_idx = first_idx
            result.end_idx = second_idx
            result.breakout_price = valley_price

            if is_top:
                result.target_price = valley_price - pattern_height
                result.stop_price = avg_peak * 1.02
            else:
                result.target_price = valley_price + pattern_height
                result.stop_price = avg_peak * 0.98

            result.description = (
                f"双{'顶' if is_top else '底'}: "
                f"{'阻力' if is_top else '支撑'}{avg_peak:.2f}, 深度{valley_depth:.1%}"
            )
            result.key_points = {
                "first_peak": first_price,
                "second_peak": second_price,
                "valley": valley_price,
            }

            return result

        return result


@dataclass
class TriangleConfig:
    """Configuration for Triangle pattern detection."""

    min_pattern_length: int = 15
    max_pattern_length: int = 60
    min_touches: int = 4  # Minimum price touches on trendlines
    convergence_threshold: float = 0.7  # Lines should converge by 70%


class TrianglePattern(BaseIndicator):
    """Triangle pattern detector.

    Detects:
    - Ascending triangle (bullish)
    - Descending triangle (bearish)
    - Symmetrical triangle (neutral)
    """

    def __init__(self, config: Optional[TriangleConfig] = None):
        super().__init__()
        self.config = config or TriangleConfig()

    def calculate(self, data: pd.DataFrame) -> PatternResult:
        """Detect triangle pattern.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            PatternResult with detection details
        """
        result = PatternResult(pattern_type=PatternType.SYMMETRICAL_TRIANGLE)

        if len(data) < self.config.min_pattern_length:
            return result

        highs = data["high"].values
        lows = data["low"].values

        # Find swing highs and lows
        window = 3
        swing_highs = []
        swing_lows = []

        for i in range(window, len(data) - window):
            if highs[i] == max(highs[i - window : i + window + 1]):
                swing_highs.append((i, highs[i]))
            if lows[i] == min(lows[i - window : i + window + 1]):
                swing_lows.append((i, lows[i]))

        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return result

        # Fit trendlines to swing highs and lows
        high_x = np.array([sh[0] for sh in swing_highs])
        high_y = np.array([sh[1] for sh in swing_highs])
        low_x = np.array([sl[0] for sl in swing_lows])
        low_y = np.array([sl[1] for sl in swing_lows])

        # Linear regression for trendlines
        if len(high_x) >= 2:
            high_slope, high_intercept = np.polyfit(high_x, high_y, 1)
        else:
            return result

        if len(low_x) >= 2:
            low_slope, low_intercept = np.polyfit(low_x, low_y, 1)
        else:
            return result

        # Determine triangle type
        slope_tolerance = 0.001  # Per bar slope tolerance for "flat"

        if abs(high_slope) < slope_tolerance and low_slope > slope_tolerance:
            triangle_type = PatternType.ASCENDING_TRIANGLE
            bias = PatternBias.BULLISH
        elif high_slope < -slope_tolerance and abs(low_slope) < slope_tolerance:
            triangle_type = PatternType.DESCENDING_TRIANGLE
            bias = PatternBias.BEARISH
        elif high_slope < 0 and low_slope > 0:
            triangle_type = PatternType.SYMMETRICAL_TRIANGLE
            bias = PatternBias.NEUTRAL
        else:
            return result

        # Calculate convergence
        start_width = (high_intercept - low_intercept)
        end_high = high_slope * (len(data) - 1) + high_intercept
        end_low = low_slope * (len(data) - 1) + low_intercept
        end_width = end_high - end_low

        if start_width <= 0:
            return result

        convergence = 1 - (end_width / start_width)

        if convergence < self.config.convergence_threshold:
            return result

        # Pattern found
        pattern_height = start_width

        confidence = 50.0
        # Bonus for touches
        confidence += min(len(swing_highs) + len(swing_lows), 8) * 5
        # Bonus for convergence
        if convergence > 0.8:
            confidence += 10
        # Recent pattern
        if max(high_x[-1], low_x[-1]) >= len(data) - 10:
            confidence += 10

        result.pattern_type = triangle_type
        result.is_detected = True
        result.confidence = min(confidence, 100)
        result.bias = bias
        result.start_idx = min(swing_highs[0][0], swing_lows[0][0])
        result.end_idx = len(data) - 1

        # Breakout and target
        if triangle_type == PatternType.ASCENDING_TRIANGLE:
            result.breakout_price = end_high
            result.target_price = end_high + pattern_height
            result.stop_price = end_low * 0.98
        elif triangle_type == PatternType.DESCENDING_TRIANGLE:
            result.breakout_price = end_low
            result.target_price = end_low - pattern_height
            result.stop_price = end_high * 1.02
        else:
            # Symmetrical - could break either way
            mid = (end_high + end_low) / 2
            result.breakout_price = mid
            result.target_price = None
            result.stop_price = None

        type_names = {
            PatternType.ASCENDING_TRIANGLE: "上升三角形",
            PatternType.DESCENDING_TRIANGLE: "下降三角形",
            PatternType.SYMMETRICAL_TRIANGLE: "对称三角形",
        }

        result.description = (
            f"{type_names[triangle_type]}: 收敛{convergence:.1%}"
        )
        result.key_points = {
            "upper_trendline_slope": high_slope,
            "lower_trendline_slope": low_slope,
            "convergence": convergence,
        }

        return result


class PatternScanner:
    """Scan for multiple chart patterns."""

    def __init__(self):
        self.patterns = {
            "cup_handle": CupAndHandle(),
            "head_shoulders": HeadAndShoulders(),
            "double_top_bottom": DoubleTopBottom(),
            "triangle": TrianglePattern(),
        }

    def scan(self, data: pd.DataFrame) -> list[PatternResult]:
        """Scan for all patterns.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of detected patterns
        """
        results = []

        for name, detector in self.patterns.items():
            result = detector.calculate(data)
            if result.is_detected:
                results.append(result)

        # Sort by confidence
        results.sort(key=lambda x: x.confidence, reverse=True)

        return results


def detect_patterns(data: pd.DataFrame) -> list[PatternResult]:
    """Convenience function to detect all patterns.

    Args:
        data: DataFrame with OHLCV data

    Returns:
        List of detected patterns sorted by confidence
    """
    scanner = PatternScanner()
    return scanner.scan(data)
