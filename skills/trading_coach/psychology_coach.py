"""
Psychology Coach for Trading Coach Skill.

Identifies emotional patterns and provides psychological guidance.
"""

import logging
import random
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class EmotionType(Enum):
    """Types of trading emotions."""

    FEAR = "fear"  # 恐惧
    GREED = "greed"  # 贪婪
    HOPE = "hope"  # 侥幸
    REGRET = "regret"  # 后悔
    OVERCONFIDENCE = "overconfidence"  # 过度自信
    PANIC = "panic"  # 恐慌
    EUPHORIA = "euphoria"  # 狂喜
    NEUTRAL = "neutral"  # 中性


class BehaviorPattern(Enum):
    """Detected trading behavior patterns."""

    OVERTRADING = "overtrading"  # 频繁交易
    LOSS_CHASING = "loss_chasing"  # 追涨杀跌
    REVENGE_TRADING = "revenge_trading"  # 报复性交易
    POSITION_AVERAGING = "position_averaging"  # 摊薄成本
    PREMATURE_EXIT = "premature_exit"  # 过早离场
    HOLDING_LOSERS = "holding_losers"  # 死扛亏损
    CONCENTRATION_RISK = "concentration_risk"  # 重仓风险
    FOMO = "fomo"  # 害怕错过


@dataclass
class PsychologyTrigger:
    """Psychology intervention trigger."""

    trigger_type: str
    severity: str  # low, medium, high, critical
    message: str
    details: dict = field(default_factory=dict)


@dataclass
class EmotionAssessment:
    """Assessment of trader's emotional state."""

    emotion: EmotionType
    intensity: float  # 0-1 scale
    triggers: list[str]
    recommendations: list[str]


@dataclass
class BehaviorAnalysis:
    """Analysis of trading behavior patterns."""

    patterns_detected: list[BehaviorPattern]
    risk_level: str  # low, medium, high
    observations: list[str]
    coaching_points: list[str]


