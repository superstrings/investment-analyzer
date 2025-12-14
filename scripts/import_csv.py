#!/usr/bin/env python3
"""
CSV Data Import Script for Investment Analyzer.

Supports importing:
- Watchlist items
- Positions
- Trades

Usage:
    python scripts/import_csv.py watchlist --user dyson --file watchlist.csv
    python scripts/import_csv.py positions --user dyson --account 12345 --file positions.csv
    python scripts/import_csv.py trades --user dyson --account 12345 --file trades.csv

CSV Format Examples:

Watchlist CSV:
    code,name,group,notes
    HK.00700,腾讯控股,科技股,核心持仓
    US.NVDA,英伟达,AI概念,关注

Positions CSV:
    code,name,qty,cost_price,market_price
    HK.00700,腾讯控股,100,350.00,380.00
    US.NVDA,英伟达,50,500.00,550.00

Trades CSV:
    deal_id,trade_time,code,name,side,qty,price,amount,fee
    D123456,2024-01-15 10:30:00,HK.00700,腾讯控股,BUY,100,350.00,35000.00,50.00
"""

import csv
import logging
import sys
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Callable, Optional

import click

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import get_users_config
from db import Account, Position, Trade, User, WatchlistItem, get_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# =============================================================================
# Column Mapping Configuration
# =============================================================================

# Watchlist column aliases (supports both Chinese and English)
WATCHLIST_COLUMN_MAP = {
    "code": ["code", "股票代码", "代码", "symbol"],
    "name": ["name", "股票名称", "名称", "stock_name"],
    "group": ["group", "group_name", "分组", "组"],
    "notes": ["notes", "备注", "note", "comment"],
}

# Position column aliases
POSITION_COLUMN_MAP = {
    "code": ["code", "股票代码", "代码", "symbol"],
    "name": ["name", "股票名称", "名称", "stock_name"],
    "qty": ["qty", "数量", "quantity", "持仓数量", "shares"],
    "cost_price": ["cost_price", "成本价", "cost", "avg_cost", "均价"],
    "market_price": ["market_price", "市价", "price", "current_price", "现价"],
    "market_val": ["market_val", "市值", "market_value", "value"],
    "pl_val": ["pl_val", "盈亏", "pnl", "profit_loss", "盈亏金额"],
    "pl_ratio": ["pl_ratio", "盈亏比例", "pnl_ratio", "profit_ratio", "收益率"],
}

# Trade column aliases
TRADE_COLUMN_MAP = {
    "deal_id": ["deal_id", "成交编号", "deal_no", "trade_id"],
    "order_id": ["order_id", "订单编号", "order_no"],
    "trade_time": ["trade_time", "成交时间", "time", "datetime", "date"],
    "code": ["code", "股票代码", "代码", "symbol"],
    "name": ["name", "股票名称", "名称", "stock_name"],
    "side": ["side", "trd_side", "方向", "买卖方向", "direction"],
    "qty": ["qty", "数量", "quantity", "成交数量", "shares"],
    "price": ["price", "成交价", "deal_price", "价格"],
    "amount": ["amount", "成交金额", "total", "金额"],
    "fee": ["fee", "手续费", "commission", "费用"],
}


@dataclass
class ImportResult:
    """Result of an import operation."""

    success: bool
    imported: int = 0
    skipped: int = 0
    errors: int = 0
    error_messages: list[str] = field(default_factory=list)

    def add_error(self, message: str):
        """Add error message."""
        self.errors += 1
        self.error_messages.append(message)


def find_column(headers: list[str], aliases: list[str]) -> Optional[str]:
    """Find a column in headers by checking aliases."""
    headers_lower = [h.lower().strip() for h in headers]
    for alias in aliases:
        if alias.lower() in headers_lower:
            idx = headers_lower.index(alias.lower())
            return headers[idx]
    return None


