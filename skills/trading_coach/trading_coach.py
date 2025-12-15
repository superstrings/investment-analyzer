"""
Trading Coach main controller.

Orchestrates plan generation, compound education, and psychology coaching.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from skills.shared import DataProvider, SkillContext, SkillResult
from skills.shared.base import BaseSkill

from .compound_educator import CompoundEducator, CompoundProjection, TradingMath
from .plan_generator import PlanGenerator, PositionAction, TradingPlan
from .psychology_coach import (
    BehaviorAnalysis,
    EmotionAssessment,
    PsychologyCoach,
    TradePattern,
)

logger = logging.getLogger(__name__)


@dataclass
class CoachingResult:
    """Result from trading coach analysis."""

    # Plan
    trading_plan: Optional[TradingPlan] = None
    position_actions: list[PositionAction] = field(default_factory=list)

    # Psychology
    trade_pattern: Optional[TradePattern] = None
    behavior_analysis: Optional[BehaviorAnalysis] = None
    emotion_assessment: Optional[EmotionAssessment] = None

    # Education
    compound_projection: Optional[CompoundProjection] = None
    trading_math: Optional[TradingMath] = None

    # Metadata
    coaching_date: date = field(default_factory=date.today)
    user_id: int = 0


class TradingCoach(BaseSkill):
    """
    Trading Coach Skill.

    Provides trading plan generation, psychology coaching,
    and compound interest education.
    """

    def __init__(self, data_provider: DataProvider = None):
        """
        Initialize trading coach.

        Args:
            data_provider: Data provider instance (optional)
        """
        super().__init__(
            name="trading_coach",
            description="交易导师 - 计划制定、心理辅导、复利教育",
        )
        self.data_provider = data_provider or DataProvider()
        self.plan_generator = PlanGenerator()
        self.psychology_coach = PsychologyCoach()
        self.compound_educator = CompoundEducator()

    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute trading coach skill.

        Args:
            context: Execution context

        Returns:
            SkillResult with coaching data
        """
        start_time = datetime.now()

        # Validate context
        is_valid, error = self.validate_context(context)
        if not is_valid:
            return SkillResult.error(self.name, error)

        try:
            request_type = context.request_type

            if request_type == "daily_plan":
                result = self._generate_daily_plan(context)
            elif request_type == "psychology_check":
                result = self._psychology_check(context)
            elif request_type == "compound_lesson":
                result = self._compound_lesson(context)
            elif request_type == "position_review":
                result = self._position_review(context)
            elif request_type == "full_coaching":
                result = self._full_coaching(context)
            else:
                # Default: full coaching
                result = self._full_coaching(context)

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
            logger.exception("Trading coach execution failed")
            return SkillResult.error(self.name, str(e))

    def get_capabilities(self) -> list[str]:
        """Get list of capabilities."""
        return [
            "daily_plan",  # Generate daily trading plan
            "psychology_check",  # Psychology assessment
            "compound_lesson",  # Compound interest education
            "position_review",  # Review positions with suggestions
            "full_coaching",  # Complete coaching session
        ]

    def _generate_daily_plan(self, context: SkillContext) -> CoachingResult:
        """Generate daily trading plan."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        # Get positions and watchlist
        positions = self.data_provider.get_positions(user_id, markets)
        watchlist = self.data_provider.get_watchlist(user_id, markets)

        # Generate plan
        plan = self.plan_generator.generate_daily_plan(
            positions=positions,
            watchlist=watchlist,
            plan_date=date.today(),
        )

        # Generate position actions
        position_actions = self.plan_generator.generate_position_actions(positions)

        return CoachingResult(
            trading_plan=plan,
            position_actions=position_actions,
            coaching_date=date.today(),
            user_id=user_id,
        )

    def _psychology_check(self, context: SkillContext) -> CoachingResult:
        """Perform psychology check."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None
        days = context.get_param("days", 30)

        # Get trades and positions
        trades = self.data_provider.get_trades(user_id, days=days)
        positions = self.data_provider.get_positions(user_id, markets)

        # Calculate total portfolio value
        total_value = sum(p.market_val for p in positions) if positions else Decimal("0")

        # Analyze patterns
        trade_pattern = self.psychology_coach.analyze_trade_patterns(trades, days)

        # Detect behavior patterns
        behavior_analysis = self.psychology_coach.detect_behavior_patterns(
            trade_pattern=trade_pattern,
            positions=positions,
            total_portfolio_value=total_value,
        )

        # Assess emotion
        recent_pl_pct = context.get_param("recent_pl_pct", 0)
        emotion_assessment = self.psychology_coach.assess_emotion(
            behavior_analysis=behavior_analysis,
            recent_pl_pct=recent_pl_pct,
        )

        return CoachingResult(
            trade_pattern=trade_pattern,
            behavior_analysis=behavior_analysis,
            emotion_assessment=emotion_assessment,
            coaching_date=date.today(),
            user_id=user_id,
        )

    def _compound_lesson(self, context: SkillContext) -> CoachingResult:
        """Generate compound interest lesson."""
        initial_capital = Decimal(str(context.get_param("capital", 100000)))
        years = context.get_param("years", 20)
        annual_return = context.get_param("annual_return", 0.14)

        # Calculate projection
        projection = self.compound_educator.calculate_compound_growth(
            initial_capital=initial_capital,
            annual_return=annual_return,
            years=years,
        )

        # Calculate trading math
        trades_per_year = context.get_param("trades_per_year", 10)
        win_rate = context.get_param("win_rate", 0.60)
        avg_profit = context.get_param("avg_profit", 0.07)
        avg_loss = context.get_param("avg_loss", 0.0233)

        trading_math = self.compound_educator.calculate_trading_math(
            trades_per_year=trades_per_year,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
        )

        return CoachingResult(
            compound_projection=projection,
            trading_math=trading_math,
            coaching_date=date.today(),
            user_id=context.user_id,
        )

    def _position_review(self, context: SkillContext) -> CoachingResult:
        """Review current positions with suggestions."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        positions = self.data_provider.get_positions(user_id, markets)
        position_actions = self.plan_generator.generate_position_actions(positions)

        return CoachingResult(
            position_actions=position_actions,
            coaching_date=date.today(),
            user_id=user_id,
        )

    def _full_coaching(self, context: SkillContext) -> CoachingResult:
        """Full coaching session combining all components."""
        user_id = context.user_id
        markets = context.markets if context.markets != ["HK", "US", "A"] else None

        # Get all data
        positions = self.data_provider.get_positions(user_id, markets)
        watchlist = self.data_provider.get_watchlist(user_id, markets)
        trades = self.data_provider.get_trades(user_id, days=30)
        total_value = sum(p.market_val for p in positions) if positions else Decimal("0")

        # Generate daily plan
        plan = self.plan_generator.generate_daily_plan(
            positions=positions,
            watchlist=watchlist,
        )
        position_actions = self.plan_generator.generate_position_actions(positions)

        # Psychology check
        trade_pattern = self.psychology_coach.analyze_trade_patterns(trades, 30)
        behavior_analysis = self.psychology_coach.detect_behavior_patterns(
            trade_pattern=trade_pattern,
            positions=positions,
            total_portfolio_value=total_value,
        )
        emotion_assessment = self.psychology_coach.assess_emotion(behavior_analysis)

        # Compound education (default values)
        initial_capital = total_value if total_value > 0 else Decimal("100000")
        projection = self.compound_educator.calculate_compound_growth(
            initial_capital=initial_capital,
            annual_return=0.14,
            years=20,
        )

        return CoachingResult(
            trading_plan=plan,
            position_actions=position_actions,
            trade_pattern=trade_pattern,
            behavior_analysis=behavior_analysis,
            emotion_assessment=emotion_assessment,
            compound_projection=projection,
            coaching_date=date.today(),
            user_id=user_id,
        )

    def _generate_report(self, result: CoachingResult, context: SkillContext) -> str:
        """Generate coaching report."""
        report_format = context.get_param("format", "markdown")
        request_type = context.request_type

        lines = []
        lines.append("# 交易导师报告")
        lines.append("")
        lines.append(f"日期: {result.coaching_date}")
        lines.append("")

        # Daily affirmation
        affirmation = self.psychology_coach.get_daily_affirmation()
        lines.append(f"> **今日箴言**: {affirmation}")
        lines.append("")

        # Trading plan
        if result.trading_plan:
            plan_report = self.plan_generator.generate_plan_report(result.trading_plan)
            lines.append(plan_report)
            lines.append("")

        # Position actions
        if result.position_actions:
            lines.append("## 持仓建议")
            lines.append("")
            lines.append("| 代码 | 名称 | 盈亏 | 建议 | 原因 |")
            lines.append("|------|------|------|------|------|")
            for action in result.position_actions:
                pl_str = f"{action.current_pl_pct:+.1f}%"
                lines.append(
                    f"| {action.code} | {action.stock_name} | {pl_str} | "
                    f"{action.suggested_action} | {action.reason} |"
                )
            lines.append("")

        # Psychology check
        if result.behavior_analysis or result.emotion_assessment:
            if result.behavior_analysis and result.emotion_assessment:
                psych_report = self.psychology_coach.generate_psychology_check(
                    result.behavior_analysis,
                    result.emotion_assessment,
                )
                lines.append(psych_report)
                lines.append("")

        # Compound education
        if result.compound_projection:
            lines.append("## 复利提醒")
            lines.append("")
            proj = result.compound_projection
            lines.append(
                f"以当前资产 ¥{proj.initial_capital:,.0f}，年化 {proj.annual_return*100:.0f}%，"
                f"{proj.years}年后可达 ¥{proj.final_value:,.0f}（{proj.multiplier:.1f}倍）"
            )
            lines.append("")

            # Quote
            author, quote = self.compound_educator.get_random_quote()
            lines.append(f"> \"{quote}\" - {author}")
            lines.append("")

        # Trading rules reminder
        lines.append("## 交易纪律")
        lines.append("")
        rules = self.plan_generator.get_trading_rules()
        for i, rule in enumerate(rules[:5], 1):  # Top 5 rules
            lines.append(f"{i}. {rule}")
        lines.append("")

        return "\n".join(lines)

    def _get_next_actions(self, result: CoachingResult) -> list[str]:
        """Get suggested next actions."""
        actions = []

        if result.trading_plan:
            if result.trading_plan.must_do_actions:
                actions.append("执行必做操作（止损/止盈）")
            if result.trading_plan.risk_warnings:
                actions.append("处理风险预警")

        if result.behavior_analysis:
            if result.behavior_analysis.risk_level == "high":
                actions.append("进行心理调整，考虑暂停交易")

        if not actions:
            actions.append("按计划执行，保持纪律")

        return actions


def generate_coaching_report(
    user_id: int,
    request_type: str = "full_coaching",
    markets: list[str] = None,
    **params,
) -> str:
    """
    Convenience function to generate coaching report.

    Args:
        user_id: User ID
        request_type: Type of coaching request
        markets: Markets to analyze
        **params: Additional parameters

    Returns:
        Markdown formatted report
    """
    provider = DataProvider()
    coach = TradingCoach(data_provider=provider)

    context = SkillContext(
        user_id=user_id,
        request_type=request_type,
        markets=markets or ["HK", "US", "A"],
        parameters=params,
    )

    result = coach.execute(context)

    if result.success:
        return result.report_content
    else:
        return f"Error: {result.error_message}"
