"""
Backtest report generation.

Generates formatted reports from backtest results including
performance metrics, trade history, and equity curves.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from .strategy import BacktestResult, Trade


class ReportFormat(str, Enum):
    """Report output format."""

    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


def format_number(value: float, decimals: int = 2) -> str:
    """Format a number with thousands separator."""
    if abs(value) >= 1000:
        return f"{value:,.{decimals}f}"
    return f"{value:.{decimals}f}"


def format_percent(value: float, decimals: int = 2) -> str:
    """Format a percentage."""
    return f"{value * 100:.{decimals}f}%"


def format_pnl(value: float, decimals: int = 2) -> str:
    """Format PnL with sign."""
    sign = "+" if value >= 0 else ""
    return f"{sign}{format_number(value, decimals)}"


def generate_text_report(result: BacktestResult) -> str:
    """Generate a plain text backtest report.

    Args:
        result: Backtest result

    Returns:
        Formatted text report
    """
    lines = []
    m = result.metrics

    # Header
    lines.append("=" * 60)
    lines.append(f"回测报告: {result.strategy_name}")
    lines.append("=" * 60)
    lines.append("")

    # Basic info
    lines.append(f"股票代码: {result.symbol}")
    lines.append(
        f"回测周期: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}"
    )
    days = (result.end_date - result.start_date).days
    lines.append(f"回测天数: {days} 天")
    lines.append("")

    # Capital
    lines.append("-" * 40)
    lines.append("资金概况")
    lines.append("-" * 40)
    lines.append(f"初始资金: {format_number(result.initial_capital)}")
    lines.append(f"最终资金: {format_number(result.final_capital)}")
    lines.append(
        f"总收益:   {format_pnl(m.total_return)} ({format_percent(m.total_return_pct)})"
    )
    lines.append(f"年化收益: {format_percent(m.annualized_return)}")
    lines.append("")

    # Risk metrics
    lines.append("-" * 40)
    lines.append("风险指标")
    lines.append("-" * 40)
    lines.append(
        f"最大回撤: {format_number(m.max_drawdown)} ({format_percent(m.max_drawdown_pct)})"
    )
    lines.append(f"夏普比率: {m.sharpe_ratio:.2f}")
    lines.append(f"索提诺比率: {m.sortino_ratio:.2f}")
    lines.append(f"卡玛比率: {m.calmar_ratio:.2f}")
    lines.append("")

    # Trade statistics
    lines.append("-" * 40)
    lines.append("交易统计")
    lines.append("-" * 40)
    lines.append(f"总交易次数: {m.total_trades}")
    lines.append(f"盈利交易:   {m.winning_trades}")
    lines.append(f"亏损交易:   {m.losing_trades}")
    lines.append(f"胜率:       {format_percent(m.win_rate)}")
    lines.append(f"平均盈利:   {format_number(m.avg_win)}")
    lines.append(f"平均亏损:   {format_number(m.avg_loss)}")
    lines.append(f"盈亏比:     {m.profit_factor:.2f}")
    lines.append(f"期望值:     {format_number(m.expectancy)}")
    lines.append(f"平均持仓:   {m.avg_holding_days:.1f} 天")
    lines.append(f"最大连胜:   {m.max_consecutive_wins}")
    lines.append(f"最大连亏:   {m.max_consecutive_losses}")
    lines.append("")

    # Trade history
    if result.trades:
        lines.append("-" * 40)
        lines.append("交易记录")
        lines.append("-" * 40)
        for i, trade in enumerate(result.trades, 1):
            pnl_str = format_pnl(trade.pnl)
            pct_str = format_percent(trade.pnl_pct)
            lines.append(
                f"{i:3d}. {trade.entry_date.strftime('%Y-%m-%d')} -> "
                f"{trade.exit_date.strftime('%Y-%m-%d')} | "
                f"入场: {trade.entry_price:.2f} | "
                f"出场: {trade.exit_price:.2f} | "
                f"盈亏: {pnl_str} ({pct_str}) | "
                f"{trade.holding_days}天"
            )
        lines.append("")

    lines.append("=" * 60)
    lines.append(f"报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    return "\n".join(lines)


def generate_markdown_report(result: BacktestResult) -> str:
    """Generate a Markdown backtest report.

    Args:
        result: Backtest result

    Returns:
        Formatted Markdown report
    """
    lines = []
    m = result.metrics

    # Header
    lines.append(f"# 回测报告: {result.strategy_name}")
    lines.append("")
    lines.append(f"**股票代码**: {result.symbol}")
    lines.append(
        f"**回测周期**: {result.start_date.strftime('%Y-%m-%d')} ~ {result.end_date.strftime('%Y-%m-%d')}"
    )
    days = (result.end_date - result.start_date).days
    lines.append(f"**回测天数**: {days} 天")
    lines.append("")

    # Summary table
    lines.append("## 业绩摘要")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 初始资金 | {format_number(result.initial_capital)} |")
    lines.append(f"| 最终资金 | {format_number(result.final_capital)} |")
    lines.append(
        f"| 总收益 | {format_pnl(m.total_return)} ({format_percent(m.total_return_pct)}) |"
    )
    lines.append(f"| 年化收益 | {format_percent(m.annualized_return)} |")
    lines.append(f"| 最大回撤 | {format_percent(m.max_drawdown_pct)} |")
    lines.append(f"| 夏普比率 | {m.sharpe_ratio:.2f} |")
    lines.append("")

    # Risk metrics
    lines.append("## 风险指标")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 最大回撤金额 | {format_number(m.max_drawdown)} |")
    lines.append(f"| 最大回撤比例 | {format_percent(m.max_drawdown_pct)} |")
    lines.append(f"| 夏普比率 | {m.sharpe_ratio:.2f} |")
    lines.append(f"| 索提诺比率 | {m.sortino_ratio:.2f} |")
    lines.append(f"| 卡玛比率 | {m.calmar_ratio:.2f} |")
    lines.append("")

    # Trade statistics
    lines.append("## 交易统计")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总交易次数 | {m.total_trades} |")
    lines.append(f"| 盈利交易 | {m.winning_trades} |")
    lines.append(f"| 亏损交易 | {m.losing_trades} |")
    lines.append(f"| 胜率 | {format_percent(m.win_rate)} |")
    lines.append(f"| 平均盈利 | {format_number(m.avg_win)} |")
    lines.append(f"| 平均亏损 | {format_number(m.avg_loss)} |")
    lines.append(f"| 盈亏比 | {m.profit_factor:.2f} |")
    lines.append(f"| 期望值 | {format_number(m.expectancy)} |")
    lines.append(f"| 平均持仓天数 | {m.avg_holding_days:.1f} |")
    lines.append(f"| 最大连胜 | {m.max_consecutive_wins} |")
    lines.append(f"| 最大连亏 | {m.max_consecutive_losses} |")
    lines.append("")

    # Trade history
    if result.trades:
        lines.append("## 交易记录")
        lines.append("")
        lines.append(
            "| # | 入场日期 | 出场日期 | 入场价 | 出场价 | 盈亏 | 收益率 | 持仓天数 |"
        )
        lines.append(
            "|---|----------|----------|--------|--------|------|--------|----------|"
        )
        for i, trade in enumerate(result.trades, 1):
            lines.append(
                f"| {i} | {trade.entry_date.strftime('%Y-%m-%d')} | "
                f"{trade.exit_date.strftime('%Y-%m-%d')} | "
                f"{trade.entry_price:.2f} | {trade.exit_price:.2f} | "
                f"{format_pnl(trade.pnl)} | {format_percent(trade.pnl_pct)} | "
                f"{trade.holding_days} |"
            )
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

    return "\n".join(lines)


def generate_json_report(result: BacktestResult) -> dict:
    """Generate a JSON backtest report.

    Args:
        result: Backtest result

    Returns:
        Dict with report data
    """
    m = result.metrics

    return {
        "strategy": result.strategy_name,
        "symbol": result.symbol,
        "period": {
            "start": result.start_date.isoformat(),
            "end": result.end_date.isoformat(),
            "days": (result.end_date - result.start_date).days,
        },
        "capital": {
            "initial": result.initial_capital,
            "final": result.final_capital,
            "total_return": m.total_return,
            "total_return_pct": m.total_return_pct,
            "annualized_return": m.annualized_return,
        },
        "risk": {
            "max_drawdown": m.max_drawdown,
            "max_drawdown_pct": m.max_drawdown_pct,
            "sharpe_ratio": m.sharpe_ratio,
            "sortino_ratio": m.sortino_ratio,
            "calmar_ratio": m.calmar_ratio,
        },
        "trades": {
            "total": m.total_trades,
            "winning": m.winning_trades,
            "losing": m.losing_trades,
            "win_rate": m.win_rate,
            "avg_win": m.avg_win,
            "avg_loss": m.avg_loss,
            "profit_factor": m.profit_factor,
            "expectancy": m.expectancy,
            "avg_holding_days": m.avg_holding_days,
            "max_consecutive_wins": m.max_consecutive_wins,
            "max_consecutive_losses": m.max_consecutive_losses,
        },
        "trade_history": [
            {
                "entry_date": t.entry_date.isoformat(),
                "exit_date": t.exit_date.isoformat(),
                "entry_price": t.entry_price,
                "exit_price": t.exit_price,
                "quantity": t.quantity,
                "pnl": t.pnl,
                "pnl_pct": t.pnl_pct,
                "holding_days": t.holding_days,
                "entry_reason": t.entry_reason,
                "exit_reason": t.exit_reason,
            }
            for t in result.trades
        ],
        "generated_at": datetime.now().isoformat(),
    }


def generate_report(
    result: BacktestResult,
    format: ReportFormat = ReportFormat.TEXT,
) -> str | dict:
    """Generate a backtest report in the specified format.

    Args:
        result: Backtest result
        format: Output format

    Returns:
        Formatted report (string for TEXT/MARKDOWN, dict for JSON)
    """
    if format == ReportFormat.TEXT:
        return generate_text_report(result)
    elif format == ReportFormat.MARKDOWN:
        return generate_markdown_report(result)
    elif format == ReportFormat.JSON:
        return generate_json_report(result)
    else:
        return generate_text_report(result)
