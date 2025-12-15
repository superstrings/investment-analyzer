"""
Deep Analyzer - Comprehensive Stock Analysis.

Combines technical analysis, fundamental data, news, and industry analysis
to provide comprehensive investment recommendations.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from skills.shared import DataProvider

from .technical_analyzer import EnhancedTechnicalAnalyzer, EnhancedTechnicalResult
from .web_data_fetcher import (
    FundamentalData,
    IndustryData,
    NewsItem,
    WebDataFetcher,
    WebDataResult,
)

logger = logging.getLogger(__name__)


@dataclass
class InvestmentRecommendation:
    """Investment recommendation with time horizons."""

    # Short-term (1-2 weeks)
    short_term_action: str  # buy, sell, hold
    short_term_reason: str
    short_term_confidence: int  # 0-100

    # Medium-term (1-3 months)
    medium_term_action: str
    medium_term_reason: str
    medium_term_confidence: int

    # Long-term (6-12 months)
    long_term_action: str
    long_term_reason: str
    long_term_confidence: int

    # Risk assessment
    risk_level: str  # low, medium, high
    risk_factors: list[str] = field(default_factory=list)

    # Entry/Exit points
    suggested_entry: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price_1: Optional[float] = None
    target_price_2: Optional[float] = None


@dataclass
class DeepAnalysisResult:
    """Complete deep analysis result."""

    # Basic info
    market: str
    code: str
    stock_name: str
    analysis_date: date
    analysis_time: datetime

    # Current state
    current_price: float
    position_held: bool = False
    position_pl_ratio: Optional[Decimal] = None

    # Analysis components
    technical: Optional[EnhancedTechnicalResult] = None
    fundamental: Optional[FundamentalData] = None
    news_items: list[NewsItem] = field(default_factory=list)
    industry: Optional[IndustryData] = None

    # Recommendation
    recommendation: Optional[InvestmentRecommendation] = None

    # Overall assessment
    overall_score: int = 50  # 0-100
    overall_rating: str = "hold"  # strong_buy, buy, hold, sell, strong_sell
    summary: str = ""

    # Processing info
    success: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DeepAnalyzer:
    """
    Deep analyzer combining multiple analysis methods.

    Designed for trend traders seeking compound growth opportunities
    in major industry cycles.
    """

    def __init__(
        self,
        data_provider: DataProvider = None,
        web_search_func=None,
        web_fetch_func=None,
    ):
        """
        Initialize deep analyzer.

        Args:
            data_provider: Data provider for market data
            web_search_func: Optional web search function for testing
            web_fetch_func: Optional web fetch function for testing
        """
        self.data_provider = data_provider or DataProvider()
        self.technical_analyzer = EnhancedTechnicalAnalyzer(self.data_provider)
        self.web_fetcher = WebDataFetcher(web_search_func, web_fetch_func)

    def analyze(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        user_id: int = None,
        include_web_data: bool = True,
    ) -> DeepAnalysisResult:
        """
        Perform comprehensive deep analysis on a stock.

        Args:
            market: Market code (HK, US, A)
            code: Stock code
            stock_name: Stock name
            user_id: User ID to check for existing position
            include_web_data: Whether to fetch web data

        Returns:
            DeepAnalysisResult with complete analysis
        """
        full_code = f"{market}.{code}"
        now = datetime.now()

        result = DeepAnalysisResult(
            market=market,
            code=code,
            stock_name=stock_name,
            analysis_date=date.today(),
            analysis_time=now,
            current_price=0.0,
        )

        try:
            # Step 1: Technical Analysis
            logger.info(f"Starting technical analysis for {full_code}")
            technical = self.technical_analyzer.analyze(market, code, stock_name)

            if technical:
                result.technical = technical
                result.current_price = technical.current_price
            else:
                result.errors.append("技术分析失败: 数据不足")
                result.success = False
                return result

            # Step 2: Check if user holds position
            if user_id:
                positions = self.data_provider.get_positions(user_id, markets=[market])
                for pos in positions:
                    if pos.code == code:
                        result.position_held = True
                        result.position_pl_ratio = pos.pl_ratio
                        if not stock_name:
                            result.stock_name = pos.stock_name
                            stock_name = pos.stock_name
                        break

            # Step 3: Web data (fundamental, news, industry)
            if include_web_data:
                logger.info(f"Fetching web data for {full_code}")
                try:
                    web_result = self.web_fetcher.fetch_sync(
                        market, code, stock_name,
                        include_news=True,
                        include_industry=True,
                    )
                    if web_result:
                        result.fundamental = web_result.fundamental
                        result.news_items = web_result.news_items
                        result.industry = web_result.industry
                except Exception as e:
                    result.warnings.append(f"网络数据获取失败: {e}")

            # Step 4: Generate recommendation
            logger.info(f"Generating recommendation for {full_code}")
            result.recommendation = self._generate_recommendation(result)

            # Step 5: Calculate overall assessment
            result.overall_score, result.overall_rating = self._calculate_overall(result)
            result.summary = self._generate_summary(result)

        except Exception as e:
            logger.exception(f"Deep analysis failed for {full_code}: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def _generate_recommendation(
        self, result: DeepAnalysisResult
    ) -> InvestmentRecommendation:
        """Generate investment recommendation based on analysis."""
        tech = result.technical

        # Initialize with defaults
        short_action = "hold"
        short_reason = ""
        short_conf = 50

        medium_action = "hold"
        medium_reason = ""
        medium_conf = 50

        long_action = "hold"
        long_reason = ""
        long_conf = 50

        risk_level = "medium"
        risk_factors = []

        # Short-term recommendation (based on technical)
        if tech:
            if tech.technical_score >= 70:
                short_action = "buy"
                short_reason = "技术面强势，短期看涨"
                short_conf = min(90, tech.technical_score)
            elif tech.technical_score >= 55:
                short_action = "buy"
                short_reason = "技术面偏强"
                short_conf = tech.technical_score
            elif tech.technical_score <= 30:
                short_action = "sell"
                short_reason = "技术面疲弱，建议规避"
                short_conf = 100 - tech.technical_score
            elif tech.technical_score <= 45:
                short_action = "hold"
                short_reason = "技术面偏弱，观望为主"
                short_conf = 60

            # Add signals to reasons
            if tech.signals:
                short_reason += f"。信号: {', '.join(tech.signals[:2])}"
            if tech.warnings:
                risk_factors.extend(tech.warnings)

        # Medium-term recommendation (technical + trend)
        if tech:
            trend = tech.trend
            if trend.medium_term == "up" and tech.ma_alignment == "bullish":
                medium_action = "buy"
                medium_reason = f"中期趋势向上，{trend.description}"
                medium_conf = trend.strength
            elif trend.medium_term == "down" and tech.ma_alignment == "bearish":
                medium_action = "sell"
                medium_reason = f"中期趋势向下，{trend.description}"
                medium_conf = 100 - trend.strength
            else:
                medium_action = "hold"
                medium_reason = "中期趋势不明朗，观望"
                medium_conf = 50

            # VCP pattern is strong medium-term signal
            if tech.vcp_detected:
                medium_action = "buy"
                medium_reason = f"VCP形态确认，蓄势待发"
                medium_conf = max(medium_conf, 70)

        # Long-term recommendation (fundamentals + industry)
        if result.fundamental:
            fund = result.fundamental
            if fund.pe_ratio and fund.pe_ratio < 20 and fund.roe and fund.roe > 15:
                long_action = "buy"
                long_reason = f"估值合理(PE:{fund.pe_ratio:.1f})，盈利能力强(ROE:{fund.roe:.1f}%)"
                long_conf = 70
            elif fund.pe_ratio and fund.pe_ratio > 50:
                long_action = "hold"
                long_reason = f"估值偏高(PE:{fund.pe_ratio:.1f})，需谨慎"
                long_conf = 60
                risk_factors.append(f"估值偏高 PE={fund.pe_ratio:.1f}")

        if result.industry:
            ind = result.industry
            if "增长" in str(ind.key_trends) or "growth" in str(ind.key_trends).lower():
                if long_action == "buy":
                    long_conf = min(90, long_conf + 10)
                    long_reason += f"。行业({ind.industry})处于增长周期"
                elif long_action == "hold":
                    long_action = "buy"
                    long_reason = f"行业({ind.industry})处于增长周期"
                    long_conf = 65

        # Adjust for news sentiment
        positive_news = len([n for n in result.news_items if n.sentiment == "positive"])
        negative_news = len([n for n in result.news_items if n.sentiment == "negative"])

        if negative_news > positive_news + 2:
            risk_factors.append("近期负面消息较多")
            risk_level = "high"
        elif positive_news > negative_news + 2:
            if short_action == "hold":
                short_action = "buy"
                short_conf = min(short_conf + 10, 70)

        # Calculate risk level
        if len(risk_factors) >= 3:
            risk_level = "high"
        elif len(risk_factors) >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Calculate entry/exit points
        entry, stop, target1, target2 = self._calculate_price_targets(result)

        return InvestmentRecommendation(
            short_term_action=short_action,
            short_term_reason=short_reason,
            short_term_confidence=short_conf,
            medium_term_action=medium_action,
            medium_term_reason=medium_reason,
            medium_term_confidence=medium_conf,
            long_term_action=long_action,
            long_term_reason=long_reason,
            long_term_confidence=long_conf,
            risk_level=risk_level,
            risk_factors=risk_factors,
            suggested_entry=entry,
            stop_loss=stop,
            target_price_1=target1,
            target_price_2=target2,
        )

    def _calculate_price_targets(
        self, result: DeepAnalysisResult
    ) -> tuple[float, float, float, float]:
        """Calculate entry, stop-loss, and target prices."""
        if not result.technical:
            return None, None, None, None

        tech = result.technical
        current = tech.current_price
        levels = tech.levels

        # Entry point: near support or current if strong
        if tech.technical_score >= 60:
            entry = current  # Enter now
        else:
            entry = levels.support_1  # Wait for pullback

        # Stop-loss: below support
        stop = levels.support_2 * 0.98  # 2% below second support

        # Target 1: first resistance
        target1 = levels.resistance_1

        # Target 2: second resistance or 20% gain
        target2 = max(levels.resistance_2, current * 1.20)

        return (
            round(entry, 2),
            round(stop, 2),
            round(target1, 2),
            round(target2, 2),
        )

    def _calculate_overall(
        self, result: DeepAnalysisResult
    ) -> tuple[int, str]:
        """Calculate overall score and rating."""
        score = 50  # Base score

        # Technical contribution (50%)
        if result.technical:
            score += (result.technical.technical_score - 50) * 0.5

        # Fundamental contribution (25%)
        if result.fundamental:
            fund = result.fundamental
            fund_score = 50

            # PE evaluation
            if fund.pe_ratio:
                if fund.pe_ratio < 15:
                    fund_score += 15
                elif fund.pe_ratio < 25:
                    fund_score += 5
                elif fund.pe_ratio > 50:
                    fund_score -= 15

            # ROE evaluation
            if fund.roe:
                if fund.roe > 20:
                    fund_score += 15
                elif fund.roe > 10:
                    fund_score += 5
                elif fund.roe < 5:
                    fund_score -= 10

            score += (fund_score - 50) * 0.25

        # News contribution (15%)
        positive = len([n for n in result.news_items if n.sentiment == "positive"])
        negative = len([n for n in result.news_items if n.sentiment == "negative"])
        news_score = 50 + (positive - negative) * 5
        news_score = max(30, min(70, news_score))
        score += (news_score - 50) * 0.15

        # Industry contribution (10%)
        if result.industry and result.industry.key_trends:
            ind_score = 55  # Slight boost for having industry data
            score += (ind_score - 50) * 0.1

        # Normalize score
        score = max(0, min(100, int(score)))

        # Determine rating
        if score >= 75:
            rating = "strong_buy"
        elif score >= 60:
            rating = "buy"
        elif score >= 40:
            rating = "hold"
        elif score >= 25:
            rating = "sell"
        else:
            rating = "strong_sell"

        return score, rating

    def _generate_summary(self, result: DeepAnalysisResult) -> str:
        """Generate a text summary of the analysis."""
        lines = []

        # Stock info
        name = result.stock_name or f"{result.market}.{result.code}"
        lines.append(f"{name} 深度分析摘要")
        lines.append(f"分析日期: {result.analysis_date}")
        lines.append(f"当前价格: {result.current_price:.2f}")
        lines.append("")

        # Position status
        if result.position_held:
            pl = result.position_pl_ratio or Decimal("0")
            status = "盈利" if pl >= 0 else "亏损"
            lines.append(f"持仓状态: 持有中 ({status} {abs(float(pl)):.1f}%)")
            lines.append("")

        # Overall rating
        rating_text = {
            "strong_buy": "强烈推荐买入",
            "buy": "建议买入",
            "hold": "持有观望",
            "sell": "建议卖出",
            "strong_sell": "强烈建议卖出",
        }
        lines.append(f"综合评分: {result.overall_score}/100")
        lines.append(f"投资建议: {rating_text.get(result.overall_rating, result.overall_rating)}")
        lines.append("")

        # Recommendation summary
        if result.recommendation:
            rec = result.recommendation
            lines.append("操作建议:")
            lines.append(f"- 短期: {rec.short_term_action.upper()} - {rec.short_term_reason}")
            lines.append(f"- 中期: {rec.medium_term_action.upper()} - {rec.medium_term_reason}")
            lines.append(f"- 长期: {rec.long_term_action.upper()} - {rec.long_term_reason}")
            lines.append(f"- 风险等级: {rec.risk_level.upper()}")

            if rec.suggested_entry:
                lines.append("")
                lines.append("价格参考:")
                lines.append(f"- 建议入场: {rec.suggested_entry:.2f}")
                lines.append(f"- 止损位: {rec.stop_loss:.2f}")
                lines.append(f"- 目标价1: {rec.target_price_1:.2f}")
                lines.append(f"- 目标价2: {rec.target_price_2:.2f}")

        return "\n".join(lines)
