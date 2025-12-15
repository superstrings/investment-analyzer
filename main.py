#!/usr/bin/env python3
"""
Investment Analyzer - 投资分析自动化系统

CLI 主程序入口
"""

import logging
import sys
from pathlib import Path
from typing import Optional

import click

from cli import (
    OutputFormat,
    console,
    create_progress,
    format_output,
    print_error,
    print_info,
    print_success,
    print_table,
    print_warning,
)
from config import ConfigurationError, get_users_config, settings
from db import Account, Position, User, check_connection, get_session, init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_user_by_name(username: str) -> Optional[User]:
    """Get user from database by username."""
    with get_session() as session:
        return session.query(User).filter_by(username=username).first()


def validate_user(ctx, param, value: str) -> str:
    """Validate user exists in configuration."""
    users_config = get_users_config()
    if not users_config.get_user(value):
        available = ", ".join(users_config.list_usernames())
        raise click.BadParameter(
            f"User '{value}' not found. Available users: {available or 'none configured'}"
        )
    return value


def parse_codes(codes: Optional[str]) -> list[str]:
    """Parse comma-separated stock codes into list."""
    if not codes:
        return []
    return [c.strip() for c in codes.split(",") if c.strip()]


def _is_option_code(market: str, code: str) -> bool:
    """Check if a stock code is an option/warrant.

    HK options: codes containing letters (e.g., SMC260629C75000, TCH260330C650000)
    US options: codes with date+C/P+strike pattern (e.g., MU260116C230000, NVDA260116C186000)
    """
    import re

    if market == "HK":
        # HK options/warrants have letters in the code
        return any(c.isalpha() for c in code)

    if market == "US":
        # US options have pattern: SYMBOL + YYMMDD + C/P + STRIKE
        # e.g., MU260116C230000, NVDA260116C186000, PLTR251219C175000
        # Pattern: letters + 6 digits + C or P + digits
        return bool(re.match(r"^[A-Z]+\d{6}[CP]\d+$", code))

    return False


@click.group()
@click.version_option(version="0.1.0")
@click.option("-v", "--verbose", is_flag=True, help="Enable verbose output")
def cli(verbose: bool):
    """Investment Analyzer - 投资分析自动化系统"""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)


# =============================================================================
# Sync Commands
# =============================================================================


@cli.group()
def sync():
    """数据同步命令"""
    pass


@sync.command("all")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=365, help="同步交易历史天数")
@click.option("--kline-days", default=250, help="同步K线天数")
def sync_all(user: str, days: int, kline_days: int):
    """同步所有数据 (持仓、交易、K线)"""
    from fetchers import FutuFetcher, KlineFetcher
    from services import SyncService

    click.echo(f"Syncing all data for user '{user}'...")

    users_config = get_users_config()
    user_config = users_config.get_user(user)

    # Get user from database
    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(
            f"Error: User '{user}' not found in database. Run 'db seed' first.",
            err=True,
        )
        sys.exit(1)

    try:
        with FutuFetcher(
            host=user_config.opend.host,
            port=user_config.opend.port,
        ) as futu:
            # Unlock trade if password available
            if user_config.has_trade_password():
                futu.unlock_trade(user_config.trade_password)

            kline = KlineFetcher()
            sync_service = SyncService(futu_fetcher=futu, kline_fetcher=kline)

            results = sync_service.sync_all(
                user_id=db_user.id,
                trade_days=days,
                kline_days=kline_days,
            )

            # Display results
            click.echo("\n--- Sync Results ---")
            for sync_type, result in results.items():
                status = (
                    click.style("OK", fg="green")
                    if result.success
                    else click.style("FAILED", fg="red")
                )
                click.echo(
                    f"{sync_type}: {status} "
                    f"(synced: {result.records_synced}, skipped: {result.records_skipped})"
                )
                if not result.success:
                    click.echo(f"  Error: {result.error_message}", err=True)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sync.command("positions")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
def sync_positions(user: str):
    """同步持仓数据"""
    from fetchers import FutuFetcher, KlineFetcher
    from services import SyncService

    click.echo(f"Syncing positions for user '{user}'...")

    users_config = get_users_config()
    user_config = users_config.get_user(user)
    db_user = get_user_by_name(user)

    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    try:
        with FutuFetcher(
            host=user_config.opend.host,
            port=user_config.opend.port,
        ) as futu:
            if user_config.has_trade_password():
                futu.unlock_trade(user_config.trade_password)

            sync_service = SyncService(futu_fetcher=futu)
            result = sync_service.sync_positions(user_id=db_user.id)

            if result.success:
                click.echo(
                    click.style("Success: ", fg="green")
                    + f"Synced {result.records_synced} positions, skipped {result.records_skipped}"
                )
            else:
                click.echo(
                    click.style(f"Error: {result.error_message}", fg="red"), err=True
                )
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sync.command("trades")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=365, help="同步天数 (默认365天)")
def sync_trades(user: str, days: int):
    """同步交易记录"""
    from fetchers import FutuFetcher
    from services import SyncService

    click.echo(f"Syncing trades for user '{user}' (last {days} days)...")

    users_config = get_users_config()
    user_config = users_config.get_user(user)
    db_user = get_user_by_name(user)

    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    try:
        with FutuFetcher(
            host=user_config.opend.host,
            port=user_config.opend.port,
        ) as futu:
            if user_config.has_trade_password():
                futu.unlock_trade(user_config.trade_password)

            sync_service = SyncService(futu_fetcher=futu)
            result = sync_service.sync_trades(user_id=db_user.id, days=days)

            if result.success:
                click.echo(
                    click.style("Success: ", fg="green")
                    + f"Synced {result.records_synced} trades, skipped {result.records_skipped}"
                )
            else:
                click.echo(
                    click.style(f"Error: {result.error_message}", fg="red"), err=True
                )
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sync.command("klines")
@click.option("--codes", "-c", required=True, help="股票代码列表 (逗号分隔)")
@click.option("--days", default=120, help="K线天数")
def sync_klines(codes: str, days: int):
    """同步K线数据"""
    from fetchers import KlineFetcher
    from services import SyncService

    code_list = parse_codes(codes)
    if not code_list:
        click.echo("Error: No valid stock codes provided.", err=True)
        sys.exit(1)

    click.echo(f"Syncing K-line data for {len(code_list)} stocks ({days} days)...")

    try:
        kline = KlineFetcher()
        sync_service = SyncService(kline_fetcher=kline)
        result = sync_service.sync_klines(codes=code_list, days=days)

        if result.success:
            click.echo(
                click.style("Success: ", fg="green")
                + f"Synced {result.records_synced} K-lines, skipped {result.records_skipped}"
            )
        else:
            click.echo(
                click.style(f"Error: {result.error_message}", fg="red"), err=True
            )
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sync.command("watchlist")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--clear", is_flag=True, help="清除现有数据后重新同步")
@click.option(
    "--groups",
    "-g",
    default=None,
    help="关注列表分组 (逗号分隔, 默认: 全部,港股,美股,沪深)",
)
def sync_watchlist_cmd(user: str, clear: bool, groups: Optional[str]):
    """同步关注列表"""
    from fetchers import FutuFetcher
    from services import SyncService

    click.echo(f"Syncing watchlist for user '{user}'...")

    users_config = get_users_config()
    user_config = users_config.get_user(user)
    db_user = get_user_by_name(user)

    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Parse groups
    group_list = None
    if groups:
        group_list = [g.strip() for g in groups.split(",")]

    try:
        with FutuFetcher(
            host=user_config.opend.host,
            port=user_config.opend.port,
        ) as futu_fetcher:
            # Unlock trade if password available
            if user_config.has_trade_password():
                futu_fetcher.unlock_trade(user_config.trade_password)

            sync_service = SyncService(futu_fetcher=futu_fetcher)
            result = sync_service.sync_watchlist(
                user_id=db_user.id,
                groups=group_list,
                clear_existing=clear,
            )

            if result.success:
                click.echo(f"Successfully synced watchlist:")
                click.echo(f"  Synced: {result.records_synced}")
                click.echo(f"  Skipped (duplicates): {result.records_skipped}")
            else:
                click.echo(f"Warning: Watchlist sync completed with issues:")
                click.echo(f"  {result.error_message}")
                click.echo(f"  Synced: {result.records_synced}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Chart Commands
# =============================================================================


@cli.group()
def chart():
    """图表生成命令"""
    pass


@chart.command("single")
@click.option("--code", "-c", required=True, help="股票代码")
@click.option("--days", default=120, help="K线天数")
@click.option(
    "--style",
    default="dark",
    type=click.Choice(["dark", "light", "chinese", "western"]),
    help="图表样式",
)
@click.option(
    "--indicators", "-i", default="ma", help="技术指标 (ma,obv,macd,rsi,bb 逗号分隔)"
)
@click.option("--output", "-o", default=None, help="输出文件路径")
def chart_single(
    code: str, days: int, style: str, indicators: str, output: Optional[str]
):
    """生成单只股票K线图"""
    from charts import ChartConfig, ChartGenerator
    from fetchers import KlineFetcher

    click.echo(f"Generating chart for {code} ({days} days, style={style})...")

    try:
        # Fetch K-line data
        fetcher = KlineFetcher()
        result = fetcher.fetch(code, days=days)

        if not result.success or result.df is None or result.df.empty:
            click.echo(f"Error: Failed to fetch K-line data for {code}", err=True)
            if result.error_message:
                click.echo(f"  {result.error_message}", err=True)
            sys.exit(1)

        # Configure chart
        indicator_list = [i.strip().lower() for i in indicators.split(",")]
        ma_periods = [5, 10, 20, 60] if "ma" in indicator_list else []

        config = ChartConfig(
            ma_periods=ma_periods,
            show_volume=True,
            show_ma="ma" in indicator_list,
            last_n_days=days,
        )

        # Determine output path
        if output:
            output_path = Path(output)
        else:
            output_dir = settings.chart.output_dir
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"{code.replace('.', '_')}.png"

        # Generate chart
        generator = ChartGenerator(style=style)
        chart_path = generator.generate(
            df=result.df,
            title=code,
            output_path=output_path,
            config=config,
        )

        if chart_path:
            click.echo(
                click.style("Success: ", fg="green") + f"Chart saved to {chart_path}"
            )
        else:
            click.echo(
                click.style("Error: ", fg="red") + "Failed to generate chart", err=True
            )
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@chart.command("watchlist")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=120, help="K线天数")
@click.option(
    "--style",
    default="dark",
    type=click.Choice(["dark", "light", "chinese", "western"]),
    help="图表样式",
)
def chart_watchlist(user: str, days: int, style: str):
    """为关注列表生成图表"""
    from services import BatchChartConfig, ChartService

    click.echo(f"Generating charts for {user}'s watchlist...")

    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    try:
        config = BatchChartConfig(days=days, style=style, output_subdir=user)
        service = ChartService(output_dir=settings.chart.output_dir)
        result = service.generate_watchlist_charts(
            user_id=db_user.id,
            config=config,
        )

        if result.charts_generated == 0 and result.error_message:
            click.echo(f"No charts generated: {result.error_message}")
            return

        # Show progress
        for path in result.generated_files:
            click.echo(f"  Generated: {path.stem}")
        for code in result.failed_codes:
            click.echo(f"  Skipped: {code} (no data)")

        total = result.charts_generated + result.charts_failed
        click.echo(
            click.style("Done: ", fg="green")
            + f"Generated {result.charts_generated}/{total} charts in {result.output_dir}"
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@chart.command("positions")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=120, help="K线天数")
@click.option(
    "--style",
    default="dark",
    type=click.Choice(["dark", "light", "chinese", "western"]),
    help="图表样式",
)
def chart_positions(user: str, days: int, style: str):
    """为持仓股票生成图表"""
    from services import BatchChartConfig, ChartService

    click.echo(f"Generating charts for {user}'s positions...")

    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    try:
        config = BatchChartConfig(
            days=days, style=style, output_subdir=f"{user}/positions"
        )
        service = ChartService(output_dir=settings.chart.output_dir)
        result = service.generate_position_charts(
            user_id=db_user.id,
            config=config,
        )

        if result.charts_generated == 0 and result.error_message:
            click.echo(f"No charts generated: {result.error_message}")
            return

        # Show progress
        for path in result.generated_files:
            click.echo(f"  Generated: {path.stem}")
        for code in result.failed_codes:
            click.echo(f"  Skipped: {code} (no data)")

        total = result.charts_generated + result.charts_failed
        click.echo(
            click.style("Done: ", fg="green")
            + f"Generated {result.charts_generated}/{total} charts in {result.output_dir}"
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Report Commands
# =============================================================================


@cli.group()
def report():
    """报告生成命令"""
    pass


@report.command("portfolio")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--output", "-o", default=None, help="输出文件路径")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="输出格式",
)
def report_portfolio(user: str, output: Optional[str], output_format: str):
    """生成持仓报告"""
    print_info(f"Generating portfolio report for user '{user}'...")

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    # Get positions summary
    with get_session() as session:
        positions = (
            session.query(Position)
            .join(Account)
            .filter(Account.user_id == db_user.id, Position.qty > 0)
            .all()
        )

        if not positions:
            print_warning("No active positions found.")
            return

        # Build positions data
        positions_data = []
        total_market_value = 0
        total_pnl = 0

        for pos in positions:
            market_value = float(pos.qty * pos.market_price) if pos.market_price else 0
            pnl = float(pos.pl_val) if pos.pl_val else 0
            pnl_pct = float(pos.pl_ratio) if pos.pl_ratio else 0

            total_market_value += market_value
            total_pnl += pnl

            positions_data.append(
                {
                    "code": pos.code,
                    "name": pos.stock_name or "N/A",
                    "qty": float(pos.qty),
                    "cost_price": float(pos.cost_price) if pos.cost_price else 0,
                    "market_price": float(pos.market_price) if pos.market_price else 0,
                    "market_val": market_value,
                    "pl_val": pnl,
                    "pl_ratio": pnl_pct,
                }
            )

        fmt = OutputFormat(output_format)

        if fmt == OutputFormat.TABLE:
            # Rich table output
            columns = [
                ("code", "Code"),
                ("name", "Name"),
                ("qty", "Qty"),
                ("cost_price", "Cost"),
                ("market_price", "Price"),
                ("market_val", "Market Val"),
                ("pl_val", "P&L"),
                ("pl_ratio", "P&L %"),
            ]
            print_table(positions_data, columns, title=f"Portfolio Report - {user}")

            # Summary
            console.print()
            pnl_color = "green" if total_pnl >= 0 else "red"
            console.print(f"[bold]Total Market Value:[/bold] {total_market_value:,.2f}")
            console.print(
                f"[bold]Total P&L:[/bold] [{pnl_color}]{total_pnl:+,.2f}[/{pnl_color}]"
            )
        else:
            result = format_output(positions_data, fmt)
            if output:
                Path(output).write_text(result)
                print_success(f"Report saved to {output}")
            else:
                console.print(result)