def parse_code(code: str) -> tuple[str, str]:
    """
    Parse stock code into market and code parts.

    Examples:
        HK.00700 -> ("HK", "00700")
        US.NVDA -> ("US", "NVDA")
        00700 -> ("HK", "00700")  # Default to HK
        NVDA -> ("US", "NVDA")    # Guess US for alphabetic
    """
    code = code.strip()

    if "." in code:
        parts = code.split(".", 1)
        return parts[0].upper(), parts[1]

    # Guess market based on code format
    if code.isdigit():
        if len(code) == 6 and code[0] in "036":
            return "A", code  # A-share
        return "HK", code  # Default HK for numeric
    else:
        return "US", code  # US for alphabetic


def parse_decimal(value: Any) -> Optional[Decimal]:
    """Parse value to Decimal, handling various formats."""
    if value is None or value == "":
        return None
    try:
        # Remove commas and convert
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if value == "" or value == "-":
                return None
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value: Any) -> Optional[int]:
    """Parse value to int."""
    if value is None or value == "":
        return None
    try:
        if isinstance(value, str):
            value = value.replace(",", "").strip()
            if value == "" or value == "-":
                return None
        return int(float(value))
    except (ValueError, TypeError):
        return None


def parse_datetime(value: Any) -> Optional[datetime]:
    """Parse value to datetime, trying multiple formats."""
    if value is None or value == "":
        return None

    if isinstance(value, datetime):
        return value

    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())

    value = str(value).strip()

    # Try common formats
    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
        "%d/%m/%Y",
        "%d-%m-%Y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def parse_date(value: Any) -> Optional[date]:
    """Parse value to date."""
    dt = parse_datetime(value)
    return dt.date() if dt else None


def parse_trade_side(value: Any) -> str:
    """Parse trade side to BUY/SELL."""
    if value is None:
        return "BUY"

    value = str(value).upper().strip()

    if value in ("BUY", "B", "买", "买入", "LONG"):
        return "BUY"
    elif value in ("SELL", "S", "卖", "卖出", "SHORT"):
        return "SELL"
    else:
        return "BUY"  # Default


# =============================================================================
# Import Functions
# =============================================================================


