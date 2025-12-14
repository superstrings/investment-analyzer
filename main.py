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

from config import ConfigurationError, get_users_config, settings
from db import User, Account, Position, get_session, check_connection, init_db

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
@click.option("--days", default=90, help="同步交易历史天数")
@click.option("--kline-days", default=120, help="同步K线天数")
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
        click.echo(f"Error: User '{user}' not found in database. Run 'db seed' first.", err=True)
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
                status = click.style("OK", fg="green") if result.success else click.style("FAILED", fg="red")
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
                    click.style("Success: ", fg="green") +
                    f"Synced {result.records_synced} positions, skipped {result.records_skipped}"
                )
            else:
                click.echo(click.style(f"Error: {result.error_message}", fg="red"), err=True)
                sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@sync.command("trades")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=90, help="同步天数")
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
                    click.style("Success: ", fg="green") +
                    f"Synced {result.records_synced} trades, skipped {result.records_skipped}"
                )
            else:
                click.echo(click.style(f"Error: {result.error_message}", fg="red"), err=True)
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
                click.style("Success: ", fg="green") +
                f"Synced {result.records_synced} K-lines, skipped {result.records_skipped}"
            )
        else:
            click.echo(click.style(f"Error: {result.error_message}", fg="red"), err=True)
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
@click.option("--style", default="dark", type=click.Choice(["dark", "light", "chinese", "western"]), help="图表样式")
@click.option("--indicators", "-i", default="ma", help="技术指标 (ma,obv,macd,rsi,bb 逗号分隔)")
@click.option("--output", "-o", default=None, help="输出文件路径")
def chart_single(code: str, days: int, style: str, indicators: str, output: Optional[str]):
    """生成单只股票K线图"""
    from fetchers import KlineFetcher
    from charts import ChartGenerator, ChartConfig

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
            click.echo(click.style("Success: ", fg="green") + f"Chart saved to {chart_path}")
        else:
            click.echo(click.style("Error: ", fg="red") + "Failed to generate chart", err=True)
            sys.exit(1)

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@chart.command("watchlist")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=120, help="K线天数")
@click.option("--style", default="dark", type=click.Choice(["dark", "light", "chinese", "western"]), help="图表样式")
def chart_watchlist(user: str, days: int, style: str):
    """为关注列表生成图表"""
    from fetchers import KlineFetcher
    from charts import ChartGenerator, ChartConfig
    from db import WatchlistItem

    click.echo(f"Generating charts for {user}'s watchlist...")

    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Get watchlist items
    with get_session() as session:
        watchlist = session.query(WatchlistItem).filter_by(user_id=db_user.id).all()
        codes = [item.code for item in watchlist]

    if not codes:
        click.echo(f"No items in watchlist for user '{user}'")
        return

    click.echo(f"Found {len(codes)} stocks in watchlist")

    try:
        fetcher = KlineFetcher()
        generator = ChartGenerator(style=style)
        config = ChartConfig(
            ma_periods=[5, 10, 20, 60],
            show_volume=True,
            last_n_days=days,
        )

        output_dir = settings.chart.output_dir / user
        output_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        for code in codes:
            result = fetcher.fetch(code, days=days)
            if result.success and result.df is not None and not result.df.empty:
                output_path = output_dir / f"{code.replace('.', '_')}.png"
                chart_path = generator.generate(
                    df=result.df,
                    title=code,
                    output_path=output_path,
                    config=config,
                )
                if chart_path:
                    success_count += 1
                    click.echo(f"  Generated: {code}")
            else:
                click.echo(f"  Skipped: {code} (no data)")

        click.echo(
            click.style("Done: ", fg="green") +
            f"Generated {success_count}/{len(codes)} charts in {output_dir}"
        )

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@chart.command("positions")
@click.option("--user", "-u", required=True, callback=validate_user, help="用户名")
@click.option("--days", default=120, help="K线天数")
@click.option("--style", default="dark", type=click.Choice(["dark", "light", "chinese", "western"]), help="图表样式")
def chart_positions(user: str, days: int, style: str):
    """为持仓股票生成图表"""
    from fetchers import KlineFetcher
    from charts import ChartGenerator, ChartConfig

    click.echo(f"Generating charts for {user}'s positions...")

    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Get position codes
    with get_session() as session:
        positions = session.query(Position).join(Account).filter(Account.user_id == db_user.id).all()
        codes = list(set(p.code for p in positions if p.qty > 0))

    if not codes:
        click.echo(f"No active positions for user '{user}'")
        return

    click.echo(f"Found {len(codes)} stocks in positions")

    try:
        fetcher = KlineFetcher()
        generator = ChartGenerator(style=style)
        config = ChartConfig(
            ma_periods=[5, 10, 20, 60],
            show_volume=True,
            last_n_days=days,
        )

        output_dir = settings.chart.output_dir / user / "positions"
        output_dir.mkdir(parents=True, exist_ok=True)

        success_count = 0
        for code in codes:
            result = fetcher.fetch(code, days=days)
            if result.success and result.df is not None and not result.df.empty:
                output_path = output_dir / f"{code.replace('.', '_')}.png"
                chart_path = generator.generate(
                    df=result.df,
                    title=code,
                    output_path=output_path,
                    config=config,
                )
                if chart_path:
                    success_count += 1
                    click.echo(f"  Generated: {code}")
            else:
                click.echo(f"  Skipped: {code} (no data)")

        click.echo(
            click.style("Done: ", fg="green") +
            f"Generated {success_count}/{len(codes)} charts in {output_dir}"
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
def report_portfolio(user: str, output: Optional[str]):
    """生成持仓报告"""
    click.echo(f"Generating portfolio report for user '{user}'...")

    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Get positions summary
    with get_session() as session:
        positions = (
            session.query(Position)
            .join(Account)
            .filter(Account.user_id == db_user.id, Position.qty > 0)
            .all()
        )

        if not positions:
            click.echo("No active positions found.")
            return

        # Display simple report
        click.echo("\n" + "=" * 60)
        click.echo(f"Portfolio Report for {user}")
        click.echo("=" * 60)

        total_market_value = 0
        total_pnl = 0

        for pos in positions:
            market_value = float(pos.qty * pos.price) if pos.price else 0
            pnl = float(pos.pl_val) if pos.pl_val else 0
            pnl_pct = float(pos.pl_pct) if pos.pl_pct else 0

            total_market_value += market_value
            total_pnl += pnl

            pnl_color = "green" if pnl >= 0 else "red"
            click.echo(
                f"\n{pos.code} ({pos.name or 'N/A'})"
                f"\n  Qty: {pos.qty:,.0f} @ {pos.cost_price or 0:.2f}"
                f"\n  Market Value: {market_value:,.2f}"
                f"\n  P&L: " + click.style(f"{pnl:+,.2f} ({pnl_pct:+.2f}%)", fg=pnl_color)
            )

        click.echo("\n" + "-" * 60)
        pnl_color = "green" if total_pnl >= 0 else "red"
        click.echo(f"Total Market Value: {total_market_value:,.2f}")
        click.echo("Total P&L: " + click.style(f"{total_pnl:+,.2f}", fg=pnl_color))
        click.echo("=" * 60)


@report.command("technical")
@click.option("--code", "-c", required=True, help="股票代码")
@click.option("--days", default=120, help="分析天数")
def report_technical(code: str, days: int):
    """生成技术分析报告"""
    from fetchers import KlineFetcher
    from analysis import TechnicalAnalyzer, AnalysisConfig

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
def account_list(user: str):
    """列出用户账户"""
    db_user = get_user_by_name(user)
    if not db_user:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    with get_session() as session:
        accounts = session.query(Account).filter_by(user_id=db_user.id).all()

        if not accounts:
            click.echo(f"No accounts found for user '{user}'")
            return

        click.echo(f"\nAccounts for {user}:")
        click.echo("-" * 50)
        for acc in accounts:
            click.echo(
                f"  [{acc.market}] {acc.futu_acc_id} "
                f"({acc.account_type or 'N/A'}) "
                f"{'Active' if acc.is_active else 'Inactive'}"
            )


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
    click.echo("Checking database connection...")
    try:
        if check_connection():
            click.echo(click.style("Success: ", fg="green") + "Database connection OK")
        else:
            click.echo(click.style("Error: ", fg="red") + "Database connection failed")
            sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@db.command("init")
@click.option("--force", is_flag=True, help="强制重建表")
def db_init(force: bool):
    """初始化数据库表"""
    click.echo("Initializing database...")
    if force:
        click.echo("Warning: This will drop all existing tables!")
        if not click.confirm("Continue?"):
            return

    try:
        init_db()
        click.echo(click.style("Success: ", fg="green") + "Database initialized")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


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

            click.echo(click.style("Success: ", fg="green") + f"Created user '{user}' (id={db_user.id})")

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
# Config Commands
# =============================================================================


@cli.group()
def config():
    """配置管理命令"""
    pass


@config.command("show")
def config_show():
    """显示当前配置"""
    click.echo("\n=== Current Configuration ===\n")

    click.echo("Database:")
    click.echo(f"  URL: {settings.database.url}")
    click.echo(f"  Pool Size: {settings.database.pool_size}")

    click.echo("\nFutu OpenD:")
    click.echo(f"  Default Host: {settings.futu.default_host}")
    click.echo(f"  Default Port: {settings.futu.default_port}")

    click.echo("\nChart:")
    click.echo(f"  Output Dir: {settings.chart.output_dir}")
    click.echo(f"  DPI: {settings.chart.dpi}")
    click.echo(f"  MAV Periods: {settings.chart.mav}")

    click.echo("\nK-line:")
    click.echo(f"  Default Days: {settings.kline.default_days}")
    click.echo(f"  Markets: {settings.kline.markets}")


@config.command("users")
def config_users():
    """列出配置的用户"""
    users_config = get_users_config()
    usernames = users_config.list_usernames()

    if not usernames:
        click.echo("No users configured. Edit config/users.yaml to add users.")
        return

    click.echo("\nConfigured Users:")
    click.echo("-" * 40)
    for username in usernames:
        user = users_config.get_user(username)
        status = click.style("Active", fg="green") if user.is_active else click.style("Inactive", fg="yellow")
        click.echo(f"  {username} ({user.display_name}) - {status}")
        click.echo(f"    OpenD: {user.opend.host}:{user.opend.port}")
        click.echo(f"    Markets: {', '.join(user.default_markets)}")


if __name__ == "__main__":
    cli()
