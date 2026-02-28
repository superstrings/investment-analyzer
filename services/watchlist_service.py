"""
Watchlist management service.

Handles CRUD operations for watchlist items with latest price data from klines.
"""

import logging
from typing import Optional

from sqlalchemy import and_, func

from db.database import get_session
from db.models import Kline, WatchlistItem

logger = logging.getLogger(__name__)


class WatchlistService:
    """Service for managing user watchlist items."""

    def get_watchlist(
        self,
        user_id: int,
        is_active: Optional[bool] = None,
        market: Optional[str] = None,
    ) -> list[dict]:
        """Get watchlist items with latest prices from klines table.

        Args:
            user_id: User ID
            is_active: Filter by active status (None = all)
            market: Filter by market (None = all)

        Returns:
            List of watchlist item dicts with latest_price, change_pct,
            signals_count, plans_count
        """
        from services.plan_service import create_plan_service
        from services.signal_service import create_signal_service

        with get_session() as session:
            query = session.query(WatchlistItem).filter(
                WatchlistItem.user_id == user_id
            )
            if is_active is not None:
                query = query.filter(WatchlistItem.is_active == is_active)
            if market:
                query = query.filter(WatchlistItem.market == market)

            items = query.order_by(
                WatchlistItem.is_active.desc(),
                WatchlistItem.sort_order,
                WatchlistItem.market,
                WatchlistItem.code,
            ).all()

            if not items:
                return []

            # Batch fetch latest prices from klines
            codes = [(it.market, it.code) for it in items]
            prices = self._get_latest_prices(session, codes)

            # Batch fetch signal/plan counts
            full_codes = [f"{it.market}.{it.code}" for it in items]

            signal_svc = create_signal_service()
            signals_by_code = signal_svc.get_signals_by_codes(user_id, full_codes)

            plan_svc = create_plan_service()
            plans_by_code = plan_svc.get_plans_by_codes(
                user_id, full_codes, include_history=True
            )

            result = []
            for it in items:
                key = (it.market, it.code)
                price_info = prices.get(key, {})
                full_code = f"{it.market}.{it.code}"
                code_signals = signals_by_code.get(full_code, [])
                code_plans = plans_by_code.get(full_code, [])

                result.append(
                    {
                        "id": it.id,
                        "market": it.market,
                        "code": it.code,
                        "full_code": full_code,
                        "stock_name": it.stock_name or "",
                        "group_name": it.group_name or "",
                        "notes": it.notes or "",
                        "is_active": it.is_active,
                        "sort_order": it.sort_order,
                        "latest_price": price_info.get("close"),
                        "prev_close": price_info.get("prev_close"),
                        "change_pct": price_info.get("change_pct"),
                        "trade_date": price_info.get("trade_date"),
                        "signals_count": len(code_signals),
                        "plans_count": len(code_plans),
                        "active_signals": len(
                            [s for s in code_signals if s.is_active]
                        ),
                        "active_plans": len(
                            [p for p in code_plans if p.status == "pending"]
                        ),
                        "created_at": it.created_at.isoformat() if it.created_at else None,
                    }
                )

            return result

    def _get_latest_prices(
        self, session, codes: list[tuple[str, str]]
    ) -> dict[tuple[str, str], dict]:
        """Get latest close price and change % from klines for multiple codes."""
        if not codes:
            return {}

        result = {}

        # Get max trade_date per code
        conditions = [
            and_(Kline.market == m, Kline.code == c) for m, c in codes
        ]
        if not conditions:
            return {}

        from sqlalchemy import or_

        # Subquery: max date per (market, code)
        max_dates_sq = (
            session.query(
                Kline.market,
                Kline.code,
                func.max(Kline.trade_date).label("max_date"),
            )
            .filter(or_(*conditions))
            .group_by(Kline.market, Kline.code)
            .subquery()
        )

        # Get latest klines
        latest_klines = (
            session.query(Kline)
            .join(
                max_dates_sq,
                and_(
                    Kline.market == max_dates_sq.c.market,
                    Kline.code == max_dates_sq.c.code,
                    Kline.trade_date == max_dates_sq.c.max_date,
                ),
            )
            .all()
        )

        # Also get previous day klines for change calculation
        latest_dates = {(k.market, k.code): k for k in latest_klines}

        # Get previous trading day klines
        prev_conditions = []
        for k in latest_klines:
            prev_conditions.append(
                and_(
                    Kline.market == k.market,
                    Kline.code == k.code,
                    Kline.trade_date < k.trade_date,
                )
            )

        prev_klines = {}
        if prev_conditions:
            # Get max date before latest for each code
            prev_max_sq = (
                session.query(
                    Kline.market,
                    Kline.code,
                    func.max(Kline.trade_date).label("prev_date"),
                )
                .filter(or_(*prev_conditions))
                .group_by(Kline.market, Kline.code)
                .subquery()
            )

            prev_rows = (
                session.query(Kline)
                .join(
                    prev_max_sq,
                    and_(
                        Kline.market == prev_max_sq.c.market,
                        Kline.code == prev_max_sq.c.code,
                        Kline.trade_date == prev_max_sq.c.prev_date,
                    ),
                )
                .all()
            )
            for pk in prev_rows:
                prev_klines[(pk.market, pk.code)] = pk

        for key, k in latest_dates.items():
            close = float(k.close) if k.close else None
            prev = prev_klines.get(key)
            prev_close = float(prev.close) if prev and prev.close else None
            change_pct = None
            if close and prev_close and prev_close != 0:
                change_pct = (close - prev_close) / prev_close

            result[key] = {
                "close": close,
                "prev_close": prev_close,
                "change_pct": change_pct,
                "trade_date": k.trade_date.isoformat() if k.trade_date else None,
            }

        return result

    def add_item(
        self,
        user_id: int,
        market: str,
        code: str,
        stock_name: str = None,
        group_name: str = None,
        notes: str = None,
    ) -> dict:
        """Add a new watchlist item."""
        with get_session() as session:
            # Check for duplicate
            existing = (
                session.query(WatchlistItem)
                .filter_by(user_id=user_id, market=market, code=code)
                .first()
            )
            if existing:
                if not existing.is_active:
                    # Reactivate archived item
                    existing.is_active = True
                    if stock_name:
                        existing.stock_name = stock_name
                    if group_name is not None:
                        existing.group_name = group_name
                    if notes is not None:
                        existing.notes = notes
                    session.flush()
                    return {"success": True, "id": existing.id, "reactivated": True}
                return {"success": False, "error": "该股票已在关注列表中"}

            item = WatchlistItem(
                user_id=user_id,
                market=market,
                code=code,
                stock_name=stock_name,
                group_name=group_name,
                notes=notes,
            )
            session.add(item)
            session.flush()
            return {"success": True, "id": item.id}

    def update_item(self, item_id: int, **kwargs) -> dict:
        """Update a watchlist item's notes, group_name, etc."""
        with get_session() as session:
            item = session.query(WatchlistItem).get(item_id)
            if not item:
                return {"success": False, "error": "Item not found"}

            for field in ("notes", "group_name", "stock_name", "sort_order"):
                if field in kwargs:
                    setattr(item, field, kwargs[field])

            session.flush()
            return {"success": True}

    def toggle_active(self, item_id: int) -> dict:
        """Toggle active/archived status."""
        with get_session() as session:
            item = session.query(WatchlistItem).get(item_id)
            if not item:
                return {"success": False, "error": "Item not found"}

            item.is_active = not item.is_active
            session.flush()
            return {"success": True, "is_active": item.is_active}

    def remove_item(self, item_id: int) -> dict:
        """Delete a watchlist item."""
        with get_session() as session:
            item = session.query(WatchlistItem).get(item_id)
            if not item:
                return {"success": False, "error": "Item not found"}

            session.delete(item)
            return {"success": True}


def create_watchlist_service() -> WatchlistService:
    """Factory function for WatchlistService."""
    return WatchlistService()
