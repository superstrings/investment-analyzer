"""
VCP (Volatility Contraction Pattern) Scanner for Analyst Skill.

Provides high-level VCP analysis including:
- Pattern detection
- Quality scoring
- Breakout level identification
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import pandas as pd

from analysis.indicators import VCP, VCPConfig, VCPResult


class VCPStage(Enum):
    """VCP pattern stage."""

    NO_PATTERN = "no_pattern"
    FORMING = "forming"  # Early stage, 1-2 contractions
    MATURE = "mature"  # 3+ contractions, near breakout
    BREAKOUT = "breakout"  # At or above pivot


@dataclass
class VCPAnalysisResult:
    """Result of VCP analysis."""

    # Pattern detection
    detected: bool
    stage: VCPStage

    # Pattern quality
    contraction_count: int
    depth_sequence: list[float]  # e.g., [25%, 15%, 8%]
    volume_dryup: bool  # Is volume decreasing
    range_tightening: bool  # Is price range contracting

    # Breakout info
    pivot_price: Optional[float]
    current_price: float
    distance_to_pivot_pct: float

    # Scoring (0-100)
    pattern_score: float
    volume_score: float
    timing_score: float  # How close to breakout
    overall_score: float

    # Signals
    signals: list[str]

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "detected": self.detected,
            "stage": self.stage.value,
            "contraction_count": self.contraction_count,
            "depth_sequence": self.depth_sequence,
            "volume_dryup": self.volume_dryup,
            "range_tightening": self.range_tightening,
            "pivot_price": self.pivot_price,
            "current_price": self.current_price,
            "distance_to_pivot_pct": self.distance_to_pivot_pct,
            "pattern_score": self.pattern_score,
            "volume_score": self.volume_score,
            "timing_score": self.timing_score,
            "overall_score": self.overall_score,
            "signals": self.signals,
        }


class VCPScanner:
    """
    High-level VCP pattern scanner.

    Analyzes stocks for VCP patterns and scores them.
    """

    def __init__(self, config: Optional[VCPConfig] = None):
        """
        Initialize VCP scanner.

        Args:
            config: VCP detection configuration
        """
        self.config = config or VCPConfig()
        self.vcp_indicator = VCP(config=self.config)

    def analyze(self, df: pd.DataFrame) -> VCPAnalysisResult:
        """
        Analyze data for VCP pattern.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            VCPAnalysisResult with analysis
        """
        signals = []

        if len(df) < 50:
            return VCPAnalysisResult(
                detected=False,
                stage=VCPStage.NO_PATTERN,
                contraction_count=0,
                depth_sequence=[],
                volume_dryup=False,
                range_tightening=False,
                pivot_price=None,
                current_price=0,
                distance_to_pivot_pct=0,
                pattern_score=0,
                volume_score=0,
                timing_score=0,
                overall_score=0,
                signals=["Insufficient data for VCP analysis"],
            )

        # Run VCP detection
        result = self.vcp_indicator.calculate(df)
        vcp_result: VCPResult = result.values

        # Get current price
        close_col = "Close" if "Close" in df.columns else "close"
        current_price = df[close_col].iloc[-1]

        # Determine stage
        stage = self._determine_stage(vcp_result, current_price)

        # Analyze volume
        volume_dryup = vcp_result.volume_trend < self.config.volume_dry_up_threshold
        volume_score = self._calculate_volume_score(vcp_result.volume_trend)

        # Analyze range
        range_tightening = (
            vcp_result.range_contraction < self.config.range_contraction_threshold
        )

        # Calculate timing score (how close to breakout)
        timing_score = self._calculate_timing_score(
            vcp_result.pivot_distance_pct, current_price, vcp_result.pivot_price
        )

        # Pattern score from VCP detector
        pattern_score = vcp_result.score

        # Calculate overall score
        overall_score = self._calculate_overall_score(
            pattern_score, volume_score, timing_score, vcp_result.is_vcp
        )

        # Generate signals
        if vcp_result.is_vcp:
            if stage == VCPStage.MATURE:
                signals.append(
                    f"VCP pattern detected - {vcp_result.contraction_count} contractions"
                )
            elif stage == VCPStage.BREAKOUT:
                signals.append("VCP breakout in progress!")

            if volume_dryup:
                signals.append("Volume drying up - positive sign")

            if vcp_result.pivot_price:
                distance = abs(vcp_result.pivot_distance_pct)
                if distance < 3:
                    signals.append(
                        f"Near pivot point ({vcp_result.pivot_price:.2f}) - watch for breakout"
                    )
                elif distance < 5:
                    signals.append(
                        f"Approaching pivot ({vcp_result.pivot_price:.2f})"
                    )

            # Add depth sequence info
            if vcp_result.depth_sequence:
                depths_str = " -> ".join(
                    [f"{d:.1f}%" for d in vcp_result.depth_sequence]
                )
                signals.append(f"Contraction depths: {depths_str}")
        else:
            if vcp_result.contraction_count == 1:
                signals.append("Early consolidation - watching for VCP formation")
            else:
                signals.append("No VCP pattern detected")

        # Include signals from VCP detector
        signals.extend(vcp_result.signals)

        return VCPAnalysisResult(
            detected=vcp_result.is_vcp,
            stage=stage,
            contraction_count=vcp_result.contraction_count,
            depth_sequence=vcp_result.depth_sequence,
            volume_dryup=volume_dryup,
            range_tightening=range_tightening,
            pivot_price=vcp_result.pivot_price,
            current_price=current_price,
            distance_to_pivot_pct=vcp_result.pivot_distance_pct,
            pattern_score=pattern_score,
            volume_score=volume_score,
            timing_score=timing_score,
            overall_score=overall_score,
            signals=signals,
        )

    def _determine_stage(self, vcp_result: VCPResult, current_price: float) -> VCPStage:
        """Determine VCP pattern stage."""
        if not vcp_result.contraction_count:
            return VCPStage.NO_PATTERN

        if vcp_result.contraction_count < 2:
            return VCPStage.FORMING

        if vcp_result.pivot_price:
            # Check if at or above pivot
            if current_price >= vcp_result.pivot_price:
                return VCPStage.BREAKOUT

        if vcp_result.is_vcp:
            return VCPStage.MATURE

        return VCPStage.FORMING

    def _calculate_volume_score(self, volume_trend: float) -> float:
        """
        Calculate volume score.

        Lower (more negative) volume trend is better for VCP.
        """
        if volume_trend < -0.4:
            return 100  # Excellent volume dryup
        elif volume_trend < -0.2:
            return 80
        elif volume_trend < 0:
            return 60
        elif volume_trend < 0.2:
            return 40
        else:
            return 20  # Volume increasing - not ideal

    def _calculate_timing_score(
        self,
        distance_pct: float,
        current_price: float,
        pivot_price: Optional[float],
    ) -> float:
        """
        Calculate timing score based on distance to pivot.

        Closer to pivot = higher score.
        """
        if pivot_price is None:
            return 30  # No pivot identified

        abs_distance = abs(distance_pct)

        if abs_distance < 2:
            return 100  # Very close to pivot
        elif abs_distance < 5:
            return 80
        elif abs_distance < 8:
            return 60
        elif abs_distance < 12:
            return 40
        else:
            return 20

    def _calculate_overall_score(
        self,
        pattern_score: float,
        volume_score: float,
        timing_score: float,
        is_vcp: bool,
    ) -> float:
        """
        Calculate overall VCP score.

        Weights:
        - Pattern quality: 50%
        - Volume: 25%
        - Timing: 25%
        """
        if not is_vcp:
            # If not a valid VCP, cap the score
            return min(30, pattern_score * 0.3)

        score = pattern_score * 0.50 + volume_score * 0.25 + timing_score * 0.25

        return max(0, min(100, score))


def scan_stocks_for_vcp(
    stock_data: dict[str, pd.DataFrame],
    min_score: float = 50,
) -> list[tuple[str, VCPAnalysisResult]]:
    """
    Scan multiple stocks for VCP patterns.

    Args:
        stock_data: Dict of code -> DataFrame
        min_score: Minimum score to include

    Returns:
        List of (code, result) tuples sorted by score descending
    """
    scanner = VCPScanner()
    results = []

    for code, df in stock_data.items():
        try:
            result = scanner.analyze(df)
            if result.overall_score >= min_score:
                results.append((code, result))
        except Exception:
            continue

    # Sort by score descending
    results.sort(key=lambda x: x[1].overall_score, reverse=True)

    return results