@dataclass
class TradePattern:
    """Analyzed trade pattern data."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    consecutive_losses: int
    consecutive_wins: int
    avg_hold_days: float
    largest_loss_pct: float
    largest_win_pct: float
    daily_trade_count: dict[date, int] = field(default_factory=dict)


# Trading wisdom quotes
TRADING_QUOTES = [
    ("杰西·利弗莫尔", "市场永远不会错，错的只有人的看法。"),
    ("杰西·利弗莫尔", "赚大钱靠的不是思考，而是坐等。"),
    ("杰西·利弗莫尔", "华尔街不会改变，因为人性不会改变。"),
    ("马克·道格拉斯", "交易的本质是管理概率和管理情绪。"),
    ("马克·道格拉斯", "你无法控制市场，但你可以控制你对市场的反应。"),
    ("霍华德·马克斯", "成功投资的关键是控制风险，而不是追求收益。"),
    ("彼得·林奇", "投资股票最大的风险不是波动，而是你自己。"),
    ("沃伦·巴菲特", "在别人恐惧时贪婪，在别人贪婪时恐惧。"),
    ("沃伦·巴菲特", "投资最重要的是避免犯大错，而不是做出精彩的决定。"),
    ("查理·芒格", "反过来想，总是反过来想。"),
    ("查理·芒格", "知道自己不知道什么，比聪明更重要。"),
    ("乔治·索罗斯", "重要的不是你对还是错，而是你对的时候赚多少，错的时候亏多少。"),
    ("Ray Dalio", "痛苦+反思=进步。"),
    ("Ed Seykota", "胜利者和失败者的区别在于如何处理亏损。"),
    ("William O'Neil", "市场永远是对的。如果你的股票在下跌，那是你错了，不是市场错了。"),
    ("保罗·都铎·琼斯", "最重要的规则是防守，而不是进攻。"),
    ("斯坦利·德鲁肯米勒", "决定成功的不是你对的次数，而是你对的时候赚多少。"),
]

# Intervention templates
INTERVENTION_TEMPLATES = {
    BehaviorPattern.OVERTRADING: {
        "title": "频繁交易警示",
        "message": "今日交易{count}次，超过建议频率。频繁交易往往是情绪驱动而非理性分析。",
        "advice": [
            "暂停交易，深呼吸，冷静10分钟",
            "复盘今天的交易动机，是计划内还是冲动？",
            "记住：最好的交易往往是不交易",
            "设置每日最大交易次数限制",
        ],
    },
    BehaviorPattern.LOSS_CHASING: {
        "title": "追涨杀跌警示",
        "message": "检测到追涨杀跌模式：高买低卖。这是最常见的亏损原因。",
        "advice": [
            "停止立即行动，市场明天还会在那里",
            "问自己：如果今天没有持仓，会在这个价位买入吗？",
            "制定买入计划，等待回调再入场",
            "避免在大涨时买入，大跌时卖出",
        ],
    },
    BehaviorPattern.REVENGE_TRADING: {
        "title": "报复性交易警示",
        "message": "亏损后立即加大仓位或频繁交易，试图快速回本。这是危险的情绪反应。",
        "advice": [
            "承认亏损，接受它是交易的一部分",
            "亏损后休息至少24小时再做决策",
            "不要试图'赢回来'，每笔交易都是独立的",
            "减小仓位，降低情绪影响",
        ],
    },
    BehaviorPattern.HOLDING_LOSERS: {
        "title": "持有亏损警示",
        "message": "发现多个持仓深度亏损但未止损。'死扛'是复利的最大敌人。",
        "advice": [
            "问自己：如果现在没有持仓，会买入吗？",
            "不是卖不卖的问题，而是资金能否更有效利用",
            "止损不是认输，是保护本金",
            "每个持仓都应该有明确的止损线",
        ],
    },
    BehaviorPattern.CONCENTRATION_RISK: {
        "title": "仓位集中警示",
        "message": "单一持仓占比过高（{pct}%），风险过度集中。",
        "advice": [
            "没有任何股票值得你全仓",
            "分散投资保护你免受黑天鹅",
            "考虑逐步减持到合理比例（<20%）",
            "高仓位带来的是焦虑，不是收益",
        ],
    },
    BehaviorPattern.FOMO: {
        "title": "FOMO（错失恐惧）警示",
        "message": "检测到追涨行为，可能受到'害怕错过'心理影响。",
        "advice": [
            "错过一只股票不会让你变穷，但追高会",
            "市场永远有机会，但你的本金是有限的",
            "好机会需要等待，而不是追逐",
            "问自己：这是你的分析，还是别人的热情？",
        ],
    },
}


class PsychologyCoach:
    """
    Trading psychology coach.

    Analyzes trading behavior and provides psychological guidance
    to help traders maintain discipline and emotional balance.
    """

    # Thresholds for triggers
    OVERTRADING_THRESHOLD = 5  # Trades per day
    CONSECUTIVE_LOSS_THRESHOLD = 3  # Consecutive losing trades
    DAILY_LOSS_THRESHOLD = 0.05  # 5% daily loss
    CONCENTRATION_THRESHOLD = 0.25  # 25% single position
    LARGE_LOSS_THRESHOLD = 0.15  # 15% single trade loss

    def __init__(self):
        """Initialize psychology coach."""
        pass

    def analyze_trade_patterns(
        self,
        trades: list,  # List of Trade objects
        days: int = 30,
    ) -> TradePattern:
        """
        Analyze trading patterns from trade history.

        Args:
            trades: List of trade records
            days: Analysis period in days

        Returns:
            TradePattern with analyzed data
        """
        if not trades:
            return TradePattern(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                consecutive_losses=0,
                consecutive_wins=0,
                avg_hold_days=0,
                largest_loss_pct=0,
                largest_win_pct=0,
            )

        cutoff_date = datetime.now() - timedelta(days=days)

        # Filter trades within period
        recent_trades = [
            t for t in trades if t.trade_time and t.trade_time >= cutoff_date
        ]

        if not recent_trades:
            return TradePattern(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                consecutive_losses=0,
                consecutive_wins=0,
                avg_hold_days=0,
                largest_loss_pct=0,
                largest_win_pct=0,
            )

        # Count daily trades
        daily_counts: dict[date, int] = {}
        for trade in recent_trades:
            trade_date = trade.trade_time.date()
            daily_counts[trade_date] = daily_counts.get(trade_date, 0) + 1

        # Calculate P&L by grouping buy/sell pairs (simplified)
        # In real implementation, would need to match buy-sell pairs
        total = len(recent_trades)
        buys = [t for t in recent_trades if t.trd_side == "BUY"]
        sells = [t for t in recent_trades if t.trd_side == "SELL"]

        # Simplified win/loss estimation (actual implementation needs P&L tracking)
        # Here we just use trade count for pattern detection
        winning = len(sells) // 2  # Rough estimate
        losing = len(sells) - winning

        return TradePattern(
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            consecutive_losses=0,  # Would need actual P&L data
            consecutive_wins=0,
            avg_hold_days=0,  # Would need buy-sell pair matching
            largest_loss_pct=0,
            largest_win_pct=0,
            daily_trade_count=daily_counts,
        )

    def detect_behavior_patterns(
        self,
        trade_pattern: TradePattern,
        positions: list = None,  # List of PositionData
        total_portfolio_value: Decimal = None,
    ) -> BehaviorAnalysis:
        """
        Detect problematic trading behavior patterns.

        Args:
            trade_pattern: Analyzed trade patterns
            positions: Current positions
            total_portfolio_value: Total portfolio value

        Returns:
            BehaviorAnalysis with detected patterns
        """
        patterns = []
        observations = []
        coaching_points = []

        # Check overtrading
        max_daily_trades = (
            max(trade_pattern.daily_trade_count.values())
            if trade_pattern.daily_trade_count
            else 0
        )
        if max_daily_trades >= self.OVERTRADING_THRESHOLD:
            patterns.append(BehaviorPattern.OVERTRADING)
            observations.append(f"单日最高交易 {max_daily_trades} 次，超过建议的 5 次上限")
            coaching_points.append("频繁交易通常反映情绪驱动，建议设置每日交易上限")

        # Check consecutive losses
        if trade_pattern.consecutive_losses >= self.CONSECUTIVE_LOSS_THRESHOLD:
            patterns.append(BehaviorPattern.REVENGE_TRADING)
            observations.append(f"连续亏损 {trade_pattern.consecutive_losses} 次")
            coaching_points.append("连续亏损后建议暂停交易，进行复盘")

        # Check position concentration
        if positions and total_portfolio_value and total_portfolio_value > 0:
            for pos in positions:
                pct = float(pos.market_val / total_portfolio_value)
                if pct >= self.CONCENTRATION_THRESHOLD:
                    patterns.append(BehaviorPattern.CONCENTRATION_RISK)
                    observations.append(
                        f"{pos.stock_name or pos.code} 占比 {pct*100:.1f}%，过度集中"
                    )
                    coaching_points.append("单一持仓不应超过组合的 20%，考虑分散风险")
                    break

        # Check holding losers
        if positions:
            deep_losses = [
                p for p in positions if p.pl_ratio and float(p.pl_ratio) < -15
            ]
            if deep_losses:
                patterns.append(BehaviorPattern.HOLDING_LOSERS)
                names = [p.stock_name or p.code for p in deep_losses[:3]]
                observations.append(f"持有深度亏损仓位: {', '.join(names)}")
                coaching_points.append("考虑是否应该止损，资金是否有更好的去处")

        # Determine risk level
        if len(patterns) >= 3:
            risk_level = "high"
        elif len(patterns) >= 1:
            risk_level = "medium"
        else:
            risk_level = "low"

        return BehaviorAnalysis(
            patterns_detected=patterns,
            risk_level=risk_level,
            observations=observations,
            coaching_points=coaching_points,
        )

    def assess_emotion(
        self,
        behavior_analysis: BehaviorAnalysis,
        recent_pl_pct: float = 0,
    ) -> EmotionAssessment:
        """
        Assess trader's emotional state based on behavior and results.

        Args:
            behavior_analysis: Behavior analysis results
            recent_pl_pct: Recent P&L percentage

        Returns:
            EmotionAssessment with emotion type and recommendations
        """
        triggers = []
        recommendations = []

        # Determine dominant emotion
        if BehaviorPattern.REVENGE_TRADING in behavior_analysis.patterns_detected:
            emotion = EmotionType.FEAR
            intensity = 0.8
            triggers.append("连续亏损引发情绪反应")
            recommendations.append("暂停交易，进行情绪管理")
        elif BehaviorPattern.FOMO in behavior_analysis.patterns_detected:
            emotion = EmotionType.GREED
            intensity = 0.7
            triggers.append("追涨行为反映 FOMO 心理")
            recommendations.append("记住：好机会需要等待，不是追逐")
        elif BehaviorPattern.OVERTRADING in behavior_analysis.patterns_detected:
            emotion = EmotionType.OVERCONFIDENCE
            intensity = 0.6
            triggers.append("频繁交易可能反映过度自信")
            recommendations.append("每笔交易前问自己：这是计划内的吗？")
        elif BehaviorPattern.HOLDING_LOSERS in behavior_analysis.patterns_detected:
            emotion = EmotionType.HOPE
            intensity = 0.7
            triggers.append("持有深度亏损反映侥幸心理")
            recommendations.append("接受错误，及时止损是成熟的表现")
        elif recent_pl_pct < -5:
            emotion = EmotionType.PANIC
            intensity = 0.8
            triggers.append(f"单日亏损 {abs(recent_pl_pct):.1f}% 可能引发恐慌")
            recommendations.append("深呼吸，这只是一天，长期才是关键")
        elif recent_pl_pct > 10:
            emotion = EmotionType.EUPHORIA
            intensity = 0.6
            triggers.append(f"大幅盈利 {recent_pl_pct:.1f}% 可能导致过度乐观")
            recommendations.append("保持警惕，盈利时也要遵守纪律")
        else:
            emotion = EmotionType.NEUTRAL
            intensity = 0.2
            recommendations.append("保持当前状态，继续按计划执行")

        return EmotionAssessment(
            emotion=emotion,
            intensity=intensity,
            triggers=triggers,
            recommendations=recommendations,
        )

    def get_intervention(
        self,
        pattern: BehaviorPattern,
        **kwargs,
    ) -> dict:
        """
        Get intervention content for a behavior pattern.

        Args:
            pattern: Detected behavior pattern
            **kwargs: Additional parameters for message formatting

        Returns:
            Dict with title, message, and advice
        """
        template = INTERVENTION_TEMPLATES.get(
            pattern,
            {
                "title": "行为提醒",
                "message": "检测到可能需要注意的交易行为模式。",
                "advice": ["建议复盘最近的交易决策", "保持冷静和纪律"],
            },
        )

        message = template["message"]
        try:
            message = message.format(**kwargs)
        except KeyError:
            pass

        return {
            "title": template["title"],
            "message": message,
            "advice": template["advice"],
        }

    def get_random_quote(self) -> tuple[str, str]:
        """
        Get a random trading wisdom quote.

        Returns:
            Tuple of (author, quote)
        """
        return random.choice(TRADING_QUOTES)

    def generate_psychology_check(
        self,
        behavior_analysis: BehaviorAnalysis,
        emotion_assessment: EmotionAssessment,
    ) -> str:
        """
        Generate a psychology check report.

        Args:
            behavior_analysis: Behavior analysis results
            emotion_assessment: Emotion assessment results

        Returns:
            Markdown formatted report
        """
        lines = []
        lines.append("# 交易心理检查报告")
        lines.append("")

        # Quote
        author, quote = self.get_random_quote()
        lines.append(f"> \"{quote}\" - {author}")
        lines.append("")

        # Emotion status
        emotion_names = {
            EmotionType.FEAR: "恐惧",
            EmotionType.GREED: "贪婪",
            EmotionType.HOPE: "侥幸",
            EmotionType.REGRET: "后悔",
            EmotionType.OVERCONFIDENCE: "过度自信",
            EmotionType.PANIC: "恐慌",
            EmotionType.EUPHORIA: "狂喜",
            EmotionType.NEUTRAL: "平静",
        }

        lines.append("## 情绪状态")
        lines.append("")
        emotion_name = emotion_names.get(emotion_assessment.emotion, "未知")
        intensity_desc = (
            "强烈" if emotion_assessment.intensity > 0.7 else
            "中等" if emotion_assessment.intensity > 0.4 else
            "轻微"
        )
        lines.append(f"**当前情绪**: {emotion_name} ({intensity_desc})")
        lines.append("")

        if emotion_assessment.triggers:
            lines.append("**触发因素**:")
            for trigger in emotion_assessment.triggers:
                lines.append(f"- {trigger}")
            lines.append("")

        # Behavior patterns
        lines.append("## 行为模式分析")
        lines.append("")
        lines.append(f"**风险等级**: {behavior_analysis.risk_level.upper()}")
        lines.append("")

        if behavior_analysis.patterns_detected:
            pattern_names = {
                BehaviorPattern.OVERTRADING: "频繁交易",
                BehaviorPattern.LOSS_CHASING: "追涨杀跌",
                BehaviorPattern.REVENGE_TRADING: "报复性交易",
                BehaviorPattern.POSITION_AVERAGING: "摊薄成本",
                BehaviorPattern.PREMATURE_EXIT: "过早离场",
                BehaviorPattern.HOLDING_LOSERS: "死扛亏损",
                BehaviorPattern.CONCENTRATION_RISK: "仓位集中",
                BehaviorPattern.FOMO: "FOMO",
            }
            lines.append("**检测到的模式**:")
            for pattern in behavior_analysis.patterns_detected:
                name = pattern_names.get(pattern, pattern.value)
                lines.append(f"- {name}")
            lines.append("")

        if behavior_analysis.observations:
            lines.append("**观察**:")
            for obs in behavior_analysis.observations:
                lines.append(f"- {obs}")
            lines.append("")

        # Coaching points
        lines.append("## 教练建议")
        lines.append("")

        all_recommendations = (
            emotion_assessment.recommendations + behavior_analysis.coaching_points
        )
        for rec in all_recommendations:
            lines.append(f"- {rec}")
        lines.append("")

        # Intervention if needed
        if behavior_analysis.patterns_detected:
            lines.append("## 具体指导")
            lines.append("")
            for pattern in behavior_analysis.patterns_detected[:2]:  # Top 2
                intervention = self.get_intervention(pattern)
                lines.append(f"### {intervention['title']}")
                lines.append("")
                lines.append(intervention["message"])
                lines.append("")
                lines.append("**建议行动**:")
                for advice in intervention["advice"]:
                    lines.append(f"1. {advice}")
                lines.append("")

        return "\n".join(lines)

    def get_daily_affirmation(self) -> str:
        """
        Get a daily trading affirmation.

        Returns:
            Affirmation text
        """
        affirmations = [
            "我按计划交易，不被情绪左右。",
            "止损是保护，不是失败。",
            "耐心等待是最有价值的技能。",
            "市场永远会有新的机会。",
            "我专注于过程，而非短期结果。",
            "复利需要时间，我愿意等待。",
            "错过机会好过错误入场。",
            "我接受亏损是交易的一部分。",
            "纪律比预测更重要。",
            "我不需要每天都交易。",
        ]
        return random.choice(affirmations)
