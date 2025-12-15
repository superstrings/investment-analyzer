"""
Risk Controller - Main orchestrator for risk analysis.

Combines PositionMonitor, RiskCalculator, and AlertGenerator
to provide comprehensive portfolio risk management.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

from analysis.portfolio import PositionData, RiskLevel
from skills.shared import DataProvider, ReportBuilder, ReportFormat

from .alert_generator import AlertGenerator, AlertSummary
from .position_monitor import PortfolioDiagnostic, PositionMonitor
from .risk_calculator import PortfolioRiskMetrics, RiskCalculator


@dataclass
class RiskControllerResult:
    """Complete risk analysis result."""

    # Analysis metadata
    user_id: int
    analysis_date: date
    portfolio_value: float

    # Component results
    diagnostic: PortfolioDiagnostic
    risk_metrics: PortfolioRiskMetrics
    alerts: AlertSummary

    # Overall assessment
    overall_risk_level: RiskLevel
    health_score: float  # 0-100
    risk_score: float  # 0-100

    # Summary
    summary: str
    priority_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "analysis_date": self.analysis_date.isoformat(),
            "portfolio_value": self.portfolio_value,
            "diagnostic": self.diagnostic.to_dict(),
            "risk_metrics": self.risk_metrics.to_dict(),
            "alerts": self.alerts.to_dict(),
            "overall_risk_level": self.overall_risk_level.value,
            "health_score": self.health_score,
            "risk_score": self.risk_score,
            "summary": self.summary,
            "priority_actions": self.priority_actions,
        }


class RiskController:
    """
    Main risk controller combining all risk analysis components.

    Provides a unified interface for:
    - Position-level diagnostics
    - Portfolio-level risk metrics
    - Risk alert generation
    """

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        position_monitor: Optional[PositionMonitor] = None,
        risk_calculator: Optional[RiskCalculator] = None,
        alert_generator: Optional[AlertGenerator] = None,
    ):
        """
        Initialize risk controller.

        Args:
            data_provider: Data provider for fetching positions
            position_monitor: Position monitor instance
            risk_calculator: Risk calculator instance
            alert_generator: Alert generator instance
        """
        self.data_provider = data_provider or DataProvider()
        self.position_monitor = position_monitor or PositionMonitor()
        self.risk_calculator = risk_calculator or RiskCalculator()
        self.alert_generator = alert_generator or AlertGenerator()

    def analyze_portfolio_risk(
        self,
        user_id: int,
        markets: Optional[list[str]] = None,
        stop_losses: Optional[dict[str, float]] = None,
    ) -> RiskControllerResult:
        """
        Perform complete portfolio risk analysis.

        Args:
            user_id: User ID to analyze
            markets: Optional list of markets to filter
            stop_losses: Optional dict of code -> stop-loss price

        Returns:
            RiskControllerResult with complete analysis
        """
        stop_losses = stop_losses or {}

        # Fetch positions
        positions = self.data_provider.get_positions(user_id, markets)

        if not positions:
            return self._empty_result(user_id)

        # Convert to PositionData
        position_data = [
            PositionData(
                market=p.market,
                code=p.code,
                stock_name=p.stock_name,
                qty=float(p.qty),
                cost_price=float(p.cost_price) if p.cost_price else None,
                market_price=float(p.market_price) if p.market_price else None,
                market_val=float(p.market_val) if p.market_val else None,
                pl_val=float(p.pl_val) if p.pl_val else None,
                pl_ratio=float(p.pl_ratio) if p.pl_ratio else None,
                position_side=p.position_side or "LONG",
            )
            for p in positions
        ]

        # Run position diagnostics
        diagnostic = self.position_monitor.diagnose_portfolio(
            position_data, stop_losses
        )

        # Run risk calculation
        risk_metrics = self.risk_calculator.calculate_risk_metrics(
            position_data, stop_losses
        )

        # Generate alerts
        alerts = self.alert_generator.generate_alerts(
            diagnostic=diagnostic,
            risk_metrics=risk_metrics,
            positions=position_data,
        )

        # Determine overall risk level
        overall_risk = self._determine_overall_risk(
            diagnostic, risk_metrics, alerts
        )

        # Generate summary
        summary = self._generate_summary(
            diagnostic, risk_metrics, alerts, overall_risk
        )

        # Combine priority actions
        priority_actions = list(dict.fromkeys(
            alerts.priority_actions +
            diagnostic.priority_actions +
            risk_metrics.priority_actions
        ))[:5]

        return RiskControllerResult(
            user_id=user_id,
            analysis_date=date.today(),
            portfolio_value=risk_metrics.total_portfolio_value,
            diagnostic=diagnostic,
            risk_metrics=risk_metrics,
            alerts=alerts,
            overall_risk_level=overall_risk,
            health_score=diagnostic.health_score,
            risk_score=risk_metrics.risk_score,
            summary=summary,
            priority_actions=priority_actions,
        )

    def analyze_positions(
        self,
        positions: list[PositionData],
        stop_losses: Optional[dict[str, float]] = None,
    ) -> RiskControllerResult:
        """
        Analyze provided positions directly.

        Args:
            positions: List of position data
            stop_losses: Optional stop-loss prices

        Returns:
            RiskControllerResult
        """
        stop_losses = stop_losses or {}

        # Run analyses
        diagnostic = self.position_monitor.diagnose_portfolio(positions, stop_losses)
        risk_metrics = self.risk_calculator.calculate_risk_metrics(positions, stop_losses)
        alerts = self.alert_generator.generate_alerts(
            diagnostic=diagnostic,
            risk_metrics=risk_metrics,
            positions=positions,
        )

        overall_risk = self._determine_overall_risk(diagnostic, risk_metrics, alerts)
        summary = self._generate_summary(diagnostic, risk_metrics, alerts, overall_risk)

        priority_actions = list(dict.fromkeys(
            alerts.priority_actions +
            diagnostic.priority_actions +
            risk_metrics.priority_actions
        ))[:5]

        return RiskControllerResult(
            user_id=0,
            analysis_date=date.today(),
            portfolio_value=risk_metrics.total_portfolio_value,
            diagnostic=diagnostic,
            risk_metrics=risk_metrics,
            alerts=alerts,
            overall_risk_level=overall_risk,
            health_score=diagnostic.health_score,
            risk_score=risk_metrics.risk_score,
            summary=summary,
            priority_actions=priority_actions,
        )

    def _determine_overall_risk(
        self,
        diagnostic: PortfolioDiagnostic,
        risk_metrics: PortfolioRiskMetrics,
        alerts: AlertSummary,
    ) -> RiskLevel:
        """Determine overall risk level."""
        # Critical alerts = very high risk
        if alerts.critical_count > 0:
            return RiskLevel.VERY_HIGH

        # Multiple urgent alerts or high risk score
        if alerts.urgent_count >= 2 or risk_metrics.risk_score >= 70:
            return RiskLevel.HIGH

        # Some warnings or medium risk score
        if alerts.warning_count >= 3 or risk_metrics.risk_score >= 40:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _generate_summary(
        self,
        diagnostic: PortfolioDiagnostic,
        risk_metrics: PortfolioRiskMetrics,
        alerts: AlertSummary,
        overall_risk: RiskLevel,
    ) -> str:
        """Generate summary text."""
        parts = []

        # Overall status
        risk_desc = {
            RiskLevel.LOW: "Portfolio risk is LOW",
            RiskLevel.MEDIUM: "Portfolio risk is MEDIUM",
            RiskLevel.HIGH: "Portfolio risk is HIGH",
            RiskLevel.VERY_HIGH: "Portfolio risk is VERY HIGH",
        }
        parts.append(risk_desc[overall_risk])

        # Health score
        parts.append(f"Health score: {diagnostic.health_score:.0f}/100")

        # Alert summary
        if alerts.critical_count > 0:
            parts.append(f"{alerts.critical_count} critical alert(s)")
        if alerts.urgent_count > 0:
            parts.append(f"{alerts.urgent_count} urgent alert(s)")

        # Key metrics
        if risk_metrics.concentration.largest_position_weight > 20:
            parts.append(f"Top position: {risk_metrics.concentration.largest_position_weight:.1f}%")

        if diagnostic.positions_without_stop > 0:
            parts.append(f"{diagnostic.positions_without_stop} positions without stop-loss")

        return ". ".join(parts) + "."

    def _empty_result(self, user_id: int) -> RiskControllerResult:
        """Return empty result for empty portfolio."""
        diagnostic = self.position_monitor.diagnose_portfolio([])
        risk_metrics = self.risk_calculator.calculate_risk_metrics([])
        alerts = self.alert_generator.generate_alerts()

        return RiskControllerResult(
            user_id=user_id,
            analysis_date=date.today(),
            portfolio_value=0,
            diagnostic=diagnostic,
            risk_metrics=risk_metrics,
            alerts=alerts,
            overall_risk_level=RiskLevel.LOW,
            health_score=100,
            risk_score=0,
            summary="No positions to analyze.",
            priority_actions=[],
        )


def generate_risk_report(
    result: RiskControllerResult,
    report_format: ReportFormat = ReportFormat.MARKDOWN,
) -> str:
    """
    Generate a formatted risk report.

    Args:
        result: Risk analysis result
        report_format: Output format

    Returns:
        Formatted report string
    """
    builder = ReportBuilder("Portfolio Risk Report", report_format)

    # Summary section
    builder.add_section("Risk Summary", level=2)
    builder.add_key_value("Analysis Date", result.analysis_date.isoformat())
    builder.add_key_value("Portfolio Value", f"${result.portfolio_value:,.2f}")
    builder.add_key_value("Risk Level", result.overall_risk_level.value.upper())
    builder.add_key_value("Health Score", f"{result.health_score:.0f}/100")
    builder.add_key_value("Risk Score", f"{result.risk_score:.0f}/100")
    builder.add_blank_line()
    builder.add_line(f"**{result.summary}**")

    # Priority Actions
    if result.priority_actions:
        builder.add_section("Priority Actions", level=2)
        builder.add_list(result.priority_actions)

    # Alerts
    if result.alerts.total_alerts > 0:
        builder.add_section("Risk Alerts", level=2)
        builder.add_key_value("Critical", str(result.alerts.critical_count))
        builder.add_key_value("Urgent", str(result.alerts.urgent_count))
        builder.add_key_value("Warning", str(result.alerts.warning_count))
        builder.add_blank_line()

        for alert in result.alerts.alerts[:10]:  # Top 10 alerts
            severity_icon = {
                "critical": "[CRITICAL]",
                "urgent": "[URGENT]",
                "warning": "[WARNING]",
                "info": "[INFO]",
            }
            icon = severity_icon.get(alert.severity.value, "")
            builder.add_line(f"{icon} **{alert.title}**")
            builder.add_line(f"  {alert.message}")
            if alert.affected_positions:
                builder.add_line(f"  Affected: {', '.join(alert.affected_positions[:5])}")
            builder.add_blank_line()

    # Concentration Analysis
    conc = result.risk_metrics.concentration
    builder.add_section("Concentration Analysis", level=2)
    conc_data = [
        {"Metric": "HHI Index", "Value": f"{conc.hhi_index:.0f}", "Status": conc.concentration_level.value},
        {"Metric": "Largest Position", "Value": f"{conc.largest_position_weight:.1f}%", "Status": "OK" if conc.largest_position_weight <= 20 else "HIGH"},
        {"Metric": "Top 5 Weight", "Value": f"{conc.top5_weight:.1f}%", "Status": "OK" if conc.top5_weight <= 70 else "HIGH"},
        {"Metric": "Diversification", "Value": f"{conc.diversification_score:.0f}/100", "Status": ""},
    ]
    builder.add_table(conc_data)

    # Stop-Loss Coverage
    sl = result.risk_metrics.stop_loss
    builder.add_section("Stop-Loss Coverage", level=2)
    builder.add_key_value("Coverage", f"{sl.coverage_ratio:.0f}%")
    builder.add_key_value("With Stop", str(sl.positions_with_stop))
    builder.add_key_value("Without Stop", str(sl.positions_without_stop))
    builder.add_key_value("Portfolio Risk", f"{sl.portfolio_stop_loss_pct:.1f}%")

    # Position Summary
    diag = result.diagnostic
    builder.add_section("Position Health", level=2)
    builder.add_key_value("Total Positions", str(diag.total_positions))
    builder.add_key_value("Healthy", str(diag.healthy_count))
    builder.add_key_value("Attention", str(diag.attention_count))
    builder.add_key_value("Warning", str(diag.warning_count))
    builder.add_key_value("Critical", str(diag.critical_count))

    # Critical/Warning positions
    critical_positions = [d for d in diag.diagnostics if d.status.value in ["critical", "warning"]]
    if critical_positions:
        builder.add_section("Positions Requiring Attention", level=2)
        pos_data = [
            {
                "Code": d.full_code,
                "Status": d.status.value.upper(),
                "P&L": f"{d.pl_ratio:+.1f}%",
                "Weight": f"{d.weight:.1f}%",
                "Stop": d.stop_loss_status.value,
            }
            for d in critical_positions[:10]
        ]
        builder.add_table(pos_data)

    return builder.build()
