"""
Trading calendar service.

Fetches and stores trading day data for HK/US/A/JP markets.
Data sources: Futu API (primary), akshare (A-share fallback).
"""

import calendar
import logging
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.database import get_session
from db.models import TradingCalendar

logger = logging.getLogger(__name__)

# Futu market code mapping
FUTU_MARKET_MAP = {
    "HK": "HK",
    "US": "US",
    "A": "CN",
    "JP": "JP_FUTURE",
}

SUPPORTED_MARKETS = ("HK", "US", "A", "JP")


class TradingCalendarService:
    """Service for trading calendar data management."""

    def __init__(
        self,
        futu_host: str = "127.0.0.1",
        futu_port: int = 11111,
    ):
        self.futu_host = futu_host
        self.futu_port = futu_port

    def sync_market(
        self,
        market: str,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> int:
        """
        Sync trading days for a market from Futu API.

        Args:
            market: Market code (HK/US/A/JP)
            start: Start date (default: Jan 1 of current year)
            end: End date (default: Dec 31 of current year)

        Returns:
            Number of trading days synced
        """
        if start is None:
            start = date(date.today().year, 1, 1)
        if end is None:
            end = date(date.today().year, 12, 31)

        futu_market = FUTU_MARKET_MAP.get(market)
        if not futu_market:
            logger.error(f"Unsupported market: {market}")
            return 0

        try:
            trading_days = self._fetch_from_futu(futu_market, start, end)
        except Exception as e:
            logger.warning(f"Futu API failed for {market}: {e}")
            if market == "A":
                logger.info("Falling back to akshare for A-share calendar")
                trading_days = self._fetch_from_akshare(start, end)
            else:
                return 0

        if not trading_days:
            return 0

        return self._upsert_trading_days(market, trading_days)

    def sync_market_akshare(
        self,
        start: Optional[date] = None,
        end: Optional[date] = None,
    ) -> int:
        """
        Sync A-share trading days from akshare (fallback).

        Returns:
            Number of trading days synced
        """
        if start is None:
            start = date(date.today().year, 1, 1)
        if end is None:
            end = date(date.today().year, 12, 31)

        trading_days = self._fetch_from_akshare(start, end)
        if not trading_days:
            return 0

        return self._upsert_trading_days("A", trading_days)

    def sync_all_markets(self, year: Optional[int] = None) -> dict[str, int]:
        """
        Sync trading days for all supported markets.

        Args:
            year: Year to sync (default: current year)

        Returns:
            Dict of market → count synced
        """
        if year is None:
            year = date.today().year

        start = date(year, 1, 1)
        end = date(year, 12, 31)

        results = {}
        for market in SUPPORTED_MARKETS:
            count = self.sync_market(market, start, end)
            results[market] = count
            logger.info(f"Synced {count} trading days for {market} ({year})")

        return results

    def is_trading_day(self, market: str, d: Optional[date] = None) -> bool:
        """
        Check if a date is a trading day for a market.

        Falls back to weekday check if no calendar data exists.
        """
        if d is None:
            d = date.today()

        # Weekend is never a trading day
        if d.weekday() >= 5:
            return False

        with get_session() as session:
            row = session.execute(
                select(TradingCalendar).where(
                    and_(
                        TradingCalendar.market == market,
                        TradingCalendar.trade_date == d,
                    )
                )
            ).scalar_one_or_none()

            if row is not None:
                return True

            # Check if we have any data for this market/year
            has_data = session.execute(
                select(TradingCalendar.id)
                .where(
                    and_(
                        TradingCalendar.market == market,
                        TradingCalendar.trade_date >= date(d.year, 1, 1),
                        TradingCalendar.trade_date <= date(d.year, 12, 31),
                    )
                )
                .limit(1)
            ).scalar_one_or_none()

        if has_data is not None:
            # We have data for this year but date is not in it → not a trading day
            return False

        # No data at all → try to sync, then re-check
        try:
            count = self.sync_market(market, date(d.year, 1, 1), date(d.year, 12, 31))
            if count > 0:
                with get_session() as session:
                    row = session.execute(
                        select(TradingCalendar).where(
                            and_(
                                TradingCalendar.market == market,
                                TradingCalendar.trade_date == d,
                            )
                        )
                    ).scalar_one_or_none()
                    return row is not None
        except Exception as e:
            logger.warning(f"Auto-sync failed for {market}: {e}")

        # Ultimate fallback: weekday = trading day
        return True

    def get_trading_days(
        self, market: str, start: date, end: date
    ) -> list[TradingCalendar]:
        """Get trading days for a market within a date range."""
        with get_session() as session:
            rows = (
                session.execute(
                    select(TradingCalendar)
                    .where(
                        and_(
                            TradingCalendar.market == market,
                            TradingCalendar.trade_date >= start,
                            TradingCalendar.trade_date <= end,
                        )
                    )
                    .order_by(TradingCalendar.trade_date)
                )
                .scalars()
                .all()
            )
            # Detach from session
            for r in rows:
                session.expunge(r)
            return rows

    def get_next_trading_day(
        self, market: str, from_date: Optional[date] = None
    ) -> Optional[date]:
        """Get the next trading day after from_date."""
        if from_date is None:
            from_date = date.today()

        with get_session() as session:
            row = session.execute(
                select(TradingCalendar)
                .where(
                    and_(
                        TradingCalendar.market == market,
                        TradingCalendar.trade_date > from_date,
                    )
                )
                .order_by(TradingCalendar.trade_date)
                .limit(1)
            ).scalar_one_or_none()

            if row:
                return row.trade_date

        # Fallback: next weekday
        d = from_date + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d

    def get_calendar_data(
        self, year: int, month: int
    ) -> list[dict]:
        """
        Get calendar data for a month, with all markets' trading status.

        Returns list of dicts:
            [{"date": "2026-02-01", "weekday": 6, "markets": {"HK": "WHOLE", "US": "WHOLE", "A": null, "JP": null}}, ...]
        """
        # Build all dates for the month
        _, num_days = calendar.monthrange(year, month)
        all_dates = [date(year, month, d) for d in range(1, num_days + 1)]

        # Fetch trading days for all markets in this month range
        start_d = date(year, month, 1)
        end_d = date(year, month, num_days)

        # Build lookup: {(market, date_str): trade_date_type}
        lookup: dict[tuple[str, str], str] = {}
        with get_session() as session:
            rows = (
                session.execute(
                    select(TradingCalendar).where(
                        and_(
                            TradingCalendar.trade_date >= start_d,
                            TradingCalendar.trade_date <= end_d,
                        )
                    )
                )
                .scalars()
                .all()
            )
            for r in rows:
                lookup[(r.market, r.trade_date.isoformat())] = r.trade_date_type

        result = []
        for d in all_dates:
            date_str = d.isoformat()
            markets = {}
            for m in SUPPORTED_MARKETS:
                markets[m] = lookup.get((m, date_str))
            result.append({
                "date": date_str,
                "weekday": d.weekday(),
                "markets": markets,
            })

        return result

    def _fetch_from_futu(
        self, futu_market: str, start: date, end: date
    ) -> list[dict]:
        """Fetch trading days from Futu API."""
        from futu import OpenQuoteContext, RET_OK

        trading_days = []
        ctx = OpenQuoteContext(host=self.futu_host, port=self.futu_port)
        try:
            ret, data = ctx.request_trading_days(
                market=futu_market,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
            )
            if ret != RET_OK:
                raise RuntimeError(f"Futu request_trading_days failed: {data}")

            for _, row in data.iterrows():
                trade_date = row.get("time", "")
                trade_type = row.get("trade_date_type", "WHOLE")
                if trade_date:
                    trading_days.append({
                        "trade_date": date.fromisoformat(str(trade_date)[:10]),
                        "trade_date_type": str(trade_type),
                        "source": "futu",
                    })

            logger.info(
                f"Fetched {len(trading_days)} trading days from Futu ({futu_market})"
            )
        finally:
            ctx.close()

        return trading_days

    def _fetch_from_akshare(self, start: date, end: date) -> list[dict]:
        """Fetch A-share trading days from akshare."""
        try:
            import akshare as ak

            df = ak.tool_trade_date_hist_sina()
            if df is None or df.empty:
                return []

            trading_days = []
            for _, row in df.iterrows():
                td = row.iloc[0]
                if hasattr(td, "date"):
                    td = td.date() if callable(td.date) else td
                elif isinstance(td, str):
                    td = date.fromisoformat(td[:10])
                else:
                    continue

                if start <= td <= end:
                    trading_days.append({
                        "trade_date": td,
                        "trade_date_type": "WHOLE",
                        "source": "akshare",
                    })

            logger.info(
                f"Fetched {len(trading_days)} A-share trading days from akshare"
            )
            return trading_days

        except Exception as e:
            logger.error(f"akshare fallback failed: {e}")
            return []

    def _upsert_trading_days(self, market: str, trading_days: list[dict]) -> int:
        """Upsert trading days into the database."""
        if not trading_days:
            return 0

        with get_session() as session:
            for td in trading_days:
                stmt = pg_insert(TradingCalendar).values(
                    market=market,
                    trade_date=td["trade_date"],
                    trade_date_type=td["trade_date_type"],
                    source=td["source"],
                    created_at=datetime.now(),
                )
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_calendar_market_date",
                    set_={
                        "trade_date_type": stmt.excluded.trade_date_type,
                        "source": stmt.excluded.source,
                    },
                )
                session.execute(stmt)

        logger.info(f"Upserted {len(trading_days)} trading days for {market}")
        return len(trading_days)


def create_trading_calendar_service() -> TradingCalendarService:
    """Factory function for TradingCalendarService."""
    from config import settings

    return TradingCalendarService(
        futu_host=settings.futu.default_host,
        futu_port=settings.futu.default_port,
    )
