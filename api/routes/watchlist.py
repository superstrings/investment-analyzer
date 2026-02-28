"""
Watchlist API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from services.watchlist_service import create_watchlist_service

router = APIRouter(tags=["watchlist"])


class WatchlistAddRequest(BaseModel):
    market: str
    code: str
    stock_name: Optional[str] = None
    group_name: Optional[str] = None
    notes: Optional[str] = None


class WatchlistUpdateRequest(BaseModel):
    notes: Optional[str] = None
    group_name: Optional[str] = None
    stock_name: Optional[str] = None
    sort_order: Optional[int] = None


@router.get("/api/watchlist")
async def api_watchlist(
    username: str = Depends(get_current_user),
    active_only: bool = True,
    market: str = "",
):
    """Get watchlist items with latest prices and signal/plan counts."""
    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    svc = create_watchlist_service()
    is_active = True if active_only else None
    items = svc.get_watchlist(user_id, is_active=is_active, market=market or None)

    return {"items": items}


@router.post("/api/watchlist")
async def api_watchlist_add(
    body: WatchlistAddRequest,
    username: str = Depends(get_current_user),
):
    """Add a new watchlist item."""
    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    svc = create_watchlist_service()
    result = svc.add_item(
        user_id=user_id,
        market=body.market,
        code=body.code,
        stock_name=body.stock_name,
        group_name=body.group_name,
        notes=body.notes,
    )
    return result


@router.put("/api/watchlist/{item_id}")
async def api_watchlist_update(
    item_id: int,
    body: WatchlistUpdateRequest,
    username: str = Depends(get_current_user),
):
    """Update a watchlist item."""
    svc = create_watchlist_service()
    kwargs = {k: v for k, v in body.dict().items() if v is not None}
    return svc.update_item(item_id, **kwargs)


@router.delete("/api/watchlist/{item_id}")
async def api_watchlist_delete(
    item_id: int,
    username: str = Depends(get_current_user),
):
    """Delete a watchlist item."""
    svc = create_watchlist_service()
    return svc.remove_item(item_id)


@router.post("/api/watchlist/{item_id}/toggle")
async def api_watchlist_toggle(
    item_id: int,
    username: str = Depends(get_current_user),
):
    """Toggle archive/restore for a watchlist item."""
    svc = create_watchlist_service()
    return svc.toggle_active(item_id)


@router.get("/api/watchlist/stock/{market}/{code}/signals")
async def api_watchlist_stock_signals(
    market: str,
    code: str,
    username: str = Depends(get_current_user),
):
    """Get all signals (active + history) for a specific stock."""
    from db.database import get_session
    from db.models import Signal, User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}

        signals = (
            session.query(Signal)
            .filter_by(user_id=user.id, market=market, code=code)
            .order_by(Signal.created_at.desc())
            .all()
        )

        result = []
        for s in signals:
            result.append(
                {
                    "id": s.id,
                    "type": s.signal_type,
                    "source": s.signal_source,
                    "score": float(s.score) if s.score else None,
                    "confidence": float(s.confidence) if s.confidence else None,
                    "trigger_price": float(s.trigger_price) if s.trigger_price else None,
                    "target_price": float(s.target_price) if s.target_price else None,
                    "stop_loss": float(s.stop_loss_price) if s.stop_loss_price else None,
                    "reason": s.reason or "",
                    "is_active": s.is_active,
                    "acted_on": s.acted_on,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
            )

    return {"signals": result, "code": f"{market}.{code}"}


@router.get("/api/watchlist/stock/{market}/{code}/plans")
async def api_watchlist_stock_plans(
    market: str,
    code: str,
    username: str = Depends(get_current_user),
):
    """Get all plans (pending + history) for a specific stock."""
    from db.database import get_session
    from db.models import TradingPlanRecord, User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}

        plans = (
            session.query(TradingPlanRecord)
            .filter_by(user_id=user.id, market=market, code=code)
            .order_by(TradingPlanRecord.plan_date.desc())
            .all()
        )

        result = []
        for p in plans:
            result.append(
                {
                    "id": p.id,
                    "action": p.action_type,
                    "priority": p.priority,
                    "status": p.status,
                    "plan_date": p.plan_date.isoformat(),
                    "entry_price": float(p.entry_price) if p.entry_price else None,
                    "stop_loss": float(p.stop_loss_price) if p.stop_loss_price else None,
                    "target_1": float(p.target_price_1) if p.target_price_1 else None,
                    "target_2": float(p.target_price_2) if p.target_price_2 else None,
                    "position_size": p.position_size or "",
                    "reason": p.reason or "",
                    "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                    "execution_price": float(p.execution_price) if p.execution_price else None,
                }
            )

    return {"plans": result, "code": f"{market}.{code}"}
