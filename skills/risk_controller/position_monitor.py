"""
Position Monitor for Risk Controller Skill.

Provides position-level risk diagnostics including:
- Stop-loss violation detection
- Position sizing analysis
- Holding period analysis
- Cost averaging opportunities
"""

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Optional

import pandas as pd

from analysis.portfolio import PositionData, PortfolioAnalyzer, RiskLevel


class PositionStatus(Enum):
    """Position health status."""

    HEALTHY = "healthy"
    ATTENTION = "attention"  # Minor concerns
    WARNING = "warning"  # Requires monitoring
    CRITICAL = "critical"  # Immediate action needed


class StopLossStatus(Enum):
    """Stop-loss status for a position."""

    SAFE = "safe"  # Above stop-loss level
    APPROACHING = "approaching"  # Within 2% of stop-loss
    TRIGGERED = "triggered"  # Below stop-loss level
    NOT_SET = "not_set"  # No stop-loss defined


@dataclass
class PositionDiagnostic:
    """Diagnostic result for a single position."""

    market: str
    code: str
    name: str
    qty: float
    cost_price: float
    current_price: float
    market_value: float

    # P&L metrics
    pl_value: float
    pl_ratio: float  # Percentage

    # Position status
    status: PositionStatus
    weight: float  # Portfolio weight %

    # Stop-loss analysis
    stop_loss_price: Optional[float]
    stop_loss_status: StopLossStatus
    distance_to_stop: float  # Percentage distance to stop-loss

    # Position sizing
    is_oversized: bool  # Exceeds max position size
    is_undersized: bool  # Below minimum meaningful size
    suggested_size_action: str  # "hold", "reduce", "add", "trim"

    # Holding analysis
    holding_days: Optional[int]
    avg_down_opportunity: bool  # Price significantly below cost basis

    # Signals
    signals: list[str] = field(default_factory=list)
    actions: list[str] = field(default_factory=list)

    @property
    def full_code(self) -> str:
        """Get full stock code."""
        return f"{self.market}.{self.code}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code": self.full_code,
            "name": self.name,
            "qty": self.qty,
            "cost_price": self.cost_price,
            "current_price": self.current_price,
            "market_value": self.market_value,
            "pl_value": self.pl_value,
            "pl_ratio": self.pl_ratio,
            "status": self.status.value,
            "weight": self.weight,
            "stop_loss_price": self.stop_loss_price,
            "stop_loss_status": self.stop_loss_status.value,
            "distance_to_stop": self.distance_to_stop,
            "is_oversized": self.is_oversized,
            "is_undersized": self.is_undersized,
            "suggested_size_action": self.suggested_size_action,
            "holding_days": self.holding_days,
            "avg_down_opportunity": self.avg_down_opportunity,
            "signals": self.signals,
            "actions": self.actions,
        }


@dataclass
class PortfolioDiagnostic:
    """Overall portfolio diagnostic result."""

    analysis_date: date
    total_positions: int
    healthy_count: int
    attention_count: int
    warning_count: int
    critical_count: int

    # Stop-loss summary
    positions_without_stop: int
    positions_approaching_stop: int
    positions_triggered_stop: int

    # Position sizing summary
    oversized_positions: int
    undersized_positions: int

    # Overall health score (0-100)
    health_score: float
    overall_status: PositionStatus

    # Position diagnostics
    diagnostics: list[PositionDiagnostic] = field(default_factory=list)

    # Summary signals
    summary_signals: list[str] = field(default_factory=list)
    priority_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "total_positions": self.total_positions,
            "healthy_count": self.healthy_count,
            "attention_count": self.attention_count,
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "positions_without_stop": self.positions_without_stop,
            "positions_approaching_stop": self.positions_approaching_stop,
            "positions_triggered_stop": self.positions_triggered_stop,
            "oversized_positions": self.oversized_positions,
            "undersized_positions": self.undersized_positions,
            "health_score": self.health_score,
            "overall_status": self.overall_status.value,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
            "summary_signals": self.summary_signals,
            "priority_actions": self.priority_actions,
        }


