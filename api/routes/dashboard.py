"""
Dashboard summary API route.
"""

from datetime import date

from fastapi import APIRouter, Depends

from api.auth import get_current_user

router = APIRouter(tags=["dashboard"])


@router.get("/api/dashboard/summary")
async def api_dashboard_summary(
    username: str = Depends(get_current_user),
):
    """Get dashboard summary data (positions + signals + plans)."""
    from db.database import get_session
    from db.models import User
    from services.plan_service import create_plan_service
    from services.signal_service import create_signal_service
    from skills.shared.data_provider import DataProvider

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    dp = DataProvider(cache_ttl_seconds=60)

    # Positions
    positions = dp.get_positions(user_id)
    total_val = sum(float(p.market_val) for p in positions)
    total_pl = sum(float(p.pl_val) for p in positions)

    # Market distribution
    market_dist = {}
    for p in positions:
        market_dist.setdefault(p.market, 0)
        market_dist[p.market] += float(p.market_val)

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

    return {
        "portfolio": {
            "total_positions": len(positions),
            "total_market_val": total_val,
            "total_pl": total_pl,
            "total_pl_ratio": (total_pl / total_val * 100) if total_val else 0,
            "market_distribution": market_dist,
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
    }
