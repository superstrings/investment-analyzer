"""
Pre-Market Analyzer for Market Observer Skill.

Generates pre-market analysis reports for trading preparation.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class GlobalMarketSnapshot:
    """Snapshot of global market performance."""

    # US Markets
    sp500_change: Optional[float] = None
    nasdaq_change: Optional[float] = None
    dow_change: Optional[float] = None

    # European Markets
    ftse_change: Optional[float] = None
    dax_change: Optional[float] = None

    # Asian Markets
    nikkei_change: Optional[float] = None
    kospi_change: Optional[float] = None
    hsi_change: Optional[float] = None

    # A-shares futures
    a50_change: Optional[float] = None

    # Commodities
    gold_change: Optional[float] = None
    oil_change: Optional[float] = None

    # Crypto
    btc_change: Optional[float] = None

    # FX
    usd_index_change: Optional[float] = None
    usd_cnh_change: Optional[float] = None


@dataclass
class EventInfo:
    """Market event information."""

    event_type: str  # earnings, economic, policy, ipo, dividend
    time: Optional[time] = None
    description: str = ""
    importance: str = "medium"  # low, medium, high
    affected_stocks: list[str] = field(default_factory=list)


@dataclass
class StockPreMarketInfo:
    """Pre-market information for a stock."""

    code: str
    stock_name: str
    prev_close: Decimal
    pre_market_price: Optional[Decimal] = None
    pre_market_change_pct: Optional[float] = None
    overnight_news: list[str] = field(default_factory=list)
    has_earnings: bool = False
    expected_move: str = ""  # up, down, flat, uncertain


@dataclass
class PreMarketReport:
    """Pre-market analysis report."""

    report_date: date
    market: str  # HK, US, A
    global_snapshot: GlobalMarketSnapshot
    market_outlook: str
    key_events: list[EventInfo]
    position_alerts: list[StockPreMarketInfo]
    watchlist_alerts: list[StockPreMarketInfo]
    trading_focus: list[str]
    risk_warnings: list[str]


class PreMarketAnalyzer:
    """
    Pre-market analyzer.

    Generates pre-market analysis reports to prepare for trading.
    """

    def __init__(self):
        """Initialize pre-market analyzer."""
        pass

    def analyze(
        self,
        market: str,
        positions: list,  # List of PositionData
        watchlist: list,  # List of WatchlistData
        global_snapshot: GlobalMarketSnapshot = None,
        events: list[EventInfo] = None,
        analysis_date: date = None,
    ) -> PreMarketReport:
        """
        Generate pre-market analysis report.

        Args:
            market: Target market (HK, US, A)
            positions: Current positions
            watchlist: Watchlist items
            global_snapshot: Global market data
            events: Known events for today
            analysis_date: Analysis date

        Returns:
            PreMarketReport
        """
        if analysis_date is None:
            analysis_date = date.today()

        if global_snapshot is None:
            global_snapshot = GlobalMarketSnapshot()

        if events is None:
            events = []

        # Generate market outlook
        market_outlook = self._generate_market_outlook(market, global_snapshot)

        # Analyze positions
        position_alerts = self._analyze_positions(positions, events)

        # Analyze watchlist
        watchlist_alerts = self._analyze_watchlist(watchlist, events)

        # Generate trading focus
        trading_focus = self._generate_trading_focus(
            market, global_snapshot, position_alerts, watchlist_alerts
        )

        # Generate risk warnings
        risk_warnings = self._generate_risk_warnings(
            global_snapshot, position_alerts
        )

        return PreMarketReport(
            report_date=analysis_date,
            market=market,
            global_snapshot=global_snapshot,
            market_outlook=market_outlook,
            key_events=events,
            position_alerts=position_alerts,
            watchlist_alerts=watchlist_alerts,
            trading_focus=trading_focus,
            risk_warnings=risk_warnings,
        )

    def _generate_market_outlook(
        self,
        market: str,
        snapshot: GlobalMarketSnapshot,
    ) -> str:
        """Generate market outlook based on global markets."""
        lines = []

        # Analyze overnight US markets (affects HK and A)
        if market in ("HK", "A"):
            us_sentiment = self._analyze_us_sentiment(snapshot)
            lines.append(f"**隔夜美股**: {us_sentiment}")

        # Analyze regional markets
        if market == "HK":
            if snapshot.a50_change is not None:
                a50_dir = "上涨" if snapshot.a50_change > 0 else "下跌"
                lines.append(f"**A50 期货**: {a50_dir} {abs(snapshot.a50_change):.1f}%")
        elif market == "A":
            if snapshot.hsi_change is not None:
                hsi_dir = "上涨" if snapshot.hsi_change > 0 else "下跌"
                lines.append(f"**恒指**: {hsi_dir} {abs(snapshot.hsi_change):.1f}%")

        # Commodities impact
        commodities_impact = self._analyze_commodities_impact(snapshot)
        if commodities_impact:
            lines.append(f"**商品市场**: {commodities_impact}")

        # FX impact
        if snapshot.usd_cnh_change is not None:
            fx_impact = self._analyze_fx_impact(snapshot)
            lines.append(f"**汇率**: {fx_impact}")

        return "\n".join(lines) if lines else "暂无全球市场数据"

    def _analyze_us_sentiment(self, snapshot: GlobalMarketSnapshot) -> str:
        """Analyze US market sentiment."""
        changes = []
        if snapshot.sp500_change is not None:
            changes.append(("标普500", snapshot.sp500_change))
        if snapshot.nasdaq_change is not None:
            changes.append(("纳斯达克", snapshot.nasdaq_change))
        if snapshot.dow_change is not None:
            changes.append(("道琼斯", snapshot.dow_change))

        if not changes:
            return "数据暂缺"

        avg_change = sum(c[1] for c in changes) / len(changes)

        parts = [f"{name} {change:+.1f}%" for name, change in changes]
        summary = ", ".join(parts)

        if avg_change > 1:
            sentiment = "强势上涨"
        elif avg_change > 0:
            sentiment = "小幅上涨"
        elif avg_change > -1:
            sentiment = "小幅下跌"
        else:
            sentiment = "大幅下跌"

        return f"{sentiment} ({summary})"

    def _analyze_commodities_impact(self, snapshot: GlobalMarketSnapshot) -> str:
        """Analyze commodities market impact."""
        impacts = []

        if snapshot.gold_change is not None:
            if abs(snapshot.gold_change) > 1:
                direction = "上涨" if snapshot.gold_change > 0 else "下跌"
                impacts.append(f"黄金{direction}{abs(snapshot.gold_change):.1f}%")

        if snapshot.oil_change is not None:
            if abs(snapshot.oil_change) > 2:
                direction = "上涨" if snapshot.oil_change > 0 else "下跌"
                impacts.append(f"原油{direction}{abs(snapshot.oil_change):.1f}%")

        return ", ".join(impacts) if impacts else ""

    def _analyze_fx_impact(self, snapshot: GlobalMarketSnapshot) -> str:
        """Analyze FX market impact."""
        if snapshot.usd_cnh_change is None:
            return ""

        if snapshot.usd_cnh_change > 0.3:
            return f"人民币贬值 {snapshot.usd_cnh_change:.1f}%，利好出口股"
        elif snapshot.usd_cnh_change < -0.3:
            return f"人民币升值 {abs(snapshot.usd_cnh_change):.1f}%，利好进口股"
        else:
            return "人民币汇率稳定"

    def _analyze_positions(
        self,
        positions: list,
        events: list[EventInfo],
    ) -> list[StockPreMarketInfo]:
        """Analyze positions for pre-market alerts."""
        alerts = []

        for pos in positions:
            # Check if position has related events
            has_earnings = any(
                pos.full_code in e.affected_stocks or pos.code in e.affected_stocks
                for e in events
                if e.event_type == "earnings"
            )

            news = []
            for event in events:
                if pos.full_code in event.affected_stocks or pos.code in event.affected_stocks:
                    news.append(event.description)

            alert = StockPreMarketInfo(
                code=pos.full_code,
                stock_name=pos.stock_name or "",
                prev_close=pos.market_price or Decimal("0"),
                has_earnings=has_earnings,
                overnight_news=news,
            )
            alerts.append(alert)

        return alerts

    def _analyze_watchlist(
        self,
        watchlist: list,
        events: list[EventInfo],
    ) -> list[StockPreMarketInfo]:
        """Analyze watchlist for pre-market alerts."""
        alerts = []

        for item in watchlist[:10]:  # Limit to top 10
            has_earnings = any(
                item.full_code in e.affected_stocks or item.code in e.affected_stocks
                for e in events
                if e.event_type == "earnings"
            )

            if has_earnings:
                alert = StockPreMarketInfo(
                    code=item.full_code,
                    stock_name=item.stock_name or "",
                    prev_close=Decimal("0"),
                    has_earnings=True,
                )
                alerts.append(alert)

        return alerts

    def _generate_trading_focus(
        self,
        market: str,
        snapshot: GlobalMarketSnapshot,
        position_alerts: list[StockPreMarketInfo],
        watchlist_alerts: list[StockPreMarketInfo],
    ) -> list[str]:
        """Generate trading focus points."""
        focus = []

        # Positions with events
        earnings_positions = [p for p in position_alerts if p.has_earnings]
        if earnings_positions:
            names = [p.stock_name or p.code for p in earnings_positions[:3]]
            focus.append(f"关注财报: {', '.join(names)}")

        # Global market direction
        us_avg = self._get_us_avg_change(snapshot)
        if us_avg is not None:
            if us_avg > 1:
                focus.append("美股强势，可关注科技股跟涨")
            elif us_avg < -1:
                focus.append("美股下跌，注意避险情绪传导")

        # Commodity plays
        if snapshot.gold_change is not None and snapshot.gold_change > 2:
            focus.append("黄金上涨，关注黄金股")
        if snapshot.oil_change is not None and snapshot.oil_change > 3:
            focus.append("原油上涨，关注油气股")

        if not focus:
            focus.append("按计划执行，关注个股机会")

        return focus

    def _generate_risk_warnings(
        self,
        snapshot: GlobalMarketSnapshot,
        position_alerts: list[StockPreMarketInfo],
    ) -> list[str]:
        """Generate risk warnings."""
        warnings = []

        # US market crash warning
        us_avg = self._get_us_avg_change(snapshot)
        if us_avg is not None and us_avg < -2:
            warnings.append(f"⚠️ 美股大跌 {us_avg:.1f}%，今日开盘可能低开")

        # Earnings volatility warning
        earnings_positions = [p for p in position_alerts if p.has_earnings]
        if earnings_positions:
            names = [p.stock_name or p.code for p in earnings_positions[:2]]
            warnings.append(f"⚠️ {', '.join(names)} 今日财报，注意波动风险")

        # Crypto crash (tech sentiment)
        if snapshot.btc_change is not None and snapshot.btc_change < -5:
            warnings.append("⚠️ 比特币大跌，可能影响科技股情绪")

        return warnings

    def _get_us_avg_change(self, snapshot: GlobalMarketSnapshot) -> Optional[float]:
        """Get average US market change."""
        changes = []
        if snapshot.sp500_change is not None:
            changes.append(snapshot.sp500_change)
        if snapshot.nasdaq_change is not None:
            changes.append(snapshot.nasdaq_change)

        if changes:
            return sum(changes) / len(changes)
        return None

    def generate_report(self, report: PreMarketReport) -> str:
        """
        Generate pre-market report in markdown format.

        Args:
            report: PreMarketReport data

        Returns:
            Markdown formatted report
        """
        market_names = {"HK": "港股", "US": "美股", "A": "A股"}
        market_name = market_names.get(report.market, report.market)

        lines = []
        lines.append(f"# {market_name}盘前分析")
        lines.append("")
        lines.append(f"日期: {report.report_date}")
        lines.append("")

        # Risk warnings first
        if report.risk_warnings:
            lines.append("## 风险提示")
            lines.append("")
            for warning in report.risk_warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Market outlook
        lines.append("## 市场概览")
        lines.append("")
        lines.append(report.market_outlook)
        lines.append("")

        # Key events
        if report.key_events:
            lines.append("## 今日重点")
            lines.append("")
            for event in report.key_events:
                importance_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(
                    event.importance, "⚪"
                )
                time_str = event.time.strftime("%H:%M") if event.time else ""
                lines.append(f"- {importance_icon} {time_str} {event.description}")
            lines.append("")

        # Position alerts
        if report.position_alerts:
            lines.append("## 持仓关注")
            lines.append("")
            for alert in report.position_alerts:
                status = "📊 财报" if alert.has_earnings else ""
                lines.append(f"- **{alert.code}** {alert.stock_name} {status}")
                for news in alert.overnight_news[:2]:
                    lines.append(f"  - {news}")
            lines.append("")

        # Trading focus
        if report.trading_focus:
            lines.append("## 今日关注")
            lines.append("")
            for focus in report.trading_focus:
                lines.append(f"- {focus}")
            lines.append("")

        return "\n".join(lines)
