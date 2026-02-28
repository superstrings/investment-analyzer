"""
Signal management service.

Handles CRUD operations for trading signals and accuracy tracking.
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_

from db.database import get_session
from db.models import Signal, SignalFeedback

logger = logging.getLogger(__name__)


@dataclass
class SignalAccuracy:
    """Signal accuracy statistics."""

    total_signals: int = 0
    acted_signals: int = 0
    profitable: int = 0
    loss: int = 0
    breakeven: int = 0
    pending: int = 0
    win_rate: float = 0.0
    avg_pl_ratio: float = 0.0


class SignalService:
    """Service for managing trading signals."""

    def create_signal(
        self,
        user_id: int,
        market: str,
        code: str,
        signal_type: str,
        signal_source: str,
        stock_name: str = None,
        signal_category: str = "stock",
        score: Decimal = None,
        confidence: Decimal = None,
        strength: str = None,
        trigger_price: Decimal = None,
        target_price: Decimal = None,
        stop_loss_price: Decimal = None,
        reason: str = None,
        metadata_json: str = None,
        expires_at: datetime = None,
    ) -> Signal:
        """Create a new trading signal."""
        # Normalize A-share market prefix: SH/SZ → A
        if market in ("SH", "SZ"):
            market = "A"

        with get_session() as session:
            signal = Signal(
                user_id=user_id,
                market=market,
                code=code,
                stock_name=stock_name,
                signal_type=signal_type.upper(),
                signal_source=signal_source,
                signal_category=signal_category,
                score=score,
                confidence=confidence,
                strength=strength,
                trigger_price=trigger_price,
                target_price=target_price,
                stop_loss_price=stop_loss_price,
                reason=reason,
                metadata_json=metadata_json,
                expires_at=expires_at,
            )
            session.add(signal)
            session.flush()
            session.expunge(signal)
            return signal

    def get_active_signals(
        self,
        user_id: int,
        market: str = None,
        signal_type: str = None,
    ) -> list[Signal]:
        """Get active (non-expired, non-acted) signals."""
        with get_session() as session:
            query = session.query(Signal).filter_by(user_id=user_id, is_active=True)
            if market:
                query = query.filter_by(market=market)
            if signal_type:
                query = query.filter_by(signal_type=signal_type.upper())
            query = query.order_by(Signal.created_at.desc())
            signals = query.all()
            for s in signals:
                session.expunge(s)
            return signals

    def get_signals_by_date(
        self, user_id: int, target_date: date = None
    ) -> list[Signal]:
        """Get signals created on a specific date."""
        if target_date is None:
            target_date = date.today()
        with get_session() as session:
            start = datetime.combine(target_date, datetime.min.time())
            end = datetime.combine(target_date, datetime.max.time())
            signals = (
                session.query(Signal)
                .filter(
                    Signal.user_id == user_id,
                    Signal.created_at >= start,
                    Signal.created_at <= end,
                )
                .order_by(Signal.created_at.desc())
                .all()
            )
            for s in signals:
                session.expunge(s)
            return signals

    def get_signals_by_codes(
        self,
        user_id: int,
        codes: list[str],
    ) -> dict[str, list[Signal]]:
        """
        Get active signals for multiple stock codes.

        Args:
            user_id: User ID
            codes: List of full codes like ["HK.00700", "US.AAPL"]

        Returns:
            Dict mapping full_code to list of active signals
        """
        with get_session() as session:
            signals = (
                session.query(Signal)
                .filter(
                    Signal.user_id == user_id,
                    Signal.is_active == True,
                )
                .order_by(Signal.created_at.desc())
                .all()
            )

            code_set = set(codes)
            result: dict[str, list[Signal]] = {}
            for s in signals:
                fc = f"{s.market}.{s.code}"
                # Normalize A-share: SH/SZ → A for matching
                if s.market in ("SH", "SZ"):
                    fc = f"A.{s.code}"
                if fc in code_set:
                    session.expunge(s)
                    result.setdefault(fc, []).append(s)

            return result

    def expire_old_signals(self, user_id: int) -> int:
        """Deactivate expired signals. Returns count of expired signals."""
        now = datetime.now()
        with get_session() as session:
            result = (
                session.query(Signal)
                .filter(
                    Signal.user_id == user_id,
                    Signal.is_active == True,
                    Signal.expires_at != None,
                    Signal.expires_at < now,
                )
                .update({"is_active": False}, synchronize_session="fetch")
            )
            return result

    def mark_acted_on(
        self,
        signal_id: int,
        user_id: int,
        action_taken: str,
        action_date: date = None,
        entry_price: Decimal = None,
        exit_price: Decimal = None,
        outcome: str = None,
        pl_amount: Decimal = None,
        pl_ratio: Decimal = None,
        notes: str = None,
    ) -> SignalFeedback:
        """Mark a signal as acted on and record feedback."""
        with get_session() as session:
            signal = session.query(Signal).filter_by(id=signal_id).first()
            if signal:
                signal.acted_on = True

            feedback = SignalFeedback(
                signal_id=signal_id,
                user_id=user_id,
                action_taken=action_taken,
                action_date=action_date or date.today(),
                entry_price=entry_price,
                exit_price=exit_price,
                outcome=outcome,
                pl_amount=pl_amount,
                pl_ratio=pl_ratio,
                notes=notes,
            )
            session.add(feedback)
            session.flush()
            session.expunge(feedback)
            return feedback

    def get_signal_accuracy(self, user_id: int, days: int = 90) -> SignalAccuracy:
        """Calculate signal accuracy statistics over a period."""
        cutoff = datetime.now() - timedelta(days=days)
        with get_session() as session:
            signals = (
                session.query(Signal)
                .filter(
                    Signal.user_id == user_id,
                    Signal.created_at >= cutoff,
                )
                .all()
            )

            total = len(signals)
            acted = sum(1 for s in signals if s.acted_on)

            feedbacks = (
                session.query(SignalFeedback)
                .filter(
                    SignalFeedback.user_id == user_id,
                    SignalFeedback.created_at >= cutoff,
                )
                .all()
            )

            profitable = sum(1 for f in feedbacks if f.outcome == "profit")
            loss = sum(1 for f in feedbacks if f.outcome == "loss")
            breakeven = sum(1 for f in feedbacks if f.outcome == "breakeven")
            pending = sum(1 for f in feedbacks if f.outcome == "pending")

            closed = profitable + loss
            win_rate = (profitable / closed * 100) if closed > 0 else 0.0

            pl_ratios = [float(f.pl_ratio) for f in feedbacks if f.pl_ratio is not None]
            avg_pl = sum(pl_ratios) / len(pl_ratios) if pl_ratios else 0.0

            return SignalAccuracy(
                total_signals=total,
                acted_signals=acted,
                profitable=profitable,
                loss=loss,
                breakeven=breakeven,
                pending=pending,
                win_rate=win_rate,
                avg_pl_ratio=avg_pl,
            )


def create_signal_service() -> SignalService:
    """Factory function for SignalService."""
    return SignalService()
