"""
Sector Rotation Analyzer for Market Observer Skill.

Analyzes sector performance and rotation patterns.
"""

import logging
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SectorPerformance:
    """Sector performance data."""

    sector_name: str
    sector_code: str
    change_1d: float = 0.0  # 1 day change %
    change_5d: float = 0.0  # 5 day change %
    change_20d: float = 0.0  # 20 day change %
    volume_ratio: float = 1.0  # Volume vs average
    stock_count: int = 0
    advancing_count: int = 0
    declining_count: int = 0
    top_gainers: list[tuple[str, float]] = field(default_factory=list)  # (code, change%)
    top_losers: list[tuple[str, float]] = field(default_factory=list)


@dataclass
class MoneyFlowData:
    """Sector money flow data."""

    sector_name: str
    net_inflow: Decimal = Decimal("0")  # Net inflow in currency
    main_inflow: Decimal = Decimal("0")  # Main force inflow
    retail_outflow: Decimal = Decimal("0")  # Retail outflow
    flow_trend: str = "neutral"  # inflow, outflow, neutral


@dataclass
class RotationSignal:
    """Sector rotation signal."""

    from_sector: str
    to_sector: str
    strength: str  # weak, medium, strong
    evidence: list[str]
    trading_idea: str


@dataclass
class SectorAnalysisReport:
    """Sector rotation analysis report."""

    report_date: date
    market: str
    top_sectors: list[SectorPerformance]  # Best performing
    bottom_sectors: list[SectorPerformance]  # Worst performing
    money_flow: list[MoneyFlowData]
    rotation_signals: list[RotationSignal]
    market_theme: str
    sector_recommendation: str


# Common sector definitions
SECTORS_HK = {
    "tech": "科技",
    "finance": "金融",
    "property": "房地产",
    "consumer": "消费",
    "healthcare": "医疗健康",
    "energy": "能源",
    "materials": "原材料",
    "industrials": "工业",
    "utilities": "公用事业",
    "telecom": "电信",
}

SECTORS_US = {
    "tech": "Technology",
    "finance": "Financials",
    "healthcare": "Healthcare",
    "consumer_disc": "Consumer Discretionary",
    "consumer_staples": "Consumer Staples",
    "energy": "Energy",
    "materials": "Materials",
    "industrials": "Industrials",
    "utilities": "Utilities",
    "real_estate": "Real Estate",
    "communication": "Communication Services",
}

SECTORS_A = {
    "tech": "信息技术",
    "finance": "金融",
    "property": "房地产",
    "consumer": "消费",
    "healthcare": "医药生物",
    "energy": "能源",
    "materials": "基础化工",
    "industrials": "机械设备",
    "utilities": "公用事业",
    "defense": "国防军工",
}


