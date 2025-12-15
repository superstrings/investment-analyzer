"""
Stock Analyzer - Main analysis orchestrator for Analyst Skill.

Combines OBV and VCP analysis into a comprehensive stock analysis.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import pandas as pd

from skills.shared import DataProvider, ReportBuilder, ReportFormat

from .obv_analyzer import OBVAnalysisResult, OBVAnalyzer
from .scoring import ScoringSystem, TechnicalScore, calculate_technical_score
from .vcp_scanner import VCPAnalysisResult, VCPScanner


@dataclass
class StockAnalysis:
    """Complete stock analysis result."""

    # Stock info
    market: str
    code: str
    name: str
    analysis_date: date

    # Price info
    current_price: float
    price_change_pct: float  # Recent change

    # Component analysis
    obv_analysis: OBVAnalysisResult
    vcp_analysis: VCPAnalysisResult

    # Combined score
    technical_score: TechnicalScore

    # Summary
    summary: str
    recommendation: str
    confidence: float  # 0-100

    # All signals combined
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "market": self.market,
            "code": self.code,
            "name": self.name,
            "analysis_date": self.analysis_date.isoformat(),
            "current_price": self.current_price,
            "price_change_pct": self.price_change_pct,
            "obv_analysis": self.obv_analysis.to_dict(),
            "vcp_analysis": self.vcp_analysis.to_dict(),
            "technical_score": self.technical_score.to_dict(),
            "summary": self.summary,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "signals": self.signals,
        }


class StockAnalyzer:
    """
    Main stock analyzer combining OBV + VCP analysis.

    Provides comprehensive technical analysis for individual stocks.
    """

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        obv_signal_period: int = 20,
        vcp_config: Optional[dict] = None,
    ):
        """
        Initialize stock analyzer.

        Args:
            data_provider: Data provider for fetching K-line data
            obv_signal_period: Signal period for OBV analysis
            vcp_config: Optional VCP configuration dict
        """
        self.data_provider = data_provider or DataProvider()
        self.obv_analyzer = OBVAnalyzer(signal_period=obv_signal_period)
        self.vcp_scanner = VCPScanner()
        self.scoring_system = ScoringSystem()

    def analyze(
        self,
        df: pd.DataFrame,
        market: str = "",
        code: str = "",
        name: str = "",
    ) -> StockAnalysis:
        """
        Analyze a stock using its K-line data.

        Args:
            df: DataFrame with OHLCV data
            market: Market code (HK, US, A)
            code: Stock code
            name: Stock name

        Returns:
            StockAnalysis with complete analysis
        """
        # Get current price and recent change
        close_col = "Close" if "Close" in df.columns else "close"
        current_price = float(df[close_col].iloc[-1])

        # Calculate recent price change (20 days)
        lookback = min(20, len(df) - 1)
        price_start = float(df[close_col].iloc[-lookback - 1])
        price_change_pct = ((current_price - price_start) / price_start) * 100

        # Run OBV analysis
        obv_result = self.obv_analyzer.analyze(df)

        # Run VCP analysis
        vcp_result = self.vcp_scanner.analyze(df)

        # Calculate combined score
        technical_score = self.scoring_system.calculate_score(
            obv_result, vcp_result, current_price
        )

        # Generate summary
        summary = self._generate_summary(obv_result, vcp_result, technical_score)

        # Combine all signals
        signals = []
        signals.extend(obv_result.signals)
        signals.extend(vcp_result.signals)

        # Calculate confidence
        confidence = self._calculate_confidence(obv_result, vcp_result, technical_score)

        return StockAnalysis(
            market=market,
            code=code,
            name=name,
            analysis_date=date.today(),
            current_price=current_price,
            price_change_pct=price_change_pct,
            obv_analysis=obv_result,
            vcp_analysis=vcp_result,
            technical_score=technical_score,
            summary=summary,
            recommendation=technical_score.action,
            confidence=confidence,
            signals=signals,
        )

    def analyze_from_db(
        self,
        market: str,
        code: str,
        days: int = 120,
        stock_name: str = "",
    ) -> Optional[StockAnalysis]:
        """
        Analyze a stock by fetching data from database.

        Args:
            market: Market code
            code: Stock code
            days: Number of days of data
            stock_name: Optional stock name

        Returns:
            StockAnalysis or None if no data
        """
        df = self.data_provider.get_klines_df(market, code, days=days)

        if df.empty:
            return None

        return self.analyze(df, market=market, code=code, name=stock_name)

    def _generate_summary(
        self,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
        score: TechnicalScore,
    ) -> str:
        """Generate analysis summary."""
        parts = []

        # Overall rating
        rating_desc = {
            "strong_buy": "Strong bullish setup",
            "buy": "Bullish bias",
            "hold": "Neutral",
            "sell": "Bearish bias",
            "strong_sell": "Weak technicals",
        }
        parts.append(rating_desc.get(score.rating.value, "Unknown"))

        # VCP status
        if vcp_result.detected:
            if vcp_result.stage.value == "mature":
                parts.append(f"VCP mature ({vcp_result.contraction_count} contractions)")
            elif vcp_result.stage.value == "breakout":
                parts.append("VCP breaking out")
            else:
                parts.append("VCP forming")

        # OBV status
        obv_desc = {
            "strong_up": "Strong accumulation",
            "up": "Accumulation",
            "sideways": "Neutral volume",
            "down": "Distribution",
            "strong_down": "Heavy distribution",
        }
        parts.append(obv_desc.get(obv_result.trend.value, ""))

        # Divergence
        if obv_result.divergence.value == "bullish":
            parts.append("Bullish divergence")
        elif obv_result.divergence.value == "bearish":
            parts.append("Bearish divergence warning")

        return ". ".join(filter(None, parts)) + "."

    def _calculate_confidence(
        self,
        obv_result: OBVAnalysisResult,
        vcp_result: VCPAnalysisResult,
        score: TechnicalScore,
    ) -> float:
        """Calculate confidence level for the analysis."""
        confidence = 50.0  # Base confidence

        # Higher score = higher confidence
        if score.final_score >= 70:
            confidence += 20
        elif score.final_score >= 50:
            confidence += 10

        # VCP detection adds confidence
        if vcp_result.detected:
            confidence += 15
            if vcp_result.contraction_count >= 3:
                confidence += 5

        # OBV confirmation adds confidence
        if obv_result.volume_confirms_price:
            confidence += 10

        # Strong OBV trend adds confidence
        if obv_result.trend.value in ("strong_up", "strong_down"):
            confidence += 5

        return min(100, confidence)


def generate_analysis_report(
    analysis: StockAnalysis,
    report_format: ReportFormat = ReportFormat.MARKDOWN,
) -> str:
    """
    Generate a formatted report for stock analysis.

    Args:
        analysis: Stock analysis result
        report_format: Output format

    Returns:
        Formatted report string
    """
    title = f"Technical Analysis: {analysis.market}.{analysis.code}"
    if analysis.name:
        title += f" ({analysis.name})"

    builder = ReportBuilder(title, report_format)

    # Summary section
    builder.add_section("Summary", level=2)
    builder.add_key_value("Rating", analysis.technical_score.rating.value.upper())
    builder.add_key_value("Score", f"{analysis.technical_score.final_score:.1f}/100")
    builder.add_key_value("Confidence", f"{analysis.confidence:.0f}%")
    builder.add_key_value("Current Price", f"{analysis.current_price:.2f}")
    builder.add_key_value("Price Change (20d)", f"{analysis.price_change_pct:+.2f}%")
    builder.add_blank_line()
    builder.add_line(f"**Summary**: {analysis.summary}")
    builder.add_line(f"**Action**: {analysis.recommendation}")

    # Technical Scores
    builder.add_section("Technical Scores", level=2)
    scores_data = [
        {
            "Component": "OBV (40%)",
            "Score": f"{analysis.obv_analysis.score:.1f}",
            "Status": analysis.obv_analysis.trend.value,
        },
        {
            "Component": "VCP (60%)",
            "Score": f"{analysis.vcp_analysis.overall_score:.1f}",
            "Status": analysis.vcp_analysis.stage.value,
        },
        {
            "Component": "Combined",
            "Score": f"{analysis.technical_score.final_score:.1f}",
            "Status": analysis.technical_score.rating.value,
        },
    ]
    builder.add_table(scores_data)

    # OBV Analysis
    builder.add_section("OBV Analysis", level=2)
    builder.add_key_value("Trend", analysis.obv_analysis.trend.value)
    builder.add_key_value("Trend Strength", f"{analysis.obv_analysis.trend_strength:.0f}%")
    builder.add_key_value("Divergence", analysis.obv_analysis.divergence.value)
    builder.add_key_value(
        "Volume Confirms Price",
        "Yes" if analysis.obv_analysis.volume_confirms_price else "No",
    )

    # VCP Analysis
    builder.add_section("VCP Analysis", level=2)
    builder.add_key_value("Pattern Detected", "Yes" if analysis.vcp_analysis.detected else "No")
    if analysis.vcp_analysis.detected:
        builder.add_key_value("Stage", analysis.vcp_analysis.stage.value)
        builder.add_key_value("Contractions", str(analysis.vcp_analysis.contraction_count))
        if analysis.vcp_analysis.depth_sequence:
            depths = " -> ".join([f"{d:.1f}%" for d in analysis.vcp_analysis.depth_sequence])
            builder.add_key_value("Depth Sequence", depths)
        builder.add_key_value("Volume Dryup", "Yes" if analysis.vcp_analysis.volume_dryup else "No")
        if analysis.vcp_analysis.pivot_price:
            builder.add_key_value("Pivot Price", f"{analysis.vcp_analysis.pivot_price:.2f}")
            builder.add_key_value(
                "Distance to Pivot",
                f"{analysis.vcp_analysis.distance_to_pivot_pct:.1f}%",
            )

    # Key Levels
    if analysis.technical_score.key_levels:
        builder.add_section("Key Levels", level=2)
        builder.add_list(analysis.technical_score.key_levels)

    # Watch Points
    if analysis.technical_score.watch_points:
        builder.add_section("Watch Points", level=2)
        builder.add_list(analysis.technical_score.watch_points)

    # Signals
    if analysis.signals:
        builder.add_section("All Signals", level=2)
        builder.add_list(analysis.signals)

    return builder.build()