@report.command("technical")
@click.option("--code", "-c", required=True, help="股票代码")
@click.option("--days", default=120, help="分析天数")
def report_technical(code: str, days: int):
    """生成技术分析报告"""
    from analysis import AnalysisConfig, TechnicalAnalyzer
    from fetchers import KlineFetcher

    click.echo(f"Generating technical report for {code} ({days} days)...")

    try:
        # Fetch K-line data
        fetcher = KlineFetcher()
        result = fetcher.fetch(code, days=days)

        if not result.success or result.df is None or result.df.empty:
            click.echo(f"Error: Failed to fetch data for {code}", err=True)
            sys.exit(1)

        # Run technical analysis
        config = AnalysisConfig(
            ma_periods=[5, 10, 20, 60],
            include_signals=True,
        )
        analyzer = TechnicalAnalyzer(config)
        analysis = analyzer.analyze(result.df)

        # Get latest values
        summary = analysis.summary()

        click.echo("\n" + "=" * 60)
        click.echo(f"Technical Analysis: {code}")
        click.echo("=" * 60)

        df = result.df
        latest = df.iloc[-1]
        click.echo(f"\nPrice: {latest['close']:.2f}")
        click.echo(f"Volume: {latest['volume']:,.0f}")

        # Moving Averages
        click.echo("\n--- Moving Averages ---")
        for key, value in summary.items():
            if key.startswith("SMA") or key.startswith("EMA"):
                if isinstance(value, (int, float)):
                    click.echo(f"  {key}: {value:.2f}")

        # RSI
        click.echo("\n--- RSI ---")
        for key, value in summary.items():
            if "RSI" in key and isinstance(value, (int, float)):
                if value > 70:
                    status = click.style("Overbought", fg="red")
                elif value < 30:
                    status = click.style("Oversold", fg="green")
                else:
                    status = "Neutral"
                click.echo(f"  {key}: {value:.2f} ({status})")

        # MACD
        click.echo("\n--- MACD ---")
        if "MACD" in summary or "MACD_Crossover" in summary:
            macd_data = summary.get("MACD") or summary.get("MACD_Crossover", {})
            if isinstance(macd_data, dict):
                for k, v in macd_data.items():
                    if isinstance(v, (int, float)):
                        click.echo(f"  {k}: {v:.4f}")

        # Bollinger Bands
        click.echo("\n--- Bollinger Bands ---")
        bb_data = summary.get("BollingerBands") or summary.get("BB_Signals", {})
        if isinstance(bb_data, dict):
            for k, v in bb_data.items():
                if isinstance(v, (int, float)):
                    click.echo(f"  {k}: {v:.2f}")

        click.echo("\n" + "=" * 60)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Account Commands
# =============================================================================


@cli.group()
def account():
    """账户管理命令"""
    pass


@account.command("list")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="输出格式",
)
def account_list(user: str, output_format: str):
    """列出用户账户"""
    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    with get_session() as session:
        accounts = session.query(Account).filter_by(user_id=db_user.id).all()

        if not accounts:
            print_warning(f"No accounts found for user '{user}'")
            return

        accounts_data = [
            {
                "market": acc.market,
                "account_id": acc.futu_acc_id,
                "type": acc.account_type or "N/A",
                "name": acc.account_name or "N/A",
                "active": acc.is_active,
            }
            for acc in accounts
        ]

        fmt = OutputFormat(output_format)
        if fmt == OutputFormat.TABLE:
            columns = [
                ("market", "Market"),
                ("account_id", "Account ID"),
                ("type", "Type"),
                ("name", "Name"),
                ("active", "Active"),
            ]
            print_table(accounts_data, columns, title=f"Accounts - {user}")
        else:
            result = format_output(accounts_data, fmt)
            console.print(result)


@account.command("info")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
def account_info(user: str):
    """显示账户详情"""
    from fetchers import FutuFetcher

    users_config = get_users_config()
    user_config = users_config.get_user(user)

    click.echo(f"Fetching account info for user '{user}'...")

    try:
        with FutuFetcher(
            host=user_config.opend.host,
            port=user_config.opend.port,
        ) as futu:
            if user_config.has_trade_password():
                futu.unlock_trade(user_config.trade_password)

            # Get account list
            result = futu.get_account_list()
            if not result.success:
                click.echo(f"Error: {result.error_message}", err=True)
                sys.exit(1)

            click.echo("\n" + "=" * 60)
            click.echo(f"Account Info for {user}")
            click.echo("=" * 60)

            for acc in result.data:
                click.echo(f"\n[{acc.market.value}] Account {acc.acc_id}")
                click.echo(f"  Type: {acc.acc_type.value}")

                # Get account funds
                funds_result = futu.get_account_info(acc.acc_id)
                if funds_result.success and funds_result.data:
                    info = funds_result.data[0]
                    click.echo(f"  Cash: {float(info.cash):,.2f}")
                    click.echo(f"  Market Value: {float(info.market_val):,.2f}")
                    click.echo(f"  Total Assets: {float(info.total_assets):,.2f}")

            click.echo("\n" + "=" * 60)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# Database Commands
