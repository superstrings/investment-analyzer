"""
Alert Generator for Risk Controller Skill.

Generates risk alerts based on portfolio analysis:
- Stop-loss alerts
- Concentration alerts
- P&L alerts
- Position sizing alerts
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional

from analysis.portfolio import PositionData, RiskLevel

from .position_monitor import PortfolioDiagnostic, PositionStatus
from .risk_calculator import ConcentrationLevel, LeverageStatus, PortfolioRiskMetrics


class AlertSeverity(Enum):
    """Alert severity level."""

    INFO = "info"  # Informational
    WARNING = "warning"  # Requires attention
    URGENT = "urgent"  # Requires prompt action
    CRITICAL = "critical"  # Requires immediate action


class AlertCategory(Enum):
    """Alert category."""

    STOP_LOSS = "stop_loss"
    CONCENTRATION = "concentration"
    LEVERAGE = "leverage"
    POSITION_SIZE = "position_size"
    PNL = "pnl"
    PORTFOLIO = "portfolio"


@dataclass
class RiskAlert:
    """A single risk alert."""

    category: AlertCategory
    severity: AlertSeverity
    title: str
    message: str
    affected_positions: list[str] = field(default_factory=list)
    recommended_actions: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "affected_positions": self.affected_positions,
            "recommended_actions": self.recommended_actions,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AlertSummary:
    """Summary of all risk alerts."""

    analysis_date: date
    total_alerts: int
    critical_count: int
    urgent_count: int
    warning_count: int
    info_count: int

    alerts: list[RiskAlert] = field(default_factory=list)

    # Grouped by category
    stop_loss_alerts: list[RiskAlert] = field(default_factory=list)
    concentration_alerts: list[RiskAlert] = field(default_factory=list)
    leverage_alerts: list[RiskAlert] = field(default_factory=list)
    position_alerts: list[RiskAlert] = field(default_factory=list)
    pnl_alerts: list[RiskAlert] = field(default_factory=list)

    # Top priority actions
    priority_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "total_alerts": self.total_alerts,
            "critical_count": self.critical_count,
            "urgent_count": self.urgent_count,
            "warning_count": self.warning_count,
            "info_count": self.info_count,
            "alerts": [a.to_dict() for a in self.alerts],
            "stop_loss_alerts": [a.to_dict() for a in self.stop_loss_alerts],
            "concentration_alerts": [a.to_dict() for a in self.concentration_alerts],
            "leverage_alerts": [a.to_dict() for a in self.leverage_alerts],
            "position_alerts": [a.to_dict() for a in self.position_alerts],
            "pnl_alerts": [a.to_dict() for a in self.pnl_alerts],
            "priority_actions": self.priority_actions,
        }


@dataclass
class AlertConfig:
    """Configuration for alert generation."""

    # Stop-loss thresholds
    stop_approaching_pct: float = 2.0  # Within 2% of stop
    no_stop_warning: bool = True  # Warn for positions without stop

    # Concentration thresholds
    max_single_position_pct: float = 20.0
    max_top3_pct: float = 50.0
    concentration_hhi_threshold: float = 2500

    # P&L thresholds
    loss_warning_pct: float = 10.0  # Warn at 10% loss
    loss_urgent_pct: float = 20.0  # Urgent at 20% loss
    loss_critical_pct: float = 30.0  # Critical at 30% loss

    # Leverage thresholds
    leverage_warning: float = 1.5
    leverage_urgent: float = 2.0
    leverage_critical: float = 3.0


class AlertGenerator:
    """
    Generate risk alerts from portfolio analysis.

    Combines position diagnostics and risk metrics to produce
    prioritized alerts for the user.
    """

    def __init__(self, config: Optional[AlertConfig] = None):
        """
        Initialize alert generator.

        Args:
            config: Alert configuration
        """
        self.config = config or AlertConfig()

    def generate_alerts(
        self,
        diagnostic: Optional[PortfolioDiagnostic] = None,
        risk_metrics: Optional[PortfolioRiskMetrics] = None,
        positions: Optional[list[PositionData]] = None,
    ) -> AlertSummary:
        """
        Generate alerts from analysis results.

        Args:
            diagnostic: Portfolio diagnostic from PositionMonitor
            risk_metrics: Risk metrics from RiskCalculator
            positions: Raw position data (for additional P&L alerts)

        Returns:
            AlertSummary with all generated alerts
        """
        alerts = []

        # Generate alerts from each source
        if diagnostic:
            alerts.extend(self._alerts_from_diagnostic(diagnostic))

        if risk_metrics:
            alerts.extend(self._alerts_from_risk_metrics(risk_metrics))

        if positions:
            alerts.extend(self._alerts_from_positions(positions))

        # Deduplicate alerts by title
        seen_titles = set()
        unique_alerts = []
        for alert in alerts:
            if alert.title not in seen_titles:
                seen_titles.add(alert.title)
                unique_alerts.append(alert)

        # Sort by severity
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.URGENT: 1,
            AlertSeverity.WARNING: 2,
            AlertSeverity.INFO: 3,
        }
        unique_alerts.sort(key=lambda x: severity_order[x.severity])

        # Build summary
        return self._build_summary(unique_alerts)

    def _alerts_from_diagnostic(
        self, diagnostic: PortfolioDiagnostic
    ) -> list[RiskAlert]:
        """Generate alerts from position diagnostic."""
        alerts = []

        # Critical positions
        critical = [d for d in diagnostic.diagnostics if d.status == PositionStatus.CRITICAL]
        if critical:
            affected = [d.full_code for d in critical]
            alerts.append(RiskAlert(
                category=AlertCategory.PORTFOLIO,
                severity=AlertSeverity.CRITICAL,
                title=f"{len(critical)} Critical Position(s)",
                message=f"{len(critical)} position(s) require immediate attention",
                affected_positions=affected,
                recommended_actions=[
                    "Review critical positions immediately",
                    "Consider closing or reducing positions",
                ],
            ))

        # Stop-loss triggered
        triggered = [d for d in diagnostic.diagnostics if d.stop_loss_status.value == "triggered"]
        if triggered:
            affected = [d.full_code for d in triggered]
            alerts.append(RiskAlert(
                category=AlertCategory.STOP_LOSS,
                severity=AlertSeverity.CRITICAL,
                title="Stop-Loss Triggered",
                message=f"{len(triggered)} position(s) have triggered stop-loss",
                affected_positions=affected,
                recommended_actions=[
                    "Review and close positions",
                    "Document reasons for holding past stop",
                ],
            ))

        # Stop-loss approaching
        approaching = [d for d in diagnostic.diagnostics if d.stop_loss_status.value == "approaching"]
        if approaching:
            affected = [d.full_code for d in approaching]
            alerts.append(RiskAlert(
                category=AlertCategory.STOP_LOSS,
                severity=AlertSeverity.URGENT,
                title="Approaching Stop-Loss",
                message=f"{len(approaching)} position(s) approaching stop-loss level",
                affected_positions=affected,
                recommended_actions=[
                    "Monitor positions closely",
                    "Prepare exit strategy",
                ],
            ))

        # No stop-loss
        if self.config.no_stop_warning and diagnostic.positions_without_stop > 0:
            without_stop = [d for d in diagnostic.diagnostics if d.stop_loss_status.value == "not_set"]
            affected = [d.full_code for d in without_stop]
            alerts.append(RiskAlert(
                category=AlertCategory.STOP_LOSS,
                severity=AlertSeverity.WARNING,
                title="Missing Stop-Loss",
                message=f"{diagnostic.positions_without_stop} position(s) without defined stop-loss",
                affected_positions=affected,
                recommended_actions=[
                    "Set stop-loss for all positions",
                    "Use 8% default if unsure",
                ],
            ))

        # Oversized positions
        oversized = [d for d in diagnostic.diagnostics if d.is_oversized]
        if oversized:
            affected = [d.full_code for d in oversized]
            alerts.append(RiskAlert(
                category=AlertCategory.POSITION_SIZE,
                severity=AlertSeverity.WARNING,
                title="Oversized Positions",
                message=f"{len(oversized)} position(s) exceed maximum position size",
                affected_positions=affected,
                recommended_actions=[
                    "Consider trimming positions",
                    f"Target max {self.config.max_single_position_pct}% per position",
                ],
            ))

        return alerts

    def _alerts_from_risk_metrics(
        self, metrics: PortfolioRiskMetrics
    ) -> list[RiskAlert]:
        """Generate alerts from risk metrics."""
        alerts = []

        # Concentration alerts
        conc = metrics.concentration
        if conc.concentration_level == ConcentrationLevel.HIGHLY_CONCENTRATED:
            alerts.append(RiskAlert(
                category=AlertCategory.CONCENTRATION,
                severity=AlertSeverity.URGENT,
                title="Highly Concentrated Portfolio",
                message=f"HHI Index: {conc.hhi_index:.0f}. Top position: {conc.largest_position_weight:.1f}%",
                recommended_actions=[
                    "Add more positions to diversify",
                    "Reduce largest positions",
                ],
            ))
        elif conc.concentration_level == ConcentrationLevel.CONCENTRATED:
            alerts.append(RiskAlert(
                category=AlertCategory.CONCENTRATION,
                severity=AlertSeverity.WARNING,
                title="Concentrated Portfolio",
                message=f"HHI Index: {conc.hhi_index:.0f}. Consider diversifying.",
                recommended_actions=[
                    "Consider adding positions",
                ],
            ))

        if conc.largest_position_weight > self.config.max_single_position_pct:
            alerts.append(RiskAlert(
                category=AlertCategory.POSITION_SIZE,
                severity=AlertSeverity.WARNING,
                title="Single Position Too Large",
                message=f"Largest position is {conc.largest_position_weight:.1f}% of portfolio",
                recommended_actions=[
                    f"Reduce to below {self.config.max_single_position_pct}%",
                ],
            ))

        # Leverage alerts
        lev = metrics.leverage
        if lev.leverage_status == LeverageStatus.DANGEROUS:
            alerts.append(RiskAlert(
                category=AlertCategory.LEVERAGE,
                severity=AlertSeverity.CRITICAL,
                title="Dangerous Leverage Level",
                message=f"Leverage ratio: {lev.leverage_ratio:.2f}x. Immediate action required.",
                recommended_actions=[
                    "Reduce positions immediately",
                    "Increase cash/equity",
                ],
            ))
        elif lev.leverage_status == LeverageStatus.HIGH:
            alerts.append(RiskAlert(
                category=AlertCategory.LEVERAGE,
                severity=AlertSeverity.URGENT,
                title="High Leverage",
                message=f"Leverage ratio: {lev.leverage_ratio:.2f}x",
                recommended_actions=[
                    "Consider reducing leverage",
                    "Monitor margin requirements",
                ],
            ))
        elif lev.leverage_status == LeverageStatus.MODERATE:
            alerts.append(RiskAlert(
                category=AlertCategory.LEVERAGE,
                severity=AlertSeverity.WARNING,
                title="Moderate Leverage",
                message=f"Leverage ratio: {lev.leverage_ratio:.2f}x",
                recommended_actions=[
                    "Monitor positions",
                ],
            ))

        # Stop-loss coverage alerts
        sl = metrics.stop_loss
        if sl.coverage_ratio < 50:
            alerts.append(RiskAlert(
                category=AlertCategory.STOP_LOSS,
                severity=AlertSeverity.WARNING,
                title="Low Stop-Loss Coverage",
                message=f"Only {sl.coverage_ratio:.0f}% of positions have stop-loss defined",
                recommended_actions=[
                    "Set stop-loss for remaining positions",
                ],
            ))

        if sl.portfolio_stop_loss_pct > 10:
            alerts.append(RiskAlert(
                category=AlertCategory.STOP_LOSS,
                severity=AlertSeverity.URGENT,
                title="High Portfolio Risk",
                message=f"Portfolio at {sl.portfolio_stop_loss_pct:.1f}% risk if all stops trigger",
                recommended_actions=[
                    "Reduce position sizes",
                    "Tighten stop-losses",
                ],
            ))

        return alerts

    def _alerts_from_positions(
        self, positions: list[PositionData]
    ) -> list[RiskAlert]:
        """Generate P&L alerts from positions."""
        alerts = []

        critical_losses = []
        urgent_losses = []
        warning_losses = []

        for pos in positions:
            if not pos.pl_ratio:
                continue

            pl = float(pos.pl_ratio)
            full_code = f"{pos.market}.{pos.code}"

            if pl <= -self.config.loss_critical_pct:
                critical_losses.append(full_code)
            elif pl <= -self.config.loss_urgent_pct:
                urgent_losses.append(full_code)
            elif pl <= -self.config.loss_warning_pct:
                warning_losses.append(full_code)

        if critical_losses:
            alerts.append(RiskAlert(
                category=AlertCategory.PNL,
                severity=AlertSeverity.CRITICAL,
                title=f"Critical Loss: {len(critical_losses)} Position(s)",
                message=f"Positions with >30% loss",
                affected_positions=critical_losses,
                recommended_actions=[
                    "Review investment thesis",
                    "Consider cutting losses",
                ],
            ))

        if urgent_losses:
            alerts.append(RiskAlert(
                category=AlertCategory.PNL,
                severity=AlertSeverity.URGENT,
                title=f"Significant Loss: {len(urgent_losses)} Position(s)",
                message=f"Positions with >20% loss",
                affected_positions=urgent_losses,
                recommended_actions=[
                    "Evaluate if thesis still valid",
                    "Set tighter stop-loss",
                ],
            ))

        if warning_losses:
            alerts.append(RiskAlert(
                category=AlertCategory.PNL,
                severity=AlertSeverity.WARNING,
                title=f"Moderate Loss: {len(warning_losses)} Position(s)",
                message=f"Positions with >10% loss",
                affected_positions=warning_losses,
                recommended_actions=[
                    "Monitor positions",
                ],
            ))

        return alerts

    def _build_summary(self, alerts: list[RiskAlert]) -> AlertSummary:
        """Build alert summary from alert list."""
        critical_count = sum(1 for a in alerts if a.severity == AlertSeverity.CRITICAL)
        urgent_count = sum(1 for a in alerts if a.severity == AlertSeverity.URGENT)
        warning_count = sum(1 for a in alerts if a.severity == AlertSeverity.WARNING)
        info_count = sum(1 for a in alerts if a.severity == AlertSeverity.INFO)

        # Group by category
        stop_loss = [a for a in alerts if a.category == AlertCategory.STOP_LOSS]
        concentration = [a for a in alerts if a.category == AlertCategory.CONCENTRATION]
        leverage = [a for a in alerts if a.category == AlertCategory.LEVERAGE]
        position = [a for a in alerts if a.category == AlertCategory.POSITION_SIZE]
        pnl = [a for a in alerts if a.category == AlertCategory.PNL]

        # Top priority actions (from critical and urgent alerts)
        priority_actions = []
        for alert in alerts:
            if alert.severity in [AlertSeverity.CRITICAL, AlertSeverity.URGENT]:
                priority_actions.extend(alert.recommended_actions)

        # Deduplicate and limit
        priority_actions = list(dict.fromkeys(priority_actions))[:5]

        return AlertSummary(
            analysis_date=date.today(),
            total_alerts=len(alerts),
            critical_count=critical_count,
            urgent_count=urgent_count,
            warning_count=warning_count,
            info_count=info_count,
            alerts=alerts,
            stop_loss_alerts=stop_loss,
            concentration_alerts=concentration,
            leverage_alerts=leverage,
            position_alerts=position,
            pnl_alerts=pnl,
            priority_actions=priority_actions,
        )
