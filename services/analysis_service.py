"""
Analysis result storage service.

Handles saving and retrieving analysis snapshots with UPSERT support.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert

from db.database import get_session
from db.models import AnalysisResult

logger = logging.getLogger(__name__)


class AnalysisResultService:
    """Service for managing analysis result snapshots."""

    def save_result(
        self,
        user_id: int,
        market: str,
        code: str,
        analysis_type: str,
        analysis_date: date = None,
        stock_name: str = None,
        overall_score: Decimal = None,
        obv_score: Decimal = None,
        vcp_score: Decimal = None,
        rating: str = None,
        current_price: Decimal = None,
        support_price: Decimal = None,
        resistance_price: Decimal = None,
        result_json: str = None,
    ) -> AnalysisResult:
        """Save or update an analysis result (UPSERT on user+market+code+date)."""
        if analysis_date is None:
            analysis_date = date.today()

        with get_session() as session:
            stmt = pg_insert(AnalysisResult).values(
                user_id=user_id,
                market=market,
                code=code,
                stock_name=stock_name,
                analysis_date=analysis_date,
                analysis_type=analysis_type,
                overall_score=overall_score,
                obv_score=obv_score,
                vcp_score=vcp_score,
                rating=rating,
                current_price=current_price,
                support_price=support_price,
                resistance_price=resistance_price,
                result_json=result_json,
            )
            stmt = stmt.on_conflict_do_update(
                constraint="uq_analysis_results_user_code_date",
                set_={
                    "analysis_type": stmt.excluded.analysis_type,
                    "stock_name": stmt.excluded.stock_name,
                    "overall_score": stmt.excluded.overall_score,
                    "obv_score": stmt.excluded.obv_score,
                    "vcp_score": stmt.excluded.vcp_score,
                    "rating": stmt.excluded.rating,
                    "current_price": stmt.excluded.current_price,
                    "support_price": stmt.excluded.support_price,
                    "resistance_price": stmt.excluded.resistance_price,
                    "result_json": stmt.excluded.result_json,
                },
            )
            session.execute(stmt)
            session.flush()

            # Fetch the result back
            result = (
                session.query(AnalysisResult)
                .filter_by(
                    user_id=user_id,
                    market=market,
                    code=code,
                    analysis_date=analysis_date,
                )
                .first()
            )
            if result:
                session.expunge(result)
            return result

    def get_latest_result(
        self, user_id: int, market: str, code: str
    ) -> Optional[AnalysisResult]:
        """Get the most recent analysis result for a stock."""
        with get_session() as session:
            result = (
                session.query(AnalysisResult)
                .filter_by(user_id=user_id, market=market, code=code)
                .order_by(AnalysisResult.analysis_date.desc())
                .first()
            )
            if result:
                session.expunge(result)
            return result

    def get_results_paginated(
        self,
        user_id: int,
        market: str = None,
        code: str = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[AnalysisResult], int]:
        """Get analysis results with pagination and filtering. Returns (results, total)."""
        with get_session() as session:
            query = session.query(AnalysisResult).filter(
                AnalysisResult.user_id == user_id
            )
            if market:
                query = query.filter(AnalysisResult.market == market)
            if code:
                if "." in code:
                    parts = code.split(".", 1)
                    query = query.filter(
                        AnalysisResult.market == parts[0],
                        AnalysisResult.code == parts[1],
                    )
                else:
                    query = query.filter(AnalysisResult.code == code)
            total = query.count()
            results = (
                query.order_by(
                    AnalysisResult.analysis_date.desc(),
                    AnalysisResult.created_at.desc(),
                )
                .offset(offset)
                .limit(limit)
                .all()
            )
            for r in results:
                session.expunge(r)
            return results, total

    def get_stats(self, user_id: int) -> dict:
        """Get aggregate stats for analysis results."""
        with get_session() as session:
            row = (
                session.query(
                    func.count(AnalysisResult.id).label("total"),
                    func.avg(AnalysisResult.overall_score).label("avg_score"),
                    func.max(AnalysisResult.overall_score).label("max_score"),
                    func.min(AnalysisResult.overall_score).label("min_score"),
                )
                .filter(AnalysisResult.user_id == user_id)
                .first()
            )
            return {
                "total": row.total or 0,
                "avg_score": float(row.avg_score) if row.avg_score else None,
                "max_score": float(row.max_score) if row.max_score else None,
                "min_score": float(row.min_score) if row.min_score else None,
            }

    def get_results_by_date(
        self, user_id: int, target_date: date = None
    ) -> list[AnalysisResult]:
        """Get all analysis results for a specific date."""
        if target_date is None:
            target_date = date.today()

        with get_session() as session:
            results = (
                session.query(AnalysisResult)
                .filter_by(user_id=user_id, analysis_date=target_date)
                .order_by(AnalysisResult.overall_score.desc().nulls_last())
                .all()
            )
            for r in results:
                session.expunge(r)
            return results

    def get_results_history(
        self, user_id: int, market: str, code: str, days: int = 30
    ) -> list[AnalysisResult]:
        """Get analysis history for a stock over N days."""
        from datetime import timedelta

        cutoff = date.today() - timedelta(days=days)
        with get_session() as session:
            results = (
                session.query(AnalysisResult)
                .filter(
                    AnalysisResult.user_id == user_id,
                    AnalysisResult.market == market,
                    AnalysisResult.code == code,
                    AnalysisResult.analysis_date >= cutoff,
                )
                .order_by(AnalysisResult.analysis_date.asc())
                .all()
            )
            for r in results:
                session.expunge(r)
            return results


def create_analysis_service() -> AnalysisResultService:
    """Factory function for AnalysisResultService."""
    return AnalysisResultService()