@dataclass
class PositionMonitorConfig:
    """Configuration for position monitoring."""

    # Stop-loss thresholds
    default_stop_loss_pct: float = 8.0  # Default 8% stop-loss
    stop_approaching_threshold: float = 2.0  # Within 2% of stop

    # Position sizing thresholds
    max_position_weight: float = 20.0  # Maximum single position weight
    min_position_weight: float = 2.0  # Minimum meaningful position
    optimal_position_weight: float = 10.0  # Target position weight

    # Loss thresholds
    attention_loss_pct: float = 5.0  # Attention at 5% loss
    warning_loss_pct: float = 10.0  # Warning at 10% loss
    critical_loss_pct: float = 15.0  # Critical at 15% loss

    # Avg down opportunity
    avg_down_threshold: float = 15.0  # 15% below cost basis


class PositionMonitor:
    """
    Monitor individual positions for risk issues.

    Provides detailed diagnostics for each position including:
    - Stop-loss monitoring
    - Position sizing analysis
    - P&L health check
    - Holding period analysis
    """

    def __init__(self, config: Optional[PositionMonitorConfig] = None):
        """
        Initialize position monitor.

        Args:
            config: Monitor configuration
        """
        self.config = config or PositionMonitorConfig()

    def diagnose_portfolio(
        self,
        positions: list[PositionData],
        stop_losses: Optional[dict[str, float]] = None,
        entry_dates: Optional[dict[str, date]] = None,
    ) -> PortfolioDiagnostic:
        """
        Diagnose all positions in portfolio.

        Args:
            positions: List of position data
            stop_losses: Optional dict of code -> stop-loss price
            entry_dates: Optional dict of code -> entry date

        Returns:
            PortfolioDiagnostic with complete portfolio diagnosis
        """
        stop_losses = stop_losses or {}
        entry_dates = entry_dates or {}

        # Filter active positions
        active = [p for p in positions if p.qty and abs(p.qty) > 0]

        if not active:
            return self._empty_diagnostic()

        # Calculate total market value for weight calculation
        total_mv = sum(self._get_market_value(p) for p in active)

        # Diagnose each position
        diagnostics = []
        for pos in active:
            market_value = self._get_market_value(pos)
            weight = (market_value / total_mv * 100) if total_mv > 0 else 0

            full_code = f"{pos.market}.{pos.code}"
            stop_loss = stop_losses.get(full_code)
            entry_date = entry_dates.get(full_code)

            diag = self._diagnose_position(
                pos, weight, stop_loss, entry_date
            )
            diagnostics.append(diag)

        # Sort by severity (critical first)
        status_order = {
            PositionStatus.CRITICAL: 0,
            PositionStatus.WARNING: 1,
            PositionStatus.ATTENTION: 2,
            PositionStatus.HEALTHY: 3,
        }
        diagnostics.sort(key=lambda x: status_order[x.status])

        # Calculate summary metrics
        return self._build_portfolio_diagnostic(diagnostics)

    def _diagnose_position(
        self,
        pos: PositionData,
        weight: float,
        stop_loss: Optional[float],
        entry_date: Optional[date],
    ) -> PositionDiagnostic:
        """Diagnose a single position."""
        signals = []
        actions = []

        # Basic metrics
        cost_price = float(pos.cost_price) if pos.cost_price else 0
        current_price = float(pos.market_price) if pos.market_price else cost_price
        market_value = self._get_market_value(pos)

        pl_value = float(pos.pl_val) if pos.pl_val else 0
        pl_ratio = float(pos.pl_ratio) if pos.pl_ratio else 0

        # Stop-loss analysis
        stop_status, distance_to_stop = self._analyze_stop_loss(
            current_price, cost_price, stop_loss
        )

        if stop_status == StopLossStatus.TRIGGERED:
            signals.append(f"Stop-loss triggered at {stop_loss:.2f}")
            actions.append("Review position - stop-loss triggered")
        elif stop_status == StopLossStatus.APPROACHING:
            signals.append(f"Approaching stop-loss ({distance_to_stop:.1f}% away)")
            actions.append("Monitor closely - near stop-loss")
        elif stop_status == StopLossStatus.NOT_SET:
            signals.append("No stop-loss defined")
            stop_loss = cost_price * (1 - self.config.default_stop_loss_pct / 100)
            distance_to_stop = ((current_price - stop_loss) / current_price * 100) if current_price > 0 else 0
            actions.append(f"Consider setting stop-loss at {stop_loss:.2f}")

        # Position sizing analysis
        is_oversized = weight > self.config.max_position_weight
        is_undersized = weight < self.config.min_position_weight

        if is_oversized:
            signals.append(f"Oversized position ({weight:.1f}% vs max {self.config.max_position_weight}%)")
            actions.append("Consider trimming position")
            suggested_action = "reduce"
        elif is_undersized:
            signals.append(f"Small position ({weight:.1f}%)")
            suggested_action = "add" if pl_ratio > 0 else "hold"
        else:
            suggested_action = "hold"

        # Holding period
        holding_days = None
        if entry_date:
            holding_days = (date.today() - entry_date).days

        # Average down opportunity
        avg_down_opportunity = pl_ratio < -self.config.avg_down_threshold

        if avg_down_opportunity:
            signals.append(f"Potential avg down opportunity ({pl_ratio:.1f}% below cost)")
            actions.append("Evaluate averaging down if thesis intact")

        # Determine overall status
        status = self._determine_status(pl_ratio, stop_status, is_oversized)

        return PositionDiagnostic(
            market=pos.market,
            code=pos.code,
            name=pos.stock_name or "",
            qty=float(pos.qty),
            cost_price=cost_price,
            current_price=current_price,
            market_value=market_value,
            pl_value=pl_value,
            pl_ratio=pl_ratio,
            status=status,
            weight=weight,
            stop_loss_price=stop_loss,
            stop_loss_status=stop_status,
            distance_to_stop=distance_to_stop,
            is_oversized=is_oversized,
            is_undersized=is_undersized,
            suggested_size_action=suggested_action,
            holding_days=holding_days,
            avg_down_opportunity=avg_down_opportunity,
            signals=signals,
            actions=actions,
        )

    def _analyze_stop_loss(
        self,
        current_price: float,
        cost_price: float,
        stop_loss: Optional[float],
    ) -> tuple[StopLossStatus, float]:
        """Analyze stop-loss status."""
        if stop_loss is None:
            return StopLossStatus.NOT_SET, 0

        if current_price <= 0:
            return StopLossStatus.NOT_SET, 0

        distance_pct = (current_price - stop_loss) / current_price * 100

        if distance_pct <= 0:
            return StopLossStatus.TRIGGERED, distance_pct
        elif distance_pct <= self.config.stop_approaching_threshold:
            return StopLossStatus.APPROACHING, distance_pct
        else:
            return StopLossStatus.SAFE, distance_pct

    def _determine_status(
        self,
        pl_ratio: float,
        stop_status: StopLossStatus,
        is_oversized: bool,
    ) -> PositionStatus:
        """Determine overall position status."""
        # Critical conditions
        if stop_status == StopLossStatus.TRIGGERED:
            return PositionStatus.CRITICAL
        if pl_ratio <= -self.config.critical_loss_pct:
            return PositionStatus.CRITICAL

        # Warning conditions
        if stop_status == StopLossStatus.APPROACHING:
            return PositionStatus.WARNING
        if pl_ratio <= -self.config.warning_loss_pct:
            return PositionStatus.WARNING
        if is_oversized and pl_ratio < 0:
            return PositionStatus.WARNING

        # Attention conditions
        if pl_ratio <= -self.config.attention_loss_pct:
            return PositionStatus.ATTENTION
        if is_oversized:
            return PositionStatus.ATTENTION
        if stop_status == StopLossStatus.NOT_SET:
            return PositionStatus.ATTENTION

        return PositionStatus.HEALTHY

    def _get_market_value(self, pos: PositionData) -> float:
        """Get market value for a position."""
        if pos.market_val:
            return float(pos.market_val)
        if pos.market_price and pos.qty:
            return float(pos.market_price) * float(pos.qty)
        return 0

    def _build_portfolio_diagnostic(
        self, diagnostics: list[PositionDiagnostic]
    ) -> PortfolioDiagnostic:
        """Build portfolio-level diagnostic from position diagnostics."""
        total = len(diagnostics)

        # Count by status
        healthy_count = sum(1 for d in diagnostics if d.status == PositionStatus.HEALTHY)
        attention_count = sum(1 for d in diagnostics if d.status == PositionStatus.ATTENTION)
        warning_count = sum(1 for d in diagnostics if d.status == PositionStatus.WARNING)
        critical_count = sum(1 for d in diagnostics if d.status == PositionStatus.CRITICAL)

        # Stop-loss summary
        without_stop = sum(1 for d in diagnostics if d.stop_loss_status == StopLossStatus.NOT_SET)
        approaching_stop = sum(1 for d in diagnostics if d.stop_loss_status == StopLossStatus.APPROACHING)
        triggered_stop = sum(1 for d in diagnostics if d.stop_loss_status == StopLossStatus.TRIGGERED)

        # Position sizing summary
        oversized = sum(1 for d in diagnostics if d.is_oversized)
        undersized = sum(1 for d in diagnostics if d.is_undersized)

        # Calculate health score
        health_score = self._calculate_health_score(
            healthy_count, attention_count, warning_count, critical_count, total
        )

        # Determine overall status
        if critical_count > 0:
            overall_status = PositionStatus.CRITICAL
        elif warning_count > total * 0.3:
            overall_status = PositionStatus.WARNING
        elif attention_count > total * 0.5:
            overall_status = PositionStatus.ATTENTION
        else:
            overall_status = PositionStatus.HEALTHY

        # Generate summary signals
        summary_signals = []
        priority_actions = []

        if critical_count > 0:
            summary_signals.append(f"{critical_count} position(s) require immediate attention")
            for d in diagnostics:
                if d.status == PositionStatus.CRITICAL:
                    priority_actions.extend(d.actions)

        if without_stop > total * 0.5:
            summary_signals.append(f"{without_stop}/{total} positions without stop-loss")
            priority_actions.append("Set stop-losses for unprotected positions")

        if oversized > 0:
            summary_signals.append(f"{oversized} oversized position(s)")
            priority_actions.append("Review position sizing")

        if triggered_stop > 0:
            summary_signals.append(f"{triggered_stop} position(s) triggered stop-loss")
            priority_actions.append("Review and potentially close triggered positions")

        return PortfolioDiagnostic(
            analysis_date=date.today(),
            total_positions=total,
            healthy_count=healthy_count,
            attention_count=attention_count,
            warning_count=warning_count,
            critical_count=critical_count,
            positions_without_stop=without_stop,
            positions_approaching_stop=approaching_stop,
            positions_triggered_stop=triggered_stop,
            oversized_positions=oversized,
            undersized_positions=undersized,
            health_score=health_score,
            overall_status=overall_status,
            diagnostics=diagnostics,
            summary_signals=summary_signals,
            priority_actions=priority_actions,
        )

    def _calculate_health_score(
        self,
        healthy: int,
        attention: int,
        warning: int,
        critical: int,
        total: int,
    ) -> float:
        """Calculate portfolio health score (0-100)."""
        if total == 0:
            return 100

        # Weighted scoring
        score = (
            healthy * 100 +
            attention * 70 +
            warning * 40 +
            critical * 0
        ) / total

        return round(score, 1)

    def _empty_diagnostic(self) -> PortfolioDiagnostic:
        """Return empty diagnostic for empty portfolio."""
        return PortfolioDiagnostic(
            analysis_date=date.today(),
            total_positions=0,
            healthy_count=0,
            attention_count=0,
            warning_count=0,
            critical_count=0,
            positions_without_stop=0,
            positions_approaching_stop=0,
            positions_triggered_stop=0,
            oversized_positions=0,
            undersized_positions=0,
            health_score=100,
            overall_status=PositionStatus.HEALTHY,
            diagnostics=[],
            summary_signals=["No positions to analyze"],
            priority_actions=[],
        )
