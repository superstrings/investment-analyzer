"""
Enhanced Technical Analyzer for Deep Analysis.

Provides comprehensive technical analysis including:
- OBV trend and divergence
- VCP pattern detection
- RSI overbought/oversold
- MACD signals
- Support/Resistance levels
- Trend analysis
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

import pandas as pd

from analysis.indicators import (
    BollingerBands,
    MACD,
    OBV,
    RSI,
)
from analysis.indicators.vcp import VCPScanner
from skills.shared import DataProvider

logger = logging.getLogger(__name__)


@dataclass
class SupportResistance:
    """Support and resistance levels."""

    support_1: float
    support_2: float
    resistance_1: float
    resistance_2: float
    pivot: float


@dataclass
class TrendAnalysis:
    """Trend analysis result."""

    short_term: str  # up, down, sideways
    medium_term: str
    long_term: str
    strength: int  # 0-100
    description: str


@dataclass
class MACDSignal:
    """MACD signal analysis."""

    macd_value: float
    signal_value: float
    histogram: float
    trend: str  # bullish, bearish, neutral
    crossover: Optional[str]  # golden_cross, death_cross, none
    divergence: Optional[str]  # bullish, bearish, none


@dataclass
class RSIAnalysis:
    """RSI analysis result."""

    value: float
    zone: str  # overbought, oversold, neutral
    trend: str  # rising, falling, flat
    divergence: Optional[str]  # bullish, bearish, none


@dataclass
class EnhancedTechnicalResult:
    """Complete enhanced technical analysis result."""

    # Basic info
    market: str
    code: str
    stock_name: str
    analysis_date: date
    current_price: float

    # Price changes
    change_1d: float
    change_5d: float
    change_20d: float
    change_60d: float

    # Trend analysis
    trend: TrendAnalysis

    # Moving averages
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    ma_alignment: str  # bullish, bearish, mixed

    # OBV
    obv_trend: str
    obv_divergence: Optional[str]
    obv_score: float

    # VCP
    vcp_detected: bool
    vcp_stage: Optional[str]
    vcp_score: float
    vcp_contractions: int

    # RSI
    rsi: RSIAnalysis

    # MACD
    macd: MACDSignal

    # Bollinger Bands
    bb_position: str  # above_upper, below_lower, middle
    bb_width: float  # volatility indicator

    # Support/Resistance
    levels: SupportResistance

    # Volume
    volume_trend: str  # increasing, decreasing, stable
    volume_ratio: float  # vs 20-day average

    # Overall
    technical_score: int  # 0-100
    technical_rating: str  # strong_buy, buy, hold, sell, strong_sell
    signals: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class EnhancedTechnicalAnalyzer:
    """
    Enhanced technical analyzer for deep stock analysis.

    Combines multiple technical indicators for comprehensive analysis.
    """

    def __init__(self, data_provider: DataProvider = None):
        """Initialize analyzer."""
        self.data_provider = data_provider or DataProvider()
        self.rsi_calculator = RSI()
        self.macd_calculator = MACD()
        self.obv_calculator = OBV()
        self.bb_calculator = BollingerBands()
        self.vcp_scanner = VCPScanner()

    def analyze(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        days: int = 250,
    ) -> Optional[EnhancedTechnicalResult]:
        """
        Perform comprehensive technical analysis.

        Args:
            market: Market code (HK, US, A)
            code: Stock code
            stock_name: Stock name
            days: Days of data to analyze

        Returns:
            EnhancedTechnicalResult or None if insufficient data
        """
        # Get K-line data
        df = self.data_provider.get_klines_df(market, code, days=days)

        if df.empty or len(df) < 60:
            logger.warning(f"Insufficient data for {market}.{code}")
            return None

        try:
            current_price = float(df["Close"].iloc[-1])

            # Calculate price changes
            change_1d = self._calc_change(df, 1)
            change_5d = self._calc_change(df, 5)
            change_20d = self._calc_change(df, 20)
            change_60d = self._calc_change(df, 60)

            # Moving averages
            ma5 = self._safe_ma(df, 5)
            ma10 = self._safe_ma(df, 10)
            ma20 = self._safe_ma(df, 20)
            ma60 = self._safe_ma(df, 60)
            ma_alignment = self._analyze_ma_alignment(ma5, ma10, ma20, ma60)

            # Trend analysis
            trend = self._analyze_trend(df, ma5, ma10, ma20, ma60)

            # OBV analysis
            obv_result = self._analyze_obv(df)

            # VCP analysis
            vcp_result = self._analyze_vcp(df)

            # RSI analysis
            rsi_result = self._analyze_rsi(df)

            # MACD analysis
            macd_result = self._analyze_macd(df)

            # Bollinger Bands
            bb_position, bb_width = self._analyze_bollinger(df)

            # Support/Resistance
            levels = self._calculate_support_resistance(df)

            # Volume analysis
            volume_trend, volume_ratio = self._analyze_volume(df)

            # Calculate overall score and rating
            signals = []
            warnings = []

            technical_score = self._calculate_overall_score(
                trend, ma_alignment, obv_result, vcp_result,
                rsi_result, macd_result, signals, warnings
            )

            technical_rating = self._score_to_rating(technical_score)

            return EnhancedTechnicalResult(
                market=market,
                code=code,
                stock_name=stock_name,
                analysis_date=date.today(),
                current_price=current_price,
                change_1d=change_1d,
                change_5d=change_5d,
                change_20d=change_20d,
                change_60d=change_60d,
                trend=trend,
                ma5=ma5,
                ma10=ma10,
                ma20=ma20,
                ma60=ma60,
                ma_alignment=ma_alignment,
                obv_trend=obv_result["trend"],
                obv_divergence=obv_result["divergence"],
                obv_score=obv_result["score"],
                vcp_detected=vcp_result["detected"],
                vcp_stage=vcp_result["stage"],
                vcp_score=vcp_result["score"],
                vcp_contractions=vcp_result["contractions"],
                rsi=rsi_result,
                macd=macd_result,
                bb_position=bb_position,
                bb_width=bb_width,
                levels=levels,
                volume_trend=volume_trend,
                volume_ratio=volume_ratio,
                technical_score=technical_score,
                technical_rating=technical_rating,
                signals=signals,
                warnings=warnings,
            )

        except Exception as e:
            logger.exception(f"Error analyzing {market}.{code}: {e}")
            return None

    def _calc_change(self, df: pd.DataFrame, days: int) -> float:
        """Calculate price change over N days."""
        if len(df) < days + 1:
            return 0.0
        current = df["Close"].iloc[-1]
        previous = df["Close"].iloc[-days - 1]
        if previous == 0:
            return 0.0
        return ((current - previous) / previous) * 100

    def _safe_ma(self, df: pd.DataFrame, period: int) -> float:
        """Safely calculate moving average."""
        if len(df) < period:
            return float(df["Close"].iloc[-1])
        return float(df["Close"].iloc[-period:].mean())

    def _analyze_ma_alignment(
        self, ma5: float, ma10: float, ma20: float, ma60: float
    ) -> str:
        """Analyze moving average alignment."""
        if ma5 > ma10 > ma20 > ma60:
            return "bullish"
        elif ma5 < ma10 < ma20 < ma60:
            return "bearish"
        else:
            return "mixed"

    def _analyze_trend(
        self,
        df: pd.DataFrame,
        ma5: float,
        ma10: float,
        ma20: float,
        ma60: float,
    ) -> TrendAnalysis:
        """Analyze price trend."""
        current = float(df["Close"].iloc[-1])

        # Short-term (5-day)
        if current > ma5:
            short_term = "up"
        elif current < ma5:
            short_term = "down"
        else:
            short_term = "sideways"

        # Medium-term (20-day)
        if current > ma20 and ma5 > ma20:
            medium_term = "up"
        elif current < ma20 and ma5 < ma20:
            medium_term = "down"
        else:
            medium_term = "sideways"

        # Long-term (60-day)
        if current > ma60 and ma20 > ma60:
            long_term = "up"
        elif current < ma60 and ma20 < ma60:
            long_term = "down"
        else:
            long_term = "sideways"

        # Trend strength
        strength = 50
        if short_term == medium_term == long_term:
            strength = 80 if short_term == "up" else 20 if short_term == "down" else 50
        elif short_term == medium_term:
            strength = 65 if short_term == "up" else 35 if short_term == "down" else 50

        # Description
        if strength >= 70:
            description = "强势上升趋势"
        elif strength >= 55:
            description = "温和上升趋势"
        elif strength <= 30:
            description = "强势下降趋势"
        elif strength <= 45:
            description = "温和下降趋势"
        else:
            description = "横盘震荡"

        return TrendAnalysis(
            short_term=short_term,
            medium_term=medium_term,
            long_term=long_term,
            strength=strength,
            description=description,
        )

    def _analyze_obv(self, df: pd.DataFrame) -> dict:
        """Analyze OBV indicator."""
        try:
            obv_df = self.obv_calculator.calculate(df)

            # Get OBV trend
            obv_values = obv_df["OBV"].tail(20).values
            obv_ma = obv_df["OBV"].tail(20).mean()
            current_obv = obv_values[-1]

            if current_obv > obv_ma * 1.05:
                trend = "up"
            elif current_obv < obv_ma * 0.95:
                trend = "down"
            else:
                trend = "sideways"

            # Check for divergence
            price_change = self._calc_change(df, 20)
            obv_change = ((current_obv - obv_values[0]) / abs(obv_values[0])) * 100 if obv_values[0] != 0 else 0

            divergence = None
            if price_change < -5 and obv_change > 5:
                divergence = "bullish"
            elif price_change > 5 and obv_change < -5:
                divergence = "bearish"

            # Score (0-100)
            score = 50
            if trend == "up":
                score += 25
            elif trend == "down":
                score -= 25
            if divergence == "bullish":
                score += 15
            elif divergence == "bearish":
                score -= 15

            return {
                "trend": trend,
                "divergence": divergence,
                "score": max(0, min(100, score)),
            }
        except Exception:
            return {"trend": "unknown", "divergence": None, "score": 50}

    def _analyze_vcp(self, df: pd.DataFrame) -> dict:
        """Analyze VCP pattern."""
        try:
            result = self.vcp_scanner.scan(df)

            return {
                "detected": result.is_valid if result else False,
                "stage": result.stage if result and result.is_valid else None,
                "score": result.score if result else 0,
                "contractions": result.contraction_count if result else 0,
            }
        except Exception:
            return {"detected": False, "stage": None, "score": 0, "contractions": 0}

    def _analyze_rsi(self, df: pd.DataFrame) -> RSIAnalysis:
        """Analyze RSI indicator."""
        try:
            rsi_df = self.rsi_calculator.calculate(df)
            rsi_values = rsi_df["RSI"].tail(5).values
            current_rsi = rsi_values[-1]

            # Zone
            if current_rsi >= 70:
                zone = "overbought"
            elif current_rsi <= 30:
                zone = "oversold"
            else:
                zone = "neutral"

            # Trend
            if len(rsi_values) >= 3:
                if rsi_values[-1] > rsi_values[-3]:
                    rsi_trend = "rising"
                elif rsi_values[-1] < rsi_values[-3]:
                    rsi_trend = "falling"
                else:
                    rsi_trend = "flat"
            else:
                rsi_trend = "flat"

            # Divergence
            price_change = self._calc_change(df, 10)
            rsi_change = rsi_values[-1] - rsi_values[0] if len(rsi_values) >= 5 else 0

            divergence = None
            if price_change < -3 and rsi_change > 5:
                divergence = "bullish"
            elif price_change > 3 and rsi_change < -5:
                divergence = "bearish"

            return RSIAnalysis(
                value=float(current_rsi),
                zone=zone,
                trend=rsi_trend,
                divergence=divergence,
            )
        except Exception:
            return RSIAnalysis(value=50, zone="neutral", trend="flat", divergence=None)

    def _analyze_macd(self, df: pd.DataFrame) -> MACDSignal:
        """Analyze MACD indicator."""
        try:
            macd_df = self.macd_calculator.calculate(df)

            macd_val = float(macd_df["MACD"].iloc[-1])
            signal_val = float(macd_df["Signal"].iloc[-1])
            hist = float(macd_df["Histogram"].iloc[-1])

            # Trend
            if macd_val > signal_val and hist > 0:
                trend = "bullish"
            elif macd_val < signal_val and hist < 0:
                trend = "bearish"
            else:
                trend = "neutral"

            # Crossover detection
            crossover = None
            if len(macd_df) >= 2:
                prev_macd = float(macd_df["MACD"].iloc[-2])
                prev_signal = float(macd_df["Signal"].iloc[-2])

                if prev_macd <= prev_signal and macd_val > signal_val:
                    crossover = "golden_cross"
                elif prev_macd >= prev_signal and macd_val < signal_val:
                    crossover = "death_cross"

            # Divergence
            divergence = None
            price_change = self._calc_change(df, 10)
            macd_values = macd_df["MACD"].tail(10).values
            macd_change = macd_values[-1] - macd_values[0] if len(macd_values) >= 10 else 0

            if price_change < -3 and macd_change > 0:
                divergence = "bullish"
            elif price_change > 3 and macd_change < 0:
                divergence = "bearish"

            return MACDSignal(
                macd_value=macd_val,
                signal_value=signal_val,
                histogram=hist,
                trend=trend,
                crossover=crossover,
                divergence=divergence,
            )
        except Exception:
            return MACDSignal(
                macd_value=0, signal_value=0, histogram=0,
                trend="neutral", crossover=None, divergence=None
            )

    def _analyze_bollinger(self, df: pd.DataFrame) -> tuple[str, float]:
        """Analyze Bollinger Bands."""
        try:
            bb_df = self.bb_calculator.calculate(df)

            current = float(df["Close"].iloc[-1])
            upper = float(bb_df["Upper"].iloc[-1])
            lower = float(bb_df["Lower"].iloc[-1])
            middle = float(bb_df["Middle"].iloc[-1])

            # Position
            if current > upper:
                position = "above_upper"
            elif current < lower:
                position = "below_lower"
            else:
                position = "middle"

            # Width (volatility)
            width = ((upper - lower) / middle) * 100 if middle != 0 else 0

            return position, float(width)
        except Exception:
            return "middle", 0.0

    def _calculate_support_resistance(self, df: pd.DataFrame) -> SupportResistance:
        """Calculate support and resistance levels."""
        try:
            # Use recent 60 days
            recent = df.tail(60)

            high = float(recent["High"].max())
            low = float(recent["Low"].min())
            close = float(recent["Close"].iloc[-1])

            # Pivot point
            pivot = (high + low + close) / 3

            # Support levels
            support_1 = 2 * pivot - high
            support_2 = pivot - (high - low)

            # Resistance levels
            resistance_1 = 2 * pivot - low
            resistance_2 = pivot + (high - low)

            return SupportResistance(
                support_1=round(support_1, 2),
                support_2=round(support_2, 2),
                resistance_1=round(resistance_1, 2),
                resistance_2=round(resistance_2, 2),
                pivot=round(pivot, 2),
            )
        except Exception:
            current = float(df["Close"].iloc[-1])
            return SupportResistance(
                support_1=current * 0.95,
                support_2=current * 0.90,
                resistance_1=current * 1.05,
                resistance_2=current * 1.10,
                pivot=current,
            )

    def _analyze_volume(self, df: pd.DataFrame) -> tuple[str, float]:
        """Analyze volume trend."""
        try:
            vol_5 = float(df["Volume"].tail(5).mean())
            vol_20 = float(df["Volume"].tail(20).mean())

            ratio = vol_5 / vol_20 if vol_20 > 0 else 1.0

            if ratio > 1.2:
                trend = "increasing"
            elif ratio < 0.8:
                trend = "decreasing"
            else:
                trend = "stable"

            return trend, round(ratio, 2)
        except Exception:
            return "stable", 1.0

    def _calculate_overall_score(
        self,
        trend: TrendAnalysis,
        ma_alignment: str,
        obv: dict,
        vcp: dict,
        rsi: RSIAnalysis,
        macd: MACDSignal,
        signals: list,
        warnings: list,
    ) -> int:
        """Calculate overall technical score."""
        score = 50  # Base score

        # Trend contribution (30%)
        score += (trend.strength - 50) * 0.3

        # MA alignment (15%)
        if ma_alignment == "bullish":
            score += 15
            signals.append("均线多头排列")
        elif ma_alignment == "bearish":
            score -= 15
            warnings.append("均线空头排列")

        # OBV contribution (15%)
        score += (obv["score"] - 50) * 0.15
        if obv["divergence"] == "bullish":
            signals.append("OBV看涨背离")
        elif obv["divergence"] == "bearish":
            warnings.append("OBV看跌背离")

        # VCP contribution (15%)
        if vcp["detected"]:
            score += 15
            signals.append(f"VCP形态形成 ({vcp['contractions']}次收缩)")

        # RSI contribution (10%)
        if rsi.zone == "oversold":
            score += 10
            signals.append("RSI超卖，可能反弹")
        elif rsi.zone == "overbought":
            score -= 10
            warnings.append("RSI超买，注意回调")

        # MACD contribution (15%)
        if macd.crossover == "golden_cross":
            score += 15
            signals.append("MACD金叉")
        elif macd.crossover == "death_cross":
            score -= 15
            warnings.append("MACD死叉")
        elif macd.trend == "bullish":
            score += 5
        elif macd.trend == "bearish":
            score -= 5

        return max(0, min(100, int(score)))

    def _score_to_rating(self, score: int) -> str:
        """Convert score to rating."""
        if score >= 80:
            return "strong_buy"
        elif score >= 60:
            return "buy"
        elif score >= 40:
            return "hold"
        elif score >= 20:
            return "sell"
        else:
            return "strong_sell"
