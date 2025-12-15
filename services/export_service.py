"""
Data export service.

Exports positions, trades, and kline data to various formats:
- CSV
- Excel (multiple worksheets)
- JSON
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.database import SessionLocal, get_session
from db.models import Account, Kline, Position, Trade, WatchlistItem


class ExportFormat(str, Enum):
    """Supported export formats."""

    CSV = "csv"
    EXCEL = "xlsx"
    JSON = "json"


@dataclass
class ExportConfig:
    """Configuration for data export."""

    output_dir: Path = field(default_factory=lambda: Path("exports"))
    include_headers: bool = True
    date_format: str = "%Y-%m-%d"
    datetime_format: str = "%Y-%m-%d %H:%M:%S"
    decimal_places: int = 4
    encoding: str = "utf-8"


@dataclass
class ExportResult:
    """Result of an export operation."""

    success: bool
    format: ExportFormat
    file_path: Optional[Path] = None
    records_exported: int = 0
    error: Optional[str] = None


@dataclass
class DateRange:
    """Date range for filtering data."""

    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class ExportService:
    """Service for exporting data to various formats.

    Supports exporting:
    - Positions (current holdings)
    - Trades (transaction history)
    - Klines (OHLCV data)
    - Watchlist (watched stocks)
    """

    def __init__(
        self,
        session: Optional[Session] = None,
        config: Optional[ExportConfig] = None,
    ):
        self.session = session
        self.config = config or ExportConfig()

        # Create output directory if it doesn't exist
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def _get_session(self) -> Session:
        """Get database session.

        Note: When no session is injected, creates a new session using SessionLocal.
        The caller should close the session when done if self.session was None.
        """
        if self.session:
            return self.session
        return SessionLocal()

    def _get_user_account_ids(self, session: Session, user_id: int) -> list[int]:
        """Get account IDs for a user."""
        query = select(Account.id).where(Account.user_id == user_id)
        result = session.execute(query).scalars().all()
        return list(result)

    def export_positions(
        self,
        user_id: int,
        format: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
        account_ids: Optional[list[int]] = None,
    ) -> ExportResult:
        """Export positions for a user.

        Args:
            user_id: User ID
            format: Export format
            filename: Custom filename (optional)
            account_ids: Filter by specific accounts (optional)

        Returns:
            ExportResult with export details
        """
        try:
            session = self._get_session()

            # Get account IDs if not specified
            if not account_ids:
                account_ids = self._get_user_account_ids(session, user_id)

            if not account_ids:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No accounts found for user",
                )

            # Build query - filter by account_ids
            query = select(Position).where(Position.account_id.in_(account_ids))
            positions = session.execute(query).scalars().all()

            if not positions:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No positions found",
                )

            # Convert to DataFrame
            data = []
            for pos in positions:
                data.append(
                    {
                        "id": pos.id,
                        "account_id": pos.account_id,
                        "snapshot_date": pos.snapshot_date,
                        "market": pos.market,
                        "code": pos.code,
                        "stock_name": pos.stock_name,
                        "qty": float(pos.qty) if pos.qty else 0,
                        "can_sell_qty": (
                            float(pos.can_sell_qty) if pos.can_sell_qty else 0
                        ),
                        "cost_price": float(pos.cost_price) if pos.cost_price else 0,
                        "market_price": (
                            float(pos.market_price) if pos.market_price else 0
                        ),
                        "market_val": float(pos.market_val) if pos.market_val else 0,
                        "pl_val": float(pos.pl_val) if pos.pl_val else 0,
                        "pl_ratio": float(pos.pl_ratio) if pos.pl_ratio else 0,
                        "position_side": pos.position_side,
                        "created_at": pos.created_at,
                    }
                )

            df = pd.DataFrame(data)

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"positions_{user_id}_{timestamp}"

            # Export
            return self._export_dataframe(df, format, filename)

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def export_trades(
        self,
        user_id: int,
        format: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
        account_ids: Optional[list[int]] = None,
        date_range: Optional[DateRange] = None,
    ) -> ExportResult:
        """Export trades for a user.

        Args:
            user_id: User ID
            format: Export format
            filename: Custom filename (optional)
            account_ids: Filter by specific accounts (optional)
            date_range: Filter by date range (optional)

        Returns:
            ExportResult with export details
        """
        try:
            session = self._get_session()

            # Get account IDs if not specified
            if not account_ids:
                account_ids = self._get_user_account_ids(session, user_id)

            if not account_ids:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No accounts found for user",
                )

            # Build query
            query = select(Trade).where(Trade.account_id.in_(account_ids))

            if date_range:
                if date_range.start_date:
                    query = query.where(Trade.trade_time >= date_range.start_date)
                if date_range.end_date:
                    query = query.where(Trade.trade_time <= date_range.end_date)

            query = query.order_by(Trade.trade_time.desc())
            trades = session.execute(query).scalars().all()

            if not trades:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No trades found",
                )

            # Convert to DataFrame
            data = []
            for trade in trades:
                data.append(
                    {
                        "id": trade.id,
                        "account_id": trade.account_id,
                        "deal_id": trade.deal_id,
                        "order_id": trade.order_id,
                        "trade_time": trade.trade_time,
                        "market": trade.market,
                        "code": trade.code,
                        "stock_name": trade.stock_name,
                        "trd_side": trade.trd_side,
                        "qty": float(trade.qty) if trade.qty else 0,
                        "price": float(trade.price) if trade.price else 0,
                        "amount": float(trade.amount) if trade.amount else 0,
                        "fee": float(trade.fee) if trade.fee else 0,
                        "currency": trade.currency,
                    }
                )

            df = pd.DataFrame(data)

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"trades_{user_id}_{timestamp}"

            # Export
            return self._export_dataframe(df, format, filename)

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def export_klines(
        self,
        code: str,
        format: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
        date_range: Optional[DateRange] = None,
        limit: Optional[int] = None,
    ) -> ExportResult:
        """Export kline data for a stock.

        Args:
            code: Stock code (e.g., "HK.00700")
            format: Export format
            filename: Custom filename (optional)
            date_range: Filter by date range (optional)
            limit: Maximum number of records (optional)

        Returns:
            ExportResult with export details
        """
        try:
            session = self._get_session()

            # Parse market and code
            if "." in code:
                market, stock_code = code.split(".", 1)
            else:
                market = ""
                stock_code = code

            # Build query
            query = select(Kline)
            if market:
                query = query.where(Kline.market == market)
            query = query.where(Kline.code == stock_code)

            if date_range:
                if date_range.start_date:
                    query = query.where(
                        Kline.trade_date >= date_range.start_date.date()
                    )
                if date_range.end_date:
                    query = query.where(Kline.trade_date <= date_range.end_date.date())

            query = query.order_by(Kline.trade_date.desc())

            if limit:
                query = query.limit(limit)

            klines = session.execute(query).scalars().all()

            if not klines:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No kline data found",
                )

            # Convert to DataFrame
            data = []
            for kline in klines:
                data.append(
                    {
                        "trade_date": kline.trade_date,
                        "market": kline.market,
                        "code": kline.code,
                        "open": float(kline.open) if kline.open else 0,
                        "high": float(kline.high) if kline.high else 0,
                        "low": float(kline.low) if kline.low else 0,
                        "close": float(kline.close) if kline.close else 0,
                        "volume": int(kline.volume) if kline.volume else 0,
                        "amount": float(kline.amount) if kline.amount else 0,
                        "ma5": float(kline.ma5) if kline.ma5 else None,
                        "ma10": float(kline.ma10) if kline.ma10 else None,
                        "ma20": float(kline.ma20) if kline.ma20 else None,
                        "ma60": float(kline.ma60) if kline.ma60 else None,
                    }
                )

            df = pd.DataFrame(data)

            # Sort by date ascending for export
            df = df.sort_values("trade_date")

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                safe_code = code.replace(".", "_")
                filename = f"klines_{safe_code}_{timestamp}"

            # Export
            return self._export_dataframe(df, format, filename)

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def export_watchlist(
        self,
        user_id: int,
        format: ExportFormat = ExportFormat.CSV,
        filename: Optional[str] = None,
    ) -> ExportResult:
        """Export watchlist for a user.

        Args:
            user_id: User ID
            format: Export format
            filename: Custom filename (optional)

        Returns:
            ExportResult with export details
        """
        try:
            session = self._get_session()

            # Build query
            query = select(WatchlistItem).where(WatchlistItem.user_id == user_id)
            watchlist = session.execute(query).scalars().all()

            if not watchlist:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No watchlist items found",
                )

            # Convert to DataFrame
            data = []
            for item in watchlist:
                data.append(
                    {
                        "id": item.id,
                        "market": item.market,
                        "code": item.code,
                        "stock_name": item.stock_name,
                        "group_name": item.group_name,
                        "notes": item.notes,
                        "sort_order": item.sort_order,
                        "is_active": item.is_active,
                        "created_at": item.created_at,
                    }
                )

            df = pd.DataFrame(data)

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"watchlist_{user_id}_{timestamp}"

            # Export
            return self._export_dataframe(df, format, filename)

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def export_all(
        self,
        user_id: int,
        format: ExportFormat = ExportFormat.EXCEL,
        filename: Optional[str] = None,
    ) -> ExportResult:
        """Export all data for a user (positions, trades, watchlist).

        Best used with EXCEL format for multi-sheet export.

        Args:
            user_id: User ID
            format: Export format (EXCEL recommended)
            filename: Custom filename (optional)

        Returns:
            ExportResult with export details
        """
        try:
            session = self._get_session()

            # Get account IDs
            account_ids = self._get_user_account_ids(session, user_id)

            # Collect all data
            dataframes = {}

            # Positions
            if account_ids:
                positions_query = select(Position).where(
                    Position.account_id.in_(account_ids)
                )
                positions = session.execute(positions_query).scalars().all()
                if positions:
                    positions_data = [
                        {
                            "market": p.market,
                            "code": p.code,
                            "stock_name": p.stock_name,
                            "qty": float(p.qty) if p.qty else 0,
                            "cost_price": float(p.cost_price) if p.cost_price else 0,
                            "market_price": (
                                float(p.market_price) if p.market_price else 0
                            ),
                            "market_val": float(p.market_val) if p.market_val else 0,
                            "pl_val": float(p.pl_val) if p.pl_val else 0,
                            "pl_ratio": float(p.pl_ratio) if p.pl_ratio else 0,
                        }
                        for p in positions
                    ]
                    dataframes["positions"] = pd.DataFrame(positions_data)

                # Trades
                trades_query = (
                    select(Trade)
                    .where(Trade.account_id.in_(account_ids))
                    .order_by(Trade.trade_time.desc())
                )
                trades = session.execute(trades_query).scalars().all()
                if trades:
                    trades_data = [
                        {
                            "trade_time": t.trade_time,
                            "market": t.market,
                            "code": t.code,
                            "stock_name": t.stock_name,
                            "trd_side": t.trd_side,
                            "qty": float(t.qty) if t.qty else 0,
                            "price": float(t.price) if t.price else 0,
                            "amount": float(t.amount) if t.amount else 0,
                            "fee": float(t.fee) if t.fee else 0,
                        }
                        for t in trades
                    ]
                    dataframes["trades"] = pd.DataFrame(trades_data)

            # Watchlist
            watchlist_query = select(WatchlistItem).where(
                WatchlistItem.user_id == user_id
            )
            watchlist = session.execute(watchlist_query).scalars().all()
            if watchlist:
                watchlist_data = [
                    {
                        "market": w.market,
                        "code": w.code,
                        "stock_name": w.stock_name,
                        "group_name": w.group_name,
                        "notes": w.notes,
                        "created_at": w.created_at,
                    }
                    for w in watchlist
                ]
                dataframes["watchlist"] = pd.DataFrame(watchlist_data)

            if not dataframes:
                return ExportResult(
                    success=True,
                    format=format,
                    records_exported=0,
                    error="No data found for user",
                )

            # Generate filename
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"portfolio_{user_id}_{timestamp}"

            # Export based on format
            if format == ExportFormat.EXCEL:
                return self._export_multi_sheet_excel(dataframes, filename)
            else:
                # For CSV/JSON, export positions only as main data
                main_df = dataframes.get("positions", list(dataframes.values())[0])
                return self._export_dataframe(main_df, format, filename)

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def _export_dataframe(
        self,
        df: pd.DataFrame,
        format: ExportFormat,
        filename: str,
    ) -> ExportResult:
        """Export a DataFrame to the specified format.

        Args:
            df: DataFrame to export
            format: Export format
            filename: Base filename (without extension)

        Returns:
            ExportResult with export details
        """
        try:
            # Determine file path
            extension = format.value
            file_path = self.config.output_dir / f"{filename}.{extension}"

            # Export based on format
            if format == ExportFormat.CSV:
                df.to_csv(
                    file_path,
                    index=False,
                    encoding=self.config.encoding,
                    date_format=self.config.datetime_format,
                )
            elif format == ExportFormat.EXCEL:
                df.to_excel(
                    file_path,
                    index=False,
                    engine="openpyxl",
                )
            elif format == ExportFormat.JSON:
                # Convert datetime columns to strings
                df_json = df.copy()
                for col in df_json.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_json[col]):
                        df_json[col] = df_json[col].dt.strftime(
                            self.config.datetime_format
                        )

                with open(file_path, "w", encoding=self.config.encoding) as f:
                    json.dump(
                        df_json.to_dict(orient="records"),
                        f,
                        ensure_ascii=False,
                        indent=2,
                        default=str,
                    )
            else:
                return ExportResult(
                    success=False,
                    format=format,
                    error=f"Unsupported format: {format}",
                )

            return ExportResult(
                success=True,
                format=format,
                file_path=file_path,
                records_exported=len(df),
            )

        except Exception as e:
            return ExportResult(
                success=False,
                format=format,
                error=str(e),
            )

    def _export_multi_sheet_excel(
        self,
        dataframes: dict[str, pd.DataFrame],
        filename: str,
    ) -> ExportResult:
        """Export multiple DataFrames to Excel sheets.

        Args:
            dataframes: Dictionary of sheet_name -> DataFrame
            filename: Base filename (without extension)

        Returns:
            ExportResult with export details
        """
        try:
            file_path = self.config.output_dir / f"{filename}.xlsx"

            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                total_records = 0
                for sheet_name, df in dataframes.items():
                    df.to_excel(writer, sheet_name=sheet_name, index=False)
                    total_records += len(df)

            return ExportResult(
                success=True,
                format=ExportFormat.EXCEL,
                file_path=file_path,
                records_exported=total_records,
            )

        except Exception as e:
            return ExportResult(
                success=False,
                format=ExportFormat.EXCEL,
                error=str(e),
            )


def create_export_service(
    session: Optional[Session] = None,
    output_dir: Optional[Path] = None,
) -> ExportService:
    """Factory function to create ExportService.

    Args:
        session: Database session (optional)
        output_dir: Output directory for exports (optional)

    Returns:
        ExportService instance
    """
    config = ExportConfig()
    if output_dir:
        config.output_dir = output_dir

    return ExportService(session=session, config=config)


def export_positions_to_csv(
    user_id: int, output_dir: Optional[Path] = None
) -> ExportResult:
    """Convenience function to export positions to CSV.

    Args:
        user_id: User ID
        output_dir: Output directory (optional)

    Returns:
        ExportResult
    """
    service = create_export_service(output_dir=output_dir)
    return service.export_positions(user_id, format=ExportFormat.CSV)


def export_trades_to_csv(
    user_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    output_dir: Optional[Path] = None,
) -> ExportResult:
    """Convenience function to export trades to CSV.

    Args:
        user_id: User ID
        start_date: Start date filter (optional)
        end_date: End date filter (optional)
        output_dir: Output directory (optional)

    Returns:
        ExportResult
    """
    service = create_export_service(output_dir=output_dir)
    date_range = DateRange(start_date=start_date, end_date=end_date)
    return service.export_trades(
        user_id, format=ExportFormat.CSV, date_range=date_range
    )


def export_klines_to_csv(
    code: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    output_dir: Optional[Path] = None,
) -> ExportResult:
    """Convenience function to export klines to CSV.

    Args:
        code: Stock code
        start_date: Start date filter (optional)
        end_date: End date filter (optional)
        output_dir: Output directory (optional)

    Returns:
        ExportResult
    """
    service = create_export_service(output_dir=output_dir)
    date_range = DateRange(start_date=start_date, end_date=end_date)
    return service.export_klines(code, format=ExportFormat.CSV, date_range=date_range)


def export_all_to_excel(
    user_id: int, output_dir: Optional[Path] = None
) -> ExportResult:
    """Convenience function to export all data to Excel.

    Args:
        user_id: User ID
        output_dir: Output directory (optional)

    Returns:
        ExportResult
    """
    service = create_export_service(output_dir=output_dir)
    return service.export_all(user_id, format=ExportFormat.EXCEL)