def import_watchlist(
    user_id: int,
    csv_path: Path,
    encoding: str = "utf-8",
) -> ImportResult:
    """
    Import watchlist items from CSV.

    CSV columns: code, name, group, notes
    """
    result = ImportResult(success=True)

    try:
        with open(csv_path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Find columns
            code_col = find_column(headers, WATCHLIST_COLUMN_MAP["code"])
            name_col = find_column(headers, WATCHLIST_COLUMN_MAP["name"])
            group_col = find_column(headers, WATCHLIST_COLUMN_MAP["group"])
            notes_col = find_column(headers, WATCHLIST_COLUMN_MAP["notes"])

            if not code_col:
                result.success = False
                result.add_error("Missing required column: code")
                return result

            with get_session() as session:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        code_raw = row.get(code_col, "").strip()
                        if not code_raw:
                            result.skipped += 1
                            continue

                        market, code = parse_code(code_raw)
                        name = row.get(name_col, "").strip() if name_col else None
                        group = row.get(group_col, "").strip() if group_col else None
                        notes = row.get(notes_col, "").strip() if notes_col else None

                        # Check if exists
                        existing = (
                            session.query(WatchlistItem)
                            .filter_by(user_id=user_id, market=market, code=code)
                            .first()
                        )

                        if existing:
                            # Update existing
                            if name:
                                existing.stock_name = name
                            if group:
                                existing.group_name = group
                            if notes:
                                existing.notes = notes
                            result.skipped += 1
                        else:
                            # Create new
                            item = WatchlistItem(
                                user_id=user_id,
                                market=market,
                                code=code,
                                stock_name=name or None,
                                group_name=group or None,
                                notes=notes or None,
                            )
                            session.add(item)
                            result.imported += 1

                    except Exception as e:
                        result.add_error(f"Row {row_num}: {e}")

                session.commit()

    except FileNotFoundError:
        result.success = False
        result.add_error(f"File not found: {csv_path}")
    except Exception as e:
        result.success = False
        result.add_error(f"Import failed: {e}")

    return result


def import_positions(
    account_id: int,
    csv_path: Path,
    snapshot_date: Optional[date] = None,
    encoding: str = "utf-8",
) -> ImportResult:
    """
    Import positions from CSV.

    CSV columns: code, name, qty, cost_price, market_price, market_val, pl_val, pl_ratio
    """
    result = ImportResult(success=True)
    snapshot_date = snapshot_date or date.today()

    try:
        with open(csv_path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Find columns
            code_col = find_column(headers, POSITION_COLUMN_MAP["code"])
            name_col = find_column(headers, POSITION_COLUMN_MAP["name"])
            qty_col = find_column(headers, POSITION_COLUMN_MAP["qty"])
            cost_col = find_column(headers, POSITION_COLUMN_MAP["cost_price"])
            price_col = find_column(headers, POSITION_COLUMN_MAP["market_price"])
            val_col = find_column(headers, POSITION_COLUMN_MAP["market_val"])
            pl_val_col = find_column(headers, POSITION_COLUMN_MAP["pl_val"])
            pl_ratio_col = find_column(headers, POSITION_COLUMN_MAP["pl_ratio"])

            if not code_col or not qty_col:
                result.success = False
                result.add_error("Missing required columns: code, qty")
                return result

            with get_session() as session:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        code_raw = row.get(code_col, "").strip()
                        if not code_raw:
                            result.skipped += 1
                            continue

                        market, code = parse_code(code_raw)
                        qty = parse_decimal(row.get(qty_col))

                        if qty is None or qty == 0:
                            result.skipped += 1
                            continue

                        name = row.get(name_col, "").strip() if name_col else None
                        cost_price = (
                            parse_decimal(row.get(cost_col)) if cost_col else None
                        )
                        market_price = (
                            parse_decimal(row.get(price_col)) if price_col else None
                        )
                        market_val = (
                            parse_decimal(row.get(val_col)) if val_col else None
                        )
                        pl_val = (
                            parse_decimal(row.get(pl_val_col)) if pl_val_col else None
                        )
                        pl_ratio = (
                            parse_decimal(row.get(pl_ratio_col))
                            if pl_ratio_col
                            else None
                        )

                        # Check if exists
                        existing = (
                            session.query(Position)
                            .filter_by(
                                account_id=account_id,
                                snapshot_date=snapshot_date,
                                market=market,
                                code=code,
                            )
                            .first()
                        )

                        if existing:
                            # Update existing
                            existing.qty = qty
                            existing.stock_name = name or existing.stock_name
                            existing.cost_price = cost_price or existing.cost_price
                            existing.market_price = (
                                market_price or existing.market_price
                            )
                            existing.market_val = market_val or existing.market_val
                            existing.pl_val = pl_val or existing.pl_val
                            existing.pl_ratio = pl_ratio or existing.pl_ratio
                            result.skipped += 1
                        else:
                            # Create new
                            position = Position(
                                account_id=account_id,
                                snapshot_date=snapshot_date,
                                market=market,
                                code=code,
                                stock_name=name or None,
                                qty=qty,
                                cost_price=cost_price,
                                market_price=market_price,
                                market_val=market_val,
                                pl_val=pl_val,
                                pl_ratio=pl_ratio,
                            )
                            session.add(position)
                            result.imported += 1

                    except Exception as e:
                        result.add_error(f"Row {row_num}: {e}")

                session.commit()

    except FileNotFoundError:
        result.success = False
        result.add_error(f"File not found: {csv_path}")
    except Exception as e:
        result.success = False
        result.add_error(f"Import failed: {e}")

    return result


def import_trades(
    account_id: int,
    csv_path: Path,
    encoding: str = "utf-8",
) -> ImportResult:
    """
    Import trades from CSV.

    CSV columns: deal_id, order_id, trade_time, code, name, side, qty, price, amount, fee
    """
    result = ImportResult(success=True)

    try:
        with open(csv_path, "r", encoding=encoding) as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames or []

            # Find columns
            deal_id_col = find_column(headers, TRADE_COLUMN_MAP["deal_id"])
            order_id_col = find_column(headers, TRADE_COLUMN_MAP["order_id"])
            time_col = find_column(headers, TRADE_COLUMN_MAP["trade_time"])
            code_col = find_column(headers, TRADE_COLUMN_MAP["code"])
            name_col = find_column(headers, TRADE_COLUMN_MAP["name"])
            side_col = find_column(headers, TRADE_COLUMN_MAP["side"])
            qty_col = find_column(headers, TRADE_COLUMN_MAP["qty"])
            price_col = find_column(headers, TRADE_COLUMN_MAP["price"])
            amount_col = find_column(headers, TRADE_COLUMN_MAP["amount"])
            fee_col = find_column(headers, TRADE_COLUMN_MAP["fee"])

            if not code_col or not qty_col or not price_col:
                result.success = False
                result.add_error("Missing required columns: code, qty, price")
                return result

            with get_session() as session:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        code_raw = row.get(code_col, "").strip()
                        if not code_raw:
                            result.skipped += 1
                            continue

                        market, code = parse_code(code_raw)
                        qty = parse_decimal(row.get(qty_col))
                        price = parse_decimal(row.get(price_col))

                        if qty is None or price is None:
                            result.skipped += 1
                            continue

                        # Generate deal_id if not provided
                        deal_id = (
                            row.get(deal_id_col, "").strip() if deal_id_col else None
                        )
                        if not deal_id:
                            deal_id = f"CSV_{row_num}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

                        trade_time = (
                            parse_datetime(row.get(time_col))
                            if time_col
                            else datetime.now()
                        )
                        if trade_time is None:
                            trade_time = datetime.now()

                        order_id = (
                            row.get(order_id_col, "").strip() if order_id_col else None
                        )
                        name = row.get(name_col, "").strip() if name_col else None
                        side = (
                            parse_trade_side(row.get(side_col)) if side_col else "BUY"
                        )
                        amount = (
                            parse_decimal(row.get(amount_col)) if amount_col else None
                        )
                        fee = parse_decimal(row.get(fee_col)) if fee_col else None

                        # Check if exists
                        existing = (
                            session.query(Trade)
                            .filter_by(account_id=account_id, deal_id=deal_id)
                            .first()
                        )

                        if existing:
                            result.skipped += 1
                        else:
                            # Create new
                            trade = Trade(
                                account_id=account_id,
                                deal_id=deal_id,
                                order_id=order_id or None,
                                trade_time=trade_time,
                                market=market,
                                code=code,
                                stock_name=name or None,
                                trd_side=side,
                                qty=qty,
                                price=price,
                                amount=amount,
                                fee=fee,
                            )
                            session.add(trade)
                            result.imported += 1

                    except Exception as e:
                        result.add_error(f"Row {row_num}: {e}")

                session.commit()

    except FileNotFoundError:
        result.success = False
        result.add_error(f"File not found: {csv_path}")
    except Exception as e:
        result.success = False
        result.add_error(f"Import failed: {e}")

    return result


# =============================================================================
# CLI Commands
# =============================================================================


def get_user_id(username: str) -> Optional[int]:
    """Get user ID by username."""
    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        return user.id if user else None


def get_account(
    user_id: int, account_id: Optional[int] = None, market: Optional[str] = None
) -> Optional[Account]:
    """Get account by user and optionally account_id or market."""
    with get_session() as session:
        query = session.query(Account).filter_by(user_id=user_id)
        if account_id:
            query = query.filter_by(futu_acc_id=account_id)
        if market:
            query = query.filter_by(market=market.upper())
        return query.first()


@click.group()
def cli():
    """CSV Data Import Tool for Investment Analyzer."""
    pass


@cli.command()
@click.option("--user", "-u", required=True, help="用户名")
@click.option(
    "--file",
    "-f",
    "file_path",
    required=True,
    type=click.Path(exists=True),
    help="CSV文件路径",
)
@click.option("--encoding", default="utf-8", help="文件编码 (默认utf-8)")
def watchlist(user: str, file_path: str, encoding: str):
    """导入关注列表"""
    # Validate user
    users_config = get_users_config()
    if not users_config.get_user(user):
        click.echo(f"Error: User '{user}' not found in configuration.", err=True)
        sys.exit(1)

    user_id = get_user_id(user)
    if not user_id:
        click.echo(
            f"Error: User '{user}' not found in database. Run 'python main.py db seed -u {user}' first.",
            err=True,
        )
        sys.exit(1)

    click.echo(f"Importing watchlist for user '{user}' from {file_path}...")

    result = import_watchlist(user_id, Path(file_path), encoding)

    if result.success:
        click.echo(
            click.style("Success: ", fg="green")
            + f"Imported {result.imported}, skipped {result.skipped}"
        )
    else:
        click.echo(click.style("Error: ", fg="red") + "Import failed", err=True)

    if result.error_messages:
        click.echo("\nErrors:")
        for msg in result.error_messages[:10]:  # Show first 10 errors
            click.echo(f"  - {msg}", err=True)
        if len(result.error_messages) > 10:
            click.echo(
                f"  ... and {len(result.error_messages) - 10} more errors", err=True
            )

    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--user", "-u", required=True, help="用户名")
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
def positions(
    user: str,
    account_id: Optional[int],
    market: Optional[str],
    file_path: str,
    snapshot_date: Optional[str],
    encoding: str,
):
    """导入持仓数据"""
    # Validate user
    users_config = get_users_config()
    if not users_config.get_user(user):
        click.echo(f"Error: User '{user}' not found in configuration.", err=True)
        sys.exit(1)

    user_id = get_user_id(user)
    if not user_id:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Get account
    account = get_account(user_id, account_id, market)
    if not account:
        click.echo(
            f"Error: Account not found. Please create an account first.", err=True
        )
        sys.exit(1)

    # Parse date
    date_obj = None
    if snapshot_date:
        try:
            date_obj = datetime.strptime(snapshot_date, "%Y-%m-%d").date()
        except ValueError:
            click.echo(f"Error: Invalid date format. Use YYYY-MM-DD.", err=True)
            sys.exit(1)

    click.echo(
        f"Importing positions for user '{user}' (account {account.futu_acc_id}) from {file_path}..."
    )

    result = import_positions(account.id, Path(file_path), date_obj, encoding)

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


@cli.command()
@click.option("--user", "-u", required=True, help="用户名")
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
def trades(
    user: str,
    account_id: Optional[int],
    market: Optional[str],
    file_path: str,
    encoding: str,
):
    """导入交易记录"""
    # Validate user
    users_config = get_users_config()
    if not users_config.get_user(user):
        click.echo(f"Error: User '{user}' not found in configuration.", err=True)
        sys.exit(1)

    user_id = get_user_id(user)
    if not user_id:
        click.echo(f"Error: User '{user}' not found in database.", err=True)
        sys.exit(1)

    # Get account
    account = get_account(user_id, account_id, market)
    if not account:
        click.echo(
            f"Error: Account not found. Please create an account first.", err=True
        )
        sys.exit(1)

    click.echo(
        f"Importing trades for user '{user}' (account {account.futu_acc_id}) from {file_path}..."
    )

    result = import_trades(account.id, Path(file_path), encoding)

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


@cli.command()
def formats():
    """显示支持的CSV格式"""
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


if __name__ == "__main__":
    cli()