# =============================================================================


@cli.group()
def db():
    """数据库管理命令"""
    pass


@db.command("check")
def db_check():
    """检查数据库连接"""
    print_info("Checking database connection...")
    try:
        with console.status("Connecting to database..."):
            result = check_connection()
        if result:
            print_success("Database connection OK")
        else:
            print_error("Database connection failed", exit_code=1)
    except Exception as e:
        print_error(f"{e}", exit_code=1)


@db.command("init")
@click.option("--force", is_flag=True, help="强制重建表")
def db_init(force: bool):
    """初始化数据库表"""
    print_info("Initializing database...")
    if force:
        print_warning("This will drop all existing tables!")
        if not click.confirm("Continue?"):
            return

    try:
        with console.status("Creating tables..."):
            init_db()
        print_success("Database initialized")
    except Exception as e:
        print_error(f"{e}", exit_code=1)


@db.command("seed")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
def db_seed(user: str):
    """为用户创建初始数据"""
    users_config = get_users_config()
    user_config = users_config.get_user(user)

    click.echo(f"Seeding data for user '{user}'...")

    try:
        with get_session() as session:
            # Check if user exists
            existing = session.query(User).filter_by(username=user).first()
            if existing:
                click.echo(f"User '{user}' already exists (id={existing.id})")
                return

            # Create user
            db_user = User(
                username=user,
                display_name=user_config.display_name,
                is_active=user_config.is_active,
            )
            session.add(db_user)
            session.commit()

            click.echo(
                click.style("Success: ", fg="green")
                + f"Created user '{user}' (id={db_user.id})"
            )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@db.command("migrate")
@click.option(
    "--direction", default="up", type=click.Choice(["up", "down"]), help="迁移方向"
)
def db_migrate(direction: str):
    """运行数据库迁移"""
    click.echo(f"Running database migration ({direction})...")

    # TODO: Implement proper migration system (e.g., Alembic)
    click.echo("Note: Migration system not yet implemented.")
    click.echo("Use 'python scripts/init_db.py' for now.")


# =============================================================================
# Import Commands
# =============================================================================


@cli.group(name="import")
def import_cmd():
    """CSV 数据导入命令"""
    pass


@import_cmd.command("watchlist")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True),
    help="CSV文件路径",
)
@click.option("--encoding", default="utf-8", help="文件编码 (默认utf-8)")
def import_watchlist(user: str, file_path: str, encoding: str):
    """导入关注列表 CSV"""
    from scripts.import_csv import get_user_id
    from scripts.import_csv import import_watchlist as do_import

    click.echo(f"Importing watchlist for user '{user}' from {file_path}...")

    user_id = get_user_id(user)
    if not user_id:
        click.echo(
            f"Error: User '{user}' not found in database. Run 'db seed -u {user}' first.",
            err=True,
        )
        sys.exit(1)

    result = do_import(user_id, Path(file_path), encoding)

    if result.success:
        click.echo(
            click.style("Success: ", fg="green")
            + f"Imported {result.imported}, skipped {result.skipped}"
        )
    else:
        click.echo(click.style("Error: ", fg="red") + "Import failed", err=True)

    if result.error_messages:
        click.echo("\nErrors:")
        for msg in result.error_messages[:10]:
            click.echo(f"  - {msg}", err=True)
        if len(result.error_messages) > 10:
            click.echo(
                f"  ... and {len(result.error_messages) - 10} more errors", err=True
            )

    sys.exit(0 if result.success else 1)


@import_cmd.command("positions")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--account", "-a", "account_id", type=int, help="账户ID (富途账户号)")
@click.option(
    "--market",
    "-m",
    type=click.Choice(["HK", "US", "A"]),
    help="市场 (如果没有指定账户ID)",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True),
    help="CSV文件路径",
)
@click.option("--date", "-d", "snapshot_date", help="快照日期 (YYYY-MM-DD，默认今天)")
@click.option("--encoding", default="utf-8", help="文件编码 (默认utf-8)")
def import_positions(
    user: str,
    account_id: Optional[int],
    market: Optional[str],
    file_path: str,
    snapshot_date: Optional[str],
    encoding: str,
):
    """导入持仓数据 CSV"""
    from scripts.import_csv import (
        get_account,
        get_user_id,
    )
    from scripts.import_csv import import_positions as do_import

    click.echo(f"Importing positions for user '{user}' from {file_path}...")

    user_id = get_user_id(user)
    if not user_id:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    account = get_account(user_id, account_id, market)
    if not account:
        click.echo(
            f"Error: Account not found. Please create an account first.", err=True
        )
        sys.exit(1)

    # Parse date
    from datetime import datetime as dt

    date_obj = None
    if snapshot_date:
        try:
            date_obj = dt.strptime(snapshot_date, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"Error: Invalid date format. Use YYYY-MM-DD.", err=True)
            sys.exit(1)

    result = do_import(account.id, Path(file_path), date_obj, encoding)

    if result.success:
        click.echo(
            click.style("Success: ", fg="green")
            + f"Imported {result.imported}, skipped {result.skipped}"
        )
    else:
        click.echo(click.style("Error: ", fg="red") + "Import failed", err=True)

    if result.error_messages:
        click.echo("\nErrors:")
        for msg in result.error_messages[:10]:
            click.echo(f"  - {msg}", err=True)
        if len(result.error_messages) > 10:
            click.echo(
                f"  ... and {len(result.error_messages) - 10} more errors", err=True
            )

    sys.exit(0 if result.success else 1)


@import_cmd.command("trades")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--account", "-a", "account_id", type=int, help="账户ID (富途账户号)")
@click.option(
    "--market",
    "-m",
    type=click.Choice(["HK", "US", "A"]),
    help="市场 (如果没有指定账户ID)",
)
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True),
    help="CSV文件路径",
)
@click.option("--encoding", default="utf-8", help="文件编码 (默认utf-8)")
def import_trades(
    user: str,
    account_id: Optional[int],
    market: Optional[str],
    file_path: str,
    encoding: str,
):
    """导入交易记录 CSV"""
    from scripts.import_csv import get_account, get_user_id
    from scripts.import_csv import import_trades as do_import

    click.echo(f"Importing trades for user '{user}' from {file_path}...")

    user_id = get_user_id(user)
    if not user_id:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    account = get_account(user_id, account_id, market)
    if not account:
        click.echo(
            f"Error: Account not found. Please create an account first.", err=True
        )
        sys.exit(1)

    result = do_import(account.id, Path(file_path), encoding)

    if result.success:
        click.echo(
            click.style("Success: ", fg="green")
            + f"Imported {result.imported}, skipped {result.skipped}"
        )
    else:
        click.echo(click.style("Error: ", fg="red") + "Import failed", err=True)

    if result.error_messages:
        click.echo("\nErrors:")
        for msg in result.error_messages[:10]:
            click.echo(f"  - {msg}", err=True)
        if len(result.error_messages) > 10:
            click.echo(
                f"  ... and {len(result.error_messages) - 10} more errors", err=True
            )

    sys.exit(0 if result.success else 1)


@import_cmd.command("formats")
def import_formats():
    """显示支持的 CSV 格式"""
    click.echo(
        """
=== Watchlist CSV Format ===
Required columns: code
Optional columns: name, group, notes

Example:
code,name,group,notes
HK.00700,腾讯控股,科技股,核心持仓
US.NVDA,英伟达,AI概念,

Column aliases (Chinese/English):
  code: 股票代码, 代码, symbol
  name: 股票名称, 名称, stock_name
  group: 分组, 组, group_name
  notes: 备注, note, comment


=== Positions CSV Format ===
Required columns: code, qty
Optional columns: name, cost_price, market_price, market_val, pl_val, pl_ratio

Example:
code,name,qty,cost_price,market_price
HK.00700,腾讯控股,100,350.00,380.00
US.NVDA,英伟达,50,500.00,550.00

Column aliases (Chinese/English):
  code: 股票代码, 代码, symbol
  qty: 数量, quantity, 持仓数量, shares
  cost_price: 成本价, cost, avg_cost, 均价
  market_price: 市价, price, current_price, 现价


=== Trades CSV Format ===
Required columns: code, qty, price
Optional columns: deal_id, order_id, trade_time, name, side, amount, fee

Example:
deal_id,trade_time,code,name,side,qty,price,amount,fee
D123456,2024-01-15 10:30:00,HK.00700,腾讯控股,BUY,100,350.00,35000.00,50.00

Column aliases (Chinese/English):
  code: 股票代码, 代码, symbol
  qty: 数量, quantity, 成交数量
  price: 成交价, deal_price, 价格
  side: 方向, 买卖方向, direction (BUY/SELL/买/卖)
  trade_time: 成交时间, time, datetime


=== Code Format ===
Supports: HK.00700, US.NVDA, 00700 (defaults to HK), NVDA (defaults to US)

=== Date/Time Formats ===
Supports: YYYY-MM-DD, YYYY/MM/DD, DD/MM/YYYY, with optional HH:MM:SS
"""
    )


# =============================================================================
# Config Commands
# =============================================================================


