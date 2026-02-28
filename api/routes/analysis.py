"""
Analysis results API routes.
"""

from datetime import date

from fastapi import APIRouter, Depends

from api.auth import get_current_user
from services.analysis_service import create_analysis_service

router = APIRouter(tags=["analysis"])


@router.get("/api/analysis")
async def api_analysis_results(
    username: str = Depends(get_current_user),
    date_str: str = "",
):
    """Get analysis results for a date."""
    from datetime import datetime

    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    target_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    )

    svc = create_analysis_service()
    results = svc.get_results_by_date(user_id, target_date)

    data = []
    for r in results:
        data.append(
            {
                "code": f"{r.market}.{r.code}",
                "name": r.stock_name or "",
                "type": r.analysis_type,
                "overall_score": float(r.overall_score) if r.overall_score else None,
                "obv_score": float(r.obv_score) if r.obv_score else None,
                "vcp_score": float(r.vcp_score) if r.vcp_score else None,
                "rating": r.rating,
                "price": float(r.current_price) if r.current_price else None,
                "support": float(r.support_price) if r.support_price else None,
                "resistance": float(r.resistance_price) if r.resistance_price else None,
            }
        )

    return {"results": data, "date": target_date.isoformat()}


@router.get("/api/analysis/{code}")
async def api_analysis_history(
    code: str,
    username: str = Depends(get_current_user),
    days: int = 30,
):
    """Get analysis history for a stock."""
    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    parts = code.split(".", 1)
    if len(parts) != 2:
        return {"error": "Invalid code format"}

    market, stock_code = parts
    db_market = "A" if market in ("SH", "SZ") else market

    svc = create_analysis_service()
    results = svc.get_results_history(user_id, db_market, stock_code, days)

    data = []
    for r in results:
        data.append(
            {
                "date": r.analysis_date.isoformat(),
                "type": r.analysis_type,
                "overall_score": float(r.overall_score) if r.overall_score else None,
                "rating": r.rating,
                "price": float(r.current_price) if r.current_price else None,
            }
        )

    return {"code": code, "history": data}
