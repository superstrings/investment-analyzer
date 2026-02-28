"""
Stock detail API routes.

Provides:
- GET /api/stock/{market}/{code} — aggregated stock info
- GET /api/stock/{market}/{code}/klines — K-line OHLCV JSON
- GET /api/search — search stocks
"""

import logging
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, or_

from api.auth import get_current_user

router = APIRouter(tags=["stock"])
logger = logging.getLogger(__name__)


@router.get("/api/stock/{market}/{code}")
async def api_stock_detail(
    market: str,
    code: str,
    username: str = Depends(get_current_user),
):
    """Get aggregated stock detail: position, trades, signals, plans."""
    from db.database import get_session
    from db.models import (
        Account,
        Kline,
        Position,
        Signal,
        Trade,
        TradingPlanRecord,
        User,
        WatchlistItem,
    )

    market = market.upper()
    full_code = f"{market}.{code}"

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

        # Basic info from watchlist or kline
        stock_name = ""
        watchlist = (
            session.query(WatchlistItem)
            .filter_by(user_id=user_id, market=market, code=code)
            .first()
        )
        if watchlist:
            stock_name = watchlist.stock_name or ""

        # Latest kline for price
        latest_kline = (
            session.query(Kline)
            .filter_by(market=market, code=code)
            .order_by(Kline.trade_date.desc())
            .first()
        )
        latest_price = float(latest_kline.close) if latest_kline else None
        if latest_kline and not stock_name:
            stock_name = ""

        # Current position
        account_ids = [
            a.id for a in session.query(Account).filter_by(user_id=user_id).all()
        ]
        position = None
        if account_ids:
            latest_dates = (
                session.query(
                    Position.account_id,
                    func.max(Position.snapshot_date).label("max_date"),
                )
                .filter(Position.account_id.in_(account_ids))
                .group_by(Position.account_id)
                .subquery()
            )
            pos = (
                session.query(Position)
                .join(
                    latest_dates,
                    (Position.account_id == latest_dates.c.account_id)
                    & (Position.snapshot_date == latest_dates.c.max_date),
                )
                .filter(Position.market == market, Position.code == code)
                .first()
            )
            if pos:
                if not stock_name:
                    stock_name = pos.stock_name or ""
                position = {
                    "qty": float(pos.qty),
                    "cost_price": float(pos.cost_price or 0),
                    "market_price": float(pos.market_price or 0),
                    "market_val": float(pos.market_val or 0),
                    "pl_val": float(pos.pl_val or 0),
                    "pl_ratio": float(pos.pl_ratio or 0),
                    "side": pos.position_side,
                }

        # Trades (last 100)
        trades = []
        if account_ids:
            trade_records = (
                session.query(Trade)
                .filter(
                    Trade.account_id.in_(account_ids),
                    Trade.market == market,
                    Trade.code == code,
                )
                .order_by(Trade.trade_time.desc())
                .limit(100)
                .all()
            )
            for t in trade_records:
                if not stock_name:
                    stock_name = t.stock_name or ""
                trades.append(
                    {
                        "time": t.trade_time.isoformat() if t.trade_time else None,
                        "side": t.trd_side,
                        "price": float(t.price),
                        "qty": float(t.qty),
                        "amount": float(t.amount) if t.amount else None,
                    }
                )

        # Signals (all, not just active)
        signals_q = (
            session.query(Signal)
            .filter_by(user_id=user_id, market=market, code=code)
            .order_by(Signal.created_at.desc())
            .limit(50)
            .all()
        )
        signals = []
        for s in signals_q:
            signals.append(
                {
                    "id": s.id,
                    "type": s.signal_type,
                    "source": s.signal_source,
                    "score": float(s.score) if s.score else None,
                    "confidence": float(s.confidence) if s.confidence else None,
                    "strength": s.strength,
                    "trigger_price": (
                        float(s.trigger_price) if s.trigger_price else None
                    ),
                    "target_price": float(s.target_price) if s.target_price else None,
                    "stop_loss": (
                        float(s.stop_loss_price) if s.stop_loss_price else None
                    ),
                    "reason": s.reason or "",
                    "is_active": s.is_active,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
            )

        # Plans (all)
        plans_q = (
            session.query(TradingPlanRecord)
            .filter_by(user_id=user_id, market=market, code=code)
            .order_by(TradingPlanRecord.plan_date.desc())
            .limit(50)
            .all()
        )
        plans = []
        for p in plans_q:
            plans.append(
                {
                    "id": p.id,
                    "action": p.action_type,
                    "priority": p.priority,
                    "status": p.status,
                    "plan_date": p.plan_date.isoformat(),
                    "entry_price": float(p.entry_price) if p.entry_price else None,
                    "stop_loss": (
                        float(p.stop_loss_price) if p.stop_loss_price else None
                    ),
                    "target_1": float(p.target_price_1) if p.target_price_1 else None,
                    "target_2": float(p.target_price_2) if p.target_price_2 else None,
                    "position_size": p.position_size or "",
                    "reason": p.reason or "",
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                    "execution_price": (
                        float(p.execution_price) if p.execution_price else None
                    ),
                }
            )

    return {
        "code": full_code,
        "market": market,
        "name": stock_name,
        "latest_price": latest_price,
        "position": position,
        "trades": trades,
        "signals": signals,
        "plans": plans,
    }


@router.get("/api/stock/{market}/{code}/klines")
async def api_stock_klines(
    market: str,
    code: str,
    days: int = 120,
):
    """Get K-line data with MA for charting."""
    from db.database import get_session
    from db.models import Kline

    market = market.upper()
    cutoff = date.today() - timedelta(days=days)

    with get_session() as session:
        klines = (
            session.query(Kline)
            .filter(
                Kline.market == market,
                Kline.code == code,
                Kline.trade_date >= cutoff,
            )
            .order_by(Kline.trade_date.asc())
            .all()
        )

        result = []
        for k in klines:
            result.append(
                {
                    "time": k.trade_date.isoformat(),
                    "open": float(k.open),
                    "high": float(k.high),
                    "low": float(k.low),
                    "close": float(k.close),
                    "volume": k.volume or 0,
                    "ma5": float(k.ma5) if k.ma5 else None,
                    "ma10": float(k.ma10) if k.ma10 else None,
                    "ma20": float(k.ma20) if k.ma20 else None,
                    "ma60": float(k.ma60) if k.ma60 else None,
                }
            )

    return {"klines": result, "market": market, "code": code, "days": days}


@router.get("/api/search")
async def api_search(
    q: str = "",
    username: str = Depends(get_current_user),
):
    """Search stocks across watchlist, positions, and klines."""
    if not q or len(q) < 1:
        return {"results": []}

    from db.database import get_session
    from db.models import Account, Kline, Position, User, WatchlistItem

    q_upper = q.upper()

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"results": []}

        seen = set()
        results = []

        # Search watchlist
        watchlist_items = (
            session.query(WatchlistItem)
            .filter(
                WatchlistItem.user_id == user.id,
                or_(
                    func.upper(
                        func.concat(WatchlistItem.market, ".", WatchlistItem.code)
                    ).contains(q_upper),
                    func.upper(WatchlistItem.stock_name).contains(q_upper),
                    func.upper(WatchlistItem.code).contains(q_upper),
                ),
            )
            .limit(10)
            .all()
        )
        for w in watchlist_items:
            fc = f"{w.market}.{w.code}"
            if fc not in seen:
                seen.add(fc)
                results.append(
                    {"code": fc, "name": w.stock_name or "", "source": "关注"}
                )

        # Search positions
        account_ids = [
            a.id for a in session.query(Account).filter_by(user_id=user.id).all()
        ]
        if account_ids:
            positions = (
                session.query(Position)
                .filter(
                    Position.account_id.in_(account_ids),
                    or_(
                        func.upper(
                            func.concat(Position.market, ".", Position.code)
                        ).contains(q_upper),
                        func.upper(Position.stock_name).contains(q_upper),
                        func.upper(Position.code).contains(q_upper),
                    ),
                )
                .distinct(Position.market, Position.code)
                .limit(10)
                .all()
            )
            for p in positions:
                fc = f"{p.market}.{p.code}"
                if fc not in seen:
                    seen.add(fc)
                    results.append(
                        {"code": fc, "name": p.stock_name or "", "source": "持仓"}
                    )

        # Search klines (by code only)
        if len(results) < 15:
            klines = (
                session.query(Kline.market, Kline.code)
                .filter(
                    or_(
                        func.upper(func.concat(Kline.market, ".", Kline.code)).contains(
                            q_upper
                        ),
                        func.upper(Kline.code).contains(q_upper),
                    )
                )
                .distinct()
                .limit(10)
                .all()
            )
            for k in klines:
                fc = f"{k.market}.{k.code}"
                if fc not in seen:
                    seen.add(fc)
                    results.append({"code": fc, "name": "", "source": "K线"})

    return {"results": results[:15]}