@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command("show")
def config_show():
    """显示当前配置"""
    from rich.panel import Panel
    from rich.tree import Tree

    tree = Tree("[bold]Configuration[/bold]")

    db_branch = tree.add("[cyan]Database[/cyan]")
    db_branch.add(f"URL: {settings.database.url}")
    db_branch.add(f"Pool Size: {settings.database.pool_size}")

    futu_branch = tree.add("[cyan]Futu OpenD[/cyan]")
    futu_branch.add(f"Default Host: {settings.futu.default_host}")
    futu_branch.add(f"Default Port: {settings.futu.default_port}")

    chart_branch = tree.add("[cyan]Chart[/cyan]")
    chart_branch.add(f"Output Dir: {settings.chart.output_dir}")
    chart_branch.add(f"DPI: {settings.chart.dpi}")
    chart_branch.add(f"MAV Periods: {settings.chart.mav}")

    kline_branch = tree.add("[cyan]K-line[/cyan]")
    kline_branch.add(f"Default Days: {settings.kline.default_days}")
    kline_branch.add(f"Markets: {settings.kline.markets}")

    console.print(tree)


@config.command("users")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json"]),
    default="table",
    help="输出格式",
)
def config_users(output_format: str):
    """列出配置的用户"""
    users_config = get_users_config()
    usernames = users_config.list_usernames()

    if not usernames:
        print_warning("No users configured. Edit config/users.yaml to add users.")
        return

    users_data = []
    for username in usernames:
        user = users_config.get_user(username)
        users_data.append(
            {
                "username": username,
                "display_name": user.display_name,
                "active": user.is_active,
                "opend_host": user.opend.host,
                "opend_port": user.opend.port,
                "markets": ", ".join(user.default_markets),
            }
        )

    fmt = (
        OutputFormat(output_format) if output_format != "table" else OutputFormat.TABLE
    )

    if fmt == OutputFormat.TABLE:
        columns = [
            ("username", "Username"),
            ("display_name", "Display Name"),
            ("active", "Active"),
            ("opend_host", "OpenD Host"),
            ("opend_port", "Port"),
            ("markets", "Markets"),
        ]
        print_table(users_data, columns, title="Configured Users")
    else:
        result = format_output(users_data, OutputFormat.JSON)
        console.print(result)


# =============================================================================
# Alert Commands
# =============================================================================


@cli.group()
def alert():
    """价格提醒命令"""
    pass


@alert.command("add")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--code", "-c", required=True, help="股票代码 (如 HK.00700)")
@click.option(
    "--type",
    "-t",
    "alert_type",
    type=click.Choice(["above", "below", "up", "down"]),
    required=True,
    help="提醒类型: above(突破), below(跌破), up(涨幅), down(跌幅)",
)
@click.option("--price", "-p", type=float, help="目标价格 (突破/跌破时必填)")
@click.option("--pct", type=float, help="目标涨跌幅百分比 (如 0.1 表示 10%)")
@click.option("--base", type=float, help="基准价格 (计算涨跌幅时使用)")
@click.option("--notes", "-n", help="备注")
def alert_add(
    user: str,
    code: str,
    alert_type: str,
    price: Optional[float],
    pct: Optional[float],
    base: Optional[float],
    notes: Optional[str],
):
    """添加价格提醒"""
    from services import AlertService, AlertType

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    # Parse stock code
    if "." in code:
        market, stock_code = code.split(".", 1)
    else:
        # Default to HK market
        market = "HK" if code.isdigit() else "US"
        stock_code = code

    # Map alert type
    type_map = {
        "above": AlertType.ABOVE,
        "below": AlertType.BELOW,
        "up": AlertType.CHANGE_UP,
        "down": AlertType.CHANGE_DOWN,
    }
    at = type_map[alert_type]

    # Validate required params
    if at in (AlertType.ABOVE, AlertType.BELOW) and price is None:
        print_error(f"--price is required for '{alert_type}' alert", exit_code=1)
    if at in (AlertType.CHANGE_UP, AlertType.CHANGE_DOWN) and pct is None:
        print_error(f"--pct is required for '{alert_type}' alert", exit_code=1)

    try:
        service = AlertService()
        created = service.create_alert(
            user_id=db_user.id,
            market=market.upper(),
            code=stock_code,
            alert_type=at,
            target_price=price,
            target_change_pct=pct,
            base_price=base,
            notes=notes,
        )

        print_success(f"Alert created (ID: {created.id})")
        console.print(f"  Code: [cyan]{created.full_code}[/cyan]")
        console.print(f"  Type: [yellow]{created.alert_type}[/yellow]")
        console.print(f"  Target: {created.target_description}")

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@alert.command("list")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--all", "-a", "show_all", is_flag=True, help="显示所有提醒(包括已触发)")
@click.option("--market", "-m", help="筛选市场 (HK/US/A)")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["table", "json", "csv"]),
    default="table",
    help="输出格式",
)
def alert_list(user: str, show_all: bool, market: Optional[str], output_format: str):
    """列出价格提醒"""
    from services import AlertService

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    service = AlertService()
    alerts = service.get_user_alerts(
        user_id=db_user.id,
        active_only=not show_all,
        market=market,
    )

    if not alerts:
        print_warning("No alerts found.")
        return

    # Build data for output
    alerts_data = []
    for a in alerts:
        target = (
            str(a.target_price)
            if a.target_price
            else f"{float(a.target_change_pct or 0):.2%}"
        )
        alerts_data.append(
            {
                "id": a.id,
                "code": a.full_code,
                "name": a.stock_name or "-",
                "type": a.alert_type,
                "target": target,
                "active": a.is_active and not a.is_triggered,
                "triggered": a.is_triggered,
                "notes": a.notes or "",
            }
        )

    fmt = OutputFormat(output_format)

    if fmt == OutputFormat.TABLE:
        columns = [
            ("id", "ID"),
            ("code", "Code"),
            ("name", "Name"),
            ("type", "Type"),
            ("target", "Target"),
            ("active", "Active"),
            ("triggered", "Triggered"),
        ]
        print_table(alerts_data, columns, title=f"Price Alerts - {user}")
    else:
        result = format_output(alerts_data, fmt)
        console.print(result)


@alert.command("delete")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.argument("alert_id", type=int)
def alert_delete(user: str, alert_id: int):
    """删除价格提醒"""
    from services import AlertService

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    service = AlertService()

    # Verify the alert belongs to the user
    existing = service.get_alert(alert_id)
    if not existing:
        print_error(f"Alert {alert_id} not found.", exit_code=1)
    if existing.user_id != db_user.id:
        print_error(f"Alert {alert_id} does not belong to user '{user}'.", exit_code=1)

    if service.delete_alert(alert_id):
        print_success(f"Alert {alert_id} deleted.")
    else:
        print_error(f"Failed to delete alert {alert_id}.", exit_code=1)


@alert.command("check")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--dry-run", is_flag=True, help="仅检查,不触发提醒")
def alert_check(user: str, dry_run: bool):
    """检查价格提醒 (需要先同步K线数据)"""
    from services import AlertService

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    service = AlertService()
    alerts = service.get_user_alerts(db_user.id, active_only=True)

    if not alerts:
        print_warning("No active alerts to check.")
        return

    # Get latest prices from database
    from db import Kline, get_session

    price_data = {}
    with get_session() as session:
        for a in alerts:
            kline = (
                session.query(Kline)
                .filter_by(market=a.market, code=a.code)
                .order_by(Kline.trade_date.desc())
                .first()
            )
            if kline:
                price_data[a.full_code] = float(kline.close)

    if not price_data:
        print_warning("No price data available. Run 'sync klines' first.")
        return

    print_info(f"Checking {len(alerts)} alerts against {len(price_data)} prices...")

    summary = service.check_all_alerts(
        db_user.id,
        price_data,
        auto_trigger=not dry_run,
    )

    console.print(f"\nChecked: {summary.total_checked}")
    console.print(f"Triggered: {summary.total_triggered}")

    if summary.results:
        console.print("\n[bold yellow]Triggered Alerts:[/bold yellow]")
        for result in summary.results:
            console.print(f"  - {result.message}")


# =============================================================================
# Backtest Commands
# =============================================================================


@cli.group()
def backtest():
    """策略回测命令"""
    pass


@backtest.command("run")
@click.option("--code", "-c", required=True, help="股票代码 (如 HK.00700)")
@click.option("--days", "-d", default=250, help="回测天数 (默认250天)")
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["ma_cross", "vcp"]),
    default="ma_cross",
    help="策略类型",
)
@click.option("--fast-ma", default=10, help="快速MA周期 (ma_cross策略)")
@click.option("--slow-ma", default=30, help="慢速MA周期 (ma_cross策略)")
@click.option("--capital", default=100000.0, help="初始资金")
@click.option("--stop-loss", type=float, help="止损比例 (如 0.08 表示 8%)")
@click.option("--take-profit", type=float, help="止盈比例 (如 0.2 表示 20%)")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["text", "markdown", "json"]),
    default="text",
    help="输出格式",
)
@click.option("--output", "-o", help="输出文件路径")
def backtest_run(
    code: str,
    days: int,
    strategy: str,
    fast_ma: int,
    slow_ma: int,
    capital: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
    output_format: str,
    output: Optional[str],
):
    """运行策略回测"""
    from backtest import (
        MACrossConfig,
        MACrossStrategy,
        ReportFormat,
        VCPBreakoutConfig,
        VCPBreakoutStrategy,
        generate_report,
        run_backtest,
    )
    from fetchers import KlineFetcher

    print_info(f"Running backtest for {code} ({days} days, strategy={strategy})...")

    try:
        # Fetch K-line data
        fetcher = KlineFetcher()
        result = fetcher.fetch(code, days=days)

        if not result.success or result.df is None or result.df.empty:
            print_error(f"Failed to fetch K-line data for {code}", exit_code=1)

        # Create strategy
        if strategy == "ma_cross":
            config = MACrossConfig(
                fast_period=fast_ma,
                slow_period=slow_ma,
                initial_capital=capital,
                stop_loss_pct=stop_loss,
                take_profit_pct=take_profit,
            )
            strat = MACrossStrategy(config)
        else:  # vcp
            config = VCPBreakoutConfig(
                initial_capital=capital,
                stop_loss_pct=stop_loss or 0.08,
                take_profit_pct=take_profit,
            )
            strat = VCPBreakoutStrategy(config)

        # Run backtest
        with console.status("Running backtest..."):
            bt_result = run_backtest(strat, result.df, symbol=code)

        # Generate report
        fmt_map = {
            "text": ReportFormat.TEXT,
            "markdown": ReportFormat.MARKDOWN,
            "json": ReportFormat.JSON,
        }
        report_format = fmt_map.get(output_format, ReportFormat.TEXT)
        report = generate_report(bt_result, format=report_format)

        # Output
        if output:
            import json

            with open(output, "w") as f:
                if isinstance(report, dict):
                    json.dump(report, f, indent=2, ensure_ascii=False, default=str)
                else:
                    f.write(report)
            print_success(f"Report saved to {output}")
        else:
            if isinstance(report, dict):
                import json

                console.print(
                    json.dumps(report, indent=2, ensure_ascii=False, default=str)
                )
            else:
                console.print(report)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@backtest.command("strategies")
