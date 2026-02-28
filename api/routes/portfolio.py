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
from services.alert_service import create_alert_service

router = APIRouter(tags=["portfolio"])


def _normalize_pl_ratio(market: str, pl_ratio) -> float:
    """Normalize pl_ratio to decimal fraction (0.1768 = 17.68%).

    Futu (HK/US/JP) stores as percentage (17.68 = 17.68%).
    A-share manual positions store as decimal (0.2841 = 28.41%).
    """
    val = float(pl_ratio or 0)
    if market in ("HK", "US", "JP") and abs(val) > 0:
        return val / 100
    return val


@router.get("/api/portfolio")
async def api_portfolio(
    username: str = Depends(get_current_user),
    market: str = "",
    db: Session = Depends(get_db),
):
    """Get portfolio positions with alerts, plans and signals."""
    from services.exchange_rate_service import create_exchange_rate_service
    from services.plan_service import create_plan_service
    from services.signal_service import create_signal_service

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

    all_positions = query.order_by(Position.market, Position.pl_ratio.desc()).all()

    # Deduplicate by (market, code) — manual account may duplicate Futu positions
    seen = set()
    positions = []
    for p in all_positions:
        key = (p.market, p.code)
        if key not in seen:
            seen.add(key)
            positions.append(p)

    fx = create_exchange_rate_service()

    # Fetch alerts, plans, signals for all position codes
    position_codes = [f"{p.market}.{p.code}" for p in positions]

    alert_svc = create_alert_service(db)
    alerts_by_code = alert_svc.get_alerts_by_codes(user.id, position_codes)

    plan_svc = create_plan_service()
    plans_by_code = plan_svc.get_plans_by_codes(user.id, position_codes, include_history=True)

    signal_svc = create_signal_service()
    signals_by_code = signal_svc.get_signals_by_codes(user.id, position_codes)

    result = []
    total_val_cny = Decimal("0")
    total_pl_cny = Decimal("0")

    for p in positions:
        currency = fx.get_market_currency(p.market)
        rate = fx.get_rate_to_cny(currency)
        market_val = p.market_val or Decimal("0")
        pl_val = p.pl_val or Decimal("0")
        val_cny = market_val * rate
        pl_cny = pl_val * rate

        full_code = f"{p.market}.{p.code}"
        code_alerts = alerts_by_code.get(full_code, [])
        alert_types = {a.alert_type for a in code_alerts}

        code_plans = plans_by_code.get(full_code, [])
        code_signals = signals_by_code.get(full_code, [])

        result.append(
            {
                "id": p.id,
                "code": full_code,
                "name": p.stock_name or "",
                "qty": float(p.qty),
                "cost_price": float(p.cost_price or 0),
                "market_price": float(p.market_price or 0),
                "market_val": float(market_val),
                "market_val_cny": float(val_cny),
                "pl_val": float(pl_val),
                "pl_val_cny": float(pl_cny),
                "pl_ratio": _normalize_pl_ratio(p.market, p.pl_ratio),
                "currency": currency,
                "side": p.position_side,
                "source": getattr(p, "source", "futu"),
                "alerts": [
                    {
                        "id": a.id,
                        "alert_type": a.alert_type,
                        "description": a.target_description,
                    }
                    for a in code_alerts
                ],
                "alert_summary": {
                    "stop_loss": "STOP_LOSS" in alert_types,
                    "take_profit": "TAKE_PROFIT" in alert_types,
                    "oco": "OCO" in alert_types,
                    "price_alert": bool(
                        alert_types & {"ABOVE", "BELOW", "CHANGE_UP", "CHANGE_DOWN"}
                    ),
                },
                "plans": [
                    {
                        "id": pl.id,
                        "action": pl.action_type,
                        "priority": pl.priority,
                        "status": pl.status,
                        "plan_date": pl.plan_date.isoformat(),
                        "entry_price": float(pl.entry_price) if pl.entry_price else None,
                        "stop_loss": float(pl.stop_loss_price) if pl.stop_loss_price else None,
                        "target_1": float(pl.target_price_1) if pl.target_price_1 else None,
                        "reason": pl.reason or "",
                    }
                    for pl in code_plans
                ],
                "signals": [
                    {
                        "id": sg.id,
                        "type": sg.signal_type,
                        "source": sg.signal_source,
                        "score": float(sg.score) if sg.score else None,
                        "reason": sg.reason or "",
                    }
                    for sg in code_signals
                ],
            }
        )
        total_val_cny += val_cny
        total_pl_cny += pl_cny

    return {
        "positions": result,
        "summary": {
            "total_positions": len(result),
            "total_market_val": float(total_val_cny),
            "total_pl": float(total_pl_cny),
            "total_pl_ratio": (
                float(total_pl_cny / total_val_cny * 100) if total_val_cny else 0
            ),
            "currency": "CNY",
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


@router.get("/api/portfolio/historical")
async def api_portfolio_historical(
    username: str = Depends(get_current_user),
    market: str = "",
    limit: int = 30,
    db: Session = Depends(get_db),
):
    """Get historical position snapshots (non-latest dates).

    Returns positions grouped by snapshot_date, ordered by date descending.
    """
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    account_ids = [acc.id for acc in db.query(Account).filter_by(user_id=user.id).all()]
    if not account_ids:
        return {"snapshots": []}

    # Find the latest snapshot date per account
    latest_dates = (
        db.query(
            Position.account_id,
            func.max(Position.snapshot_date).label("max_date"),
        )
        .filter(Position.account_id.in_(account_ids))
        .group_by(Position.account_id)
        .subquery()
    )

    # Get distinct historical dates (excluding latest)
    hist_dates_q = (
        db.query(Position.snapshot_date)
        .filter(Position.account_id.in_(account_ids))
        .outerjoin(
            latest_dates,
            (Position.account_id == latest_dates.c.account_id)
            & (Position.snapshot_date == latest_dates.c.max_date),
        )
        .filter(latest_dates.c.max_date == None)  # noqa: E711
    )
    if market:
        hist_dates_q = hist_dates_q.filter(Position.market == market)

    hist_dates = (
        hist_dates_q.distinct()
        .order_by(Position.snapshot_date.desc())
        .limit(limit)
        .all()
    )

    if not hist_dates:
        return {"snapshots": []}

    date_list = [d[0] for d in hist_dates]

    # Fetch positions for those dates
    pos_query = db.query(Position).filter(
        Position.account_id.in_(account_ids),
        Position.snapshot_date.in_(date_list),
    )
    if market:
        pos_query = pos_query.filter(Position.market == market)

    positions = pos_query.order_by(
        Position.snapshot_date.desc(), Position.market, Position.code
    ).all()

    # Group by date
    from collections import defaultdict

    by_date = defaultdict(list)
    for p in positions:
        by_date[p.snapshot_date].append(
            {
                "code": f"{p.market}.{p.code}",
                "name": p.stock_name or "",
                "qty": float(p.qty),
                "cost_price": float(p.cost_price or 0),
                "market_price": float(p.market_price or 0),
                "market_val": float(p.market_val or 0),
                "pl_val": float(p.pl_val or 0),
                "pl_ratio": _normalize_pl_ratio(p.market, p.pl_ratio),
            }
        )

    snapshots = [
        {"date": d.isoformat(), "positions": by_date[d]} for d in sorted(by_date.keys(), reverse=True)
    ]

    return {"snapshots": snapshots}
