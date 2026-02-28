"""
Alert CRUD API routes.
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.auth import get_current_user
from api.dependencies import get_db, resolve_user

router = APIRouter(tags=["alerts"])


class CreateAlertRequest(BaseModel):
    market: str
    code: str
    alert_type: str  # ABOVE/BELOW/STOP_LOSS/TAKE_PROFIT/OCO/CHANGE_UP/CHANGE_DOWN
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    target_change_pct: Optional[float] = None
    base_price: Optional[float] = None
    stock_name: Optional[str] = None
    notes: Optional[str] = None


@router.get("/api/alerts")
async def api_list_alerts(
    username: str = Depends(get_current_user),
    market: Optional[str] = None,
    code: Optional[str] = None,
    active_only: bool = True,
):
    """List alerts for the current user."""
    from db.database import get_session
    from db.models import User
    from services.alert_service import create_alert_service

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"error": "User not found"}

        svc = create_alert_service(session)
        alerts = svc.get_user_alerts(
            user.id, active_only=active_only, market=market, code=code
        )

        return {
            "alerts": [
                {
                    "id": a.id,
                    "code": a.full_code,
                    "stock_name": a.stock_name or "",
                    "alert_type": a.alert_type,
                    "target_price": float(a.target_price) if a.target_price else None,
                    "stop_loss_price": (
                        float(a.stop_loss_price) if a.stop_loss_price else None
                    ),
                    "take_profit_price": (
                        float(a.take_profit_price) if a.take_profit_price else None
                    ),
                    "target_change_pct": (
                        float(a.target_change_pct) if a.target_change_pct else None
                    ),
                    "description": a.target_description,
                    "notes": a.notes or "",
                    "is_active": a.is_active,
                    "is_triggered": a.is_triggered,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                }
                for a in alerts
            ]
        }


@router.post("/api/alerts")
async def api_create_alert(
    body: CreateAlertRequest,
    username: str = Depends(get_current_user),
):
    """Create a new price alert."""
    from db.database import get_session
    from db.models import User
    from services.alert_service import AlertType, create_alert_service

    try:
        alert_type = AlertType(body.alert_type.upper())
    except ValueError:
        return {"success": False, "error": f"Invalid alert type: {body.alert_type}"}

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"success": False, "error": "User not found"}

        svc = create_alert_service(session)
        try:
            alert = svc.create_alert(
                user_id=user.id,
                market=body.market,
                code=body.code,
                alert_type=alert_type,
                target_price=body.target_price,
                stop_loss_price=body.stop_loss_price,
                take_profit_price=body.take_profit_price,
                target_change_pct=body.target_change_pct,
                base_price=body.base_price,
                stock_name=body.stock_name,
                notes=body.notes,
            )
            return {
                "success": True,
                "alert": {
                    "id": alert.id,
                    "code": alert.full_code,
                    "alert_type": alert.alert_type,
                    "description": alert.target_description,
                },
            }
        except ValueError as e:
            return {"success": False, "error": str(e)}


@router.delete("/api/alerts/{alert_id}")
async def api_delete_alert(
    alert_id: int,
    username: str = Depends(get_current_user),
):
    """Delete an alert."""
    from db.database import get_session
    from db.models import PriceAlert, User
    from services.alert_service import create_alert_service

    with get_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if not user:
            return {"success": False, "error": "User not found"}

        # Verify ownership
        alert = session.query(PriceAlert).filter_by(id=alert_id).first()
        if not alert or alert.user_id != user.id:
            return {"success": False, "error": "Alert not found"}

        svc = create_alert_service(session)
        svc.delete_alert(alert_id)
        return {"success": True}
