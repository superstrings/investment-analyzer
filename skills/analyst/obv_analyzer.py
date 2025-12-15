"""
OBV (On-Balance Volume) Analyzer for Analyst Skill.

Provides high-level OBV analysis including:
- Trend detection (up/down/sideways)
- Divergence detection (bullish/bearish)
- Volume confirmation for price moves
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from analysis.indicators import OBV, OBVDivergence


class OBVTrend(Enum):
    """OBV trend classification."""

    STRONG_UP = "strong_up"
    UP = "up"
    SIDEWAYS = "sideways"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


class DivergenceType(Enum):
    """Divergence type."""

    BULLISH = "bullish"
    BEARISH = "bearish"
    NONE = "none"


@dataclass
class OBVAnalysisResult:
    """Result of OBV analysis."""

    # Core OBV values
    current_obv: float
    obv_ma: float  # Moving average of OBV
    obv_change_pct: float  # Recent change %

    # Trend analysis
    trend: OBVTrend
    trend_strength: float  # 0-100

    # Divergence
    divergence: DivergenceType
    divergence_strength: float  # 0-100

    # Volume confirmation
    volume_confirms_price: bool
    confirmation_score: float  # 0-100

    # Overall OBV score (0-100)
    score: float

    # Signals/messages
    signals: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "current_obv": self.current_obv,
            "obv_ma": self.obv_ma,
            "obv_change_pct": self.obv_change_pct,
            "trend": self.trend.value,
            "trend_strength": self.trend_strength,
            "divergence": self.divergence.value,
            "divergence_strength": self.divergence_strength,
            "volume_confirms_price": self.volume_confirms_price,
            "confirmation_score": self.confirmation_score,
            "score": self.score,
            "signals": self.signals,
        }


class OBVAnalyzer:
    """
    High-level OBV analyzer.

    Analyzes OBV for:
    1. Trend direction and strength
    2. Divergences with price
    3. Volume confirmation of price moves
    """

    def __init__(
        self,
        signal_period: int = 20,
        divergence_lookback: int = 14,
        trend_period: int = 20,
    ):
        """
        Initialize OBV analyzer.

        Args:
            signal_period: Period for OBV signal line
            divergence_lookback: Lookback for divergence detection
            trend_period: Period for trend analysis
        """
        self.signal_period = signal_period
        self.divergence_lookback = divergence_lookback
        self.trend_period = trend_period

    def analyze(self, df: pd.DataFrame) -> OBVAnalysisResult:
        """
        Analyze OBV for the given data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            OBVAnalysisResult with analysis results
        """
        signals = []

        if len(df) < self.trend_period + 10:
            return OBVAnalysisResult(
                current_obv=0,
                obv_ma=0,
                obv_change_pct=0,
                trend=OBVTrend.SIDEWAYS,
                trend_strength=0,
                divergence=DivergenceType.NONE,
                divergence_strength=0,
                volume_confirms_price=False,
                confirmation_score=0,
                score=0,
                signals=["Insufficient data for OBV analysis"],
            )

        # Calculate OBV with signal line
        obv_indicator = OBV(signal_period=self.signal_period)
        obv_result = obv_indicator.calculate(df)
        obv_df = obv_result.values

        current_obv = obv_df["OBV"].iloc[-1]
        obv_ma = obv_df["OBV_signal"].iloc[-1]

        # Calculate OBV change
        obv_start = obv_df["OBV"].iloc[-self.trend_period]
        obv_change_pct = (
            ((current_obv - obv_start) / abs(obv_start) * 100) if obv_start != 0 else 0
        )

        # Analyze trend
        trend, trend_strength = self._analyze_trend(obv_df)

        # Detect divergence
        divergence_indicator = OBVDivergence(lookback=self.divergence_lookback)
        div_result = divergence_indicator.calculate(df)
        divergence, divergence_strength = self._analyze_divergence(div_result.values)

        # Check volume confirmation
        confirms, confirmation_score = self._check_volume_confirmation(df, obv_df)

        # Generate signals
        if trend == OBVTrend.STRONG_UP:
            signals.append("OBV in strong uptrend - institutional buying")
        elif trend == OBVTrend.STRONG_DOWN:
            signals.append("OBV in strong downtrend - institutional selling")

        if divergence == DivergenceType.BULLISH:
            signals.append("Bullish OBV divergence - potential reversal up")
        elif divergence == DivergenceType.BEARISH:
            signals.append("Bearish OBV divergence - potential reversal down")

        if confirms:
            signals.append("Volume confirms price action")
        else:
            signals.append("Volume does not confirm price - caution")

        # Calculate overall score
        score = self._calculate_score(
            trend_strength, divergence, divergence_strength, confirmation_score
        )

        return OBVAnalysisResult(
            current_obv=current_obv,
            obv_ma=obv_ma,
            obv_change_pct=obv_change_pct,
            trend=trend,
            trend_strength=trend_strength,
            divergence=divergence,
            divergence_strength=divergence_strength,
            volume_confirms_price=confirms,
            confirmation_score=confirmation_score,
            score=score,
            signals=signals,
        )

    def _analyze_trend(
        self, obv_df: pd.DataFrame
    ) -> tuple[OBVTrend, float]:
        """Analyze OBV trend."""
        obv = obv_df["OBV"]
        obv_signal = obv_df["OBV_signal"]

        # Recent trend (last 20 bars)
        recent_obv = obv.iloc[-self.trend_period :]

        # Calculate slope using linear regression
        x = range(len(recent_obv))
        slope = (
            (len(x) * sum(x * recent_obv) - sum(x) * sum(recent_obv))
            / (len(x) * sum(x**2 for x in x) - sum(x) ** 2)
            if len(x) > 1
            else 0
        )

        # Normalize slope relative to OBV magnitude
        avg_obv = abs(recent_obv.mean()) if recent_obv.mean() != 0 else 1
        normalized_slope = slope / avg_obv * 100

        # Current position relative to signal line
        above_signal = obv.iloc[-1] > obv_signal.iloc[-1]

        # Determine trend
        if normalized_slope > 2 and above_signal:
            trend = OBVTrend.STRONG_UP
            strength = min(100, abs(normalized_slope) * 20)
        elif normalized_slope > 0.5:
            trend = OBVTrend.UP
            strength = min(80, 40 + abs(normalized_slope) * 15)
        elif normalized_slope < -2 and not above_signal:
            trend = OBVTrend.STRONG_DOWN
            strength = min(100, abs(normalized_slope) * 20)
        elif normalized_slope < -0.5:
            trend = OBVTrend.DOWN
            strength = min(80, 40 + abs(normalized_slope) * 15)
        else:
            trend = OBVTrend.SIDEWAYS
            strength = 30

        return trend, strength

    def _analyze_divergence(
        self, div_df: pd.DataFrame
    ) -> tuple[DivergenceType, float]:
        """Analyze divergences in recent data."""
        recent_div = div_df["divergence"].iloc[-10:]

        bullish_count = (recent_div == 1).sum()
        bearish_count = (recent_div == -1).sum()

        if bullish_count > 0:
            return DivergenceType.BULLISH, min(100, bullish_count * 30)
        elif bearish_count > 0:
            return DivergenceType.BEARISH, min(100, bearish_count * 30)
        else:
            return DivergenceType.NONE, 0

    def _check_volume_confirmation(
        self, df: pd.DataFrame, obv_df: pd.DataFrame
    ) -> tuple[bool, float]:
        """Check if volume confirms price action."""
        close = df["Close"] if "Close" in df.columns else df["close"]
        obv = obv_df["OBV"]

        # Price trend (last 10 bars)
        price_change = (close.iloc[-1] - close.iloc[-10]) / close.iloc[-10] * 100
        obv_change = (
            (obv.iloc[-1] - obv.iloc[-10]) / abs(obv.iloc[-10]) * 100
            if obv.iloc[-10] != 0
            else 0
        )

        # Confirmation: both moving same direction
        price_up = price_change > 0
        obv_up = obv_change > 0

        confirms = price_up == obv_up

        # Calculate confirmation score
        if confirms:
            # Strong confirmation if both have similar magnitude
            magnitude_ratio = min(abs(obv_change), abs(price_change)) / max(
                abs(obv_change), abs(price_change), 0.01
            )
            score = 50 + magnitude_ratio * 50
        else:
            score = 30 - min(30, abs(price_change - obv_change))

        return confirms, max(0, min(100, score))

    def _calculate_score(
        self,
        trend_strength: float,
        divergence: DivergenceType,
        divergence_strength: float,
        confirmation_score: float,
    ) -> float:
        """Calculate overall OBV score (0-100)."""
        # Base score from trend strength (40%)
        score = trend_strength * 0.4

        # Divergence bonus/penalty (30%)
        if divergence == DivergenceType.BULLISH:
            score += divergence_strength * 0.3
        elif divergence == DivergenceType.BEARISH:
            score -= divergence_strength * 0.15  # Bearish is a warning, not full penalty

        # Confirmation score (30%)
        score += confirmation_score * 0.3

        return max(0, min(100, score))
