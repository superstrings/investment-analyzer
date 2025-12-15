"""
Compound Interest Educator for Trading Coach Skill.

Teaches compound interest principles and calculates growth projections.
"""

import logging
import random
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CompoundProjection:
    """Compound interest projection result."""

    annual_return: float  # Annual return rate (e.g., 0.14 for 14%)
    years: int
    initial_capital: Decimal
    final_value: Decimal
    total_gain: Decimal
    multiplier: float  # How many times the initial capital

    # Year-by-year breakdown
    yearly_values: list[Decimal] = field(default_factory=list)


@dataclass
class TradingMath:
    """Trading mathematics calculation."""

    trades_per_year: int  # Number of trades per year
    win_rate: float  # Win rate (e.g., 0.6 for 60%)
    avg_profit_per_trade: float  # Average profit % per winning trade
    avg_loss_per_trade: float  # Average loss % per losing trade
    expected_annual_return: float  # Calculated expected annual return
    expected_multiplier_10y: float  # 10 year multiplier
    expected_multiplier_20y: float  # 20 year multiplier


@dataclass
class CompoundLesson:
    """A compound interest lesson with content."""

    title: str
    content: str
    key_insight: str
    example_calculation: Optional[str] = None


# Famous compound interest quotes
COMPOUND_QUOTES = [
    ("爱因斯坦", "复利是世界第八大奇迹。理解它的人赚取它，不理解它的人支付它。"),
    ("沃伦·巴菲特", "我的财富来源于美国、一些幸运基因和复利的结合。"),
    ("本杰明·富兰克林", "金钱生金钱，而它生的金钱又能生更多金钱。"),
    ("查理·芒格", "复利的第一条规则是：除非万不得已，永远不要打断它。"),
    ("彼得·林奇", "在股市中，时间是你最好的朋友，而冲动是你最大的敌人。"),
    ("霍华德·马克斯", "投资成功的秘诀是活得久、持有长。"),
    ("约翰·博格", "时间是你的朋友，冲动是你的敌人。利用复利的力量，避免市场择时的陷阱。"),
    ("李录", "真正的财富创造来自于长期持有优质资产，让复利发挥魔力。"),
]

# Multiplier reference table (years × annual return rate)
MULTIPLIER_TABLE = {
    # (years, return_rate): multiplier
    (10, 0.10): 2.59,
    (10, 0.14): 3.71,
    (10, 0.18): 5.23,
    (10, 0.20): 6.19,
    (10, 0.25): 9.31,
    (20, 0.10): 6.73,
    (20, 0.14): 13.74,
    (20, 0.18): 27.39,
    (20, 0.20): 38.34,
    (20, 0.25): 86.74,
    (25, 0.10): 10.83,
    (25, 0.14): 26.46,
    (25, 0.18): 62.67,
    (25, 0.20): 95.40,
    (25, 0.25): 264.70,
    (30, 0.10): 17.45,
    (30, 0.14): 50.95,
    (30, 0.18): 143.37,
    (30, 0.20): 237.38,
    (30, 0.25): 807.79,
}


