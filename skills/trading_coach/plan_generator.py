"""
Trading Plan Generator for Trading Coach Skill.

Generates daily trading plans, checklists, and action items.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ActionPriority(Enum):
    """Action item priority levels."""

    MUST_DO = "must_do"  # 必须执行
    SHOULD_DO = "should_do"  # 应该执行
    CONSIDER = "consider"  # 考虑执行
    MONITOR = "monitor"  # 持续监控
    FORBIDDEN = "forbidden"  # 禁止操作


class ActionType(Enum):
    """Types of trading actions."""

    BUY = "buy"  # 买入
    SELL = "sell"  # 卖出
    SET_STOP_LOSS = "set_stop_loss"  # 设置止损
    TAKE_PROFIT = "take_profit"  # 止盈
    ADD_POSITION = "add_position"  # 加仓
    REDUCE_POSITION = "reduce_position"  # 减仓
    WATCH = "watch"  # 关注
    AVOID = "avoid"  # 回避


@dataclass
class ActionItem:
    """A single action item in the trading plan."""

    priority: ActionPriority
    action_type: ActionType
    code: str  # Stock code
    stock_name: str
    description: str
    reason: str
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None
    position_size: Optional[str] = None  # e.g., "1/3 仓位"
    time_window: Optional[str] = None  # e.g., "开盘后30分钟"


@dataclass
class ChecklistItem:
    """A checklist item for trading discipline."""

    category: str  # pre_trade, during_trade, post_trade
    item: str
    is_required: bool = True


@dataclass
class TradingPlan:
    """Daily trading plan."""

    plan_date: date
    market_overview: str
    must_do_actions: list[ActionItem]
    should_do_actions: list[ActionItem]
    watch_list: list[ActionItem]
    forbidden_actions: list[ActionItem]
    checklist: list[ChecklistItem]
    notes: list[str]
    risk_warnings: list[str]


@dataclass
class PositionAction:
    """Suggested action for an existing position."""

    code: str
    stock_name: str
    current_pl_pct: float
    suggested_action: str
    reason: str
    target_price: Optional[Decimal] = None
    stop_loss: Optional[Decimal] = None


# Pre-trade checklist items
PRE_TRADE_CHECKLIST = [
    ChecklistItem("pre_trade", "查看隔夜全球市场走势", True),
    ChecklistItem("pre_trade", "检查今日重大财经事件/数据发布", True),
    ChecklistItem("pre_trade", "复习昨日交易和计划", True),
    ChecklistItem("pre_trade", "确认当前仓位和可用资金", True),
    ChecklistItem("pre_trade", "检查持仓股票的盘前动态", True),
    ChecklistItem("pre_trade", "确认今日止损线位置", True),
    ChecklistItem("pre_trade", "确认情绪状态，是否适合交易", False),
]

# During-trade checklist items
DURING_TRADE_CHECKLIST = [
    ChecklistItem("during_trade", "买入前确认：这是计划内的交易吗？", True),
    ChecklistItem("during_trade", "买入时设置止损单", True),
    ChecklistItem("during_trade", "不追涨超过3%的股票", True),
    ChecklistItem("during_trade", "单次交易不超过总仓位的20%", True),
    ChecklistItem("during_trade", "避免开盘15分钟内冲动交易", False),
    ChecklistItem("during_trade", "大跌时不恐慌卖出", False),
]

# Post-trade checklist items
POST_TRADE_CHECKLIST = [
    ChecklistItem("post_trade", "记录今日所有交易", True),
    ChecklistItem("post_trade", "复盘交易决策：符合计划吗？", True),
    ChecklistItem("post_trade", "检查持仓盈亏变化", True),
    ChecklistItem("post_trade", "更新明日关注列表", False),
    ChecklistItem("post_trade", "总结今日市场特点", False),
]


class PlanGenerator:
    """
    Trading plan generator.

    Generates daily trading plans based on positions, alerts,
    and market conditions.
    """

    def __init__(self):
        """Initialize plan generator."""
        pass

    def generate_daily_plan(
        self,
        positions: list,  # List of PositionData
        watchlist: list,  # List of WatchlistData
        alerts: list = None,  # Risk alerts
        analyst_results: list = None,  # Analyst skill results
        plan_date: date = None,
    ) -> TradingPlan:
        """
        Generate a daily trading plan.

        Args:
            positions: Current positions
            watchlist: Watchlist items
            alerts: Risk alerts from risk controller
            analyst_results: Analysis results from analyst skill
            plan_date: Plan date (default: today)

        Returns:
            TradingPlan with actions and checklist
        """
        if plan_date is None:
            plan_date = date.today()

        must_do = []
        should_do = []
        watch_list = []
        forbidden = []
        notes = []
        risk_warnings = []

        # Process risk alerts
        if alerts:
            for alert in alerts:
                severity = getattr(alert, "severity", "info")
                message = getattr(alert, "message", str(alert))

                if severity in ("critical", "urgent"):
                    risk_warnings.append(f"[{severity.upper()}] {message}")

        # Process positions for actions
        for pos in positions:
            pl_pct = float(pos.pl_ratio) if pos.pl_ratio else 0

            # Check stop loss
            if pl_pct < -8:
                must_do.append(
                    ActionItem(
                        priority=ActionPriority.MUST_DO,
                        action_type=ActionType.SELL,
                        code=pos.full_code,
                        stock_name=pos.stock_name or "",
                        description=f"止损卖出 (亏损 {abs(pl_pct):.1f}%)",
                        reason="已触及止损线，严格执行纪律",
                        stop_loss_price=pos.market_price,
                    )
                )
            elif pl_pct < -5:
                should_do.append(
                    ActionItem(
                        priority=ActionPriority.SHOULD_DO,
                        action_type=ActionType.SET_STOP_LOSS,
                        code=pos.full_code,
                        stock_name=pos.stock_name or "",
                        description=f"检查止损线 (当前亏损 {abs(pl_pct):.1f}%)",
                        reason="亏损接近止损线，确认应对策略",
                    )
                )

            # Check take profit
            if pl_pct >= 30:
                should_do.append(
                    ActionItem(
                        priority=ActionPriority.SHOULD_DO,
                        action_type=ActionType.TAKE_PROFIT,
                        code=pos.full_code,
                        stock_name=pos.stock_name or "",
                        description=f"考虑部分止盈 (盈利 {pl_pct:.1f}%)",
                        reason="盈利超30%，建议减仓1/3锁定利润",
                        position_size="1/3 仓位",
                    )
                )
            elif pl_pct >= 50:
                must_do.append(
                    ActionItem(
                        priority=ActionPriority.MUST_DO,
                        action_type=ActionType.TAKE_PROFIT,
                        code=pos.full_code,
                        stock_name=pos.stock_name or "",
                        description=f"执行止盈计划 (盈利 {pl_pct:.1f}%)",
                        reason="盈利超50%，建议减仓1/2",
                        position_size="1/2 仓位",
                    )
                )

        # Process analyst results for watch/buy signals
        if analyst_results:
            for result in analyst_results:
                score = getattr(result, "overall_score", 0)
                signal = getattr(result, "signal", "")
                code = getattr(result, "code", "")
                name = getattr(result, "name", "")

                if signal == "BUY" and score >= 80:
                    should_do.append(
                        ActionItem(
                            priority=ActionPriority.SHOULD_DO,
                            action_type=ActionType.BUY,
                            code=code,
                            stock_name=name,
                            description=f"关注买入机会 (评分 {score:.0f})",
                            reason="技术分析显示买入信号",
                            target_price=getattr(result, "pivot_price", None),
                            stop_loss_price=getattr(result, "stop_loss", None),
                        )
                    )
                elif signal == "WATCH":
                    watch_list.append(
                        ActionItem(
                            priority=ActionPriority.MONITOR,
                            action_type=ActionType.WATCH,
                            code=code,
                            stock_name=name,
                            description=f"持续观察 (评分 {score:.0f})",
                            reason="形态发展中，等待突破确认",
                        )
                    )

        # Add standard watchlist items
        for item in watchlist[:5]:  # Top 5
            if not any(a.code == item.full_code for a in watch_list + should_do):
                watch_list.append(
                    ActionItem(
                        priority=ActionPriority.MONITOR,
                        action_type=ActionType.WATCH,
                        code=item.full_code,
                        stock_name=item.stock_name,
                        description="关注列表",
                        reason="保持关注，等待机会",
                    )
                )

        # Add forbidden actions based on risk warnings
        if risk_warnings:
            forbidden.append(
                ActionItem(
                    priority=ActionPriority.FORBIDDEN,
                    action_type=ActionType.ADD_POSITION,
                    code="*",
                    stock_name="任何股票",
                    description="禁止加仓",
                    reason="存在未处理的风险预警",
                )
            )

        # Market overview (placeholder - would be populated by market observer)
        market_overview = self._generate_market_overview()

        # Build checklist
        checklist = (
            PRE_TRADE_CHECKLIST + DURING_TRADE_CHECKLIST + POST_TRADE_CHECKLIST
        )

        # Add notes
        notes.append(f"计划日期: {plan_date}")
        notes.append(f"持仓数量: {len(positions)}")
        notes.append(f"关注股票: {len(watchlist)}")

        return TradingPlan(
            plan_date=plan_date,
            market_overview=market_overview,
            must_do_actions=must_do,
            should_do_actions=should_do,
            watch_list=watch_list[:10],  # Limit to 10
            forbidden_actions=forbidden,
            checklist=checklist,
            notes=notes,
            risk_warnings=risk_warnings,
        )

    def _generate_market_overview(self) -> str:
        """Generate market overview text."""
        # In real implementation, would fetch actual market data
        weekday = datetime.now().weekday()
        weekday_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

        return f"""