def backtest_strategies():
    """列出可用的回测策略"""
    console.print("\n[bold]Available Strategies[/bold]\n")

    console.print("[cyan]ma_cross[/cyan] - Moving Average Crossover")
    console.print("  Uses fast and slow MA crossover for entry/exit signals.")
    console.print("  Parameters:")
    console.print("    --fast-ma: Fast MA period (default: 10)")
    console.print("    --slow-ma: Slow MA period (default: 30)")
    console.print()

    console.print("[cyan]vcp[/cyan] - VCP Breakout")
    console.print("  Detects VCP patterns and enters on pivot breakout.")
    console.print("  Uses ATR-based trailing stop for exits.")
    console.print("  Parameters:")
    console.print("    --stop-loss: Stop loss percentage (default: 8%)")
    console.print()

    console.print("[bold]Example:[/bold]")
    console.print(
        "  python main.py backtest run -c HK.00700 -d 365 -s ma_cross --fast-ma 5 --slow-ma 20"
    )


@backtest.command("compare")
@click.option("--code", "-c", required=True, help="股票代码")
@click.option("--days", "-d", default=365, help="回测天数")
def backtest_compare(code: str, days: int):
    """比较多种策略的回测结果"""
    from backtest import (
        MACrossConfig,
        MACrossStrategy,
        VCPBreakoutConfig,
        VCPBreakoutStrategy,
        run_backtest,
    )
    from fetchers import KlineFetcher

    print_info(f"Comparing strategies for {code} ({days} days)...")

    try:
        # Fetch data
        fetcher = KlineFetcher()
        result = fetcher.fetch(code, days=days)

        if not result.success or result.df is None or result.df.empty:
            print_error(f"Failed to fetch data for {code}", exit_code=1)

        # Define strategies to test
        strategies = [
            ("MA(5/20)", MACrossStrategy(MACrossConfig(fast_period=5, slow_period=20))),
            (
                "MA(10/30)",
                MACrossStrategy(MACrossConfig(fast_period=10, slow_period=30)),
            ),
            (
                "MA(20/60)",
                MACrossStrategy(MACrossConfig(fast_period=20, slow_period=60)),
            ),
            ("VCP", VCPBreakoutStrategy(VCPBreakoutConfig())),
        ]

        # Run backtests
        results_data = []
        for name, strat in strategies:
            with console.status(f"Testing {name}..."):
                bt_result = run_backtest(strat, result.df.copy(), symbol=code)
                m = bt_result.metrics
                results_data.append(
                    {
                        "strategy": name,
                        "return": f"{m.total_return_pct * 100:.2f}%",
                        "sharpe": f"{m.sharpe_ratio:.2f}",
                        "max_dd": f"{m.max_drawdown_pct * 100:.2f}%",
                        "win_rate": f"{m.win_rate * 100:.1f}%",
                        "trades": m.total_trades,
                        "profit_factor": f"{m.profit_factor:.2f}",
                    }
                )

        # Display comparison
        columns = [
            ("strategy", "Strategy"),
            ("return", "Return"),
            ("sharpe", "Sharpe"),
            ("max_dd", "Max DD"),
            ("win_rate", "Win Rate"),
            ("trades", "Trades"),
            ("profit_factor", "PF"),
        ]
        print_table(results_data, columns, title=f"Strategy Comparison - {code}")

    except Exception as e:
        print_error(f"{e}", exit_code=1)


# =============================================================================
# Export Commands
# =============================================================================


@cli.group()
def export():
    """数据导出命令"""
    pass


