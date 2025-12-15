"""
Scoring System for Analyst Skill.

Combines OBV (40%) + VCP (60%) into a unified technical score.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .obv_analyzer import DivergenceType, OBVAnalysisResult, OBVTrend
from .vcp_scanner import VCPAnalysisResult, VCPStage


class TechnicalRating(Enum):
    """Overall technical rating."""

    STRONG_BUY = "strong_buy"  # Score >= 80
    BUY = "buy"  # Score >= 65
    HOLD = "hold"  # Score >= 45
    SELL = "sell"  # Score >= 25
    STRONG_SELL = "strong_sell"  # Score < 25


class SignalStrength(Enum):
    """Signal strength level."""

    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class TechnicalScore:
    """Combined technical analysis score."""

    # Component scores
    obv_score: float  # 0-100
    vcp_score: float  # 0-100

    # Weighted final score
    final_score: float  # 0-100 (OBV 40% + VCP 60%)

    # Rating
    rating: TechnicalRating
    signal_strength: SignalStrength

    # Key metrics summary
    obv_trend: str
    obv_divergence: str
    vcp_detected: bool
    vcp_stage: str
    pivot_price: Optional[float]
    distance_to_pivot: float

    # Action recommendations
    action: str
    key_levels: list[str]
    watch_points: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "obv_score": self.obv_score,
            "vcp_score": self.vcp_score,
            "final_score": self.final_score,
            "rating": self.rating.value,
            "signal_strength": self.signal_strength.value,
            "obv_trend": self.obv_trend,
            "obv_divergence": self.obv_divergence,
            "vcp_detected": self.vcp_detected,
            "vcp_stage": self.vcp_stage,
            "pivot_price": self.pivot_price,
            "distance_to_pivot": self.distance_to_pivot,
            "action": self.action,
            "key_levels": self.key_levels,
            "watch_points": self.watch_points,
        }


class ScoringSystem:
    """
    Technical scoring system combining OBV and VCP.

    Weights:
    - OBV: 40% (量价关系分析)
    - VCP: 60% (形态突破潜力)
    """

    OBV_WEIGHT = 0.40
    VCP_WEIGHT = 0.60

    def __init__(
        self,
        obv_weight: float = 0.40,
        vcp_weight: float = 0.60,
    ):
        """
        Initialize scoring system.

        Args:
            obv_weight: Weight for OBV score (default 40%)
            vcp_weight: Weight for VCP score (default 60%)
        """
        total = obv_weight + vcp_weight
        self.obv_weight = obv_weight / total
        self.vcp_weight = vcp_weight / total

    def calculate_score(
        self,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
        current_price: Optional[float] = None,
    ) -> TechnicalScore:
        """
        Calculate combined technical score.

        Args:
            obv_result: OBV analysis result
            vcp_result: VCP analysis result
            current_price: Current stock price

        Returns:
            TechnicalScore with combined analysis
        """
        # Get component scores
        obv_score = obv_result.score
        vcp_score = vcp_result.overall_score

        # Calculate weighted final score
        final_score = obv_score * self.obv_weight + vcp_score * self.vcp_weight

        # Apply bonuses/penalties for specific conditions
        final_score = self._apply_adjustments(
            final_score, obv_result, vcp_result
        )

        # Determine rating
        rating = self._get_rating(final_score)
        signal_strength = self._get_signal_strength(final_score, obv_result, vcp_result)

        # Generate action recommendation
        action = self._generate_action(rating, obv_result, vcp_result)

        # Identify key levels
        key_levels = self._identify_key_levels(vcp_result, current_price)

        # Generate watch points
        watch_points = self._generate_watch_points(obv_result, vcp_result)

        return TechnicalScore(
            obv_score=obv_score,
            vcp_score=vcp_score,
            final_score=final_score,
            rating=rating,
            signal_strength=signal_strength,
            obv_trend=obv_result.trend.value,
            obv_divergence=obv_result.divergence.value,
            vcp_detected=vcp_result.detected,
            vcp_stage=vcp_result.stage.value,
            pivot_price=vcp_result.pivot_price,
            distance_to_pivot=vcp_result.distance_to_pivot_pct,
            action=action,
            key_levels=key_levels,
            watch_points=watch_points,
        )

    def _apply_adjustments(
        self,
        score: float,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
    ) -> float:
        """Apply bonus/penalty adjustments to score."""
        adjusted = score

        # Bonus: VCP + bullish OBV divergence (strong setup)
        if vcp_result.detected and obv_result.divergence == DivergenceType.BULLISH:
            adjusted += 10

        # Bonus: VCP near breakout with strong OBV
        if vcp_result.stage == VCPStage.MATURE and obv_result.trend in (
            OBVTrend.STRONG_UP,
            OBVTrend.UP,
        ):
            adjusted += 8

        # Bonus: Volume confirms + VCP forming
        if obv_result.volume_confirms_price and vcp_result.volume_dryup:
            adjusted += 5

        # Penalty: Bearish divergence
        if obv_result.divergence == DivergenceType.BEARISH:
            adjusted -= 10

        # Penalty: Strong downtrend in OBV
        if obv_result.trend == OBVTrend.STRONG_DOWN:
            adjusted -= 8

        return max(0, min(100, adjusted))

    def _get_rating(self, score: float) -> TechnicalRating:
        """Get rating based on score."""
        if score >= 80:
            return TechnicalRating.STRONG_BUY
        elif score >= 65:
            return TechnicalRating.BUY
        elif score >= 45:
            return TechnicalRating.HOLD
        elif score >= 25:
            return TechnicalRating.SELL
        else:
            return TechnicalRating.STRONG_SELL

    def _get_signal_strength(
        self,
        score: float,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
    ) -> SignalStrength:
        """Determine signal strength."""
        # Strong signal: High score + VCP detected + good OBV
        if score >= 75 and vcp_result.detected and obv_result.trend in (
            OBVTrend.STRONG_UP,
            OBVTrend.UP,
        ):
            return SignalStrength.STRONG

        # Moderate signal: Good score + either VCP or OBV positive
        if score >= 55 and (vcp_result.detected or obv_result.score >= 60):
            return SignalStrength.MODERATE

        # Weak signal: Some positive indicators
        if score >= 40:
            return SignalStrength.WEAK

        return SignalStrength.NONE

    def _generate_action(
        self,
        rating: TechnicalRating,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
    ) -> str:
        """Generate action recommendation."""
        if rating == TechnicalRating.STRONG_BUY:
            if vcp_result.stage == VCPStage.BREAKOUT:
                return "Consider buying - VCP breakout in progress"
            elif vcp_result.stage == VCPStage.MATURE:
                return "Add to watchlist - VCP ready for breakout"
            else:
                return "Strong technical setup - monitor for entry"

        elif rating == TechnicalRating.BUY:
            if vcp_result.detected:
                return "Watch for VCP breakout entry"
            else:
                return "Positive technicals - look for pullback entry"

        elif rating == TechnicalRating.HOLD:
            if obv_result.divergence == DivergenceType.BULLISH:
                return "Hold - bullish divergence forming"
            elif obv_result.divergence == DivergenceType.BEARISH:
                return "Hold with caution - bearish divergence"
            else:
                return "Hold - wait for clearer signal"

        elif rating == TechnicalRating.SELL:
            return "Consider reducing position"

        else:  # STRONG_SELL
            return "Consider exiting - weak technicals"

    def _identify_key_levels(
        self,
        vcp_result: VCPAnalysisResult,
        current_price: Optional[float],
    ) -> list[str]:
        """Identify key price levels."""
        levels = []

        if vcp_result.pivot_price:
            levels.append(f"Pivot/Breakout: {vcp_result.pivot_price:.2f}")

        if current_price and vcp_result.pivot_price:
            # Stop loss suggestion (typically 7-8% below pivot or entry)
            stop = vcp_result.pivot_price * 0.92
            levels.append(f"Stop Loss (8%): {stop:.2f}")

        return levels

    def _generate_watch_points(
        self,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
    ) -> list[str]:
        """Generate watch points for monitoring."""
        points = []

        if vcp_result.detected and vcp_result.pivot_price:
            points.append(f"Watch for break above {vcp_result.pivot_price:.2f}")

        if obv_result.divergence == DivergenceType.BULLISH:
            points.append("Monitor for reversal confirmation")
        elif obv_result.divergence == DivergenceType.BEARISH:
            points.append("Watch for breakdown - bearish divergence present")

        if vcp_result.volume_dryup:
            points.append("Volume drying up - watch for volume spike on breakout")

        if not obv_result.volume_confirms_price:
            points.append("Volume not confirming price - wait for confirmation")

        return points


def calculate_technical_score(
    obv_result: OBVAnalysisResult,
    vcp_result: VCPAnalysisResult,
    current_price: Optional[float] = None,
) -> TechnicalScore:
    """
    Convenience function to calculate technical score.

    Args:
        obv_result: OBV analysis result
        vcp_result: VCP analysis result
        current_price: Current price

    Returns:
        TechnicalScore
    """
    scorer = ScoringSystem()
    return scorer.calculate_score(obv_result, vcp_result, current_price)