class SectorRotationAnalyzer:
    """
    Sector rotation analyzer.

    Analyzes sector performance, money flow, and rotation patterns.
    """

    def __init__(self):
        """Initialize sector rotation analyzer."""
        pass

    def analyze(
        self,
        market: str,
        sector_data: list[SectorPerformance] = None,
        money_flow_data: list[MoneyFlowData] = None,
        analysis_date: date = None,
    ) -> SectorAnalysisReport:
        """
        Analyze sector rotation.

        Args:
            market: Market code (HK, US, A)
            sector_data: Sector performance data
            money_flow_data: Money flow data
            analysis_date: Analysis date

        Returns:
            SectorAnalysisReport
        """
        if analysis_date is None:
            analysis_date = date.today()

        if sector_data is None:
            sector_data = []

        if money_flow_data is None:
            money_flow_data = []

        # Sort sectors by performance
        sorted_sectors = sorted(
            sector_data,
            key=lambda x: x.change_1d,
            reverse=True,
        )

        top_sectors = sorted_sectors[:5] if len(sorted_sectors) >= 5 else sorted_sectors
        bottom_sectors = sorted_sectors[-5:] if len(sorted_sectors) >= 5 else []

        # Detect rotation signals
        rotation_signals = self._detect_rotation_signals(
            sector_data, money_flow_data
        )

        # Generate market theme
        market_theme = self._identify_market_theme(top_sectors, bottom_sectors)

        # Generate sector recommendation
        recommendation = self._generate_recommendation(
            top_sectors, bottom_sectors, rotation_signals
        )

        return SectorAnalysisReport(
            report_date=analysis_date,
            market=market,
            top_sectors=top_sectors,
            bottom_sectors=bottom_sectors,
            money_flow=money_flow_data,
            rotation_signals=rotation_signals,
            market_theme=market_theme,
            sector_recommendation=recommendation,
        )

    def _detect_rotation_signals(
        self,
        sector_data: list[SectorPerformance],
        money_flow_data: list[MoneyFlowData],
    ) -> list[RotationSignal]:
        """Detect sector rotation signals."""
        signals = []

        if len(sector_data) < 2:
            return signals

        # Compare short-term vs longer-term performance
        for sector in sector_data:
            # Momentum shift detection
            if sector.change_1d > 2 and sector.change_20d < 0:
                # Potential new leader emerging
                signals.append(RotationSignal(
                    from_sector="前期热点",
                    to_sector=sector.sector_name,
                    strength="medium",
                    evidence=[
                        f"{sector.sector_name} 今日涨 {sector.change_1d:.1f}%",
                        f"近20日跌 {sector.change_20d:.1f}%，可能反转",
                    ],
                    trading_idea=f"关注 {sector.sector_name} 反转机会",
                ))
            elif sector.change_1d < -2 and sector.change_20d > 10:
                # Previous leader weakening
                signals.append(RotationSignal(
                    from_sector=sector.sector_name,
                    to_sector="待观察",
                    strength="weak",
                    evidence=[
                        f"{sector.sector_name} 今日跌 {sector.change_1d:.1f}%",
                        f"近20日涨 {sector.change_20d:.1f}%，可能获利回吐",
                    ],
                    trading_idea=f"警惕 {sector.sector_name} 回调风险",
                ))

        # Money flow based signals
        for flow in money_flow_data:
            if flow.net_inflow > 0 and flow.flow_trend == "inflow":
                matching_sector = next(
                    (s for s in sector_data if s.sector_name == flow.sector_name),
                    None,
                )
                if matching_sector and matching_sector.change_1d > 0:
                    signals.append(RotationSignal(
                        from_sector="其他板块",
                        to_sector=flow.sector_name,
                        strength="medium" if flow.net_inflow > 1000000000 else "weak",
                        evidence=[
                            f"资金净流入 {flow.net_inflow/100000000:.1f}亿",
                            f"价格上涨 {matching_sector.change_1d:.1f}%",
                        ],
                        trading_idea=f"资金正在流入 {flow.sector_name}",
                    ))

        return signals[:5]  # Limit to top 5 signals

    def _identify_market_theme(
        self,
        top_sectors: list[SectorPerformance],
        bottom_sectors: list[SectorPerformance],
    ) -> str:
        """Identify market theme based on sector performance."""
        if not top_sectors:
            return "市场方向不明，观望为主"

        # Identify theme based on leading sectors
        top_names = [s.sector_name.lower() for s in top_sectors[:3]]

        if any("科技" in n or "tech" in n for n in top_names):
            return "科技主导，成长风格"
        elif any("金融" in n or "finance" in n for n in top_names):
            return "金融领涨，价值回归"
        elif any("消费" in n or "consumer" in n for n in top_names):
            return "消费复苏，内需驱动"
        elif any("能源" in n or "energy" in n for n in top_names):
            return "能源强势，通胀交易"
        elif any("医疗" in n or "health" in n for n in top_names):
            return "医疗领先，防御配置"
        elif any("公用" in n or "util" in n for n in top_names):
            return "公用事业领涨，避险情绪"
        else:
            return "板块轮动中，关注热点切换"

    def _generate_recommendation(
        self,
        top_sectors: list[SectorPerformance],
        bottom_sectors: list[SectorPerformance],
        rotation_signals: list[RotationSignal],
    ) -> str:
        """Generate sector recommendation."""
        recommendations = []

        # Based on top sectors
        if top_sectors:
            top = top_sectors[0]
            if top.change_1d > 3:
                recommendations.append(f"关注 {top.sector_name} 板块延续性")
            elif top.change_1d > 1:
                recommendations.append(f"{top.sector_name} 表现较好，可适度关注")

        # Based on bottom sectors
        if bottom_sectors:
            bottom = bottom_sectors[-1]
            if bottom.change_1d < -3:
                if bottom.change_20d < -10:
                    recommendations.append(f"{bottom.sector_name} 持续弱势，暂时回避")
                else:
                    recommendations.append(f"{bottom.sector_name} 今日调整，观察是否超跌")

        # Based on rotation signals
        strong_signals = [s for s in rotation_signals if s.strength == "strong"]
        if strong_signals:
            recommendations.append(strong_signals[0].trading_idea)

        if not recommendations:
            return "市场板块分化不明显，保持观望"

        return " | ".join(recommendations[:3])

    def get_sector_mapping(self, market: str) -> dict[str, str]:
        """Get sector code to name mapping."""
        if market == "HK":
            return SECTORS_HK
        elif market == "US":
            return SECTORS_US
        elif market == "A":
            return SECTORS_A
        else:
            return SECTORS_HK

    def generate_report(self, report: SectorAnalysisReport) -> str:
        """
        Generate sector analysis report in markdown format.

        Args:
            report: SectorAnalysisReport data

        Returns:
            Markdown formatted report
        """
        market_names = {"HK": "港股", "US": "美股", "A": "A股"}
        market_name = market_names.get(report.market, report.market)

        lines = []
        lines.append(f"# {market_name}板块轮动分析")
        lines.append("")
        lines.append(f"日期: {report.report_date}")
        lines.append("")

        # Market theme
        lines.append("## 市场风格")
        lines.append("")
        lines.append(f"**{report.market_theme}**")
        lines.append("")

        # Top sectors
        if report.top_sectors:
            lines.append("## 强势板块 Top 5")
            lines.append("")
            lines.append("| 排名 | 板块 | 今日 | 5日 | 20日 |")
            lines.append("|------|------|------|------|------|")
            for i, sector in enumerate(report.top_sectors, 1):
                lines.append(
                    f"| {i} | {sector.sector_name} | "
                    f"{sector.change_1d:+.1f}% | "
                    f"{sector.change_5d:+.1f}% | "
                    f"{sector.change_20d:+.1f}% |"
                )
            lines.append("")

        # Bottom sectors
        if report.bottom_sectors:
            lines.append("## 弱势板块")
            lines.append("")
            lines.append("| 板块 | 今日 | 5日 | 20日 |")
            lines.append("|------|------|------|------|")
            for sector in reversed(report.bottom_sectors[-3:]):
                lines.append(
                    f"| {sector.sector_name} | "
                    f"{sector.change_1d:+.1f}% | "
                    f"{sector.change_5d:+.1f}% | "
                    f"{sector.change_20d:+.1f}% |"
                )
            lines.append("")

        # Money flow
        if report.money_flow:
            lines.append("## 资金流向")
            lines.append("")
            inflows = [f for f in report.money_flow if f.flow_trend == "inflow"]
            outflows = [f for f in report.money_flow if f.flow_trend == "outflow"]

            if inflows:
                lines.append("**资金流入**:")
                for flow in inflows[:3]:
                    lines.append(f"- {flow.sector_name}: {flow.net_inflow/100000000:+.1f}亿")
            if outflows:
                lines.append("**资金流出**:")
                for flow in outflows[:3]:
                    lines.append(f"- {flow.sector_name}: {flow.net_inflow/100000000:+.1f}亿")
            lines.append("")

        # Rotation signals
        if report.rotation_signals:
            lines.append("## 轮动信号")
            lines.append("")
            for signal in report.rotation_signals:
                strength_icon = {"strong": "🔴", "medium": "🟡", "weak": "🟢"}.get(
                    signal.strength, "⚪"
                )
                lines.append(f"### {strength_icon} {signal.from_sector} → {signal.to_sector}")
                for evidence in signal.evidence:
                    lines.append(f"- {evidence}")
                lines.append(f"- **建议**: {signal.trading_idea}")
                lines.append("")

        # Recommendation
        lines.append("## 操作建议")
        lines.append("")
        lines.append(report.sector_recommendation)
        lines.append("")

        return "\n".join(lines)
