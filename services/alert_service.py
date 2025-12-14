"""
Price alert service for monitoring stock prices.

Provides functionality to:
- Create, update, and delete price alerts
- Check alerts against current prices
- Trigger alerts and notifications
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy.orm import Session

from db import PriceAlert, User, get_session


class AlertType(str, Enum):
    """Alert type enumeration."""

    ABOVE = "ABOVE"  # Price goes above target
    BELOW = "BELOW"  # Price goes below target
    CHANGE_UP = "CHANGE_UP"  # Price increases by percentage
    CHANGE_DOWN = "CHANGE_DOWN"  # Price decreases by percentage


@dataclass
class AlertResult:
    """Result of an alert check."""

    alert_id: int
    triggered: bool
    current_price: Optional[float] = None
    target_price: Optional[float] = None
    change_pct: Optional[float] = None
    message: Optional[str] = None


@dataclass
class AlertSummary:
    """Summary of alert checks."""

    total_checked: int = 0
    total_triggered: int = 0
    results: list[AlertResult] = None

    def __post_init__(self):
        if self.results is None:
            self.results = []


class AlertService:
    """Service for managing and checking price alerts."""

    def __init__(self, session: Optional[Session] = None):
        """Initialize alert service.

        Args:
            session: Optional SQLAlchemy session. If not provided,
                     a new session will be created for each operation.
        """
        self._session = session
        self._external_session = session is not None

    def _get_session(self) -> Session:
        """Get or create a session."""
        if self._session:
            return self._session
        return get_session().__enter__()

    def create_alert(
        self,
        user_id: int,
        market: str,
        code: str,
        alert_type: AlertType,
        target_price: Optional[float] = None,
        target_change_pct: Optional[float] = None,
        base_price: Optional[float] = None,
        stock_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PriceAlert:
        """
        Create a new price alert.

        Args:
            user_id: User ID
            market: Market code (HK/US/A)
            code: Stock code
            alert_type: Type of alert (ABOVE/BELOW/CHANGE_UP/CHANGE_DOWN)
            target_price: Target price for ABOVE/BELOW alerts
            target_change_pct: Target change percentage for CHANGE alerts
            base_price: Base price for calculating change percentage
            stock_name: Optional stock name
            notes: Optional notes

        Returns:
            Created PriceAlert instance

        Raises:
            ValueError: If required parameters are missing
        """
        # Validate parameters
        if alert_type in (AlertType.ABOVE, AlertType.BELOW):
            if target_price is None:
                raise ValueError(f"target_price is required for {alert_type} alerts")
        else:  # CHANGE_UP/CHANGE_DOWN
            if target_change_pct is None:
                raise ValueError(
                    f"target_change_pct is required for {alert_type} alerts"
                )

        session = self._get_session()

        alert = PriceAlert(
            user_id=user_id,
            market=market.upper(),
            code=code,
            stock_name=stock_name,
            alert_type=alert_type.value,
            target_price=Decimal(str(target_price)) if target_price else None,
            target_change_pct=(
                Decimal(str(target_change_pct)) if target_change_pct else None
            ),
            base_price=Decimal(str(base_price)) if base_price else None,
            notes=notes,
            is_active=True,
            is_triggered=False,
        )

        session.add(alert)
        session.commit()
        session.refresh(alert)

        return alert

    def get_alert(self, alert_id: int) -> Optional[PriceAlert]:
        """Get an alert by ID."""
        session = self._get_session()
        return session.query(PriceAlert).filter_by(id=alert_id).first()

    def get_user_alerts(
        self,
        user_id: int,
        active_only: bool = True,
        market: Optional[str] = None,
        code: Optional[str] = None,
    ) -> list[PriceAlert]:
        """
        Get alerts for a user.

        Args:
            user_id: User ID
            active_only: Only return active (non-triggered) alerts
            market: Optional filter by market
            code: Optional filter by stock code

        Returns:
            List of PriceAlert instances
        """
        session = self._get_session()
        query = session.query(PriceAlert).filter_by(user_id=user_id)

        if active_only:
            query = query.filter_by(is_active=True, is_triggered=False)
        if market:
            query = query.filter_by(market=market.upper())
        if code:
            query = query.filter_by(code=code)

        return query.order_by(PriceAlert.created_at.desc()).all()

    def update_alert(
        self,
        alert_id: int,
        target_price: Optional[float] = None,
        target_change_pct: Optional[float] = None,
        base_price: Optional[float] = None,
        notes: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[PriceAlert]:
        """
        Update an existing alert.

        Args:
            alert_id: Alert ID to update
            target_price: New target price
            target_change_pct: New target change percentage
            base_price: New base price
            notes: New notes
            is_active: Active status

        Returns:
            Updated PriceAlert or None if not found
        """
        session = self._get_session()
        alert = session.query(PriceAlert).filter_by(id=alert_id).first()

        if not alert:
            return None

        if target_price is not None:
            alert.target_price = Decimal(str(target_price))
        if target_change_pct is not None:
            alert.target_change_pct = Decimal(str(target_change_pct))
        if base_price is not None:
            alert.base_price = Decimal(str(base_price))
        if notes is not None:
            alert.notes = notes
        if is_active is not None:
            alert.is_active = is_active

        session.commit()
        session.refresh(alert)

        return alert

    def delete_alert(self, alert_id: int) -> bool:
        """
        Delete an alert.

        Args:
            alert_id: Alert ID to delete

        Returns:
            True if deleted, False if not found
        """
        session = self._get_session()
        alert = session.query(PriceAlert).filter_by(id=alert_id).first()

        if not alert:
            return False

        session.delete(alert)
        session.commit()

        return True

    def check_alert(self, alert: PriceAlert, current_price: float) -> AlertResult:
        """
        Check if an alert should be triggered.

        Args:
            alert: PriceAlert instance
            current_price: Current stock price

        Returns:
            AlertResult with trigger status
        """
        triggered = False
        message = None
        change_pct = None

        alert_type = AlertType(alert.alert_type)

        if alert_type == AlertType.ABOVE:
            target = float(alert.target_price)
            if current_price >= target:
                triggered = True
                message = (
                    f"{alert.full_code} 突破 {target:.2f} (现价: {current_price:.2f})"
                )

        elif alert_type == AlertType.BELOW:
            target = float(alert.target_price)
            if current_price <= target:
                triggered = True
                message = (
                    f"{alert.full_code} 跌破 {target:.2f} (现价: {current_price:.2f})"
                )

        elif alert_type == AlertType.CHANGE_UP:
            base = float(alert.base_price) if alert.base_price else 0
            if base > 0:
                change_pct = (current_price - base) / base
                target_pct = float(alert.target_change_pct)
                if change_pct >= target_pct:
                    triggered = True
                    message = f"{alert.full_code} 涨幅达 {change_pct:.2%} (目标: +{target_pct:.2%})"

        elif alert_type == AlertType.CHANGE_DOWN:
            base = float(alert.base_price) if alert.base_price else 0
            if base > 0:
                change_pct = (current_price - base) / base
                target_pct = float(alert.target_change_pct)
                if change_pct <= -abs(target_pct):
                    triggered = True
                    message = f"{alert.full_code} 跌幅达 {change_pct:.2%} (目标: -{abs(target_pct):.2%})"

        return AlertResult(
            alert_id=alert.id,
            triggered=triggered,
            current_price=current_price,
            target_price=float(alert.target_price) if alert.target_price else None,
            change_pct=change_pct,
            message=message,
        )

    def trigger_alert(
        self, alert_id: int, triggered_price: float
    ) -> Optional[PriceAlert]:
        """
        Mark an alert as triggered.

        Args:
            alert_id: Alert ID
            triggered_price: Price at which alert was triggered

        Returns:
            Updated PriceAlert or None if not found
        """
        session = self._get_session()
        alert = session.query(PriceAlert).filter_by(id=alert_id).first()

        if not alert:
            return None

        alert.is_triggered = True
        alert.triggered_at = datetime.now()
        alert.triggered_price = Decimal(str(triggered_price))

        session.commit()
        session.refresh(alert)

        return alert

    def check_all_alerts(
        self,
        user_id: int,
        price_data: dict[str, float],
        auto_trigger: bool = True,
    ) -> AlertSummary:
        """
        Check all active alerts for a user against current prices.

        Args:
            user_id: User ID
            price_data: Dict mapping "MARKET.CODE" to current price
            auto_trigger: Whether to automatically mark triggered alerts

        Returns:
            AlertSummary with check results
        """
        alerts = self.get_user_alerts(user_id, active_only=True)
        summary = AlertSummary()

        for alert in alerts:
            full_code = alert.full_code
            if full_code not in price_data:
                continue

            current_price = price_data[full_code]
            result = self.check_alert(alert, current_price)
            summary.total_checked += 1

            if result.triggered:
                summary.total_triggered += 1
                if auto_trigger:
                    self.trigger_alert(alert.id, current_price)
                summary.results.append(result)

        return summary

    def reset_alert(self, alert_id: int) -> Optional[PriceAlert]:
        """
        Reset a triggered alert to active state.

        Args:
            alert_id: Alert ID

        Returns:
            Updated PriceAlert or None if not found
        """
        session = self._get_session()
        alert = session.query(PriceAlert).filter_by(id=alert_id).first()

        if not alert:
            return None

        alert.is_triggered = False
        alert.triggered_at = None
        alert.triggered_price = None
        alert.is_active = True

        session.commit()
        session.refresh(alert)

        return alert


def create_alert_service(session: Optional[Session] = None) -> AlertService:
    """Factory function to create AlertService."""
    return AlertService(session=session)
