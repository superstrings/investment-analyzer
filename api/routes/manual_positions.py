"""
Manual positions CRUD API.

Allows adding/editing/deleting manually tracked positions.
"""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_
from sqlalchemy.orm import Session

from api.auth import get_current_user
from api.dependencies import get_db, resolve_user
from db.models import Account, Position

router = APIRouter(tags=["manual_positions"])


class ManualPositionCreate(BaseModel):
    market: str  # HK, US, A, JP
    code: str
    stock_name: str = ""
    qty: float
    cost_price: float
    market_price: float = 0


class ManualPositionUpdate(BaseModel):
    stock_name: str | None = None
    qty: float | None = None
    cost_price: float | None = None
    market_price: float | None = None


def _get_or_create_manual_account(db: Session, user_id: int) -> Account:
    """Get or create a virtual account for manual positions."""
    acc = db.query(Account).filter_by(user_id=user_id, account_name="manual").first()
    if not acc:
        acc = Account(
            user_id=user_id,
            futu_acc_id=0,
            account_name="manual",
            account_type="REAL",
            market="ALL",
            currency="CNY",
            is_active=True,
        )
        db.add(acc)
        db.flush()
    return acc


@router.get("/api/positions/manual")
async def list_manual_positions(
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all manual positions."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    account_ids = [acc.id for acc in db.query(Account).filter_by(user_id=user.id).all()]
    if not account_ids:
        return {"positions": []}

    positions = (
        db.query(Position)
        .filter(
            Position.account_id.in_(account_ids),
            Position.source == "manual",
        )
        .order_by(Position.market, Position.code)
        .all()
    )

    return {
        "positions": [
            {
                "id": p.id,
                "market": p.market,
                "code": p.code,
                "stock_name": p.stock_name or "",
                "qty": float(p.qty),
                "cost_price": float(p.cost_price or 0),
                "market_price": float(p.market_price or 0),
                "market_val": float(p.market_val or 0),
                "pl_val": float(p.pl_val or 0),
                "pl_ratio": float(p.pl_ratio or 0),
                "source": "manual",
            }
            for p in positions
        ]
    }


@router.post("/api/positions/manual")
async def create_manual_position(
    data: ManualPositionCreate,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a manual position."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    acc = _get_or_create_manual_account(db, user.id)
    today = date.today()

    # Check for existing manual position with same code
    existing = (
        db.query(Position)
        .filter(
            and_(
                Position.account_id == acc.id,
                Position.snapshot_date == today,
                Position.market == data.market,
                Position.code == data.code,
                Position.source == "manual",
            )
        )
        .first()
    )
    if existing:
        return {"error": f"手动持仓 {data.market}.{data.code} 今日已存在"}

    qty = Decimal(str(data.qty))
    cost_price = Decimal(str(data.cost_price))
    market_price = Decimal(str(data.market_price)) if data.market_price else cost_price
    market_val = qty * market_price
    pl_val = (market_price - cost_price) * qty
    pl_ratio = (market_price - cost_price) / cost_price if cost_price else Decimal("0")

    position = Position(
        account_id=acc.id,
        snapshot_date=today,
        market=data.market,
        code=data.code,
        stock_name=data.stock_name,
        qty=qty,
        cost_price=cost_price,
        market_price=market_price,
        market_val=market_val,
        pl_val=pl_val,
        pl_ratio=pl_ratio,
        position_side="LONG",
        source="manual",
    )
    db.add(position)
    db.commit()

    return {"success": True, "id": position.id}


@router.put("/api/positions/manual/{position_id}")
async def update_manual_position(
    position_id: int,
    data: ManualPositionUpdate,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update a manual position."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    position = db.query(Position).filter_by(id=position_id, source="manual").first()
    if not position:
        return {"error": "Position not found"}

    if data.stock_name is not None:
        position.stock_name = data.stock_name
    if data.qty is not None:
        position.qty = Decimal(str(data.qty))
    if data.cost_price is not None:
        position.cost_price = Decimal(str(data.cost_price))
    if data.market_price is not None:
        position.market_price = Decimal(str(data.market_price))

    # Recalculate derived fields
    position.market_val = position.qty * (position.market_price or Decimal("0"))
    if position.cost_price and position.cost_price > 0:
        position.pl_val = (
            (position.market_price or Decimal("0")) - position.cost_price
        ) * position.qty
        position.pl_ratio = (
            (position.market_price or Decimal("0")) - position.cost_price
        ) / position.cost_price
    db.commit()

    return {"success": True}


@router.delete("/api/positions/manual/{position_id}")
async def delete_manual_position(
    position_id: int,
    username: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a manual position."""
    user = resolve_user(db, username)
    if not user:
        return {"error": "User not found"}

    position = db.query(Position).filter_by(id=position_id, source="manual").first()
    if not position:
        return {"error": "Position not found"}

    db.delete(position)
    db.commit()

    return {"success": True}
