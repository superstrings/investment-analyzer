"""
Signals API routes.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.dependencies import get_db, resolve_user
from services.signal_service import create_signal_service

router = APIRouter(tags=["signals"])


class FeedbackRequest(BaseModel):
    action_taken: str  # followed/ignored/partial
    entry_price: Optional[float] = None
    exit_price: Optional[float] = None
    outcome: Optional[str] = None  # profit/loss/breakeven/pending
    pl_amount: Optional[float] = None
    pl_ratio: Optional[float] = None
    notes: Optional[str] = None


@router.get("/api/signals")
async def api_signals(
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
    market: str = "",
    signal_type: str = "",
    active_only: bool = True,
    code: str = "",
    offset: int = 0,
    limit: int = 20,
):
    """Get signals with optional pagination."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}
    user_id = user.id

    svc = create_signal_service()

    signals, total = svc.get_signals_paginated(
        user_id,
        active_only=active_only,
        market=market or None,
        signal_type=signal_type or None,
        code=code or None,
        offset=offset,
        limit=limit,
    )

    result = []
    for s in signals:
        result.append(
            {
                "id": s.id,
                "code": f"{s.market}.{s.code}",
                "name": s.stock_name or "",
                "type": s.signal_type,
                "source": s.signal_source,
                "score": float(s.score) if s.score else None,
                "confidence": float(s.confidence) if s.confidence else None,
                "strength": s.strength,
                "trigger_price": float(s.trigger_price) if s.trigger_price else None,
                "target_price": float(s.target_price) if s.target_price else None,
                "stop_loss": float(s.stop_loss_price) if s.stop_loss_price else None,
                "reason": s.reason or "",
                "acted_on": s.acted_on,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
        )

    # Get accuracy stats
    accuracy = svc.get_signal_accuracy(user_id)

    return {
        "signals": result,
        "total": total,
        "offset": offset,
        "limit": limit,
        "accuracy": {
            "total": accuracy.total_signals,
            "win_rate": accuracy.win_rate,
            "profitable": accuracy.profitable,
            "loss": accuracy.loss,
        },
    }


@router.post("/api/signals/{signal_id}/feedback")
async def api_signal_feedback(
    signal_id: int,
    body: FeedbackRequest,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record signal feedback."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}
    user_id = user.id

    svc = create_signal_service()
    feedback = svc.mark_acted_on(
        signal_id=signal_id,
        user_id=user_id,
        action_taken=body.action_taken,
        entry_price=Decimal(str(body.entry_price)) if body.entry_price else None,
        exit_price=Decimal(str(body.exit_price)) if body.exit_price else None,
        outcome=body.outcome,
        pl_amount=Decimal(str(body.pl_amount)) if body.pl_amount else None,
        pl_ratio=Decimal(str(body.pl_ratio)) if body.pl_ratio else None,
        notes=body.notes,
    )

    return {"success": True, "feedback_id": feedback.id}
