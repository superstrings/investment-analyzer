"""
Batch Analyzer for Analyst Skill.

Analyzes multiple stocks and ranks them by technical score.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import pandas as pd

from skills.shared import DataProvider, ReportBuilder, ReportFormat

from .stock_analyzer import StockAnalysis, StockAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class BatchAnalysisResult:
    """Result of batch stock analysis."""

    # Analysis metadata
    analysis_date: date
    total_analyzed: int
    successful: int
    failed: int

    # Results sorted by score
    results: list[StockAnalysis] = field(default_factory=list)

    # Top performers
    top_vcp: list[StockAnalysis] = field(default_factory=list)  # Best VCP setups
    top_obv: list[StockAnalysis] = field(default_factory=list)  # Best OBV trends
    top_overall: list[StockAnalysis] = field(default_factory=list)  # Highest combined

    # Categories
    strong_buy: list[StockAnalysis] = field(default_factory=list)
    buy: list[StockAnalysis] = field(default_factory=list)
    hold: list[StockAnalysis] = field(default_factory=list)
    sell: list[StockAnalysis] = field(default_factory=list)

    # Failed codes
    failed_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "total_analyzed": self.total_analyzed,
            "successful": self.successful,
            "failed": self.failed,
            "results": [r.to_dict() for r in self.results],
            "top_vcp": [r.to_dict() for r in self.top_vcp],
            "top_obv": [r.to_dict() for r in self.top_obv],
            "top_overall": [r.to_dict() for r in self.top_overall],
            "strong_buy": [r.to_dict() for r in self.strong_buy],
            "buy": [r.to_dict() for r in self.buy],
            "hold": [r.to_dict() for r in self.hold],
            "sell": [r.to_dict() for r in self.sell],
            "failed_codes": self.failed_codes,
        }


class BatchAnalyzer:
    """
    Batch analyzer for scanning multiple stocks.

    Analyzes a list of stocks and ranks them by various criteria.
    """

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        days: int = 120,
    ):
        """
        Initialize batch analyzer.

        Args:
            data_provider: Data provider for K-line data
            days: Number of days for analysis
        """
        self.data_provider = data_provider or DataProvider()
        self.days = days
        self.stock_analyzer = StockAnalyzer(data_provider=self.data_provider)

    def analyze_codes(
        self,
        codes: list[str],
        stock_names: Optional[dict[str, str]] = None,
    ) -> BatchAnalysisResult:
        """
        Analyze a list of stock codes.

        Args:
            codes: List of full codes (e.g., ["HK.00700", "US.NVDA"])
            stock_names: Optional dict of code -> name

        Returns:
            BatchAnalysisResult with all analyses
        """
        stock_names = stock_names or {}
        results = []
        failed_codes = []

        for full_code in codes:
            try:
                # Parse code
                if "." in full_code:
                    market, code = full_code.split(".", 1)
                else:
                    market = "HK" if full_code.isdigit() else "US"
                    code = full_code

                # Fetch data
                df = self.data_provider.get_klines_df(market, code, days=self.days)

                if df.empty:
                    logger.warning(f"No data for {full_code}")
                    failed_codes.append(full_code)
                    continue

                # Analyze
                name = stock_names.get(full_code, "")
                analysis = self.stock_analyzer.analyze(df, market, code, name)
                results.append(analysis)

            except Exception as e:
                logger.error(f"Error analyzing {full_code}: {e}")
                failed_codes.append(full_code)

        # Sort by overall score
        results.sort(key=lambda x: x.technical_score.final_score, reverse=True)

        # Categorize results
        return self._categorize_results(results, failed_codes)

    def analyze_user_stocks(
        self,
        user_id: int,
        include_positions: bool = True,
        include_watchlist: bool = True,
        markets: Optional[list[str]] = None,
    ) -> BatchAnalysisResult:
        """
        Analyze all stocks for a user (positions + watchlist).

        Args:
            user_id: User ID
            include_positions: Include position stocks
            include_watchlist: Include watchlist stocks
            markets: Filter by markets

        Returns:
            BatchAnalysisResult
        """
        codes = []
        names = {}

        if include_positions:
            positions = self.data_provider.get_positions(user_id, markets)
            for pos in positions:
                full_code = pos.full_code
                codes.append(full_code)
                names[full_code] = pos.stock_name

        if include_watchlist:
            watchlist = self.data_provider.get_watchlist(user_id, markets)
            for item in watchlist:
                full_code = item.full_code
                if full_code not in codes:
                    codes.append(full_code)
                    names[full_code] = item.stock_name

        return self.analyze_codes(codes, names)

    def _categorize_results(
        self,
        results: list[StockAnalysis],
        failed_codes: list[str],
    ) -> BatchAnalysisResult:
        """Categorize analysis results."""
        # Top performers
        top_vcp = sorted(
            [r for r in results if r.vcp_analysis.detected],
            key=lambda x: x.vcp_analysis.overall_score,
            reverse=True,
        )[:5]

        top_obv = sorted(
            results,
            key=lambda x: x.obv_analysis.score,
            reverse=True,
        )[:5]

        top_overall = results[:5]

        # By rating
        strong_buy = [r for r in results if r.technical_score.rating.value == "strong_buy"]
        buy = [r for r in results if r.technical_score.rating.value == "buy"]
        hold = [r for r in results if r.technical_score.rating.value == "hold"]
        sell = [
            r
            for r in results
            if r.technical_score.rating.value in ("sell", "strong_sell")
        ]

        return BatchAnalysisResult(
            analysis_date=date.today(),
            total_analyzed=len(results) + len(failed_codes),
            successful=len(results),
            failed=len(failed_codes),
            results=results,
            top_vcp=top_vcp,
            top_obv=top_obv,
            top_overall=top_overall,
            strong_buy=strong_buy,
            buy=buy,
            hold=hold,
            sell=sell,
            failed_codes=failed_codes,
        )


def generate_batch_report(
    batch_result: BatchAnalysisResult,
    report_format: ReportFormat = ReportFormat.MARKDOWN,
    include_all: bool = False,
) -> str:
    """
    Generate a formatted batch analysis report.

    Args:
        batch_result: Batch analysis result
        report_format: Output format
        include_all: Include all stocks or just highlights

    Returns:
        Formatted report string
    """
    builder = ReportBuilder("Batch Technical Analysis", report_format)

    # Summary section
    builder.add_section("Analysis Summary", level=2)
    builder.add_key_value("Date", batch_result.analysis_date.isoformat())
    builder.add_key_value("Total Stocks", str(batch_result.total_analyzed))
    builder.add_key_value("Successful", str(batch_result.successful))
    builder.add_key_value("Failed", str(batch_result.failed))
    builder.add_blank_line()

    # Distribution
    builder.add_key_value("Strong Buy", str(len(batch_result.strong_buy)))
    builder.add_key_value("Buy", str(len(batch_result.buy)))
    builder.add_key_value("Hold", str(len(batch_result.hold)))
    builder.add_key_value("Sell/Strong Sell", str(len(batch_result.sell)))

    # Top Overall
    if batch_result.top_overall:
        builder.add_section("Top 5 Overall", level=2)
        top_data = [
            {
                "Code": f"{r.market}.{r.code}",
                "Name": r.name[:10] if r.name else "-",
                "Score": f"{r.technical_score.final_score:.0f}",
                "Rating": r.technical_score.rating.value,
                "VCP": "Yes" if r.vcp_analysis.detected else "-",
                "OBV": r.obv_analysis.trend.value[:4],
            }
            for r in batch_result.top_overall
        ]
        builder.add_table(top_data)

    # Top VCP Setups
    if batch_result.top_vcp:
        builder.add_section("Top VCP Setups", level=2)
        vcp_data = [
            {
                "Code": f"{r.market}.{r.code}",
                "Name": r.name[:10] if r.name else "-",
                "VCP Score": f"{r.vcp_analysis.overall_score:.0f}",
                "Stage": r.vcp_analysis.stage.value,
                "Contractions": str(r.vcp_analysis.contraction_count),
                "Pivot": f"{r.vcp_analysis.pivot_price:.2f}" if r.vcp_analysis.pivot_price else "-",
            }
            for r in batch_result.top_vcp
        ]
        builder.add_table(vcp_data)

    # Top OBV Trends
    if batch_result.top_obv:
        builder.add_section("Top OBV Trends", level=2)
        obv_data = [
            {
                "Code": f"{r.market}.{r.code}",
                "Name": r.name[:10] if r.name else "-",
                "OBV Score": f"{r.obv_analysis.score:.0f}",
                "Trend": r.obv_analysis.trend.value,
                "Divergence": r.obv_analysis.divergence.value,
                "Confirms": "Yes" if r.obv_analysis.volume_confirms_price else "No",
            }
            for r in batch_result.top_obv
        ]
        builder.add_table(obv_data)

    # Strong Buy Recommendations
    if batch_result.strong_buy:
        builder.add_section("Strong Buy Signals", level=2)
        for r in batch_result.strong_buy[:10]:
            builder.add_line(f"**{r.market}.{r.code}** ({r.name})")
            builder.add_line(f"  Score: {r.technical_score.final_score:.0f} | {r.recommendation}")
            builder.add_blank_line()

    # All Results (if requested)
    if include_all and batch_result.results:
        builder.add_section("All Results", level=2)
        all_data = [
            {
                "Code": f"{r.market}.{r.code}",
                "Score": f"{r.technical_score.final_score:.0f}",
                "Rating": r.technical_score.rating.value,
                "OBV": f"{r.obv_analysis.score:.0f}",
                "VCP": f"{r.vcp_analysis.overall_score:.0f}",
            }
            for r in batch_result.results
        ]
        builder.add_table(all_data)

    # Failed codes
    if batch_result.failed_codes:
        builder.add_section("Failed Analysis", level=2)
        builder.add_line("No data available for:")
        builder.add_list(batch_result.failed_codes)

    return builder.build()
