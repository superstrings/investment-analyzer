"""
Portfolio API routes and dashboard page.
"""

import json
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.dependencies import get_db, resolve_user
from db.models import Account, AccountSnapshot, Position

router = APIRouter(tags=["portfolio"])


@router.get("/api/portfolio")
async def api_portfolio(
    username: str = Depends(get_current_user),
    market: str = "",
    db: Session = Depends(get_db),
):
    """Get portfolio positions."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    account_ids = [acc.id for acc in db.query(Account).filter_by(user_id=user.id).all()]
    if not account_ids:
        return {"positions": [], "summary": {}}

    # Get latest snapshot positions
    latest_dates = (
        db.query(
            Position.account_id,
            func.max(Position.snapshot_date).label("max_date"),
        )
        .filter(Position.account_id.in_(account_ids))
        .group_by(Position.account_id)
        .subquery()
    )

    query = db.query(Position).join(
        latest_dates,
        (Position.account_id == latest_dates.c.account_id)
        & (Position.snapshot_date == latest_dates.c.max_date),
    )
    if market:
        query = query.filter(Position.market == market)

    positions = query.all()

    result = []
    total_val = Decimal("0")
    total_pl = Decimal("0")

    for p in positions:
        result.append(
            {
                "code": f"{p.market}.{p.code}",
                "name": p.stock_name or "",
                "qty": float(p.qty),
                "cost_price": float(p.cost_price or 0),
                "market_price": float(p.market_price or 0),
                "market_val": float(p.market_val or 0),
                "pl_val": float(p.pl_val or 0),
                "pl_ratio": float(p.pl_ratio or 0),
                "side": p.position_side,
            }
        )
        total_val += p.market_val or Decimal("0")
        total_pl += p.pl_val or Decimal("0")

    return {
        "positions": result,
        "summary": {
            "total_positions": len(result),
            "total_market_val": float(total_val),
            "total_pl": float(total_pl),
            "total_pl_ratio": float(total_pl / total_val * 100) if total_val else 0,
        },
    }


@router.get("/api/portfolio/history")
async def api_portfolio_history(
    username: str = Depends(get_current_user),
    days: int = 90,
    db: Session = Depends(get_db),
):
    """Get account value history."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    accounts = db.query(Account).filter_by(user_id=user.id).all()
    start_date = date.today() - timedelta(days=days)

    history = {}
    for acc in accounts:
        snapshots = (
            db.query(AccountSnapshot)
            .filter(
                AccountSnapshot.account_id == acc.id,
                AccountSnapshot.snapshot_date >= start_date,
            )
            .order_by(AccountSnapshot.snapshot_date.asc())
            .all()
        )
        if snapshots:
            history[f"{acc.market}"] = [
                {
                    "date": s.snapshot_date.isoformat(),
                    "total_assets": float(s.total_assets or 0),
                    "cash": float(s.cash or 0),
                    "market_val": float(s.market_val or 0),
                }
                for s in snapshots
            ]

    return {"history": history}
