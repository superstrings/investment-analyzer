"""
Unified data provider for Skills.

Provides cached access to positions, trades, klines, and watchlist data.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd

from db import Account, Kline, Position, Trade, User, WatchlistItem, get_session

logger = logging.getLogger(__name__)


@dataclass
class PositionData:
    """Position data for analysis."""

    market: str
    code: str
    stock_name: str
    qty: Decimal
    cost_price: Decimal
    market_price: Decimal
    market_val: Decimal
    pl_val: Decimal
    pl_ratio: Decimal
    position_side: str = "LONG"

    @property
    def full_code(self) -> str:
        """Get full code with market prefix."""
        return f"{self.market}.{self.code}"


@dataclass
class KlineData:
    """K-line data for analysis."""

    market: str
    code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal = Decimal("0")


@dataclass
class WatchlistData:
    """Watchlist item data."""

    market: str
    code: str
    stock_name: str
    group_name: str = ""

    @property
    def full_code(self) -> str:
        """Get full code with market prefix."""
        return f"{self.market}.{self.code}"


class DataProvider:
    """
    Unified data provider for skills.

    Provides cached access to database data and external APIs.
    Decouples skills from data sources.
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        """
        Initialize data provider.

        Args:
            cache_ttl_seconds: Cache time-to-live in seconds (default: 5 minutes)
        """
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self._cache: dict[str, tuple[datetime, any]] = {}

    def _get_cache(self, key: str) -> Optional[any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            cached_time, value = self._cache[key]
            if datetime.now() - cached_time < self.cache_ttl:
                return value
            del self._cache[key]
        return None

    def _set_cache(self, key: str, value: any) -> None:
        """Set value in cache."""
        self._cache[key] = (datetime.now(), value)

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()

    # =========================================================================
    # User Data
    # =========================================================================

    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        cache_key = f"user:{user_id}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        with get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                # Detach from session
                session.expunge(user)
                self._set_cache(cache_key, user)
            return user

    # =========================================================================
    # Position Data
    # =========================================================================

    def get_positions(
        self,
        user_id: int,
        markets: list[str] = None,
    ) -> list[PositionData]:
        """
        Get user positions.

        Args:
            user_id: User ID
            markets: Filter by markets (default: all)

        Returns:
            List of PositionData
        """
        cache_key = f"positions:{user_id}:{','.join(sorted(markets or []))}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        positions = []
        with get_session() as session:
            # Get user's account IDs first
            account_ids = [
                acc.id
                for acc in session.query(Account).filter_by(user_id=user_id).all()
            ]

            if not account_ids:
                self._set_cache(cache_key, positions)
                return positions

            # Query positions by account IDs
            query = session.query(Position).filter(Position.account_id.in_(account_ids))
            if markets:
                query = query.filter(Position.market.in_(markets))

            for pos in query.all():
                positions.append(
                    PositionData(
                        market=pos.market,
                        code=pos.code,
                        stock_name=pos.stock_name,
                        qty=pos.qty,
                        cost_price=pos.cost_price,
                        market_price=pos.market_price,
                        market_val=pos.market_val,
                        pl_val=pos.pl_val,
                        pl_ratio=pos.pl_ratio,
                        position_side=pos.position_side,
                    )
                )

        self._set_cache(cache_key, positions)
        return positions

    def get_position_codes(self, user_id: int, markets: list[str] = None) -> list[str]:
        """Get list of position codes (e.g., ['HK.00700', 'US.NVDA'])."""
        positions = self.get_positions(user_id, markets)
        return [p.full_code for p in positions]

    # =========================================================================
    # Watchlist Data
    # =========================================================================

    def get_watchlist(
        self,
        user_id: int,
        markets: list[str] = None,
        exclude_indices: bool = True,
    ) -> list[WatchlistData]:
        """
        Get user watchlist.

        Args:
            user_id: User ID
            markets: Filter by markets (default: all)
            exclude_indices: Exclude indices and currency pairs

        Returns:
            List of WatchlistData
        """
        cache_key = (
            f"watchlist:{user_id}:{','.join(sorted(markets or []))}:{exclude_indices}"
        )
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        watchlist = []
        with get_session() as session:
            query = session.query(WatchlistItem).filter_by(user_id=user_id)
            if markets:
                query = query.filter(WatchlistItem.market.in_(markets))

            for item in query.all():
                # Filter out indices and currency
                if exclude_indices:
                    if not self._is_individual_stock(item.market, item.code):
                        continue

                watchlist.append(
                    WatchlistData(
                        market=item.market,
                        code=item.code,
                        stock_name=item.stock_name,
                        group_name=item.group_name or "",
                    )
                )

        self._set_cache(cache_key, watchlist)
        return watchlist

    def get_watchlist_codes(
        self,
        user_id: int,
        markets: list[str] = None,
        exclude_indices: bool = True,
    ) -> list[str]:
        """Get list of watchlist codes."""
        watchlist = self.get_watchlist(user_id, markets, exclude_indices)
        return [w.full_code for w in watchlist]

    def _is_individual_stock(self, market: str, code: str) -> bool:
        """Check if code is an individual stock (not index/currency)."""
        if market == "A":
            # 000001 is Shanghai index
            if code == "000001":
                return False
            return True
        elif market == "HK":
            # 8xxxxx are indices, USDCNH is currency
            if code.startswith("8") or code == "USDCNH":
                return False
            return True
        elif market == "US":
            # .SPX, .VIX are indices
            if code.startswith("."):
                return False
            return True
        return True

    # =========================================================================
    # K-line Data
    # =========================================================================

    def get_klines(
        self,
        market: str,
        code: str,
        days: int = 120,
        end_date: date = None,
    ) -> list[KlineData]:
        """
        Get K-line data from database.

        Args:
            market: Market code (HK, US, A, SH, SZ)
            code: Stock code
            days: Number of days
            end_date: End date (default: today)

        Returns:
            List of KlineData sorted by date ascending
        """
        if end_date is None:
            end_date = date.today()
        start_date = end_date - timedelta(days=days)

        # Normalize A-share market codes (SH/SZ -> A)
        db_market = market
        if market in ("SH", "SZ"):
            db_market = "A"

        cache_key = f"klines:{market}:{code}:{days}:{end_date}"
        cached = self._get_cache(cache_key)
        if cached:
            return cached

        klines = []
        with get_session() as session:
            query = (
                session.query(Kline)
                .filter_by(market=db_market, code=code)
                .filter(Kline.trade_date >= start_date)
                .filter(Kline.trade_date <= end_date)
                .order_by(Kline.trade_date.asc())
            )

            for k in query.all():
                klines.append(
                    KlineData(
                        market=k.market,
                        code=k.code,
                        trade_date=k.trade_date,
                        open=k.open,
                        high=k.high,
                        low=k.low,
                        close=k.close,
                        volume=k.volume,
                        amount=k.amount or Decimal("0"),
                    )
                )

        self._set_cache(cache_key, klines)
        return klines

    def get_klines_df(
        self,
        market: str,
        code: str,
        days: int = 120,
        end_date: date = None,
    ) -> pd.DataFrame:
        """
        Get K-line data as DataFrame.

        Args:
            market: Market code
            code: Stock code
            days: Number of days
            end_date: End date

        Returns:
            DataFrame with OHLCV columns, indexed by date
        """
        klines = self.get_klines(market, code, days, end_date)

        if not klines:
            return pd.DataFrame()

        data = []
        for k in klines:
            data.append(
                {
                    "Date": k.trade_date,
                    "Open": float(k.open),
                    "High": float(k.high),
                    "Low": float(k.low),
                    "Close": float(k.close),
                    "Volume": float(k.volume),
                    "Amount": float(k.amount),
                }
            )

        df = pd.DataFrame(data)
        df["Date"] = pd.to_datetime(df["Date"])
        df.set_index("Date", inplace=True)
        return df

    def get_latest_price(self, market: str, code: str) -> Optional[Decimal]:
        """Get latest closing price."""
        klines = self.get_klines(market, code, days=5)
        if klines:
            return klines[-1].close
        return None

    # =========================================================================
    # Trade Data
    # =========================================================================

    def get_trades(
        self,
        user_id: int,
        start_date: date = None,
        end_date: date = None,
        markets: list[str] = None,
        days: int = None,
    ) -> list[Trade]:
        """
        Get user trades.

        Args:
            user_id: User ID
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            markets: Filter by markets
            days: Shorthand for start_date (days ago from today)

        Returns:
            List of Trade objects
        """
        if end_date is None:
            end_date = date.today()
        if days is not None:
            start_date = end_date - timedelta(days=days)
        elif start_date is None:
            start_date = end_date - timedelta(days=30)

        trades = []
        with get_session() as session:
            # Get user's account IDs first
            account_ids = [
                acc.id
                for acc in session.query(Account).filter_by(user_id=user_id).all()
            ]

            if not account_ids:
                return trades

            # Query trades by account IDs
            query = (
                session.query(Trade)
                .filter(Trade.account_id.in_(account_ids))
                .filter(
                    Trade.trade_time
                    >= datetime.combine(start_date, datetime.min.time())
                )
                .filter(
                    Trade.trade_time <= datetime.combine(end_date, datetime.max.time())
                )
            )
            if markets:
                query = query.filter(Trade.market.in_(markets))

            query = query.order_by(Trade.trade_time.desc())

            for t in query.all():
                session.expunge(t)
                trades.append(t)

        return trades

    # =========================================================================
    # Aggregate Methods
    # =========================================================================

    def get_all_tracked_codes(
        self,
        user_id: int,
        markets: list[str] = None,
    ) -> list[str]:
        """
        Get all codes user is tracking (positions + watchlist).

        Args:
            user_id: User ID
            markets: Filter by markets

        Returns:
            Deduplicated list of codes
        """
        position_codes = set(self.get_position_codes(user_id, markets))
        watchlist_codes = set(self.get_watchlist_codes(user_id, markets))
        return sorted(position_codes | watchlist_codes)

    def get_portfolio_summary(self, user_id: int) -> dict:
        """
        Get portfolio summary statistics.

        Args:
            user_id: User ID

        Returns:
            Dict with total_value, total_cost, total_pl, pl_ratio, position_count
        """
        positions = self.get_positions(user_id)

        if not positions:
            return {
                "total_value": Decimal("0"),
                "total_cost": Decimal("0"),
                "total_pl": Decimal("0"),
                "pl_ratio": Decimal("0"),
                "position_count": 0,
            }

        total_value = sum(p.market_val for p in positions)
        total_cost = sum(p.cost_price * p.qty for p in positions)
        total_pl = sum(p.pl_val for p in positions)

        pl_ratio = Decimal("0")
        if total_cost > 0:
            pl_ratio = (total_pl / total_cost) * 100

        return {
            "total_value": total_value,
            "total_cost": total_cost,
            "total_pl": total_pl,
            "pl_ratio": pl_ratio,
            "position_count": len(positions),
        }
