"""
Data synchronization service for Investment Analyzer.

Coordinates syncing data from Futu OpenD and akshare to the database.

Usage:
    from services import SyncService
    from fetchers import FutuFetcher, KlineFetcher

    # Create fetchers
    futu = FutuFetcher()
    kline = KlineFetcher()

    # Create sync service
    sync = SyncService(futu_fetcher=futu, kline_fetcher=kline)

    # Sync all data for a user
    result = sync.sync_all(user_id=1)

    # Or sync specific data types
    sync.sync_positions(user_id=1)
    sync.sync_trades(user_id=1, days=30)
    sync.sync_klines(codes=["HK.00700", "US.NVDA"], days=120)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from db.database import get_session
from db.models import (
    Account,
    AccountSnapshot,
    Kline,
    Position,
    SyncLog,
    Trade,
    User,
    WatchlistItem,
)
from fetchers import FutuFetcher, KlineFetcher, Market
from fetchers.base import AccountInfo, PositionInfo, TradeInfo
from fetchers.kline_fetcher import KlineData

logger = logging.getLogger(__name__)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    success: bool
    sync_type: str
    records_synced: int = 0
    records_skipped: int = 0
    error_message: str = ""
    duration_seconds: float = 0.0
    details: dict = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        sync_type: str,
        records_synced: int,
        records_skipped: int = 0,
        duration: float = 0.0,
        details: Optional[dict] = None,
    ) -> "SyncResult":
        """Create successful sync result."""
        return cls(
            success=True,
            sync_type=sync_type,
            records_synced=records_synced,
            records_skipped=records_skipped,
            duration_seconds=duration,
            details=details or {},
        )

    @classmethod
    def error(cls, sync_type: str, message: str) -> "SyncResult":
        """Create error sync result."""
        return cls(
            success=False,
            sync_type=sync_type,
            error_message=message,
        )


class SyncService:
    """
    Data synchronization service.

    Syncs data from Futu OpenD and akshare to the database.
    Supports incremental sync and logs all operations.
    """

    def __init__(
        self,
        futu_fetcher: Optional[FutuFetcher] = None,
        kline_fetcher: Optional[KlineFetcher] = None,
    ):
        """
        Initialize sync service.

        Args:
            futu_fetcher: FutuFetcher instance for trading data
            kline_fetcher: KlineFetcher instance for K-line data
        """
        self.futu_fetcher = futu_fetcher
        self.kline_fetcher = kline_fetcher or KlineFetcher()

    def sync_positions(
        self,
        user_id: int,
        snapshot_date: Optional[date] = None,
        session: Optional[Session] = None,
    ) -> SyncResult:
        """
        Sync positions for a user's accounts.

        Fetches current positions from Futu and saves as daily snapshot.

        Args:
            user_id: User ID to sync positions for
            snapshot_date: Date for snapshot (default: today)
            session: Optional existing session

        Returns:
            SyncResult with sync status
        """
        if not self.futu_fetcher:
            return SyncResult.error("POSITIONS", "FutuFetcher not configured")

        start_time = datetime.now()
        snapshot_date = snapshot_date or date.today()

        def _sync(sess: Session) -> SyncResult:
            # Get user and accounts
            user = sess.get(User, user_id)
            if not user:
                return SyncResult.error("POSITIONS", f"User {user_id} not found")

            accounts = sess.scalars(
                select(Account).where(
                    and_(Account.user_id == user_id, Account.is_active == True)
                )
            ).all()

            if not accounts:
                return SyncResult.error(
                    "POSITIONS", f"No active accounts for user {user_id}"
                )

            total_synced = 0
            total_skipped = 0
            account_details = {}

            for account in accounts:
                # Fetch positions from Futu
                result = self.futu_fetcher.get_positions(acc_id=account.futu_acc_id)

                if not result.success:
                    logger.warning(
                        f"Failed to fetch positions for account {account.futu_acc_id}: {result.error_message}"
                    )
                    account_details[account.futu_acc_id] = {
                        "error": result.error_message
                    }
                    continue

                synced = 0
                skipped = 0

                for pos_info in result.data:
                    # Check if position already exists for this date
                    existing = sess.scalars(
                        select(Position).where(
                            and_(
                                Position.account_id == account.id,
                                Position.snapshot_date == snapshot_date,
                                Position.market == pos_info.market.value,
                                Position.code == pos_info.code,
                            )
                        )
                    ).first()

                    if existing:
                        # Update existing position
                        existing.qty = pos_info.qty
                        existing.can_sell_qty = pos_info.can_sell_qty
                        existing.cost_price = pos_info.cost_price
                        existing.market_price = pos_info.market_price
                        existing.market_val = pos_info.market_val
                        existing.pl_val = pos_info.pl_val
                        existing.pl_ratio = pos_info.pl_ratio
                        existing.stock_name = pos_info.stock_name
                        existing.position_side = pos_info.position_side.value
                        skipped += 1
                    else:
                        # Create new position
                        position = Position(
                            account_id=account.id,
                            snapshot_date=snapshot_date,
                            market=pos_info.market.value,
                            code=pos_info.code,
                            stock_name=pos_info.stock_name,
                            qty=pos_info.qty,
                            can_sell_qty=pos_info.can_sell_qty,
                            cost_price=pos_info.cost_price,
                            market_price=pos_info.market_price,
                            market_val=pos_info.market_val,
                            pl_val=pos_info.pl_val,
                            pl_ratio=pos_info.pl_ratio,
                            position_side=pos_info.position_side.value,
                        )
                        sess.add(position)
                        synced += 1

                total_synced += synced
                total_skipped += skipped
                account_details[account.futu_acc_id] = {
                    "synced": synced,
                    "updated": skipped,
                }

            # Also sync account snapshots
            self._sync_account_snapshots(sess, accounts, snapshot_date)

            # Log sync operation
            duration = (datetime.now() - start_time).total_seconds()
            self._log_sync(
                sess,
                user_id=user_id,
                sync_type="POSITIONS",
                status="SUCCESS",
                records_count=total_synced + total_skipped,
                started_at=start_time,
            )

            return SyncResult.ok(
                sync_type="POSITIONS",
                records_synced=total_synced,
                records_skipped=total_skipped,
                duration=duration,
                details={"accounts": account_details},
            )

        if session:
            return _sync(session)
        else:
            with get_session() as sess:
                return _sync(sess)

    def sync_trades(
        self,
        user_id: int,
        days: int = 90,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        session: Optional[Session] = None,
    ) -> SyncResult:
        """
        Sync trades for a user's accounts.

        Fetches historical trades from Futu and saves to database.
        Uses deal_id for deduplication.

        Args:
            user_id: User ID to sync trades for
            days: Number of days to sync (default: 90)
            start_date: Start date (overrides days)
            end_date: End date (default: today)
            session: Optional existing session

        Returns:
            SyncResult with sync status
        """
        if not self.futu_fetcher:
            return SyncResult.error("TRADES", "FutuFetcher not configured")

        start_time = datetime.now()

        # Calculate date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=days)

        def _sync(sess: Session) -> SyncResult:
            # Get user and accounts
            user = sess.get(User, user_id)
            if not user:
                return SyncResult.error("TRADES", f"User {user_id} not found")

            accounts = sess.scalars(
                select(Account).where(
                    and_(Account.user_id == user_id, Account.is_active == True)
                )
            ).all()

            if not accounts:
                return SyncResult.error(
                    "TRADES", f"No active accounts for user {user_id}"
                )

            total_synced = 0
            total_skipped = 0
            account_details = {}

            for account in accounts:
                # Fetch historical trades from Futu
                result = self.futu_fetcher.get_history_deals(
                    acc_id=account.futu_acc_id,
                    start_date=start_date,
                    end_date=end_date,
                )

                if not result.success:
                    logger.warning(
                        f"Failed to fetch trades for account {account.futu_acc_id}: {result.error_message}"
                    )
                    account_details[account.futu_acc_id] = {
                        "error": result.error_message
                    }
                    continue

                synced = 0
                skipped = 0

                for trade_info in result.data:
                    # Check if trade already exists (by deal_id)
                    existing = sess.scalars(
                        select(Trade).where(
                            and_(
                                Trade.account_id == account.id,
                                Trade.deal_id == trade_info.deal_id,
                            )
                        )
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                    # Create new trade
                    trade = Trade(
                        account_id=account.id,
                        deal_id=trade_info.deal_id,
                        order_id=trade_info.order_id,
                        trade_time=trade_info.trade_time,
                        market=trade_info.market.value,
                        code=trade_info.code,
                        stock_name=trade_info.stock_name,
                        trd_side=trade_info.trd_side.value,
                        qty=trade_info.qty,
                        price=trade_info.price,
                        amount=trade_info.amount,
                        fee=trade_info.fee,
                        currency=trade_info.currency,
                    )
                    sess.add(trade)
                    synced += 1

                total_synced += synced
                total_skipped += skipped
                account_details[account.futu_acc_id] = {
                    "synced": synced,
                    "skipped": skipped,
                }

            # Log sync operation
            duration = (datetime.now() - start_time).total_seconds()
            self._log_sync(
                sess,
                user_id=user_id,
                sync_type="TRADES",
                status="SUCCESS",
                records_count=total_synced,
                started_at=start_time,
            )

            return SyncResult.ok(
                sync_type="TRADES",
                records_synced=total_synced,
                records_skipped=total_skipped,
                duration=duration,
                details={
                    "accounts": account_details,
                    "date_range": f"{start_date} to {end_date}",
                },
            )

        if session:
            return _sync(session)
        else:
            with get_session() as sess:
                return _sync(sess)

    def sync_klines(
        self,
        codes: list[str],
        days: int = 120,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust: str = "qfq",
        user_id: Optional[int] = None,
        session: Optional[Session] = None,
    ) -> SyncResult:
        """
        Sync K-line data for specified stocks.

        Fetches K-line data from akshare and saves to database.
        Supports incremental sync by checking existing dates.

        Args:
            codes: List of stock codes to sync
            days: Number of days to sync (default: 120)
            start_date: Start date (overrides days)
            end_date: End date (default: today)
            adjust: Price adjustment type
            user_id: Optional user ID for logging
            session: Optional existing session

        Returns:
            SyncResult with sync status
        """
        start_time = datetime.now()

        def _sync(sess: Session) -> SyncResult:
            total_synced = 0
            total_skipped = 0
            code_details = {}

            for code in codes:
                # Fetch K-line data
                result = self.kline_fetcher.fetch(
                    code=code,
                    days=days,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=adjust,
                )

                if not result.success:
                    logger.warning(
                        f"Failed to fetch klines for {code}: {result.error_message}"
                    )
                    code_details[code] = {"error": result.error_message}
                    continue

                synced = 0
                skipped = 0

                for kline_data in result.data:
                    # Check if kline already exists
                    existing = sess.scalars(
                        select(Kline).where(
                            and_(
                                Kline.market == kline_data.market.value,
                                Kline.code == kline_data.code,
                                Kline.trade_date == kline_data.trade_date,
                            )
                        )
                    ).first()

                    if existing:
                        # Update existing kline
                        existing.open = kline_data.open
                        existing.high = kline_data.high
                        existing.low = kline_data.low
                        existing.close = kline_data.close
                        existing.volume = kline_data.volume
                        existing.amount = kline_data.amount
                        existing.turnover_rate = kline_data.turnover_rate
                        existing.change_pct = kline_data.change_pct
                        skipped += 1
                    else:
                        # Create new kline
                        kline = Kline(
                            market=kline_data.market.value,
                            code=kline_data.code,
                            trade_date=kline_data.trade_date,
                            open=kline_data.open,
                            high=kline_data.high,
                            low=kline_data.low,
                            close=kline_data.close,
                            volume=kline_data.volume,
                            amount=kline_data.amount,
                            turnover_rate=kline_data.turnover_rate,
                            change_pct=kline_data.change_pct,
                        )
                        sess.add(kline)
                        synced += 1

                total_synced += synced
                total_skipped += skipped
                code_details[code] = {"synced": synced, "updated": skipped}

            # Log sync operation
            duration = (datetime.now() - start_time).total_seconds()
            self._log_sync(
                sess,
                user_id=user_id,
                sync_type="KLINES",
                status="SUCCESS",
                records_count=total_synced + total_skipped,
                started_at=start_time,
            )

            return SyncResult.ok(
                sync_type="KLINES",
                records_synced=total_synced,
                records_skipped=total_skipped,
                duration=duration,
                details={"codes": code_details},
            )

        if session:
            return _sync(session)
        else:
            with get_session() as sess:
                return _sync(sess)

    def sync_watchlist_klines(
        self,
        user_id: int,
        days: int = 120,
        session: Optional[Session] = None,
    ) -> SyncResult:
        """
        Sync K-lines for all stocks in user's watchlist.

        Args:
            user_id: User ID
            days: Number of days to sync
            session: Optional existing session

        Returns:
            SyncResult with sync status
        """

        def _get_codes(sess: Session) -> list[str]:
            items = sess.scalars(
                select(WatchlistItem).where(
                    and_(
                        WatchlistItem.user_id == user_id,
                        WatchlistItem.is_active == True,
                    )
                )
            ).all()
            return [item.full_code for item in items]

        if session:
            codes = _get_codes(session)
            return self.sync_klines(codes, days=days, user_id=user_id, session=session)
        else:
            with get_session() as sess:
                codes = _get_codes(sess)
                return self.sync_klines(codes, days=days, user_id=user_id, session=sess)

    def sync_position_klines(
        self,
        user_id: int,
        days: int = 120,
        session: Optional[Session] = None,
    ) -> SyncResult:
        """
        Sync K-lines for all stocks in user's positions.

        Args:
            user_id: User ID
            days: Number of days to sync
            session: Optional existing session

        Returns:
            SyncResult with sync status
        """

        def _get_codes(sess: Session) -> list[str]:
            # Get unique codes from today's positions
            today = date.today()
            positions = sess.scalars(
                select(Position)
                .join(Account)
                .where(
                    and_(
                        Account.user_id == user_id,
                        Position.snapshot_date == today,
                    )
                )
            ).all()

            # Get unique codes
            codes = set()
            for pos in positions:
                codes.add(f"{pos.market}.{pos.code}")
            return list(codes)

        if session:
            codes = _get_codes(session)
            return self.sync_klines(codes, days=days, user_id=user_id, session=session)
        else:
            with get_session() as sess:
                codes = _get_codes(sess)
                return self.sync_klines(codes, days=days, user_id=user_id, session=sess)

    def sync_all(
        self,
        user_id: int,
        trade_days: int = 90,
        kline_days: int = 120,
        include_klines: bool = True,
        session: Optional[Session] = None,
    ) -> dict[str, SyncResult]:
        """
        Sync all data for a user.

        Syncs positions, trades, and optionally K-lines for watchlist/positions.

        Args:
            user_id: User ID to sync
            trade_days: Number of days of trade history
            kline_days: Number of days of K-line history
            include_klines: Whether to sync K-line data
            session: Optional existing session

        Returns:
            Dict mapping sync type to SyncResult
        """
        results = {}

        def _sync(sess: Session) -> dict[str, SyncResult]:
            # Sync positions
            results["positions"] = self.sync_positions(user_id, session=sess)

            # Sync trades
            results["trades"] = self.sync_trades(user_id, days=trade_days, session=sess)

            # Sync K-lines for positions and watchlist
            if include_klines:
                results["position_klines"] = self.sync_position_klines(
                    user_id, days=kline_days, session=sess
                )
                results["watchlist_klines"] = self.sync_watchlist_klines(
                    user_id, days=kline_days, session=sess
                )

            return results

        if session:
            return _sync(session)
        else:
            with get_session() as sess:
                return _sync(sess)

    def _sync_account_snapshots(
        self,
        session: Session,
        accounts: list[Account],
        snapshot_date: date,
    ) -> int:
        """
        Sync account balance snapshots.

        Args:
            session: Database session
            accounts: List of accounts to sync
            snapshot_date: Date for snapshot

        Returns:
            Number of snapshots synced
        """
        synced = 0

        for account in accounts:
            # Fetch account info from Futu
            result = self.futu_fetcher.get_account_info(acc_id=account.futu_acc_id)

            if not result.success or not result.data:
                logger.warning(
                    f"Failed to fetch account info for {account.futu_acc_id}: {result.error_message}"
                )
                continue

            acc_info = result.data[0]

            # Check if snapshot exists
            existing = session.scalars(
                select(AccountSnapshot).where(
                    and_(
                        AccountSnapshot.account_id == account.id,
                        AccountSnapshot.snapshot_date == snapshot_date,
                    )
                )
            ).first()

            if existing:
                # Update existing snapshot
                existing.total_assets = acc_info.total_assets
                existing.cash = acc_info.cash
                existing.market_val = acc_info.market_val
                existing.frozen_cash = acc_info.frozen_cash
                existing.buying_power = acc_info.buying_power
                existing.max_power_short = acc_info.max_power_short
                existing.currency = acc_info.currency
            else:
                # Create new snapshot
                snapshot = AccountSnapshot(
                    account_id=account.id,
                    snapshot_date=snapshot_date,
                    total_assets=acc_info.total_assets,
                    cash=acc_info.cash,
                    market_val=acc_info.market_val,
                    frozen_cash=acc_info.frozen_cash,
                    buying_power=acc_info.buying_power,
                    max_power_short=acc_info.max_power_short,
                    currency=acc_info.currency,
                )
                session.add(snapshot)
                synced += 1

        return synced

    def _log_sync(
        self,
        session: Session,
        sync_type: str,
        status: str,
        records_count: int,
        started_at: datetime,
        user_id: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> SyncLog:
        """
        Log a sync operation.

        Args:
            session: Database session
            sync_type: Type of sync operation
            status: Sync status (SUCCESS/FAILED/PARTIAL)
            records_count: Number of records synced
            started_at: When sync started
            user_id: Optional user ID
            error_message: Optional error message

        Returns:
            Created SyncLog record
        """
        log = SyncLog(
            user_id=user_id,
            sync_type=sync_type,
            status=status,
            records_count=records_count,
            error_message=error_message,
            started_at=started_at,
            finished_at=datetime.now(),
        )
        session.add(log)
        return log

    def get_last_sync(
        self,
        user_id: int,
        sync_type: str,
        session: Optional[Session] = None,
    ) -> Optional[SyncLog]:
        """
        Get the last sync log for a user and type.

        Args:
            user_id: User ID
            sync_type: Type of sync operation
            session: Optional existing session

        Returns:
            Last SyncLog or None
        """

        def _get(sess: Session) -> Optional[SyncLog]:
            return sess.scalars(
                select(SyncLog)
                .where(
                    and_(
                        SyncLog.user_id == user_id,
                        SyncLog.sync_type == sync_type,
                    )
                )
                .order_by(SyncLog.created_at.desc())
                .limit(1)
            ).first()

        if session:
            return _get(session)
        else:
            with get_session() as sess:
                return _get(sess)


def create_sync_service(
    futu_fetcher: Optional[FutuFetcher] = None,
    kline_fetcher: Optional[KlineFetcher] = None,
) -> SyncService:
    """
    Factory function to create a SyncService.

    Args:
        futu_fetcher: Optional FutuFetcher instance
        kline_fetcher: Optional KlineFetcher instance

    Returns:
        SyncService instance
    """
    return SyncService(
        futu_fetcher=futu_fetcher,
        kline_fetcher=kline_fetcher,
    )
