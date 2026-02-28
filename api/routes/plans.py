"""
Trading plans API routes.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from services.plan_service import create_plan_service

router = APIRouter(tags=["plans"])


class ExecuteRequest(BaseModel):
    price: Optional[float] = None
    notes: Optional[str] = None


class CancelRequest(BaseModel):
    reason: Optional[str] = None


@router.get("/api/plans")
async def api_plans(
    username: str = Depends(get_current_user),
    date_str: str = "",
    status: str = "",
    code: str = "",
    all_dates: bool = False,
    offset: int = 0,
    limit: int = 20,
):
    """Get trading plans with optional pagination."""
    from db.database import get_session
    from db.models import User

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}
        user_id = user.id

    svc = create_plan_service()

    if all_dates or code:
        # Use paginated query (no date filter)
        plans_list, total = svc.get_plans_paginated(
            user_id,
            status=status or None,
            code=code or None,
            offset=offset,
            limit=limit,
        )
        result = []
        for p in plans_list:
            result.append(
                {
                    "id": p.id,
                    "code": f"{p.market}.{p.code}",
                    "name": p.stock_name or "",
                    "action": p.action_type,
                    "priority": p.priority,
                    "entry_price": float(p.entry_price) if p.entry_price else None,
                    "stop_loss": (
                        float(p.stop_loss_price) if p.stop_loss_price else None
                    ),
                    "target_1": float(p.target_price_1) if p.target_price_1 else None,
                    "target_2": float(p.target_price_2) if p.target_price_2 else None,
                    "position_size": p.position_size or "",
                    "reason": p.reason or "",
                    "status": p.status,
                    "plan_date": p.plan_date.isoformat(),
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                    "execution_price": (
                        float(p.execution_price) if p.execution_price else None
                    ),
                }
            )
        return {
            "plans": result,
            "total": total,
            "offset": offset,
            "limit": limit,
        }

    # Legacy date-based query
    from datetime import datetime

    target_date = (
        datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    )

    if status:
        plans = svc.get_plans_by_date(user_id, target_date)
        plans = [p for p in plans if p.status == status]
    else:
        plans = svc.get_plans_by_date(user_id, target_date)

    result = []
    for p in plans:
        result.append(
            {
                "id": p.id,
                "code": f"{p.market}.{p.code}",
                "name": p.stock_name or "",
                "action": p.action_type,
                "priority": p.priority,
                "entry_price": float(p.entry_price) if p.entry_price else None,
                "stop_loss": float(p.stop_loss_price) if p.stop_loss_price else None,
                "target_1": float(p.target_price_1) if p.target_price_1 else None,
                "target_2": float(p.target_price_2) if p.target_price_2 else None,
                "position_size": p.position_size or "",
                "reason": p.reason or "",
                "status": p.status,
                "plan_date": p.plan_date.isoformat(),
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "executed_at": p.executed_at.isoformat() if p.executed_at else None,
                "execution_price": (
                    float(p.execution_price) if p.execution_price else None
                ),
            }
        )

    return {"plans": result, "date": target_date.isoformat()}


@router.post("/api/plans/{plan_id}/execute")
async def api_execute_plan(
    plan_id: int,
    body: ExecuteRequest,
    username: str = Depends(get_current_user),
):
    """Mark a plan as executed."""
    svc = create_plan_service()
    plan = svc.mark_executed(
        plan_id,
        price=Decimal(str(body.price)) if body.price else None,
        notes=body.notes,
    )
    if not plan:
        return {"error": f"Plan #{plan_id} not found"}

    return {"success": True, "plan_id": plan.id, "status": plan.status}


@router.post("/api/plans/{plan_id}/cancel")
async def api_cancel_plan(
    plan_id: int,
    body: CancelRequest,
    username: str = Depends(get_current_user),
):
    """Cancel a plan."""
    svc = create_plan_service()
    plan = svc.cancel_plan(plan_id, reason=body.reason)
    if not plan:
        return {"error": f"Plan #{plan_id} not found"}

    return {"success": True, "plan_id": plan.id, "status": plan.status}
