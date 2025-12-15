"""
Post-Market Summarizer for Market Observer Skill.

Generates post-market summary reports for daily review.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MarketSummary:
    """Summary of market performance."""

    market: str  # HK, US, A
    index_name: str  # e.g., "恒生指数", "上证指数"
    index_close: Decimal = Decimal("0")
    index_change: float = 0.0
    volume_change_pct: float = 0.0  # vs average
    advance_count: int = 0
    decline_count: int = 0
    unchanged_count: int = 0


@dataclass
class PositionDailySummary:
    """Daily summary for a position."""

    code: str
    stock_name: str
    open_price: Decimal
    close_price: Decimal
    high_price: Decimal
    low_price: Decimal
    daily_change_pct: float
    volume_ratio: float = 1.0  # Today volume / avg volume
    pl_contribution: Decimal = Decimal("0")  # P&L contribution in currency
    notes: list[str] = field(default_factory=list)


@dataclass
class TradeSummary:
    """Summary of today's trades."""

    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    total_buy_amount: Decimal = Decimal("0")
    total_sell_amount: Decimal = Decimal("0")
    net_cash_flow: Decimal = Decimal("0")
    trade_details: list[dict] = field(default_factory=list)


@dataclass
class AnomalyStock:
    """Stock with unusual activity."""

    code: str
    stock_name: str
    anomaly_type: str  # volume_spike, price_spike, gap_up, gap_down
    change_pct: float
    volume_ratio: float
    description: str


@dataclass
class PostMarketReport:
    """Post-market summary report."""

    report_date: date
    market: str
    market_summary: MarketSummary
    portfolio_change_pct: float
    portfolio_pl_today: Decimal
    position_summaries: list[PositionDailySummary]
    trade_summary: TradeSummary
    anomaly_stocks: list[AnomalyStock]
    tomorrow_focus: list[str]
    lessons_learned: list[str]