class CompoundEducator:
    """
    Compound interest educator.

    Teaches compound interest principles and provides calculations
    to help traders understand long-term wealth building.
    """

    def __init__(self):
        """Initialize compound educator."""
        pass

    def calculate_compound_growth(
        self,
        initial_capital: Decimal,
        annual_return: float,
        years: int,
    ) -> CompoundProjection:
        """
        Calculate compound growth projection.

        Args:
            initial_capital: Starting capital
            annual_return: Annual return rate (e.g., 0.14 for 14%)
            years: Number of years

        Returns:
            CompoundProjection with yearly breakdown
        """
        yearly_values = []
        current_value = initial_capital

        for _ in range(years):
            yearly_values.append(current_value)
            current_value = current_value * Decimal(str(1 + annual_return))

        final_value = current_value
        total_gain = final_value - initial_capital
        multiplier = float(final_value / initial_capital) if initial_capital > 0 else 0

        return CompoundProjection(
            annual_return=annual_return,
            years=years,
            initial_capital=initial_capital,
            final_value=final_value.quantize(Decimal("0.01")),
            total_gain=total_gain.quantize(Decimal("0.01")),
            multiplier=round(multiplier, 2),
            yearly_values=[v.quantize(Decimal("0.01")) for v in yearly_values],
        )

    def calculate_trading_math(
        self,
        trades_per_year: int,
        win_rate: float,
        avg_profit: float,
        avg_loss: float,
    ) -> TradingMath:
        """
        Calculate expected returns based on trading statistics.

        Formula: E[R] = win_rate × avg_profit - (1 - win_rate) × avg_loss

        Args:
            trades_per_year: Number of trades per year
            win_rate: Win rate (0-1)
            avg_profit: Average profit per winning trade (e.g., 0.07 for 7%)
            avg_loss: Average loss per losing trade (e.g., 0.0233 for 2.33%)

        Returns:
            TradingMath with expected returns
        """
        # Expected return per trade
        expected_per_trade = win_rate * avg_profit - (1 - win_rate) * avg_loss

        # Annual return (compounded over trades)
        annual_return = (1 + expected_per_trade) ** trades_per_year - 1

        # Calculate multipliers
        multiplier_10y = (1 + annual_return) ** 10
        multiplier_20y = (1 + annual_return) ** 20

        return TradingMath(
            trades_per_year=trades_per_year,
            win_rate=win_rate,
            avg_profit_per_trade=avg_profit,
            avg_loss_per_trade=avg_loss,
            expected_annual_return=round(annual_return, 4),
            expected_multiplier_10y=round(multiplier_10y, 2),
            expected_multiplier_20y=round(multiplier_20y, 2),
        )

    def get_multiplier_table(self) -> dict[tuple[int, float], float]:
        """
        Get the compound multiplier reference table.

        Returns:
            Dict mapping (years, return_rate) to multiplier
        """
        return MULTIPLIER_TABLE.copy()

    def find_required_return(
        self,
        target_multiplier: float,
        years: int,
    ) -> float:
        """
        Find required annual return to achieve target multiplier.

        Args:
            target_multiplier: Target growth multiple (e.g., 10 for 10x)
            years: Investment period in years

        Returns:
            Required annual return rate
        """
        # Solve for r: (1 + r)^n = multiplier
        # r = multiplier^(1/n) - 1
        required_return = target_multiplier ** (1 / years) - 1
        return round(required_return, 4)

    def find_required_years(
        self,
        target_multiplier: float,
        annual_return: float,
    ) -> int:
        """
        Find required years to achieve target multiplier.

        Args:
            target_multiplier: Target growth multiple
            annual_return: Annual return rate

        Returns:
            Required years (rounded up)
        """
        import math

        # Solve for n: (1 + r)^n = multiplier
        # n = log(multiplier) / log(1 + r)
        if annual_return <= 0:
            return 999  # Infinite
        years = math.log(target_multiplier) / math.log(1 + annual_return)
        return math.ceil(years)

    def get_random_quote(self) -> tuple[str, str]:
        """
        Get a random compound interest quote.

        Returns:
            Tuple of (author, quote)
        """
        return random.choice(COMPOUND_QUOTES)

    def get_lesson(self, topic: str) -> CompoundLesson:
        """
        Get a compound interest lesson by topic.

        Args:
            topic: Lesson topic (time_value, power_of_waiting, start_early,
                   consistency, avoid_losses, patience)

        Returns:
            CompoundLesson with content
        """
        lessons = {
            "time_value": CompoundLesson(
                title="时间的价值",
                content="""
时间是复利最重要的变量。同样的年化收益率，投资30年和20年的结果天差地别。

以14%年化收益率为例：
- 10年：本金增长 3.7 倍
- 20年：本金增长 13.7 倍
- 30年：本金增长 50.9 倍

从20年到30年，仅多10年时间，收益却从13.7倍跃升到50.9倍！
这就是复利的"指数爆炸"阶段。
""".strip(),
                key_insight="复利的真正威力在后期爆发，耐心持有是成功的关键。",
                example_calculation="100万本金 × 14%年化 × 30年 = 5,095万",
            ),
            "power_of_waiting": CompoundLesson(
                title="等待的力量",
                content="""
巴菲特99%的财富是在50岁之后赚到的。这不是偶然，而是复利的必然结果。

假设从25岁开始投资，年化收益15%：
- 50岁（25年）：本金增长 32.9 倍
- 65岁（40年）：本金增长 267.9 倍
- 80岁（55年）：本金增长 2,179.6 倍

从50岁到80岁的30年，财富从32.9倍增长到2,179.6倍。
这就是为什么"活得久"在投资中如此重要。
""".strip(),
                key_insight="财富的大部分增长发生在投资生涯的后半段。",
            ),
            "start_early": CompoundLesson(
                title="早开始的优势",
                content="""
假设目标是65岁退休时积累1000万资产，年化收益12%：

- 25岁开始：每月只需投入 1,234 元
- 35岁开始：每月需要投入 3,748 元
- 45岁开始：每月需要投入 12,144 元

早10年开始，每月投入减少67%！
早20年开始，每月投入减少90%！

时间是免费的杠杆，越早使用越有利。
""".strip(),
                key_insight="最好的投资时机是十年前，其次是现在。",
            ),
            "consistency": CompoundLesson(
                title="一致性的威力",
                content="""
复利需要持续稳定的正收益，而非偶尔的大赚。

情景对比（10年投资期）：
- 方案A：每年稳定15%收益 → 最终 4.05 倍
- 方案B：偶尔大赚(+50%)但有几年亏损(-20%) → 最终可能只有 2-3 倍

更重要的是：
- 亏损50%需要盈利100%才能回本
- 亏损20%需要盈利25%才能回本

避免大亏损比追求大收益更重要！
""".strip(),
                key_insight="稳定复利 > 波动高收益。避免亏损是第一要务。",
            ),
            "avoid_losses": CompoundLesson(
                title="避免亏损的数学",
                content="""
亏损对复利的破坏是不对称的：

| 亏损幅度 | 需要盈利回本 |
|---------|-------------|
| -10%    | +11.1%      |
| -20%    | +25%        |
| -30%    | +42.9%      |
| -40%    | +66.7%      |
| -50%    | +100%       |

这就是为什么止损如此重要：
- 小亏损(8%)只需9%就能回本
- 大亏损(50%)需要翻倍才能回本

严格止损是保护复利的生命线。
""".strip(),
                key_insight="亏损的恢复成本呈指数增长，严格止损保护复利。",
            ),
            "patience": CompoundLesson(
                title="耐心的回报",
                content="""
为什么大多数人无法享受复利？

心理障碍：
1. 即时满足偏好：想要快速致富
2. 线性思维：低估后期的指数增长
3. 损失厌恶：无法承受短期波动
4. 频繁交易：打断复利过程

成功的复利投资者特点：
- 以年为单位思考，而非日/周
- 专注过程而非结果
- 接受"无聊"的等待
- 把波动视为机会而非威胁

"我们不是在等待市场做什么，我们是在等待时间发挥作用。"
""".strip(),
                key_insight="复利需要耐心，而耐心是最稀缺的投资资源。",
            ),
        }

        return lessons.get(
            topic,
            CompoundLesson(
                title="复利基础",
                content="复利是指将投资收益再投资，使本金和收益一起产生更多收益的过程。",
                key_insight="复利是财富增长的核心引擎。",
            ),
        )

    def generate_compound_report(
        self,
        initial_capital: Decimal,
        target_years: int = 20,
        scenarios: list[float] = None,
    ) -> str:
        """
        Generate a compound interest education report.

        Args:
            initial_capital: Starting capital
            target_years: Target investment period
            scenarios: List of annual return rates to compare

        Returns:
            Markdown formatted report
        """
        if scenarios is None:
            scenarios = [0.10, 0.14, 0.18, 0.20, 0.25]

        lines = []
        lines.append("# 复利教育报告")
        lines.append("")

        # Quote
        author, quote = self.get_random_quote()
        lines.append(f"> \"{quote}\" - {author}")
        lines.append("")

        # Projections table
        lines.append("## 复利增长预测")
        lines.append("")
        lines.append(f"初始本金: ¥{initial_capital:,.2f}")
        lines.append(f"投资期限: {target_years} 年")
        lines.append("")

        lines.append("| 年化收益率 | 最终价值 | 增长倍数 | 总收益 |")
        lines.append("|-----------|---------|---------|--------|")

        for rate in scenarios:
            projection = self.calculate_compound_growth(
                initial_capital, rate, target_years
            )
            lines.append(
                f"| {rate*100:.0f}% | ¥{projection.final_value:,.0f} | "
                f"{projection.multiplier:.1f}x | ¥{projection.total_gain:,.0f} |"
            )

        lines.append("")

        # Key insight
        lesson = self.get_lesson("time_value")
        lines.append("## 核心洞察")
        lines.append("")
        lines.append(f"**{lesson.key_insight}**")
        lines.append("")

        # Required returns to achieve targets
        lines.append("## 目标规划")
        lines.append("")
        lines.append("要实现财富目标，需要的年化收益率：")
        lines.append("")
        lines.append("| 目标倍数 | 10年需要 | 20年需要 | 30年需要 |")
        lines.append("|---------|---------|---------|---------|")

        for mult in [5, 10, 20, 50]:
            r10 = self.find_required_return(mult, 10)
            r20 = self.find_required_return(mult, 20)
            r30 = self.find_required_return(mult, 30)
            lines.append(f"| {mult}x | {r10*100:.1f}% | {r20*100:.1f}% | {r30*100:.1f}% |")

        lines.append("")

        # Trading math example
        lines.append("## 交易数学")
        lines.append("")
        lines.append("标准交易模型（参考）：")
        tm = self.calculate_trading_math(
            trades_per_year=10,
            win_rate=0.60,
            avg_profit=0.07,
            avg_loss=0.0233,
        )
        lines.append(f"- 年交易次数: {tm.trades_per_year}")
        lines.append(f"- 胜率: {tm.win_rate*100:.0f}%")
        lines.append(f"- 平均盈利: {tm.avg_profit_per_trade*100:.1f}%")
        lines.append(f"- 平均亏损: {tm.avg_loss_per_trade*100:.2f}%")
        lines.append(f"- **预期年化收益: {tm.expected_annual_return*100:.1f}%**")
        lines.append(f"- 10年预期倍数: {tm.expected_multiplier_10y:.1f}x")
        lines.append(f"- 20年预期倍数: {tm.expected_multiplier_20y:.1f}x")

        return "\n".join(lines)
