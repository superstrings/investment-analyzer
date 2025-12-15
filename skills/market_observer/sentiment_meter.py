"""
Sentiment Meter for Market Observer Skill.

Calculates market sentiment score based on multiple indicators.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class SentimentLevel(Enum):
    """Market sentiment levels."""

    EXTREME_FEAR = "extreme_fear"  # 0-20
    FEAR = "fear"  # 20-40
    NEUTRAL = "neutral"  # 40-60
    GREED = "greed"  # 60-80
    EXTREME_GREED = "extreme_greed"  # 80-100


@dataclass
class MarketIndicators:
    """Market indicators for sentiment calculation."""

    # Price indicators
    advance_decline_ratio: float = 0.5  # Advancing / (Advancing + Declining)
    new_high_low_ratio: float = 0.5  # New Highs / (New Highs + New Lows)
    above_ma20_pct: float = 0.5  # % of stocks above MA20

    # Volume indicators
    up_volume_ratio: float = 0.5  # Up volume / Total volume
    avg_volume_change: float = 0.0  # % change from average volume

    # Volatility indicators
    vix_value: Optional[float] = None  # VIX index value
    market_change_pct: float = 0.0  # Index daily change %

    # Optional: margin/leverage indicators
    margin_balance_change: Optional[float] = None  # Margin balance change %


@dataclass
class SentimentResult:
    """Market sentiment analysis result."""

    score: float  # 0-100
    level: SentimentLevel
    calculation_date: date
    components: dict[str, float]  # Individual component scores
    interpretation: str
    trading_implication: str


# VIX level interpretation
VIX_LEVELS = {
    (0, 12): ("极低", "市场过度乐观，可能回调"),
    (12, 17): ("低", "市场平静，适合持有"),
    (17, 25): ("中等", "正常波动，保持警惕"),
    (25, 35): ("高", "市场恐慌，可能出现机会"),
    (35, 100): ("极高", "极度恐慌，历史性机会"),
}


class SentimentMeter:
    """
    Market sentiment meter.

    Calculates market sentiment score (0-100) based on multiple indicators.
    """

    # Component weights
    WEIGHTS = {
        "advance_decline": 0.20,
        "new_high_low": 0.15,
        "above_ma": 0.15,
        "volume": 0.15,
        "vix": 0.20,
        "market_change": 0.15,
    }

    def __init__(self):
        """Initialize sentiment meter."""
        pass

    def calculate_sentiment(
        self,
        indicators: MarketIndicators,
        calculation_date: date = None,
    ) -> SentimentResult:
        """
        Calculate market sentiment score.

        Args:
            indicators: Market indicators
            calculation_date: Date of calculation

        Returns:
            SentimentResult with score and interpretation
        """
        if calculation_date is None:
            calculation_date = date.today()

        components = {}

        # Advance/Decline ratio (0-1 -> 0-100)
        ad_score = indicators.advance_decline_ratio * 100
        components["advance_decline"] = ad_score

        # New High/Low ratio (0-1 -> 0-100)
        hl_score = indicators.new_high_low_ratio * 100
        components["new_high_low"] = hl_score

        # Above MA20 % (0-1 -> 0-100)
        ma_score = indicators.above_ma20_pct * 100
        components["above_ma"] = ma_score

        # Volume analysis (up volume ratio)
        volume_score = indicators.up_volume_ratio * 100
        components["volume"] = volume_score

        # VIX interpretation (inverted: high VIX = low sentiment)
        if indicators.vix_value is not None:
            vix_score = self._vix_to_sentiment(indicators.vix_value)
        else:
            vix_score = 50  # Neutral if no VIX data
        components["vix"] = vix_score

        # Market change (map -5% to +5% -> 0 to 100)
        change_score = self._change_to_sentiment(indicators.market_change_pct)
        components["market_change"] = change_score

        # Calculate weighted average
        total_score = sum(
            components[key] * self.WEIGHTS[key] for key in self.WEIGHTS
        )

        # Determine level
        level = self._score_to_level(total_score)

        # Generate interpretation
        interpretation = self._generate_interpretation(total_score, level, components)
        trading_implication = self._generate_trading_implication(total_score, level)

        return SentimentResult(
            score=round(total_score, 1),
            level=level,
            calculation_date=calculation_date,
            components=components,
            interpretation=interpretation,
            trading_implication=trading_implication,
        )

    def _vix_to_sentiment(self, vix: float) -> float:
        """
        Convert VIX to sentiment score.

        High VIX (fear) -> Low sentiment score
        Low VIX (greed) -> High sentiment score

        Args:
            vix: VIX index value

        Returns:
            Sentiment score (0-100)
        """
        # Map VIX: 10 -> 90, 20 -> 60, 30 -> 30, 40 -> 10
        if vix <= 10:
            return 95
        elif vix <= 12:
            return 85
        elif vix <= 15:
            return 75
        elif vix <= 18:
            return 65
        elif vix <= 22:
            return 50
        elif vix <= 25:
            return 40
        elif vix <= 30:
            return 30
        elif vix <= 35:
            return 20
        elif vix <= 40:
            return 15
        else:
            return 10

    def _change_to_sentiment(self, change_pct: float) -> float:
        """
        Convert market change to sentiment score.

        Args:
            change_pct: Market change percentage

        Returns:
            Sentiment score (0-100)
        """
        # Map: -5% -> 0, 0% -> 50, +5% -> 100
        score = 50 + (change_pct * 10)
        return max(0, min(100, score))

    def _score_to_level(self, score: float) -> SentimentLevel:
        """Convert score to sentiment level."""
        if score < 20:
            return SentimentLevel.EXTREME_FEAR
        elif score < 40:
            return SentimentLevel.FEAR
        elif score < 60:
            return SentimentLevel.NEUTRAL
        elif score < 80:
            return SentimentLevel.GREED
        else:
            return SentimentLevel.EXTREME_GREED

    def _generate_interpretation(
        self,
        score: float,
        level: SentimentLevel,
        components: dict[str, float],
    ) -> str:
        """Generate interpretation text."""
        level_names = {
            SentimentLevel.EXTREME_FEAR: "极度恐惧",
            SentimentLevel.FEAR: "恐惧",
            SentimentLevel.NEUTRAL: "中性",
            SentimentLevel.GREED: "贪婪",
            SentimentLevel.EXTREME_GREED: "极度贪婪",
        }

        # Find strongest signal
        max_component = max(components.items(), key=lambda x: abs(x[1] - 50))
        min_component = min(components.items(), key=lambda x: abs(x[1] - 50))

        component_names = {
            "advance_decline": "涨跌比",
            "new_high_low": "新高新低比",
            "above_ma": "站上均线比例",
            "volume": "成交量分布",
            "vix": "波动率指数",
            "market_change": "指数涨跌",
        }

        lines = []
        lines.append(f"市场情绪: {level_names[level]} ({score:.0f}/100)")
        lines.append(f"主要信号: {component_names[max_component[0]]} ({max_component[1]:.0f})")

        return "\n".join(lines)

    def _generate_trading_implication(
        self,
        score: float,
        level: SentimentLevel,
    ) -> str:
        """Generate trading implication."""
        implications = {
            SentimentLevel.EXTREME_FEAR: "历史表明极度恐惧时期往往是买入良机。考虑逐步建仓优质股票。",
            SentimentLevel.FEAR: "市场情绪偏悲观，但还未到极端。保持观望，准备逢低吸纳。",
            SentimentLevel.NEUTRAL: "市场情绪中性，按计划执行即可。关注个股机会。",
            SentimentLevel.GREED: "市场情绪偏乐观，注意风险。考虑部分止盈。",
            SentimentLevel.EXTREME_GREED: "市场过度乐观，风险较高。建议减仓或保持现金。",
        }
        return implications[level]

    def get_vix_interpretation(self, vix: float) -> tuple[str, str]:
        """
        Get VIX interpretation.

        Args:
            vix: VIX value

        Returns:
            Tuple of (level_name, interpretation)
        """
        for (low, high), (name, interpretation) in VIX_LEVELS.items():
            if low <= vix < high:
                return name, interpretation
        return "未知", "VIX 值异常"

    def generate_sentiment_report(
        self,
        result: SentimentResult,
        vix: Optional[float] = None,
    ) -> str:
        """
        Generate sentiment analysis report.

        Args:
            result: Sentiment result
            vix: Optional VIX value for detailed analysis

        Returns:
            Markdown formatted report
        """
        lines = []
        lines.append("# 市场情绪分析")
        lines.append("")
        lines.append(f"日期: {result.calculation_date}")
        lines.append("")

        # Sentiment gauge
        level_names = {
            SentimentLevel.EXTREME_FEAR: "极度恐惧 😱",
            SentimentLevel.FEAR: "恐惧 😰",
            SentimentLevel.NEUTRAL: "中性 😐",
            SentimentLevel.GREED: "贪婪 🤑",
            SentimentLevel.EXTREME_GREED: "极度贪婪 🚀",
        }

        lines.append("## 情绪指数")
        lines.append("")
        lines.append(f"**{result.score:.0f}/100** - {level_names[result.level]}")
        lines.append("")

        # Visual gauge
        filled = int(result.score / 10)
        empty = 10 - filled
        gauge = "▓" * filled + "░" * empty
        lines.append(f"[{gauge}]")
        lines.append("")

        # Component breakdown
        lines.append("## 分项指标")
        lines.append("")
        component_names = {
            "advance_decline": "涨跌比",
            "new_high_low": "新高新低比",
            "above_ma": "站上均线比例",
            "volume": "成交量分布",
            "vix": "波动率指数",
            "market_change": "指数涨跌",
        }

        lines.append("| 指标 | 得分 | 权重 |")
        lines.append("|------|------|------|")
        for key, score in result.components.items():
            name = component_names.get(key, key)
            weight = self.WEIGHTS.get(key, 0) * 100
            lines.append(f"| {name} | {score:.0f} | {weight:.0f}% |")
        lines.append("")

        # VIX analysis if available
        if vix is not None:
            lines.append("## VIX 分析")
            lines.append("")
            vix_level, vix_interp = self.get_vix_interpretation(vix)
            lines.append(f"**VIX: {vix:.1f}** ({vix_level})")
            lines.append("")
            lines.append(f"{vix_interp}")
            lines.append("")

        # Interpretation
        lines.append("## 解读")
        lines.append("")
        lines.append(result.interpretation)
        lines.append("")

        # Trading implication
        lines.append("## 操作建议")
        lines.append("")
        lines.append(result.trading_implication)
        lines.append("")

        return "\n".join(lines)
