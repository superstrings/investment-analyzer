"""
Dashboard summary API route.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func

from api.auth import get_current_user

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/summary")
async def api_dashboard_summary(
    username: str = Depends(get_current_user),
):
    """Get dashboard summary data (positions + signals + plans)."""
    from db.database import get_session
    from db.models import Account, Position, User
    from services.exchange_rate_service import create_exchange_rate_service
    from services.plan_service import create_plan_service
    from services.signal_service import create_signal_service

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

        # Get latest snapshot positions (same logic as portfolio API)
        account_ids = [
            acc.id
            for acc in session.query(Account).filter_by(user_id=user_id).all()
        ]

        positions = []
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
            all_positions = (
                session.query(Position)
                .join(
                    latest_dates,
                    (Position.account_id == latest_dates.c.account_id)
                    & (Position.snapshot_date == latest_dates.c.max_date),
                )
                .order_by(Position.market, Position.pl_ratio.desc())
                .all()
            )

            # Deduplicate by (market, code)
            seen = set()
            positions = []
            for p in all_positions:
                key = (p.market, p.code)
                if key not in seen:
                    seen.add(key)
                    positions.append(p)

    fx = create_exchange_rate_service()

    total_val_cny = Decimal("0")
    total_pl_cny = Decimal("0")
    market_dist = {}  # market -> CNY value

    for p in positions:
        currency = fx.get_market_currency(p.market)
        rate = fx.get_rate_to_cny(currency)
        market_val = p.market_val or Decimal("0")
        pl_val = p.pl_val or Decimal("0")
        val_cny = market_val * rate
        pl_cny = pl_val * rate

        total_val_cny += val_cny
        total_pl_cny += pl_cny
        market_dist.setdefault(p.market, 0)
        market_dist[p.market] += float(val_cny)

    # Active signals
    signal_svc = create_signal_service()
    signals = signal_svc.get_active_signals(user_id)
    signal_counts = {}
    for s in signals:
        signal_counts[s.signal_type] = signal_counts.get(s.signal_type, 0) + 1

    # Today's plans
    plan_svc = create_plan_service()
    plans = plan_svc.get_plans_by_date(user_id, date.today())
    plan_counts = {"pending": 0, "executed": 0, "cancelled": 0}
    for p in plans:
        plan_counts[p.status] = plan_counts.get(p.status, 0) + 1

    # Signal accuracy
    accuracy = signal_svc.get_signal_accuracy(user_id)

    # Exchange rates
    rates = fx.get_all_rates()

    return {
        "portfolio": {
            "total_positions": len(positions),
            "total_market_val": float(total_val_cny),
            "total_pl": float(total_pl_cny),
            "total_pl_ratio": (
                float(total_pl_cny / total_val_cny * 100) if total_val_cny else 0
            ),
            "market_distribution": market_dist,
            "currency": "CNY",
        },
        "signals": {
            "active_count": len(signals),
            "by_type": signal_counts,
        },
        "plans": {
            "today_count": len(plans),
            "by_status": plan_counts,
        },
        "accuracy": {
            "win_rate": accuracy.win_rate,
            "total_signals": accuracy.total_signals,
            "profitable": accuracy.profitable,
            "loss": accuracy.loss,
        },
        "exchange_rates": {k: float(v) for k, v in rates.items()},
    }


@router.post("/api/dashboard/push-dingtalk")
async def api_push_dingtalk(username: str = Depends(get_current_user)):
    """Push portfolio summary + plans to DingTalk."""
    from api.routes.dingtalk import (
        _format_plans_summary,
        _format_positions_summary,
        _format_signals_summary,
        _get_default_user_id,
    )
    from services.dingtalk_service import create_dingtalk_service

    user_id = _get_default_user_id()
    if not user_id:
        return {"success": False, "error": "User not found"}

    dingtalk = create_dingtalk_service()
    if not dingtalk.webhook_url:
        return {"success": False, "error": "DingTalk not configured"}

    positions_md = _format_positions_summary(user_id)
    plans_md = _format_plans_summary(user_id)
    signals_md = _format_signals_summary(user_id)

    full_md = f"{positions_md}\n\n---\n\n{plans_md}\n\n---\n\n{signals_md}"
    result = dingtalk.send_markdown("每日概览", full_md, user_id=user_id, message_type="portfolio_summary")

    return {"success": result}


@router.get("/api/exchange-rates")
async def api_exchange_rates(username: str = Depends(get_current_user)):
    """Get current exchange rates with update timestamps."""
    from services.exchange_rate_service import create_exchange_rate_service

    fx = create_exchange_rate_service()
    return {"rates": fx.get_all_rates_with_time()}


@router.post("/api/exchange-rates/refresh")
async def api_refresh_exchange_rates(username: str = Depends(get_current_user)):
    """Trigger BOC API refresh and write updated rates to DB."""
    from services.exchange_rate_service import create_exchange_rate_service

    fx = create_exchange_rate_service()
    result = fx.refresh_rates()
    return result