class PostMarketSummarizer:
    """
    Post-market summarizer.

    Generates end-of-day summary reports for review and planning.
    """

    def __init__(self):
        """Initialize post-market summarizer."""
        pass

    def summarize(
        self,
        market: str,
        positions: list,  # List of PositionData
        trades: list = None,  # Today's trades
        klines: dict = None,  # Dict of code -> today's kline
        market_summary: MarketSummary = None,
        summary_date: date = None,
    ) -> PostMarketReport:
        """
        Generate post-market summary report.

        Args:
            market: Market code (HK, US, A)
            positions: Current positions
            trades: Today's trades
            klines: Today's kline data by code
            market_summary: Market summary data
            summary_date: Summary date

        Returns:
            PostMarketReport
        """
        if summary_date is None:
            summary_date = date.today()

        if trades is None:
            trades = []

        if klines is None:
            klines = {}

        if market_summary is None:
            market_summary = self._create_default_market_summary(market)

        # Summarize positions
        position_summaries = self._summarize_positions(positions, klines)

        # Calculate portfolio change
        portfolio_pl_today = sum(p.pl_contribution for p in position_summaries)
        total_value = sum(p.market_val for p in positions) if positions else Decimal("0")
        portfolio_change_pct = 0.0
        if total_value > 0:
            portfolio_change_pct = float(portfolio_pl_today / total_value) * 100

        # Summarize trades
        trade_summary = self._summarize_trades(trades, summary_date)

        # Find anomaly stocks
        anomaly_stocks = self._find_anomalies(position_summaries)

        # Generate tomorrow's focus
        tomorrow_focus = self._generate_tomorrow_focus(
            market_summary, position_summaries, anomaly_stocks
        )

        # Generate lessons learned
        lessons_learned = self._generate_lessons(
            portfolio_change_pct, position_summaries, trade_summary
        )

        return PostMarketReport(
            report_date=summary_date,
            market=market,
            market_summary=market_summary,
            portfolio_change_pct=portfolio_change_pct,
            portfolio_pl_today=portfolio_pl_today,
            position_summaries=position_summaries,
            trade_summary=trade_summary,
            anomaly_stocks=anomaly_stocks,
            tomorrow_focus=tomorrow_focus,
            lessons_learned=lessons_learned,
        )

    def _create_default_market_summary(self, market: str) -> MarketSummary:
        """Create default market summary."""
        index_names = {
            "HK": "恒生指数",
            "US": "标普500",
            "A": "上证指数",
        }
        return MarketSummary(
            market=market,
            index_name=index_names.get(market, market),
        )

    def _summarize_positions(
        self,
        positions: list,
        klines: dict,
    ) -> list[PositionDailySummary]:
        """Summarize position performance."""
        summaries = []

        for pos in positions:
            kline = klines.get(pos.full_code) or klines.get(pos.code)

            if kline:
                daily_change = float(
                    (kline.close - kline.open) / kline.open * 100
                ) if kline.open > 0 else 0
                pl_contribution = (kline.close - kline.open) * pos.qty
                summary = PositionDailySummary(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    open_price=kline.open,
                    close_price=kline.close,
                    high_price=kline.high,
                    low_price=kline.low,
                    daily_change_pct=daily_change,
                    volume_ratio=1.0,  # Would need historical data
                    pl_contribution=pl_contribution,
                )
            else:
                # No kline data, use position data
                summary = PositionDailySummary(
                    code=pos.full_code,
                    stock_name=pos.stock_name or "",
                    open_price=pos.market_price or Decimal("0"),
                    close_price=pos.market_price or Decimal("0"),
                    high_price=pos.market_price or Decimal("0"),
                    low_price=pos.market_price or Decimal("0"),
                    daily_change_pct=0.0,
                    pl_contribution=Decimal("0"),
                )

            # Add notes based on performance
            if summary.daily_change_pct > 5:
                summary.notes.append("大涨，关注是否止盈")
            elif summary.daily_change_pct < -5:
                summary.notes.append("大跌，检查止损位")

            summaries.append(summary)

        return summaries

    def _summarize_trades(
        self,
        trades: list,
        trade_date: date,
    ) -> TradeSummary:
        """Summarize today's trades."""
        today_trades = [
            t for t in trades
            if hasattr(t, "trade_time") and t.trade_time.date() == trade_date
        ]

        if not today_trades:
            return TradeSummary()

        buy_trades = [t for t in today_trades if t.trd_side == "BUY"]
        sell_trades = [t for t in today_trades if t.trd_side == "SELL"]

        total_buy = sum(t.price * t.qty for t in buy_trades)
        total_sell = sum(t.price * t.qty for t in sell_trades)

        trade_details = []
        for t in today_trades:
            trade_details.append({
                "time": t.trade_time.strftime("%H:%M"),
                "code": f"{t.market}.{t.code}",
                "side": t.trd_side,
                "qty": float(t.qty),
                "price": float(t.price),
            })

        return TradeSummary(
            total_trades=len(today_trades),
            buy_trades=len(buy_trades),
            sell_trades=len(sell_trades),
            total_buy_amount=total_buy,
            total_sell_amount=total_sell,
            net_cash_flow=total_sell - total_buy,
            trade_details=trade_details,
        )

    def _find_anomalies(
        self,
        position_summaries: list[PositionDailySummary],
    ) -> list[AnomalyStock]:
        """Find stocks with unusual activity."""
        anomalies = []

        for pos in position_summaries:
            # Price spike
            if abs(pos.daily_change_pct) > 5:
                direction = "大涨" if pos.daily_change_pct > 0 else "大跌"
                anomalies.append(AnomalyStock(
                    code=pos.code,
                    stock_name=pos.stock_name,
                    anomaly_type="price_spike",
                    change_pct=pos.daily_change_pct,
                    volume_ratio=pos.volume_ratio,
                    description=f"{direction} {abs(pos.daily_change_pct):.1f}%",
                ))

            # Volume spike
            if pos.volume_ratio > 2:
                anomalies.append(AnomalyStock(
                    code=pos.code,
                    stock_name=pos.stock_name,
                    anomaly_type="volume_spike",
                    change_pct=pos.daily_change_pct,
                    volume_ratio=pos.volume_ratio,
                    description=f"放量 {pos.volume_ratio:.1f}倍",
                ))

        return anomalies

    def _generate_tomorrow_focus(
        self,
        market_summary: MarketSummary,
        position_summaries: list[PositionDailySummary],
        anomalies: list[AnomalyStock],
    ) -> list[str]:
        """Generate tomorrow's focus points."""
        focus = []

        # Market trend
        if market_summary.index_change > 2:
            focus.append("大盘强势，关注是否持续")
        elif market_summary.index_change < -2:
            focus.append("大盘弱势，控制仓位")

        # Big movers
        big_movers = [p for p in position_summaries if abs(p.daily_change_pct) > 3]
        if big_movers:
            for mover in big_movers[:2]:
                action = "关注止盈" if mover.daily_change_pct > 0 else "检查止损"
                focus.append(f"{mover.stock_name or mover.code}: {action}")

        # Anomalies
        for anomaly in anomalies[:2]:
            if anomaly.anomaly_type == "volume_spike":
                focus.append(f"{anomaly.stock_name}: 关注放量后续")

        if not focus:
            focus.append("保持观察，按计划执行")

        return focus

    def _generate_lessons(
        self,
        portfolio_change_pct: float,
        position_summaries: list[PositionDailySummary],
        trade_summary: TradeSummary,
    ) -> list[str]:
        """Generate lessons learned from today."""
        lessons = []

        # Portfolio performance
        if portfolio_change_pct > 3:
            lessons.append("✅ 今日组合表现良好，保持纪律")
        elif portfolio_change_pct < -3:
            lessons.append("⚠️ 今日组合回撤较大，复盘止损执行情况")

        # Trading activity
        if trade_summary.total_trades > 5:
            lessons.append("⚠️ 今日交易较频繁，检查是否情绪驱动")
        elif trade_summary.total_trades == 0:
            lessons.append("✅ 今日无交易，保持耐心是美德")

        # Big losers
        big_losers = [p for p in position_summaries if p.daily_change_pct < -5]
        if big_losers:
            for loser in big_losers[:1]:
                lessons.append(f"📉 {loser.stock_name or loser.code} 跌幅较大，检查是否应该止损")

        return lessons

    def generate_report(self, report: PostMarketReport) -> str:
        """
        Generate post-market report in markdown format.

        Args:
            report: PostMarketReport data

        Returns:
            Markdown formatted report
        """
        market_names = {"HK": "港股", "US": "美股", "A": "A股"}
        market_name = market_names.get(report.market, report.market)

        lines = []
        lines.append(f"# {market_name}盘后总结")
        lines.append("")
        lines.append(f"日期: {report.report_date}")
        lines.append("")

        # Portfolio summary
        pl_sign = "+" if report.portfolio_pl_today >= 0 else ""
        change_sign = "+" if report.portfolio_change_pct >= 0 else ""
        emoji = "📈" if report.portfolio_change_pct >= 0 else "📉"

        lines.append("## 组合概览")
        lines.append("")
        lines.append(f"**今日盈亏**: {emoji} {pl_sign}{report.portfolio_pl_today:,.0f}")
        lines.append(f"**涨跌幅**: {change_sign}{report.portfolio_change_pct:.2f}%")
        lines.append("")

        # Market summary
        ms = report.market_summary
        lines.append("## 市场表现")
        lines.append("")
        idx_sign = "+" if ms.index_change >= 0 else ""
        lines.append(f"**{ms.index_name}**: {idx_sign}{ms.index_change:.2f}%")
        if ms.advance_count > 0 or ms.decline_count > 0:
            lines.append(f"涨: {ms.advance_count} | 跌: {ms.decline_count} | 平: {ms.unchanged_count}")
        lines.append("")

        # Position performance
        if report.position_summaries:
            lines.append("## 持仓表现")
            lines.append("")
            lines.append("| 代码 | 名称 | 涨跌 | 备注 |")
            lines.append("|------|------|------|------|")
            for pos in sorted(
                report.position_summaries,
                key=lambda x: x.daily_change_pct,
                reverse=True,
            ):
                change_str = f"{pos.daily_change_pct:+.1f}%"
                notes = ", ".join(pos.notes) if pos.notes else "-"
                lines.append(f"| {pos.code} | {pos.stock_name} | {change_str} | {notes} |")
            lines.append("")

        # Trade summary
        if report.trade_summary.total_trades > 0:
            ts = report.trade_summary
            lines.append("## 今日交易")
            lines.append("")
            lines.append(f"- 交易笔数: {ts.total_trades} (买入 {ts.buy_trades}, 卖出 {ts.sell_trades})")
            lines.append(f"- 买入金额: ¥{ts.total_buy_amount:,.0f}")
            lines.append(f"- 卖出金额: ¥{ts.total_sell_amount:,.0f}")
            lines.append(f"- 净现金流: ¥{ts.net_cash_flow:+,.0f}")
            lines.append("")

        # Anomalies
        if report.anomaly_stocks:
            lines.append("## 异动提醒")
            lines.append("")
            for anomaly in report.anomaly_stocks:
                lines.append(f"- **{anomaly.code}** {anomaly.stock_name}: {anomaly.description}")
            lines.append("")

        # Tomorrow focus
        if report.tomorrow_focus:
            lines.append("## 明日关注")
            lines.append("")
            for focus in report.tomorrow_focus:
                lines.append(f"- {focus}")
            lines.append("")

        # Lessons learned
        if report.lessons_learned:
            lines.append("## 经验总结")
            lines.append("")
            for lesson in report.lessons_learned:
                lines.append(f"- {lesson}")
            lines.append("")

        return "\n".join(lines)