@export.command("positions")
@click.option("--user", "-u", default="dyson", help="用户名")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "xlsx", "json"]),
    default="csv",
    help="导出格式",
)
@click.option("--output", "-o", help="输出目录")
def export_positions_cmd(user: str, format: str, output: str):
    """导出持仓数据"""
    from pathlib import Path

    from db.database import get_session
    from db.models import User
    from services.export_service import ExportConfig, ExportFormat, ExportService

    username = validate_user(None, None, user)
    if not username:
        print_error(f"User not found: {user}", exit_code=1)

    try:
        # Get user ID from database
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                print_error(f"User '{username}' not found in database", exit_code=1)
                return
            user_id = user_obj.id

        config = ExportConfig()
        if output:
            config.output_dir = Path(output)

        service = ExportService(config=config)
        export_format = ExportFormat(format)

        result = service.export_positions(user_id, format=export_format)

        if result.success:
            if result.records_exported > 0:
                print_success(
                    f"Exported {result.records_exported} positions to {result.file_path}"
                )
            else:
                print_warning("No positions found to export")
        else:
            print_error(f"Export failed: {result.error}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@export.command("trades")
@click.option("--user", "-u", default="dyson", help="用户名")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "xlsx", "json"]),
    default="csv",
    help="导出格式",
)
@click.option("--start-date", "-s", help="开始日期 (YYYY-MM-DD)")
@click.option("--end-date", "-e", help="结束日期 (YYYY-MM-DD)")
@click.option("--output", "-o", help="输出目录")
def export_trades_cmd(
    user: str, format: str, start_date: str, end_date: str, output: str
):
    """导出交易记录"""
    from datetime import datetime
    from pathlib import Path

    from db.database import get_session
    from db.models import User
    from services.export_service import (
        DateRange,
        ExportConfig,
        ExportFormat,
        ExportService,
    )

    username = validate_user(None, None, user)
    if not username:
        print_error(f"User not found: {user}", exit_code=1)

    try:
        # Get user ID from database
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                print_error(f"User '{username}' not found in database", exit_code=1)
                return
            user_id = user_obj.id

        config = ExportConfig()
        if output:
            config.output_dir = Path(output)

        service = ExportService(config=config)
        export_format = ExportFormat(format)

        # Parse dates
        date_range = DateRange()
        if start_date:
            date_range.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            date_range.end_date = datetime.strptime(end_date, "%Y-%m-%d")

        result = service.export_trades(
            user_id, format=export_format, date_range=date_range
        )

        if result.success:
            if result.records_exported > 0:
                print_success(
                    f"Exported {result.records_exported} trades to {result.file_path}"
                )
            else:
                print_warning("No trades found to export")
        else:
            print_error(f"Export failed: {result.error}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@export.command("klines")
@click.option("--code", "-c", required=True, help="股票代码 (e.g., HK.00700)")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "xlsx", "json"]),
    default="csv",
    help="导出格式",
)
@click.option("--start-date", "-s", help="开始日期 (YYYY-MM-DD)")
@click.option("--end-date", "-e", help="结束日期 (YYYY-MM-DD)")
@click.option("--limit", "-l", type=int, help="最大记录数")
@click.option("--output", "-o", help="输出目录")
def export_klines_cmd(
    code: str, format: str, start_date: str, end_date: str, limit: int, output: str
):
    """导出K线数据"""
    from datetime import datetime
    from pathlib import Path

    from services.export_service import (
        DateRange,
        ExportConfig,
        ExportFormat,
        ExportService,
    )

    try:
        config = ExportConfig()
        if output:
            config.output_dir = Path(output)

        service = ExportService(config=config)
        export_format = ExportFormat(format)

        # Parse dates
        date_range = DateRange()
        if start_date:
            date_range.start_date = datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            date_range.end_date = datetime.strptime(end_date, "%Y-%m-%d")

        result = service.export_klines(
            code, format=export_format, date_range=date_range, limit=limit
        )

        if result.success:
            if result.records_exported > 0:
                print_success(
                    f"Exported {result.records_exported} kline records to {result.file_path}"
                )
            else:
                print_warning(f"No kline data found for {code}")
        else:
            print_error(f"Export failed: {result.error}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@export.command("watchlist")
@click.option("--user", "-u", default="dyson", help="用户名")
@click.option(
    "--format",
    "-f",
    type=click.Choice(["csv", "xlsx", "json"]),
    default="csv",
    help="导出格式",
)
@click.option("--output", "-o", help="输出目录")
def export_watchlist_cmd(user: str, format: str, output: str):
    """导出关注列表"""
    from pathlib import Path

    from db.database import get_session
    from db.models import User
    from services.export_service import ExportConfig, ExportFormat, ExportService

    username = validate_user(None, None, user)
    if not username:
        print_error(f"User not found: {user}", exit_code=1)

    try:
        # Get user ID from database
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                print_error(f"User '{username}' not found in database", exit_code=1)
                return
            user_id = user_obj.id

        config = ExportConfig()
        if output:
            config.output_dir = Path(output)

        service = ExportService(config=config)
        export_format = ExportFormat(format)

        result = service.export_watchlist(user_id, format=export_format)

        if result.success:
            if result.records_exported > 0:
                print_success(
                    f"Exported {result.records_exported} watchlist items to {result.file_path}"
                )
            else:
                print_warning("No watchlist items found to export")
        else:
            print_error(f"Export failed: {result.error}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@export.command("all")
@click.option("--user", "-u", default="dyson", help="用户名")
@click.option("--output", "-o", help="输出目录")
def export_all_cmd(user: str, output: str):
    """导出所有数据到 Excel (多工作表)"""
    from pathlib import Path

    from db.database import get_session
    from db.models import User
    from services.export_service import ExportConfig, ExportFormat, ExportService

    username = validate_user(None, None, user)
    if not username:
        print_error(f"User not found: {user}", exit_code=1)

    try:
        # Get user ID from database
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                print_error(f"User '{username}' not found in database", exit_code=1)
                return
            user_id = user_obj.id

        config = ExportConfig()
        if output:
            config.output_dir = Path(output)

        service = ExportService(config=config)

        result = service.export_all(user_id, format=ExportFormat.EXCEL)

        if result.success:
            if result.records_exported > 0:
                print_success(
                    f"Exported {result.records_exported} total records to {result.file_path}"
                )
            else:
                print_warning("No data found to export")
        else:
            print_error(f"Export failed: {result.error}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


# =============================================================================
# Skill Commands
# =============================================================================


@cli.group()
def skill():
    """Skills 分析命令 (分析师/风控/教练/观察员)"""
    pass


@skill.command("list")
def skill_list():
    """列出可用的 Skills"""
    console.print("\n[bold]Available Skills[/bold]\n")

    console.print("[cyan]analyst[/cyan] - 技术分析师")
    console.print("  OBV + VCP 双核心技术分析, 评分系统")
    console.print("  Usage: skill run analyst -u <user> -c <code>")
    console.print()

    console.print("[cyan]risk[/cyan] - 风控师")
    console.print("  持仓诊断、风险预警、仓位建议")
    console.print("  Usage: skill run risk -u <user>")
    console.print()

    console.print("[cyan]coach[/cyan] - 交易导师")
    console.print("  交易计划制定、心理辅导、复利教育")
    console.print("  Usage: skill run coach -u <user> --type <daily_plan|psychology_check|compound_lesson|full_coaching>")
    console.print()

    console.print("[cyan]observer[/cyan] - 市场观察员")
    console.print("  盘前分析、盘后总结、板块轮动、情绪指数")
    console.print("  Usage: skill run observer -u <user> --type <pre_market|post_market|sector|sentiment|full|auto>")
    console.print()


@skill.command("run")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option(
    "--type",
    "-t",
    "skill_type",
    required=True,
    type=click.Choice(["analyst", "risk", "coach", "observer"]),
    help="Skill 类型",
)
@click.option("--code", "-c", help="股票代码 (单股分析时必填)")
@click.option("--codes", help="股票代码列表 (逗号分隔, 批量分析时使用)")
@click.option("--market", "-m", type=click.Choice(["HK", "US", "A"]), help="市场筛选")
@click.option("--days", "-d", default=120, help="分析天数 (默认120天)")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["markdown", "json", "text"]),
    default="markdown",
    help="输出格式",
)
@click.option("--output", "-o", help="输出文件路径")
def skill_run(
    user: str,
    skill_type: str,
    code: Optional[str],
    codes: Optional[str],
    market: Optional[str],
    days: int,
    output_format: str,
    output: Optional[str],
):
    """运行指定的 Skill"""
    from skills.shared import DataProvider, ReportBuilder, ReportFormat, SkillContext

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)

    # Parse codes
    code_list = []
    if code:
        code_list = [code]
    elif codes:
        code_list = parse_codes(codes)

    # Determine request type
    request_type = "single_stock" if len(code_list) == 1 else "batch"
    if not code_list:
        request_type = "portfolio"

    # Build context
    markets = [market] if market else ["HK", "US", "A"]
    context = SkillContext(
        user_id=db_user.id,
        request_type=request_type,
        parameters={"days": days},
        codes=code_list,
        markets=markets,
    )

    print_info(f"Running {skill_type} skill for user '{user}'...")

    try:
        # Map output format
        format_map = {
            "markdown": ReportFormat.MARKDOWN,
            "json": ReportFormat.JSON,
            "text": ReportFormat.TEXT,
        }
        report_format = format_map.get(output_format, ReportFormat.MARKDOWN)

        # Execute skill based on type
        if skill_type == "analyst":
            result = _run_analyst_skill(context, report_format)
        elif skill_type == "risk":
            result = _run_risk_skill(context, report_format)
        elif skill_type == "coach":
            result = _run_coach_skill(context, report_format)
        elif skill_type == "observer":
            result = _run_observer_skill(context, report_format)
        else:
            print_error(f"Unknown skill type: {skill_type}", exit_code=1)
            return

        # Handle result
        if not result.success:
            print_error(f"Skill execution failed: {result.error_message}", exit_code=1)
            return

        # Output report
        if output:
            Path(output).write_text(result.report_content)
            print_success(f"Report saved to {output}")
        else:
            console.print(result.report_content)

        # Show next actions if any
        if result.next_actions:
            console.print("\n[bold yellow]Suggested Next Actions:[/bold yellow]")
            for action in result.next_actions:
                console.print(f"  - {action}")

    except Exception as e:
        logger.exception("Skill execution error")
        print_error(f"{e}", exit_code=1)


def _run_analyst_skill(context, report_format):
    """Run the analyst skill with OBV + VCP analysis."""
    from skills.analyst import (
        BatchAnalyzer,
        StockAnalyzer,
        generate_analysis_report,
        generate_batch_report,
    )
    from skills.shared import DataProvider, SkillResult

    provider = DataProvider()
    days = context.get_param("days", 120)

    # Single stock analysis
    if context.codes and len(context.codes) == 1:
        full_code = context.codes[0]
        if "." in full_code:
            market, code = full_code.split(".", 1)
        else:
            market = "HK" if full_code.isdigit() else "US"
            code = full_code

        # Get stock name from positions or watchlist
        stock_name = ""
        positions = provider.get_positions(context.user_id, [market])
        for p in positions:
            if p.code == code:
                stock_name = p.stock_name
                break
        if not stock_name:
            watchlist = provider.get_watchlist(context.user_id, [market])
            for w in watchlist:
                if w.code == code:
                    stock_name = w.stock_name
                    break

        # Run single stock analysis
        analyzer = StockAnalyzer(data_provider=provider)
        analysis = analyzer.analyze_from_db(market, code, days=days, stock_name=stock_name)

        if analysis is None:
            return SkillResult.error(
                "analyst",
                f"No K-line data available for {market}.{code}. Run 'sync klines' first.",
            )

        report = generate_analysis_report(analysis, report_format)

        return SkillResult.ok(
            skill_name="analyst",
            result_type="single_stock_analysis",
            data=analysis.to_dict(),
            report_content=report,
            next_actions=_get_analyst_next_actions(analysis),
        )

    # Batch analysis
    batch_analyzer = BatchAnalyzer(data_provider=provider, days=days)

    if context.codes:
        # Analyze specific codes
        result = batch_analyzer.analyze_codes(context.codes)
    else:
        # Analyze user's positions and watchlist
        result = batch_analyzer.analyze_user_stocks(
            user_id=context.user_id,
            include_positions=True,
            include_watchlist=True,
            markets=context.markets if context.markets != ["HK", "US", "A"] else None,
        )

    if result.successful == 0 and result.failed > 0:
        return SkillResult.error(
            "analyst",
            f"Failed to analyze any stocks. {result.failed} failures. Check K-line data.",
        )

    report = generate_batch_report(result, report_format)

    return SkillResult.ok(
        skill_name="analyst",
        result_type="batch_analysis",
        data=result.to_dict(),
        report_content=report,
        next_actions=[
            f"Analyzed {result.successful} stocks successfully",
            f"Strong Buy: {len(result.strong_buy)}, Buy: {len(result.buy)}",
            "Run 'skill run analyst -c <code>' for detailed single stock analysis",
        ],
    )


def _get_analyst_next_actions(analysis) -> list[str]:
    """Generate next action suggestions based on analysis result."""
    actions = []
    score = analysis.technical_score

    if score.rating.value == "strong_buy":
        if analysis.vcp_analysis.stage.value == "breakout":
            actions.append("VCP breakout in progress - consider entry if within risk tolerance")
        elif analysis.vcp_analysis.stage.value == "mature":
            actions.append(f"Watch for breakout above pivot: {score.pivot_price:.2f}" if score.pivot_price else "Watch for breakout")
        actions.append("Set stop loss at 7-8% below entry")
    elif score.rating.value == "buy":
        if analysis.vcp_analysis.detected:
            actions.append("VCP forming - add to watchlist for breakout")
        else:
            actions.append("Positive technicals - look for pullback entry")
    elif score.rating.value == "hold":
        if analysis.obv_analysis.divergence.value == "bullish":
            actions.append("Bullish divergence forming - monitor for reversal")
        elif analysis.obv_analysis.divergence.value == "bearish":
            actions.append("Bearish divergence warning - tighten stops")
        else:
            actions.append("Wait for clearer signal")
    elif score.rating.value in ("sell", "strong_sell"):
        actions.append("Consider reducing position or exiting")
        actions.append("Review risk management")

    # Add key levels if available
    if score.key_levels:
        actions.append(f"Key levels: {', '.join(score.key_levels)}")

    return actions


