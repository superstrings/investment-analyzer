"""
Trading plan management service.

Handles CRUD operations for trading plans with execution tracking.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from db.database import get_session
from db.models import TradingPlanRecord

logger = logging.getLogger(__name__)


class TradingPlanService:
    """Service for managing trading plans."""

    def create_plan(
        self,
        user_id: int,
        market: str,
        code: str,
        action_type: str,
        plan_date: date = None,
        stock_name: str = None,
        priority: str = "consider",
        entry_price: Decimal = None,
        stop_loss_price: Decimal = None,
        target_price_1: Decimal = None,
        target_price_2: Decimal = None,
        position_size: str = None,
        reason: str = None,
        signal_id: int = None,
    ) -> TradingPlanRecord:
        """Create a new trading plan."""
        # Normalize A-share market prefix: SH/SZ → A
        if market in ("SH", "SZ"):
            market = "A"

        if plan_date is None:
            plan_date = date.today()

        with get_session() as session:
            plan = TradingPlanRecord(
                user_id=user_id,
                market=market,
                code=code,
                stock_name=stock_name,
                plan_date=plan_date,
                action_type=action_type,
                priority=priority,
                entry_price=entry_price,
                stop_loss_price=stop_loss_price,
                target_price_1=target_price_1,
                target_price_2=target_price_2,
                position_size=position_size,
                reason=reason,
                signal_id=signal_id,
            )
            session.add(plan)
            session.flush()
            session.expunge(plan)
            return plan

    def get_active_plans(
        self, user_id: int, target_date: date = None
    ) -> list[TradingPlanRecord]:
        """Get active (pending) plans, optionally filtered by date."""
        with get_session() as session:
            query = session.query(TradingPlanRecord).filter_by(
                user_id=user_id, status="pending"
            )
            if target_date:
                query = query.filter_by(plan_date=target_date)
            query = query.order_by(
                TradingPlanRecord.plan_date.desc(),
                TradingPlanRecord.created_at.desc(),
            )
            plans = query.all()
            for p in plans:
                session.expunge(p)
            return plans

    def get_plans_by_date(
        self, user_id: int, target_date: date = None
    ) -> list[TradingPlanRecord]:
        """Get all plans for a specific date (any status)."""
        if target_date is None:
            target_date = date.today()

        with get_session() as session:
            plans = (
                session.query(TradingPlanRecord)
                .filter_by(user_id=user_id, plan_date=target_date)
                .order_by(TradingPlanRecord.created_at.desc())
                .all()
            )
            for p in plans:
                session.expunge(p)
            return plans

    def get_plans_paginated(
        self,
        user_id: int,
        status: str = None,
        code: str = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[TradingPlanRecord], int]:
        """Get plans with pagination and filtering. Returns (plans, total_count)."""
        with get_session() as session:
            query = session.query(TradingPlanRecord).filter(
                TradingPlanRecord.user_id == user_id
            )
            if status:
                query = query.filter(TradingPlanRecord.status == status)
            if code:
                if "." in code:
                    parts = code.split(".", 1)
                    query = query.filter(
                        TradingPlanRecord.market == parts[0],
                        TradingPlanRecord.code == parts[1],
                    )
                else:
                    query = query.filter(TradingPlanRecord.code == code)
            total = query.count()
            plans = (
                query.order_by(
                    TradingPlanRecord.plan_date.desc(),
                    TradingPlanRecord.created_at.desc(),
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            for p in plans:
                session.expunge(p)
            return plans, total

    def mark_executed(
        self,
        plan_id: int,
        price: Decimal = None,
        notes: str = None,
    ) -> Optional[TradingPlanRecord]:
        """Mark a plan as executed."""
        with get_session() as session:
            plan = session.query(TradingPlanRecord).filter_by(id=plan_id).first()
            if not plan:
                return None
            plan.status = "executed"
            plan.executed_at = datetime.now()
            plan.execution_price = price
            plan.execution_notes = notes
            session.flush()
            session.expunge(plan)
            return plan

    def cancel_plan(
        self, plan_id: int, reason: str = None
    ) -> Optional[TradingPlanRecord]:
        """Cancel a plan."""
        with get_session() as session:
            plan = session.query(TradingPlanRecord).filter_by(id=plan_id).first()
            if not plan:
                return None
            plan.status = "cancelled"
            if reason:
                plan.execution_notes = reason
            session.flush()
            session.expunge(plan)
            return plan

    def get_plans_by_codes(
        self,
        user_id: int,
        codes: list[str],
        include_history: bool = False,
    ) -> dict[str, list[TradingPlanRecord]]:
        """
        Get plans for multiple stock codes.

        Args:
            user_id: User ID
            codes: List of full codes like ["HK.00700", "US.AAPL"]
            include_history: If True, include executed/cancelled plans (last 30 days)

        Returns:
            Dict mapping full_code to list of plans
        """
        with get_session() as session:
            query = session.query(TradingPlanRecord).filter(
                TradingPlanRecord.user_id == user_id,
            )
            if not include_history:
                query = query.filter(TradingPlanRecord.status == "pending")
            else:
                # Include recent history (last 30 days)
                cutoff = date.today() - timedelta(days=30)
                query = query.filter(TradingPlanRecord.plan_date >= cutoff)

            query = query.order_by(
                TradingPlanRecord.plan_date.desc(),
                TradingPlanRecord.created_at.desc(),
            )
            plans = query.all()

            code_set = set(codes)
            result: dict[str, list[TradingPlanRecord]] = {}
            for p in plans:
                fc = p.full_code
                # Normalize A-share: SH/SZ → A for matching
                if p.market in ("SH", "SZ"):
                    fc = f"A.{p.code}"
                if fc in code_set:
                    session.expunge(p)
                    result.setdefault(fc, []).append(p)

            return result

    def expire_old_plans(self, user_id: int, before_date: date = None) -> int:
        """Expire old pending plans. Returns count of expired plans."""
        if before_date is None:
            before_date = date.today()

        with get_session() as session:
            result = (
                session.query(TradingPlanRecord)
                .filter(
                    TradingPlanRecord.user_id == user_id,
                    TradingPlanRecord.status == "pending",
                    TradingPlanRecord.plan_date < before_date,
                )
                .update({"status": "expired"}, synchronize_session="fetch")
            )
            return result


def create_plan_service() -> TradingPlanService:
    """Factory function for TradingPlanService."""
    return TradingPlanService()
