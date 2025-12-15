"""
Market Observer main controller.

Orchestrates pre-market, post-market, sector rotation, and sentiment analysis.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from skills.shared import DataProvider, SkillContext, SkillResult
from skills.shared.base import BaseSkill, MarketSchedule, MarketState

from .post_market import PostMarketReport, PostMarketSummarizer
from .pre_market import GlobalMarketSnapshot, PreMarketAnalyzer, PreMarketReport
from .sector_rotation import SectorAnalysisReport, SectorRotationAnalyzer
from .sentiment_meter import MarketIndicators, SentimentMeter, SentimentResult

logger = logging.getLogger(__name__)


@dataclass
class MarketObserverResult:
    """Result from market observer analysis."""

    observation_date: date
    market: str
    observation_type: str  # pre_market, post_market, sector, sentiment, full

    # Pre-market analysis
    pre_market_report: Optional[PreMarketReport] = None

    # Post-market analysis
    post_market_report: Optional[PostMarketReport] = None

    # Sector analysis
    sector_report: Optional[SectorAnalysisReport] = None

    # Sentiment analysis
    sentiment_result: Optional[SentimentResult] = None

    # Metadata
    user_id: int = 0


class MarketObserver(BaseSkill):
    """
    Market Observer Skill.

    Provides market analysis including pre-market preparation,
    post-market summary, sector rotation, and sentiment analysis.
    """

    def __init__(self, data_provider: DataProvider = None):
        """
        Initialize market observer.

        Args:
            data_provider: Data provider instance (optional)
        """
        super().__init__(
            name="market_observer",
            description="市场观察员 - 盘前分析、盘后总结、板块轮动、情绪指数",
        )
        self.data_provider = data_provider or DataProvider()
        self.pre_market_analyzer = PreMarketAnalyzer()
        self.post_market_summarizer = PostMarketSummarizer()
        self.sector_analyzer = SectorRotationAnalyzer()
        self.sentiment_meter = SentimentMeter()
        self.schedule = MarketSchedule()

    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute market observer skill.

        Args:
            context: Execution context

        Returns:
            SkillResult with observation data
        """
        start_time = datetime.now()

        # Validate context
        is_valid, error = self.validate_context(context)
        if not is_valid:
            return SkillResult.error(self.name, error)

        try:
            request_type = context.request_type
            market = context.markets[0] if context.markets else "HK"

            if request_type == "pre_market":
                result = self._pre_market_analysis(context, market)
            elif request_type == "post_market":
                result = self._post_market_analysis(context, market)
            elif request_type == "sector":
                result = self._sector_analysis(context, market)
            elif request_type == "sentiment":
                result = self._sentiment_analysis(context, market)
            elif request_type == "full":
                result = self._full_observation(context, market)
            else:
                # Auto-detect based on market state
                result = self._auto_observation(context, market)

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return SkillResult(
                success=True,
                skill_name=self.name,
                result_type=request_type,
                data=result,
                report_content=self._generate_report(result, context),
                execution_time_ms=elapsed,
                next_actions=self._get_next_actions(result),
            )

        except Exception as e:
            logger.exception("Market observer execution failed")
            return SkillResult.error(self.name, str(e))

    def get_capabilities(self) -> list[str]:
        """Get list of capabilities."""
        return [
            "pre_market",  # Pre-market analysis
            "post_market",  # Post-market summary
            "sector",  # Sector rotation analysis
            "sentiment",  # Market sentiment
            "full",  # Full observation
            "auto",  # Auto-detect based on time
        ]

    def _pre_market_analysis(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Generate pre-market analysis."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        # Get positions and watchlist
        positions = self.data_provider.get_positions(user_id, markets)
        watchlist = self.data_provider.get_watchlist(user_id, markets)

        # Get global snapshot (in real implementation, would fetch from API)
        global_snapshot = context.get_param("global_snapshot", GlobalMarketSnapshot())

        # Generate pre-market report
        pre_market_report = self.pre_market_analyzer.analyze(
            market=market,
            positions=positions,
            watchlist=watchlist,
            global_snapshot=global_snapshot,
        )

        return MarketObserverResult(
            observation_date=date.today(),
            market=market,
            observation_type="pre_market",
            pre_market_report=pre_market_report,
            user_id=user_id,
        )

    def _post_market_analysis(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Generate post-market summary."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        # Get positions
        positions = self.data_provider.get_positions(user_id, markets)

        # Get today's trades
        trades = self.data_provider.get_trades(
            user_id,
            start_date=date.today(),
            end_date=date.today(),
        )

        # Generate post-market report
        post_market_report = self.post_market_summarizer.summarize(
            market=market,
            positions=positions,
            trades=trades,
        )

        return MarketObserverResult(
            observation_date=date.today(),
            market=market,
            observation_type="post_market",
            post_market_report=post_market_report,
            user_id=user_id,
        )

    def _sector_analysis(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Generate sector rotation analysis."""
        # Get sector data from parameters (in real implementation, would fetch from API)
        sector_data = context.get_param("sector_data", [])
        money_flow = context.get_param("money_flow", [])

        # Generate sector report
        sector_report = self.sector_analyzer.analyze(
            market=market,
            sector_data=sector_data,
            money_flow_data=money_flow,
        )

        return MarketObserverResult(
            observation_date=date.today(),
            market=market,
            observation_type="sector",
            sector_report=sector_report,
            user_id=context.user_id,
        )

    def _sentiment_analysis(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Generate sentiment analysis."""
        # Get market indicators from parameters
        indicators = context.get_param("indicators", MarketIndicators())

        # Calculate sentiment
        sentiment_result = self.sentiment_meter.calculate_sentiment(indicators)

        return MarketObserverResult(
            observation_date=date.today(),
            market=market,
            observation_type="sentiment",
            sentiment_result=sentiment_result,
            user_id=context.user_id,
        )

    def _full_observation(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Generate full market observation."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        # Get data
        positions = self.data_provider.get_positions(user_id, markets)
        watchlist = self.data_provider.get_watchlist(user_id, markets)
        trades = self.data_provider.get_trades(
            user_id,
            start_date=date.today(),
            end_date=date.today(),
        )

        # Pre-market
        global_snapshot = context.get_param("global_snapshot", GlobalMarketSnapshot())
        pre_market_report = self.pre_market_analyzer.analyze(
            market=market,
            positions=positions,
            watchlist=watchlist,
            global_snapshot=global_snapshot,
        )

        # Post-market
        post_market_report = self.post_market_summarizer.summarize(
            market=market,
            positions=positions,
            trades=trades,
        )

        # Sector
        sector_data = context.get_param("sector_data", [])
        sector_report = self.sector_analyzer.analyze(
            market=market,
            sector_data=sector_data,
        )

        # Sentiment
        indicators = context.get_param("indicators", MarketIndicators())
        sentiment_result = self.sentiment_meter.calculate_sentiment(indicators)

        return MarketObserverResult(
            observation_date=date.today(),
            market=market,
            observation_type="full",
            pre_market_report=pre_market_report,
            post_market_report=post_market_report,
            sector_report=sector_report,
            sentiment_result=sentiment_result,
            user_id=user_id,
        )

    def _auto_observation(
        self,
        context: SkillContext,
        market: str,
    ) -> MarketObserverResult:
        """Auto-detect observation type based on market state."""
        market_state = self.schedule.get_market_state(market)

        if market_state == MarketState.PRE_MARKET:
            return self._pre_market_analysis(context, market)
        elif market_state == MarketState.POST_MARKET:
            return self._post_market_analysis(context, market)
        elif market_state == MarketState.OPEN:
            # During market hours, provide sentiment
            return self._sentiment_analysis(context, market)
        else:
            # Market closed, provide full observation
            return self._full_observation(context, market)

    def _generate_report(
        self,
        result: MarketObserverResult,
        context: SkillContext,
    ) -> str:
        """Generate observation report."""
        lines = []
        lines.append("# 市场观察报告")
        lines.append("")
        lines.append(f"日期: {result.observation_date}")
        lines.append(f"市场: {result.market}")
        lines.append("")

        # Pre-market report
        if result.pre_market_report:
            pre_report = self.pre_market_analyzer.generate_report(
                result.pre_market_report
            )
            lines.append(pre_report)
            lines.append("")

        # Post-market report
        if result.post_market_report:
            post_report = self.post_market_summarizer.generate_report(
                result.post_market_report
            )
            lines.append(post_report)
            lines.append("")

        # Sector report
        if result.sector_report:
            sector_report = self.sector_analyzer.generate_report(
                result.sector_report
            )
            lines.append(sector_report)
            lines.append("")

        # Sentiment report
        if result.sentiment_result:
            sentiment_report = self.sentiment_meter.generate_sentiment_report(
                result.sentiment_result
            )
            lines.append(sentiment_report)
            lines.append("")

        return "\n".join(lines)

    def _get_next_actions(self, result: MarketObserverResult) -> list[str]:
        """Get suggested next actions."""
        actions = []

        if result.pre_market_report:
            if result.pre_market_report.risk_warnings:
                actions.append("处理风险提示")
            if result.pre_market_report.trading_focus:
                actions.append("确认今日交易计划")

        if result.post_market_report:
            if result.post_market_report.anomaly_stocks:
                actions.append("分析异动股票")
            if result.post_market_report.lessons_learned:
                actions.append("记录经验教训")

        if result.sentiment_result:
            level = result.sentiment_result.level.value
            if "fear" in level:
                actions.append("考虑逢低布局")
            elif "greed" in level:
                actions.append("考虑获利了结")

        if not actions:
            actions.append("继续观察市场")

        return actions


def generate_observation_report(
    user_id: int,
    request_type: str = "auto",
    market: str = "HK",
    **params,
) -> str:
    """
    Convenience function to generate market observation report.

    Args:
        user_id: User ID
        request_type: Type of observation request
        market: Market code
        **params: Additional parameters

    Returns:
        Markdown formatted report
    """
    provider = DataProvider()
    observer = MarketObserver(data_provider=provider)

    context = SkillContext(
        user_id=user_id,
        request_type=request_type,
        markets=[market],
        parameters=params,
    )

    result = observer.execute(context)

    if result.success:
        return result.report_content
    else:
        return f"Error: {result.error_message}"
