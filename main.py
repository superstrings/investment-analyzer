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


if __name__ == "__main__":
    cli()