def _run_risk_skill(context, report_format):
    """Run the risk controller skill for portfolio risk analysis."""
    from skills.risk_controller import RiskController, generate_risk_report
    from skills.shared import DataProvider, SkillResult

    provider = DataProvider()

    # Create risk controller
    controller = RiskController(data_provider=provider)

    # Run risk analysis
    result = controller.analyze_portfolio_risk(
        user_id=context.user_id,
        markets=context.markets if context.markets != ["HK", "US", "A"] else None,
    )

    if result.portfolio_value == 0:
        return SkillResult.error(
            "risk_controller",
            "No positions found. Sync positions first with 'sync positions'.",
        )

    # Generate report
    report = generate_risk_report(result, report_format)

    # Build next actions
    next_actions = result.priority_actions.copy() if result.priority_actions else []
    next_actions.append(
        f"Risk Level: {result.overall_risk_level.value.upper()}, "
        f"Health: {result.health_score:.0f}/100, "
        f"Risk: {result.risk_score:.0f}/100"
    )

    if result.alerts.critical_count > 0:
        next_actions.insert(0, f"{result.alerts.critical_count} CRITICAL alert(s) require immediate attention!")

    return SkillResult.ok(
        skill_name="risk_controller",
        result_type="portfolio_risk_analysis",
        data=result.to_dict(),
        report_content=report,
        next_actions=next_actions,
    )


def _run_coach_skill(context, report_format):
    """Run the trading coach skill for trading guidance."""
    from skills.shared import DataProvider, SkillResult
    from skills.trading_coach import TradingCoach

    provider = DataProvider()

    # Create trading coach
    coach = TradingCoach(data_provider=provider)

    # Determine request type based on context
    # Default to full_coaching, or use parameters
    request_type = context.get_param("type", "full_coaching")
    context.request_type = request_type

    # Execute coaching session
    result = coach.execute(context)

    if not result.success:
        return SkillResult.error("trading_coach", result.error_message)

    # Build next actions from result
    next_actions = result.next_actions.copy() if result.next_actions else []

    # Add coaching summary
    if result.data:
        coaching_result = result.data
        if hasattr(coaching_result, "trading_plan") and coaching_result.trading_plan:
            plan = coaching_result.trading_plan
            must_do = len(plan.must_do_actions)
            warnings = len(plan.risk_warnings)
            if must_do > 0:
                next_actions.insert(0, f"{must_do} 项必做操作需要执行")
            if warnings > 0:
                next_actions.insert(0, f"{warnings} 项风险警示需要关注")

    return SkillResult.ok(
        skill_name="trading_coach",
        result_type=request_type,
        data=result.data,
        report_content=result.report_content,
        next_actions=next_actions,
    )


def _run_observer_skill(context, report_format):
    """Run the market observer skill for market analysis."""
    from skills.market_observer import MarketObserver
    from skills.shared import DataProvider, SkillResult

    provider = DataProvider()

    # Create market observer
    observer = MarketObserver(data_provider=provider)

    # Determine request type based on context parameters
    # Options: pre_market, post_market, sector, sentiment, full, auto
    request_type = context.get_param("type", "auto")
    context.request_type = request_type

    # Execute observation
    result = observer.execute(context)

    if not result.success:
        return SkillResult.error("market_observer", result.error_message)

    # Build next actions from result
    next_actions = result.next_actions.copy() if result.next_actions else []

    # Add observation summary
    if result.data:
        obs_result = result.data
        if hasattr(obs_result, "sentiment_result") and obs_result.sentiment_result:
            sentiment = obs_result.sentiment_result
            next_actions.insert(
                0,
                f"Market Sentiment: {sentiment.level.value} ({sentiment.score:.0f}/100)",
            )

    return SkillResult.ok(
        skill_name="market_observer",
        result_type=request_type,
        data=result.data,
        report_content=result.report_content,
        next_actions=next_actions,
    )


@skill.command("info")
@click.argument(
    "skill_type", type=click.Choice(["analyst", "risk", "coach", "observer"])
)
def skill_info(skill_type: str):
    """显示 Skill 详细信息"""
    info = {
        "analyst": {
            "name": "技术分析师 (Analyst)",
            "description": "基于 OBV + VCP 双核心的技术分析系统",
            "capabilities": [
                "single_stock_analysis - 单股技术分析",
                "batch_scan - 批量扫描筛选",
                "portfolio_overview - 持仓技术状态总览",
            ],
            "indicators": [
                "OBV (On-Balance Volume) - 能量潮, 检测资金流向",
                "VCP (Volatility Contraction Pattern) - 波动收缩形态",
            ],
            "scoring": "OBV (40%) + VCP (60%) = 综合技术评分",
        },
        "risk": {
            "name": "风控师 (Risk Controller)",
            "description": "投资组合风险管理系统",
            "capabilities": [
                "position_monitor - 持仓诊断 (止损/仓位/盈亏状态)",
                "risk_calculator - 风险计算 (集中度/止损覆盖/杠杆)",
                "alert_generator - 风险预警生成",
            ],
            "metrics": [
                "HHI Index - 集中度指数 (0-10000)",
                "Health Score - 健康评分 (0-100)",
                "Risk Score - 风险评分 (0-100)",
            ],
        },
        "coach": {
            "name": "交易导师 (Trading Coach)",
            "description": "交易计划制定、心理辅导、复利教育",
            "capabilities": [
                "daily_plan - 今日交易计划生成",
                "psychology_check - 交易心理状态检查",
                "compound_lesson - 复利教育课程",
                "position_review - 持仓操作建议",
                "full_coaching - 完整教练会话",
            ],
            "components": [
                "PlanGenerator - 交易计划和检查清单",
                "PsychologyCoach - 情绪评估和行为分析",
                "CompoundEducator - 复利计算和财富规划",
            ],
        },
        "observer": {
            "name": "市场观察员 (Market Observer)",
            "description": "盘前分析、盘后总结、板块轮动、情绪指数",
            "capabilities": [
                "pre_market - 盘前分析 (全球市场、重大事件、风险预警)",
                "post_market - 盘后总结 (组合盈亏、异动提醒、经验总结)",
                "sector - 板块轮动 (强弱板块、资金流向、轮动信号)",
                "sentiment - 情绪指数 (0-100评分、VIX解读、策略建议)",
                "full - 完整观察 (包含以上所有内容)",
                "auto - 自动检测 (根据市场时间选择合适的分析类型)",
            ],
            "components": [
                "PreMarketAnalyzer - 隔夜市场、事件检测、交易准备",
                "PostMarketSummarizer - 盈亏统计、异动分析、明日关注",
                "SectorRotationAnalyzer - 板块排行、轮动信号、配置建议",
                "SentimentMeter - 多维度指标、情绪评分、交易策略",
            ],
        },
    }

    skill_info = info.get(skill_type, {})

    console.print(f"\n[bold cyan]{skill_info.get('name', skill_type)}[/bold cyan]")
    console.print(f"\n{skill_info.get('description', 'No description')}\n")

    if "capabilities" in skill_info:
        console.print("[bold]Capabilities:[/bold]")
        for cap in skill_info["capabilities"]:
            console.print(f"  - {cap}")
        console.print()

    if "indicators" in skill_info:
        console.print("[bold]Technical Indicators:[/bold]")
        for ind in skill_info["indicators"]:
            console.print(f"  - {ind}")
        console.print()

    if "metrics" in skill_info:
        console.print("[bold]Metrics:[/bold]")
        for metric in skill_info["metrics"]:
            console.print(f"  - {metric}")
        console.print()

    if "components" in skill_info:
        console.print("[bold]Components:[/bold]")
        for comp in skill_info["components"]:
            console.print(f"  - {comp}")
        console.print()

    if "scoring" in skill_info:
        console.print(f"[bold]Scoring:[/bold] {skill_info['scoring']}\n")

    if "status" in skill_info:
        console.print(f"[yellow]Status: {skill_info['status']}[/yellow]\n")


# =============================================================================
# Workflow Commands
# =============================================================================


@cli.group()
def workflow():
    """工作流命令 - 每日/月度自动化分析"""
    pass


def _save_workflow_report(
    report: str,
    workflow_type: str,
    phase: str = None,
    output: str = None,
    save: bool = False,
) -> str | None:
    """
    Save workflow report to file.

    Args:
        report: Report content (Markdown)
        workflow_type: Type of workflow (daily, monthly, auto)
        phase: Workflow phase (pre_market, post_market, auto)
        output: Custom output path
        save: Auto-generate filename if True

    Returns:
        Path to saved file or None
    """
    from datetime import datetime
    from pathlib import Path

    if not output and not save:
        return None

    # Determine output path
    if output:
        output_path = Path(output)
    else:
        # Auto-generate filename
        output_dir = Path("reports/output")
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        phase_suffix = f"_{phase}" if phase and phase != "auto" else ""
        filename = f"workflow_{workflow_type}{phase_suffix}_{timestamp}.md"
        output_path = output_dir / filename

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write report
    output_path.write_text(report, encoding="utf-8")

    return str(output_path)