**今日是{weekday_names[weekday]}**

- 注意今日经济数据发布时间
- 检查持仓股票是否有财报/公告
- 留意大盘整体趋势
""".strip()

    def generate_position_actions(
        self,
        positions: list,  # List of PositionData
    ) -> list[PositionAction]:
        """
        Generate suggested actions for each position.

        Args:
            positions: Current positions

        Returns:
            List of PositionAction suggestions
        """
        actions = []

        for pos in positions:
            pl_pct = float(pos.pl_ratio) if pos.pl_ratio else 0

            if pl_pct <= -15:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="立即止损",
                    reason="深度亏损，保护剩余本金",
                )
            elif pl_pct <= -8:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="触及止损线",
                    reason="严格执行止损纪律",
                )
            elif pl_pct <= -5:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="密切关注",
                    reason="接近止损位，准备应对",
                )
            elif pl_pct >= 100:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="保留1/3长持",
                    reason="翻倍后减仓至1/3，剩余让利润奔跑",
                )
            elif pl_pct >= 50:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="减仓1/2",
                    reason="盈利50%，锁定部分利润",
                )
            elif pl_pct >= 30:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="减仓1/3",
                    reason="盈利30%，开始分批止盈",
                )
            elif pl_pct >= 20:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="上移止损到成本价",
                    reason="盈利20%后保本，让利润奔跑",
                )
            elif pl_pct >= 10:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="上移止损",
                    reason="盈利中，收紧止损保护利润",
                )
            else:
                action = PositionAction(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    current_pl_pct=pl_pct,
                    suggested_action="持有观察",
                    reason="正常波动范围内",
                )

            actions.append(action)

        return actions

    def generate_plan_report(self, plan: TradingPlan) -> str:
        """
        Generate a trading plan report in markdown format.

        Args:
            plan: Trading plan

        Returns:
            Markdown formatted report
        """
        lines = []
        lines.append(f"# 今日交易计划 ({plan.plan_date})")
        lines.append("")

        # Market overview
        lines.append("## 市场概览")
        lines.append("")
        lines.append(plan.market_overview)
        lines.append("")

        # Risk warnings
        if plan.risk_warnings:
            lines.append("## ⚠️ 风险警示")
            lines.append("")
            for warning in plan.risk_warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Must do actions
        if plan.must_do_actions:
            lines.append("## 🔴 必须执行")
            lines.append("")
            for action in plan.must_do_actions:
                lines.append(f"### {action.code} {action.stock_name}")
                lines.append(f"- **操作**: {action.description}")
                lines.append(f"- **原因**: {action.reason}")
                if action.stop_loss_price:
                    lines.append(f"- **止损价**: {action.stop_loss_price}")
                if action.position_size:
                    lines.append(f"- **仓位**: {action.position_size}")
                lines.append("")

        # Should do actions
        if plan.should_do_actions:
            lines.append("## 🟡 建议执行")
            lines.append("")
            for action in plan.should_do_actions:
                lines.append(f"### {action.code} {action.stock_name}")
                lines.append(f"- **操作**: {action.description}")
                lines.append(f"- **原因**: {action.reason}")
                if action.target_price:
                    lines.append(f"- **目标价**: {action.target_price}")
                if action.stop_loss_price:
                    lines.append(f"- **止损价**: {action.stop_loss_price}")
                lines.append("")

        # Watch list
        if plan.watch_list:
            lines.append("## 👀 关注列表")
            lines.append("")
            lines.append("| 代码 | 名称 | 说明 |")
            lines.append("|------|------|------|")
            for action in plan.watch_list:
                lines.append(
                    f"| {action.code} | {action.stock_name} | {action.description} |"
                )
            lines.append("")

        # Forbidden actions
        if plan.forbidden_actions:
            lines.append("## 🚫 禁止操作")
            lines.append("")
            for action in plan.forbidden_actions:
                lines.append(f"- **{action.description}**: {action.reason}")
            lines.append("")

        # Pre-trade checklist
        pre_trade = [c for c in plan.checklist if c.category == "pre_trade"]
        if pre_trade:
            lines.append("## ✅ 盘前检查清单")
            lines.append("")
            for item in pre_trade:
                required = "（必选）" if item.is_required else "（可选）"
                lines.append(f"- [ ] {item.item} {required}")
            lines.append("")

        # During-trade checklist
        during_trade = [c for c in plan.checklist if c.category == "during_trade"]
        if during_trade:
            lines.append("## ✅ 盘中纪律")
            lines.append("")
            for item in during_trade:
                required = "（必选）" if item.is_required else "（可选）"
                lines.append(f"- [ ] {item.item} {required}")
            lines.append("")

        # Notes
        if plan.notes:
            lines.append("## 📝 备注")
            lines.append("")
            for note in plan.notes:
                lines.append(f"- {note}")
            lines.append("")

        return "\n".join(lines)

    def get_trading_rules(self) -> list[str]:
        """
        Get list of trading rules to follow.

        Returns:
            List of trading rules
        """
        return [
            "止损纪律：任何股票最大亏损不超过 8%",
            "仓位控制：单只股票不超过总仓位 20%",
            "分批操作：买入/卖出分 2-3 次执行",
            "禁止追涨：不买当日涨幅超 3% 的股票",
            "冷静期：亏损后 24 小时内不做新的买入决策",
            "止盈阶梯：+30% 减 1/3，+50% 减 1/2，+100% 保留 1/3",
            "现金底线：保持至少 15% 现金仓位",
            "杠杆限制：总杠杆不超过 1.5 倍",
            "交易次数：每日交易不超过 5 次",
            "情绪管理：大喜大悲时不做决策",
        ]
