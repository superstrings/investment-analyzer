"""
Trading calendar API routes.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from api.auth import get_current_user

router = APIRouter(tags=["calendar"])


class CalendarSyncRequest(BaseModel):
    market: str
    year: Optional[int] = None


@router.get("/api/calendar")
async def api_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    username: str = Depends(get_current_user),
):
    """Get calendar data for a month."""
    from services.trading_calendar_service import create_trading_calendar_service

    today = date.today()
    if year is None:
        year = today.year
    if month is None:
        month = today.month

    svc = create_trading_calendar_service()
    days = svc.get_calendar_data(year, month)

    return {
        "year": year,
        "month": month,
        "days": days,
    }


@router.post("/api/calendar/sync")
async def api_calendar_sync(
    body: CalendarSyncRequest,
    username: str = Depends(get_current_user),
):
    """Sync trading calendar data for a market."""
    from services.trading_calendar_service import (
        SUPPORTED_MARKETS,
        create_trading_calendar_service,
    )

    market = body.market.upper()
    year = body.year or date.today().year

    svc = create_trading_calendar_service()

    if market == "ALL":
        results = svc.sync_all_markets(year)
        total = sum(results.values())
        return {"success": True, "count": total, "details": results}

    if market not in SUPPORTED_MARKETS:
        return {"success": False, "error": f"Unsupported market: {market}"}

    start = date(year, 1, 1)
    end = date(year, 12, 31)
    count = svc.sync_market(market, start, end)

    return {"success": True, "count": count}
