"""
投资教练 - AI 智能建议生成器

基于投资分析框架 V10.10 生成专业的交易改进建议。
核心原则：止损优先，估值先行，周期顺势，量价确认，完整计划

框架来源: ~/Documents/trade/prompt/daily-analysis-prompt-v10_10.md
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from .statistics import TradeStatistics
from .trade_matcher import MatchedTrade


@dataclass
class RecommendationItem:
    """单条建议"""

    category: str  # 优势/问题/建议
    priority: int  # 1=最高优先级, 3=一般
    title: str  # 简短标题
    content: str  # 详细内容
    framework_ref: Optional[str] = None  # 框架参考条款


@dataclass
class TradeRecommendation:
    """交易建议汇总"""

    strengths: list[RecommendationItem]  # 优势
    weaknesses: list[RecommendationItem]  # 问题
    suggestions: list[RecommendationItem]  # 建议
    risk_alerts: list[RecommendationItem]  # 风险警示
    framework_version: str = "V10.10"


class InvestmentCoach:
    """
    投资教练 - 基于 V10.10 框架生成智能建议

    核心规则（摘自 V10.10）:
    1. 杠杆红线: >2.0x 强制减仓, >1.8x 停止加仓
    2. 止损规则: -10% 触发立即执行
    3. 期权仓位: 单个≤5%, 同标的≤8%, 总仓位≤15%
    4. 盈亏比目标: >1.0 (平均盈利 > 平均亏损)
    5. 胜率目标: >50%
    6. 持仓纪律: 盈利交易持有时间应 > 亏损交易

    历史教训（摘自 V10.10）:
    - 集中 + 没有止损 = 灾难
    - 技术指标可被操控，一致预期难以操控
    - 没有完整操作计划的交易 = 赌博
    - 期权必须设 OCO 订单，避免裸卖空风险
    """

    # V10.10 框架核心参数
    FRAMEWORK_PARAMS = {
        "leverage_warning": Decimal("1.5"),
        "leverage_stop_add": Decimal("1.8"),
        "leverage_force_reduce": Decimal("2.0"),
        "stop_loss_pct": Decimal("-0.10"),
        "single_stock_base_limit": Decimal("0.25"),
        "single_option_limit": Decimal("0.05"),
        "same_underlying_option_limit": Decimal("0.08"),
        "total_option_limit": Decimal("0.15"),
        "target_profit_loss_ratio": Decimal("1.0"),
        "target_win_rate": Decimal("0.5"),
        "big_loss_threshold": Decimal("-0.5"),
        "option_take_profit_1": Decimal("0.30"),
        "option_take_profit_2": Decimal("0.50"),
        "option_stop_loss_1": Decimal("-0.30"),
        "option_stop_loss_2": Decimal("-0.50"),
    }

    def __init__(self):
        self.recommendations: list[RecommendationItem] = []

    def analyze(
        self,
        stats: TradeStatistics,
        stock_trades: list[MatchedTrade],
        option_trades: list[MatchedTrade],
    ) -> TradeRecommendation:
        """
        分析交易统计并生成建议

        Args:
            stats: 交易统计数据
            stock_trades: 股票交易列表
            option_trades: 期权交易列表

        Returns:
            TradeRecommendation 建议汇总
        """
        strengths = []
        weaknesses = []
        suggestions = []
        risk_alerts = []

        # === 分析优势 ===
        strengths.extend(self._analyze_strengths(stats, stock_trades, option_trades))

        # === 分析问题 ===
        weaknesses.extend(self._analyze_weaknesses(stats, stock_trades, option_trades))

        # === 生成建议 ===
        suggestions.extend(
            self._generate_suggestions(stats, stock_trades, option_trades)
        )

        # === 风险警示 ===
        risk_alerts.extend(
            self._generate_risk_alerts(stats, stock_trades, option_trades)
        )

        return TradeRecommendation(
            strengths=strengths,
            weaknesses=weaknesses,
            suggestions=suggestions,
            risk_alerts=risk_alerts,
            framework_version="V10.10",
        )

    def _analyze_strengths(
        self,
        stats: TradeStatistics,
        stock_trades: list[MatchedTrade],
        option_trades: list[MatchedTrade],
    ) -> list[RecommendationItem]:
        """分析优势"""
        strengths = []

        # 1. 胜率分析
        if stats.win_rate >= 0.6:
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=1,
                    title="优秀的胜率",
                    content=f"胜率高达 {stats.win_rate:.1%}，显示出良好的选股和择时能力。"
                    f"继续保持对估值和技术面的综合判断。",
                    framework_ref="V10.10 第三部分：估值分析框架",
                )
            )
        elif stats.win_rate >= 0.5:
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=2,
                    title="稳健的胜率",
                    content=f"胜率 {stats.win_rate:.1%} 超过50%，说明交易决策整体正确。",
                    framework_ref="V10.10 核心规则",
                )
            )

        # 2. 盈亏比分析
        if stats.profit_loss_ratio >= Decimal("1.5"):
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=1,
                    title="出色的盈亏比",
                    content=f"盈亏比达到 {float(stats.profit_loss_ratio):.2f}，"
                    f"远超1.0的基准线。这意味着即使胜率下降，整体仍能盈利。",
                    framework_ref="V10.10 6.1 决策优先级",
                )
            )
        elif stats.profit_loss_ratio >= Decimal("1.0"):
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=2,
                    title="健康的盈亏比",
                    content=f"盈亏比 {float(stats.profit_loss_ratio):.2f} 超过1.0，"
                    f"说明平均盈利大于平均亏损，符合框架要求。",
                    framework_ref="V10.10 核心规则",
                )
            )

        # 3. 持仓纪律
        if (
            stats.avg_winning_holding_days > 0
            and stats.avg_losing_holding_days > 0
            and stats.avg_winning_holding_days > stats.avg_losing_holding_days
        ):
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=2,
                    title="良好的持仓纪律",
                    content=f"盈利交易平均持仓 {stats.avg_winning_holding_days:.1f} 天，"
                    f"亏损交易平均持仓 {stats.avg_losing_holding_days:.1f} 天。"
                    f"做到了'让利润奔跑，截断亏损'。",
                    framework_ref="V10.10 历史教训精华",
                )
            )

        # 4. 净利润
        if stats.net_profit > 0:
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=1,
                    title="整体盈利",
                    content=f"期间净利润 {float(stats.net_profit):,.0f} HKD，"
                    f"交易策略整体有效。",
                )
            )

        # 5. 期权交易表现
        if option_trades and stats.option_net_profit > 0:
            strengths.append(
                RecommendationItem(
                    category="优势",
                    priority=2,
                    title="期权交易盈利",
                    content=f"期权交易净盈利 {float(stats.option_net_profit):,.0f} HKD，"
                    f"期权策略执行有效。",
                    framework_ref="V10.10 6.5 期权规则",
                )
            )

        # 6. 市场分散
        if stats.market_stats and len(stats.market_stats) >= 2:
            profitable_markets = [
                m for m, s in stats.market_stats.items() if s.net_profit > 0
            ]
            if len(profitable_markets) >= 2:
                strengths.append(
                    RecommendationItem(
                        category="优势",
                        priority=3,
                        title="多市场盈利",
                        content=f"在 {len(profitable_markets)} 个市场实现盈利，"
                        f"风险分散策略有效。",
                    )
                )

        return strengths

    def _analyze_weaknesses(
        self,
        stats: TradeStatistics,
        stock_trades: list[MatchedTrade],
        option_trades: list[MatchedTrade],
    ) -> list[RecommendationItem]:
        """分析问题"""
        weaknesses = []

        # 1. 盈亏比问题（核心问题）
        if stats.profit_loss_ratio < Decimal("1.0"):
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=1,
                    title="盈亏比不足",
                    content=f"盈亏比仅为 {float(stats.profit_loss_ratio):.2f}（低于1.0），"
                    f"平均亏损 {float(stats.avg_loss):,.0f} 大于平均盈利 {float(stats.avg_profit):,.0f}。"
                    f"这说明止损不够及时，让亏损交易持有过久。"
                    f"框架教训：'集中 + 没有止损 = 灾难'。",
                    framework_ref="V10.10 历史教训精华",
                )
            )

        # 2. 胜率问题
        if stats.win_rate < Decimal("0.4"):
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=1,
                    title="胜率偏低",
                    content=f"胜率仅 {stats.win_rate:.1%}，低于40%警戒线。"
                    f"需要改进选股和择时策略，建议使用框架中的'估值筛选 + 技术评分'双重确认。",
                    framework_ref="V10.10 6.1 决策优先级",
                )
            )
        elif stats.win_rate < Decimal("0.5"):
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=2,
                    title="胜率有待提升",
                    content=f"胜率 {stats.win_rate:.1%} 略低于50%，"
                    f"建议加强基本面估值筛选，'估值不通过不交易'。",
                    framework_ref="V10.10 第三部分：估值分析框架",
                )
            )

        # 3. 大幅亏损问题
        big_loss_trades = [
            t
            for t in stock_trades + option_trades
            if t.profit_loss_ratio < Decimal("-0.3")
        ]
        if big_loss_trades:
            extreme_losses = [t for t in big_loss_trades if t.profit_loss_ratio < Decimal("-0.5")]
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=1,
                    title="存在大幅亏损交易",
                    content=f"有 {len(big_loss_trades)} 笔交易亏损超过30%"
                    + (f"（其中 {len(extreme_losses)} 笔超过50%）" if extreme_losses else "")
                    + "。框架规定股票止损线为-10%，期权止损线为-30%。"
                    f"大幅亏损严重拖累整体表现，必须严格执行止损。",
                    framework_ref="V10.10 6.5 期权规则 OCO订单",
                )
            )

        # 4. 持仓纪律问题
        if (
            stats.avg_winning_holding_days > 0
            and stats.avg_losing_holding_days > 0
            and stats.avg_winning_holding_days < stats.avg_losing_holding_days
        ):
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=2,
                    title="持仓纪律颠倒",
                    content=f"盈利交易平均持仓 {stats.avg_winning_holding_days:.1f} 天，"
                    f"亏损交易平均持仓 {stats.avg_losing_holding_days:.1f} 天。"
                    f"这是典型的'止盈过早，止损过晚'，需要扭转。",
                    framework_ref="V10.10 历史教训精华",
                )
            )

        # 5. 期权亏损问题
        if option_trades and stats.option_net_profit < 0:
            weaknesses.append(
                RecommendationItem(
                    category="问题",
                    priority=2,
                    title="期权交易亏损",
                    content=f"期权交易净亏损 {float(abs(stats.option_net_profit)):,.0f} HKD。"
                    f"期权是高风险工具，必须严格控制仓位（总仓位≤15%）并设置OCO订单。",
                    framework_ref="V10.10 6.5 期权规则",
                )
            )

        # 6. 过度交易问题
        all_trades = stock_trades + option_trades
        if all_trades:
            avg_holding = sum(t.holding_days for t in all_trades) / len(all_trades)
            short_term_trades = [t for t in all_trades if t.holding_days <= 3]
            if len(short_term_trades) / len(all_trades) > 0.5:
                weaknesses.append(
                    RecommendationItem(
                        category="问题",
                        priority=3,
                        title="短线交易过多",
                        content=f"超过50%的交易持仓不超过3天（{len(short_term_trades)}/{len(all_trades)}），"
                        f"平均持仓仅 {avg_holding:.1f} 天。"
                        f"频繁交易增加手续费成本，也难以把握趋势性行情。",
                    )
                )

        return weaknesses

    def _generate_suggestions(
        self,
        stats: TradeStatistics,
        stock_trades: list[MatchedTrade],
        option_trades: list[MatchedTrade],
    ) -> list[RecommendationItem]:
        """生成建议"""
        suggestions = []

        # 1. 止损建议（最重要）
        if stats.profit_loss_ratio < Decimal("1.0"):
            suggestions.append(
                RecommendationItem(
                    category="建议",
                    priority=1,
                    title="严格执行止损",
                    content="建议措施：\n"
                    "1. 股票：买入后立即设置 -10% 止损单\n"
                    "2. 期权：使用 OCO 订单（+30%止盈 / -30%止损）\n"
                    "3. 每笔交易前明确止损价位，写入交易计划\n"
                    "4. 触发止损后不犹豫，立即执行",
                    framework_ref="V10.10 6.5 期权规则 OCO订单",
                )
            )

        # 2. 估值筛选建议
        if stats.win_rate < Decimal("0.5"):
            suggestions.append(
                RecommendationItem(
                    category="建议",
                    priority=1,
                    title="加强估值筛选",
                    content="交易前必须完成估值筛选：\n"
                    "1. Forward PE + PB-ROE 矩阵分析\n"
                    "2. 周期股用 PB-ROE，成长股用 Forward PE\n"
                    "3. 估值筛选不通过的标的，技术形态再好也不买\n"
                    "4. 参考框架第三部分的估值判断矩阵",
                    framework_ref="V10.10 第三部分：估值分析框架",
                )
            )

        # 3. 入场时机建议
        suggestions.append(
            RecommendationItem(
                category="建议",
                priority=2,
                title="使用量价转换确认入场",
                content="V10.10 新增的入场方法：\n"
                "1. 日K线定方向（OBV + VCP 评分）\n"
                "2. 60分钟K线找入场（量价转换信号）\n"
                "3. 底部确认：下跌缩量 → 反弹放量\n"
                "4. 顶部确认：上涨缩量 → 下跌放量\n"
                "核心原则：不追涨！等量价转换确认后再入场",
                framework_ref="V10.10 第五部分（续）：60分钟量价转换入场系统",
            )
        )

        # 4. 持仓优化建议
        if stats.avg_winning_holding_days < stats.avg_losing_holding_days:
            suggestions.append(
                RecommendationItem(
                    category="建议",
                    priority=2,
                    title="优化持仓策略",
                    content="调整持仓策略：\n"
                    "1. 盈利交易：设置移动止盈，让利润奔跑\n"
                    "2. 亏损交易：触发止损就走，不抱幻想\n"
                    "3. 目标：盈利持仓时间 > 亏损持仓时间",
                )
            )

        # 5. 期权使用建议
        if option_trades:
            suggestions.append(
                RecommendationItem(
                    category="建议",
                    priority=2,
                    title="优化期权策略",
                    content="期权交易规范：\n"
                    "1. 仓位限制：单个期权≤5%，同标的≤8%，总仓位≤15%\n"
                    "2. IV 选择：IV Rank<30%适合买期权，>70%适合卖期权\n"
                    "3. 期限选择：到期日>45天，避免时间价值快速衰减\n"
                    "4. 必须设置OCO：+30%止盈，-30%止损",
                    framework_ref="V10.10 6.5 期权规则",
                )
            )

        # 6. 交易计划建议
        suggestions.append(
            RecommendationItem(
                category="建议",
                priority=3,
                title="制定完整交易计划",
                content="每笔交易前必须明确：\n"
                "1. 买入理由（估值 + 技术面）\n"
                "2. 买入区间和仓位\n"
                "3. 止损价位（必须！）\n"
                "4. 止盈目标（第一目标 + 第二目标）\n"
                "框架教训：没有完整操作计划的交易 = 赌博",
                framework_ref="V10.10 历史教训精华",
            )
        )

        # 7. 市场选择建议
        if stats.market_stats:
            best_market = max(
                stats.market_stats.items(),
                key=lambda x: float(x[1].win_rate) if x[1].total_trades >= 5 else 0,
            )
            if best_market[1].total_trades >= 5:
                market_name = {"HK": "港股", "US": "美股", "SH": "A股", "SZ": "A股"}.get(
                    best_market[0], best_market[0]
                )
                suggestions.append(
                    RecommendationItem(
                        category="建议",
                        priority=3,
                        title=f"关注{market_name}市场",
                        content=f"{market_name}市场表现最佳（胜率 {best_market[1].win_rate:.1%}），"
                        f"建议保持对该市场的关注和研究深度。",
                    )
                )

        return suggestions

    def _generate_risk_alerts(
        self,
        stats: TradeStatistics,
        stock_trades: list[MatchedTrade],
        option_trades: list[MatchedTrade],
    ) -> list[RecommendationItem]:
        """生成风险警示"""
        alerts = []

        # 1. 期权仓位警示
        if option_trades:
            option_loss_rate = (
                1 - stats.option_win_rate if stats.option_win_rate else Decimal("0")
            )
            if option_loss_rate > Decimal("0.6"):
                alerts.append(
                    RecommendationItem(
                        category="风险警示",
                        priority=1,
                        title="期权亏损率过高",
                        content=f"期权交易亏损率 {option_loss_rate:.1%} 超过60%，"
                        f"建议暂停期权交易，重新评估策略。"
                        f"确保期权仓位不超过总资产15%。",
                        framework_ref="V10.10 6.5 期权规则",
                    )
                )

        # 2. 连续亏损警示
        all_trades = sorted(
            stock_trades + option_trades, key=lambda t: t.sell_date or ""
        )
        if len(all_trades) >= 5:
            recent_trades = all_trades[-5:]
            recent_losses = sum(1 for t in recent_trades if t.profit_loss < 0)
            if recent_losses >= 4:
                alerts.append(
                    RecommendationItem(
                        category="风险警示",
                        priority=1,
                        title="近期连续亏损",
                        content=f"最近5笔交易中有{recent_losses}笔亏损，"
                        f"建议暂停交易，复盘最近的交易决策，"
                        f"检查是否偏离了框架的核心原则。",
                    )
                )

        # 3. 单标的集中警示
        if stock_trades:
            from collections import Counter

            code_counts = Counter(t.code for t in stock_trades)
            most_traded = code_counts.most_common(1)[0]
            if most_traded[1] >= 10 and most_traded[1] / len(stock_trades) > 0.3:
                alerts.append(
                    RecommendationItem(
                        category="风险警示",
                        priority=2,
                        title="单标的交易过于集中",
                        content=f"标的 {most_traded[0]} 交易了 {most_traded[1]} 次，"
                        f"占比 {most_traded[1]/len(stock_trades):.1%}。"
                        f"过度集中增加风险，建议分散到多个标的。",
                    )
                )

        # 4. 平均亏损过大警示
        if stats.avg_loss > stats.avg_profit * 2:
            alerts.append(
                RecommendationItem(
                    category="风险警示",
                    priority=1,
                    title="平均亏损远超平均盈利",
                    content=f"平均亏损 {float(stats.avg_loss):,.0f} 是平均盈利 {float(stats.avg_profit):,.0f} 的2倍以上。"
                    f"这说明止损执行严重不足，必须立即改正。"
                    f"框架核心教训：集中 + 没有止损 = 灾难。",
                    framework_ref="V10.10 历史教训精华",
                )
            )

        return alerts

    def format_for_docx(self, recommendation: TradeRecommendation) -> dict:
        """
        格式化建议供 Word 报告使用

        Returns:
            包含各类建议的字典
        """
        return {
            "framework_version": recommendation.framework_version,
            "strengths": [
                {"title": r.title, "content": r.content, "ref": r.framework_ref}
                for r in sorted(recommendation.strengths, key=lambda x: x.priority)
            ],
            "weaknesses": [
                {"title": r.title, "content": r.content, "ref": r.framework_ref}
                for r in sorted(recommendation.weaknesses, key=lambda x: x.priority)
            ],
            "suggestions": [
                {"title": r.title, "content": r.content, "ref": r.framework_ref}
                for r in sorted(recommendation.suggestions, key=lambda x: x.priority)
            ],
            "risk_alerts": [
                {"title": r.title, "content": r.content, "ref": r.framework_ref}
                for r in sorted(recommendation.risk_alerts, key=lambda x: x.priority)
            ],
        }

    def get_summary(self, recommendation: TradeRecommendation) -> str:
        """获取建议摘要（用于 CLI 输出）"""
        lines = [
            f"=== 投资教练分析 (框架 {recommendation.framework_version}) ===",
            "",
        ]

        if recommendation.strengths:
            lines.append("【优势】")
            for s in recommendation.strengths[:3]:
                lines.append(f"  ✓ {s.title}")
            lines.append("")

        if recommendation.weaknesses:
            lines.append("【问题】")
            for w in recommendation.weaknesses[:3]:
                lines.append(f"  ✗ {w.title}")
            lines.append("")

        if recommendation.risk_alerts:
            lines.append("【风险警示】")
            for r in recommendation.risk_alerts:
                lines.append(f"  ⚠ {r.title}")
            lines.append("")

        if recommendation.suggestions:
            lines.append("【建议】")
            for i, s in enumerate(recommendation.suggestions[:5], 1):
                lines.append(f"  {i}. {s.title}")

        return "\n".join(lines)