@workflow.command("run")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option(
    "--type",
    "-t",
    "workflow_type",
    type=click.Choice(["daily", "monthly", "auto"]),
    default="auto",
    help="工作流类型",
)
@click.option("--market", "-m", default="HK", help="市场代码")
@click.option(
    "--phase",
    "-p",
    type=click.Choice(["pre_market", "post_market", "auto"]),
    default="auto",
    help="工作流阶段 (仅 daily)",
)
@click.option("--force", "-f", is_flag=True, help="强制执行 (忽略时间检查)")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--save", "-s", is_flag=True, help="自动保存到 reports/output/")
def workflow_run(
    user: str,
    workflow_type: str,
    market: str,
    phase: str,
    force: bool,
    output: str,
    save: bool,
):
    """执行工作流"""
    from db.database import get_session
    from db.models import User
    from skills.shared import SkillContext
    from skills.workflow import WorkflowEngine

    try:
        # Get user ID
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == user).first()
            if not user_obj:
                print_error(f"User '{user}' not found", exit_code=1)
                return
            user_id = user_obj.id

        # Create context
        context = SkillContext(
            user_id=user_id,
            request_type=workflow_type,
            markets=[market],
            parameters={
                "phase": phase,
                "force": force,
            },
        )

        # Run workflow
        engine = WorkflowEngine()
        result = engine.execute(context)

        if result.success:
            console.print(result.report_content)
            console.print()

            # Save report if requested
            saved_path = _save_workflow_report(
                result.report_content,
                workflow_type,
                phase,
                output,
                save,
            )
            if saved_path:
                print_success(f"报告已保存到: {saved_path}")

            if result.next_actions:
                console.print("[bold]Next Actions:[/bold]")
                for action in result.next_actions:
                    console.print(f"  - {action}")
        else:
            print_error(f"Workflow failed: {result.error_message}", exit_code=1)

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@workflow.command("daily")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--market", "-m", default="HK", help="市场代码")
@click.option(
    "--phase",
    "-p",
    type=click.Choice(["pre_market", "post_market", "auto"]),
    default="auto",
    help="工作流阶段",
)
@click.option("--output", "-o", help="输出文件路径")
@click.option("--save", "-s", is_flag=True, help="自动保存到 reports/output/")
def workflow_daily(user: str, market: str, phase: str, output: str, save: bool):
    """执行每日工作流"""
    from db.database import get_session
    from db.models import User
    from skills.workflow import run_daily_workflow

    try:
        # Get user ID
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == user).first()
            if not user_obj:
                print_error(f"User '{user}' not found", exit_code=1)
                return
            user_id = user_obj.id

        report = run_daily_workflow(
            user_id=user_id,
            phase=phase,
            markets=[market],
        )

        console.print(report)

        # Save report if requested
        saved_path = _save_workflow_report(report, "daily", phase, output, save)
        if saved_path:
            print_success(f"报告已保存到: {saved_path}")

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@workflow.command("monthly")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--market", "-m", default="HK", help="市场代码")
@click.option("--force", "-f", is_flag=True, help="强制执行 (非月末)")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--save", "-s", is_flag=True, help="自动保存到 reports/output/")
def workflow_monthly(user: str, market: str, force: bool, output: str, save: bool):
    """执行月度工作流"""
    from db.database import get_session
    from db.models import User
    from skills.workflow import run_monthly_workflow

    try:
        # Get user ID
        with get_session() as session:
            user_obj = session.query(User).filter(User.username == user).first()
            if not user_obj:
                print_error(f"User '{user}' not found", exit_code=1)
                return
            user_id = user_obj.id

        report = run_monthly_workflow(
            user_id=user_id,
            markets=[market],
            force=force,
        )

        console.print(report)

        # Save report if requested
        saved_path = _save_workflow_report(report, "monthly", None, output, save)
        if saved_path:
            print_success(f"报告已保存到: {saved_path}")

    except Exception as e:
        print_error(f"{e}", exit_code=1)


@workflow.command("status")
@click.option("--market", "-m", default="HK", help="市场代码")
def workflow_status(market: str):
    """显示工作流调度状态"""
    from skills.workflow import WorkflowEngine

    try:
        engine = WorkflowEngine()
        info = engine.get_schedule_info(market)

        console.print(f"\n[bold cyan]Workflow Status - {market}[/bold cyan]\n")

        console.print(f"Current Phase: [bold]{info['current_phase']}[/bold]")
        console.print(f"Next Phase: {info['next_phase']}")
        if info['next_phase_time']:
            console.print(f"Next Phase Time: {info['next_phase_time']}")
        console.print(f"Is Trading Day: {'Yes' if info['is_trading_day'] else 'No'}")
        console.print(f"Is Month End: {'Yes' if info['is_month_end'] else 'No'}")
        console.print()

    except Exception as e:
        print_error(f"{e}", exit_code=1)


# =============================================================================
# Deep Analysis Command
# =============================================================================


@cli.command("deep-analyze")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--code", "-c", help="股票代码 (如 HK.00700)")
@click.option("--codes", help="股票代码列表 (逗号分隔)")
@click.option(
    "--market",
    "-m",
    type=click.Choice(["HK", "US", "A"], case_sensitive=False),
    help="市场代码，批量分析该市场所有关注股票",
)
@click.option("--no-web", is_flag=True, help="不获取网络数据 (仅技术分析)")
@click.option("--output", "-o", help="输出文件路径")
@click.option("--save", "-s", is_flag=True, help="自动保存到 reports/output/")
def deep_analyze(
    user: str,
    code: Optional[str],
    codes: Optional[str],
    market: Optional[str],
    no_web: bool,
    output: Optional[str],
    save: bool,
):
    """
    深度分析 - 综合技术面、基本面、行业和新闻的完整分析报告

    适合追求复利增长的趋势交易者，综合多维度分析生成投资建议。

    Examples:
        python main.py deep-analyze -u dyson -c HK.00700
        python main.py deep-analyze -u dyson -c HK.00981 --save
        python main.py deep-analyze -u dyson --codes "HK.00700,HK.00981" -o report.md
        python main.py deep-analyze -u dyson --market HK --save
        python main.py deep-analyze -u dyson -m US -s
    """
    from datetime import datetime
    from pathlib import Path

    from skills.deep_analyzer import DeepAnalyzer, generate_deep_analysis_report
    from skills.shared import DataProvider

    db_user = get_user_by_name(user)
    if not db_user:
        print_error(f"User '{user}' not found in database.", exit_code=1)
        return

    # Initialize data provider early for market option
    data_provider = DataProvider()

    # Parse codes
    code_list = []
    selected_market = None

    if code:
        code_list = [code]
    elif codes:
        code_list = parse_codes(codes)
    elif market:
        # Fetch all stocks from positions and watchlist for the specified market
        selected_market = market.upper()

        # Map A-share market codes
        market_filters = [selected_market]
        if selected_market == "A":
            market_filters = ["A", "SH", "SZ"]

        # Get position codes (exclude options/warrants)
        positions = data_provider.get_positions(db_user.id, market_filters)
        pos_codes = set()
        for p in positions:
            # Skip options/warrants
            if _is_option_code(p.market, p.code):
                continue
            pos_codes.add(f"{p.market}.{p.code}")

        # Get watchlist codes (exclude indices)
        watchlist = data_provider.get_watchlist(
            db_user.id, market_filters, exclude_indices=True
        )
        watch_codes = set()
        for w in watchlist:
            # Use original market prefix for A-shares
            if w.market == "A":
                # Determine SH or SZ based on code
                if w.code.startswith("6"):
                    watch_codes.add(f"SH.{w.code}")
                else:
                    watch_codes.add(f"SZ.{w.code}")
            else:
                watch_codes.add(f"{w.market}.{w.code}")

        code_list = sorted(pos_codes | watch_codes)

        if code_list:
            print_info(
                f"找到 {len(code_list)} 只 {selected_market} 股票 "
                f"(持仓: {len(pos_codes)}, 关注: {len(watch_codes - pos_codes)})"
            )
        else:
            print_warning(f"未找到 {selected_market} 市场的股票")
            return

    if not code_list:
        print_error("请指定 --code, --codes 或 --market 选项", exit_code=1)
        return

    # Initialize analyzer (data_provider already created above)
    analyzer = DeepAnalyzer(data_provider)

    reports = []
    for full_code in code_list:
        # Parse market and code
        if "." in full_code:
            market, stock_code = full_code.split(".", 1)
        else:
            market = "HK" if full_code.isdigit() else "US"
            stock_code = full_code

        print_info(f"深度分析 {market}.{stock_code}...")

        try:
            # Get stock name from positions or watchlist
            stock_name = ""
            positions = data_provider.get_positions(db_user.id, [market])
            for p in positions:
                if p.code == stock_code:
                    stock_name = p.stock_name
                    break
            if not stock_name:
                watchlist = data_provider.get_watchlist(db_user.id, [market])
                for w in watchlist:
                    if w.code == stock_code:
                        stock_name = w.stock_name
                        break

            # Run analysis
            result = analyzer.analyze(
                market=market,
                code=stock_code,
                stock_name=stock_name,
                user_id=db_user.id,
                include_web_data=not no_web,
            )

            if result.success:
                report = generate_deep_analysis_report(result)
                reports.append(report)

                # Print to console if not saving
                if not output and not save:
                    console.print(report)
                    console.print("\n" + "=" * 80 + "\n")

                print_success(
                    f"{market}.{stock_code} 分析完成 - "
                    f"综合评分: {result.overall_score}/100 ({result.overall_rating})"
                )
            else:
                print_warning(f"{market}.{stock_code} 分析失败: {', '.join(result.errors)}")

        except Exception as e:
            logger.exception(f"Error analyzing {full_code}")
            print_warning(f"{full_code} 分析出错: {e}")

    # Save reports if requested
    if (output or save) and reports:
        combined_report = "\n\n---\n\n".join(reports)

        if output:
            output_path = Path(output)
        else:
            # Auto-generate filename
            output_dir = Path("reports/output")
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
            if len(code_list) == 1:
                filename = f"deep_analysis_{code_list[0].replace('.', '_')}_{timestamp}.md"
            elif selected_market:
                filename = f"deep_analysis_{selected_market}_{timestamp}.md"
            else:
                filename = f"deep_analysis_batch_{timestamp}.md"
            output_path = output_dir / filename

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(combined_report, encoding="utf-8")
        print_success(f"报告已保存到: {output_path}")


if __name__ == "__main__":
    cli()
