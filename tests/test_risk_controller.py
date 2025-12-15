"""
Tests for Risk Controller Skill components.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from analysis.portfolio import PositionData, RiskLevel
from skills.risk_controller import (
    AlertCategory,
    AlertConfig,
    AlertGenerator,
    AlertSeverity,
    AlertSummary,
    ConcentrationLevel,
    ConcentrationMetrics,
    LeverageMetrics,
    LeverageStatus,
    PortfolioDiagnostic,
    PortfolioRiskMetrics,
    PositionDiagnostic,
    PositionMonitor,
    PositionMonitorConfig,
    PositionSizeRecommendation,
    PositionStatus,
    RiskAlert,
    RiskCalculator,
    RiskCalculatorConfig,
    RiskController,
    RiskControllerResult,
    StopLossMetrics,
    StopLossStatus,
    generate_risk_report,
)
from skills.shared import ReportFormat


# =============================================================================
# Test Data Fixtures
# =============================================================================


def create_sample_positions(count: int = 10) -> list[PositionData]:
    """Create sample positions for testing."""
    positions = []
    base_value = 100000

    for i in range(count):
        market = "HK" if i % 3 == 0 else ("US" if i % 3 == 1 else "A")
        code = f"0000{i}" if market == "HK" else f"STOCK{i}"

        qty = 1000 + i * 100
        cost_price = 50 + i * 5
        market_price = cost_price * (1 + (i - 5) * 0.05)  # Mix of gains and losses

        positions.append(PositionData(
            market=market,
            code=code,
            stock_name=f"Test Stock {i}",
            qty=float(qty),
            cost_price=cost_price,
            market_price=market_price,
            market_val=qty * market_price,
            pl_val=qty * (market_price - cost_price),
            pl_ratio=((market_price - cost_price) / cost_price) * 100,
            position_side="LONG",
        ))

    return positions


def create_concentrated_positions() -> list[PositionData]:
    """Create concentrated portfolio for testing."""
    return [
        PositionData(
            market="HK",
            code="00700",
            stock_name="Tencent",
            qty=1000,
            cost_price=300,
            market_price=380,
            market_val=380000,
            pl_val=80000,
            pl_ratio=26.67,
            position_side="LONG",
        ),
        PositionData(
            market="US",
            code="NVDA",
            stock_name="NVIDIA",
            qty=100,
            cost_price=100,
            market_price=120,
            market_val=12000,
            pl_val=2000,
            pl_ratio=20.0,
            position_side="LONG",
        ),
        PositionData(
            market="US",
            code="AAPL",
            stock_name="Apple",
            qty=50,
            cost_price=180,
            market_price=170,
            market_val=8500,
            pl_val=-500,
            pl_ratio=-5.56,
            position_side="LONG",
        ),
    ]


def create_losing_positions() -> list[PositionData]:
    """Create positions with significant losses."""
    return [
        PositionData(
            market="HK",
            code="00001",
            stock_name="CK Hutchison",
            qty=1000,
            cost_price=50,
            market_price=35,  # -30% loss
            market_val=35000,
            pl_val=-15000,
            pl_ratio=-30.0,
            position_side="LONG",
        ),
        PositionData(
            market="US",
            code="TSLA",
            stock_name="Tesla",
            qty=100,
            cost_price=300,
            market_price=240,  # -20% loss
            market_val=24000,
            pl_val=-6000,
            pl_ratio=-20.0,
            position_side="LONG",
        ),
        PositionData(
            market="HK",
            code="09988",
            stock_name="Alibaba",
            qty=500,
            cost_price=100,
            market_price=85,  # -15% loss
            market_val=42500,
            pl_val=-7500,
            pl_ratio=-15.0,
            position_side="LONG",
        ),
    ]


# =============================================================================
# PositionStatus Enum Tests
# =============================================================================


class TestPositionStatus:
    """Tests for PositionStatus enum."""

    def test_values(self):
        """Test enum values."""
        assert PositionStatus.HEALTHY.value == "healthy"
        assert PositionStatus.ATTENTION.value == "attention"
        assert PositionStatus.WARNING.value == "warning"
        assert PositionStatus.CRITICAL.value == "critical"


class TestStopLossStatus:
    """Tests for StopLossStatus enum."""

    def test_values(self):
        """Test enum values."""
        assert StopLossStatus.SAFE.value == "safe"
        assert StopLossStatus.APPROACHING.value == "approaching"
        assert StopLossStatus.TRIGGERED.value == "triggered"
        assert StopLossStatus.NOT_SET.value == "not_set"


# =============================================================================
# PositionDiagnostic Tests
# =============================================================================


class TestPositionDiagnostic:
    """Tests for PositionDiagnostic dataclass."""

    def test_creation(self):
        """Test creating PositionDiagnostic."""
        diag = PositionDiagnostic(
            market="HK",
            code="00700",
            name="Tencent",
            qty=1000,
            cost_price=300,
            current_price=380,
            market_value=380000,
            pl_value=80000,
            pl_ratio=26.67,
            status=PositionStatus.HEALTHY,
            weight=50.0,
            stop_loss_price=280,
            stop_loss_status=StopLossStatus.SAFE,
            distance_to_stop=26.3,
            is_oversized=True,
            is_undersized=False,
            suggested_size_action="reduce",
            holding_days=30,
            avg_down_opportunity=False,
            signals=["Oversized position"],
            actions=["Consider trimming"],
        )
        assert diag.full_code == "HK.00700"
        assert diag.status == PositionStatus.HEALTHY

    def test_to_dict(self):
        """Test conversion to dictionary."""
        diag = PositionDiagnostic(
            market="US",
            code="AAPL",
            name="Apple",
            qty=100,
            cost_price=180,
            current_price=190,
            market_value=19000,
            pl_value=1000,
            pl_ratio=5.56,
            status=PositionStatus.ATTENTION,
            weight=10.0,
            stop_loss_price=165,
            stop_loss_status=StopLossStatus.SAFE,
            distance_to_stop=13.2,
            is_oversized=False,
            is_undersized=False,
            suggested_size_action="hold",
            holding_days=None,
            avg_down_opportunity=False,
        )
        d = diag.to_dict()
        assert d["code"] == "US.AAPL"
        assert d["status"] == "attention"


# =============================================================================
# PositionMonitor Tests
# =============================================================================


class TestPositionMonitor:
    """Tests for PositionMonitor class."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = PositionMonitor()
        assert monitor.config is not None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = PositionMonitorConfig(
            default_stop_loss_pct=10.0,
            max_position_weight=15.0,
        )
        monitor = PositionMonitor(config=config)
        assert monitor.config.default_stop_loss_pct == 10.0
        assert monitor.config.max_position_weight == 15.0

    def test_diagnose_portfolio(self):
        """Test portfolio diagnosis."""
        positions = create_sample_positions(5)
        monitor = PositionMonitor()

        result = monitor.diagnose_portfolio(positions)

        assert isinstance(result, PortfolioDiagnostic)
        assert result.total_positions == 5
        assert len(result.diagnostics) == 5

    def test_diagnose_empty_portfolio(self):
        """Test diagnosis of empty portfolio."""
        monitor = PositionMonitor()
        result = monitor.diagnose_portfolio([])

        assert result.total_positions == 0
        assert result.health_score == 100
        assert result.overall_status == PositionStatus.HEALTHY

    def test_diagnose_with_stop_losses(self):
        """Test diagnosis with stop-loss prices."""
        positions = create_sample_positions(3)
        stop_losses = {
            f"{positions[0].market}.{positions[0].code}": positions[0].market_price * 0.92,
        }

        monitor = PositionMonitor()
        result = monitor.diagnose_portfolio(positions, stop_losses=stop_losses)

        # First position should have stop-loss set
        diag = result.diagnostics[0]
        # Some position should have stop set
        has_stop = any(d.stop_loss_status != StopLossStatus.NOT_SET for d in result.diagnostics)
        assert has_stop

    def test_diagnose_critical_positions(self):
        """Test detection of critical positions."""
        positions = create_losing_positions()
        monitor = PositionMonitor()

        result = monitor.diagnose_portfolio(positions)

        # Should have critical/warning positions due to large losses
        assert result.critical_count > 0 or result.warning_count > 0


# =============================================================================
# ConcentrationLevel Enum Tests
# =============================================================================


class TestConcentrationLevel:
    """Tests for ConcentrationLevel enum."""

    def test_values(self):
        """Test enum values."""
        assert ConcentrationLevel.WELL_DIVERSIFIED.value == "well_diversified"
        assert ConcentrationLevel.MODERATE.value == "moderate"
        assert ConcentrationLevel.CONCENTRATED.value == "concentrated"
        assert ConcentrationLevel.HIGHLY_CONCENTRATED.value == "highly_concentrated"


class TestLeverageStatus:
    """Tests for LeverageStatus enum."""

    def test_values(self):
        """Test enum values."""
        assert LeverageStatus.NONE.value == "none"
        assert LeverageStatus.LOW.value == "low"
        assert LeverageStatus.MODERATE.value == "moderate"
        assert LeverageStatus.HIGH.value == "high"
        assert LeverageStatus.DANGEROUS.value == "dangerous"


# =============================================================================
# RiskCalculator Tests
# =============================================================================


class TestRiskCalculator:
    """Tests for RiskCalculator class."""

    def test_init(self):
        """Test calculator initialization."""
        calc = RiskCalculator()
        assert calc.config is not None

    def test_init_with_config(self):
        """Test initialization with custom config."""
        config = RiskCalculatorConfig(
            max_single_position_weight=25.0,
            default_risk_per_trade_pct=2.0,
        )
        calc = RiskCalculator(config=config)
        assert calc.config.max_single_position_weight == 25.0

    def test_calculate_risk_metrics(self):
        """Test risk metrics calculation."""
        positions = create_sample_positions(10)
        calc = RiskCalculator()

        result = calc.calculate_risk_metrics(positions)

        assert isinstance(result, PortfolioRiskMetrics)
        assert result.total_portfolio_value > 0
        assert 0 <= result.risk_score <= 100

    def test_calculate_empty_portfolio(self):
        """Test calculation for empty portfolio."""
        calc = RiskCalculator()
        result = calc.calculate_risk_metrics([])

        assert result.total_portfolio_value == 0
        assert result.risk_score == 0
        assert result.risk_level == RiskLevel.LOW

    def test_calculate_concentrated_portfolio(self):
        """Test calculation for concentrated portfolio."""
        positions = create_concentrated_positions()
        calc = RiskCalculator()

        result = calc.calculate_risk_metrics(positions)

        # Should detect high concentration
        assert result.concentration.largest_position_weight > 50
        assert result.concentration.concentration_level in [
            ConcentrationLevel.CONCENTRATED,
            ConcentrationLevel.HIGHLY_CONCENTRATED,
        ]

    def test_calculate_position_size(self):
        """Test position size calculation."""
        calc = RiskCalculator()

        recommendation = calc.calculate_position_size(
            market="HK",
            code="00700",
            current_price=380,
            stop_loss_price=350,
            portfolio_value=1000000,
            risk_budget_pct=1.0,
        )

        assert isinstance(recommendation, PositionSizeRecommendation)
        assert recommendation.max_shares > 0
        assert recommendation.max_value > 0
        assert 0 < recommendation.max_weight <= 20


# =============================================================================
# AlertGenerator Tests
# =============================================================================


class TestAlertSeverity:
    """Tests for AlertSeverity enum."""

    def test_values(self):
        """Test enum values."""
        assert AlertSeverity.INFO.value == "info"
        assert AlertSeverity.WARNING.value == "warning"
        assert AlertSeverity.URGENT.value == "urgent"
        assert AlertSeverity.CRITICAL.value == "critical"


class TestAlertCategory:
    """Tests for AlertCategory enum."""

    def test_values(self):
        """Test enum values."""
        assert AlertCategory.STOP_LOSS.value == "stop_loss"
        assert AlertCategory.CONCENTRATION.value == "concentration"
        assert AlertCategory.LEVERAGE.value == "leverage"
        assert AlertCategory.PNL.value == "pnl"


class TestRiskAlert:
    """Tests for RiskAlert dataclass."""

    def test_creation(self):
        """Test creating RiskAlert."""
        alert = RiskAlert(
            category=AlertCategory.STOP_LOSS,
            severity=AlertSeverity.URGENT,
            title="Stop-Loss Approaching",
            message="2 positions approaching stop-loss",
            affected_positions=["HK.00700", "US.AAPL"],
            recommended_actions=["Monitor closely"],
        )
        assert alert.severity == AlertSeverity.URGENT
        assert len(alert.affected_positions) == 2

    def test_to_dict(self):
        """Test conversion to dictionary."""
        alert = RiskAlert(
            category=AlertCategory.PNL,
            severity=AlertSeverity.WARNING,
            title="Loss Warning",
            message="Test",
        )
        d = alert.to_dict()
        assert d["category"] == "pnl"
        assert d["severity"] == "warning"


class TestAlertGenerator:
    """Tests for AlertGenerator class."""

    def test_init(self):
        """Test generator initialization."""
        gen = AlertGenerator()
        assert gen.config is not None

    def test_generate_alerts_empty(self):
        """Test alert generation with no input."""
        gen = AlertGenerator()
        result = gen.generate_alerts()

        assert isinstance(result, AlertSummary)
        assert result.total_alerts == 0

    def test_generate_alerts_from_diagnostic(self):
        """Test alert generation from diagnostic."""
        positions = create_losing_positions()
        monitor = PositionMonitor()
        diagnostic = monitor.diagnose_portfolio(positions)

        gen = AlertGenerator()
        result = gen.generate_alerts(diagnostic=diagnostic)

        assert result.total_alerts > 0
        # Should have PNL related alerts
        assert result.pnl_alerts or result.stop_loss_alerts

    def test_generate_alerts_from_risk_metrics(self):
        """Test alert generation from risk metrics."""
        positions = create_concentrated_positions()
        calc = RiskCalculator()
        metrics = calc.calculate_risk_metrics(positions)

        gen = AlertGenerator()
        result = gen.generate_alerts(risk_metrics=metrics)

        # Should have concentration alerts
        assert result.concentration_alerts or result.position_alerts


# =============================================================================
# RiskController Tests
# =============================================================================


class TestRiskController:
    """Tests for RiskController class."""

    def test_init(self):
        """Test controller initialization."""
        controller = RiskController()
        assert controller.position_monitor is not None
        assert controller.risk_calculator is not None
        assert controller.alert_generator is not None

    def test_analyze_positions(self):
        """Test analyzing positions directly."""
        positions = create_sample_positions(5)
        controller = RiskController()

        result = controller.analyze_positions(positions)

        assert isinstance(result, RiskControllerResult)
        assert result.portfolio_value > 0
        assert 0 <= result.health_score <= 100
        assert 0 <= result.risk_score <= 100

    def test_analyze_empty_positions(self):
        """Test analyzing empty positions."""
        controller = RiskController()
        result = controller.analyze_positions([])

        assert result.portfolio_value == 0
        assert result.overall_risk_level == RiskLevel.LOW

    def test_analyze_with_critical_issues(self):
        """Test analysis with critical issues."""
        positions = create_losing_positions()
        controller = RiskController()

        result = controller.analyze_positions(positions)

        # Should detect high risk due to losses
        assert result.overall_risk_level in [RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.VERY_HIGH]

    def test_result_to_dict(self):
        """Test result to_dict conversion."""
        positions = create_sample_positions(3)
        controller = RiskController()

        result = controller.analyze_positions(positions)
        d = result.to_dict()

        assert "analysis_date" in d
        assert "portfolio_value" in d
        assert "diagnostic" in d
        assert "risk_metrics" in d
        assert "alerts" in d


# =============================================================================
# Report Generation Tests
# =============================================================================


class TestGenerateRiskReport:
    """Tests for generate_risk_report function."""

    def test_markdown_report(self):
        """Test generating markdown report."""
        positions = create_sample_positions(5)
        controller = RiskController()
        result = controller.analyze_positions(positions)

        report = generate_risk_report(result, ReportFormat.MARKDOWN)

        assert "Portfolio Risk Report" in report
        assert "Risk Summary" in report
        assert "Risk Level" in report

    def test_text_report(self):
        """Test generating text report."""
        positions = create_sample_positions(3)
        controller = RiskController()
        result = controller.analyze_positions(positions)

        report = generate_risk_report(result, ReportFormat.TEXT)

        assert len(report) > 0
        assert "Risk" in report


# =============================================================================
# Integration Tests
# =============================================================================


class TestRiskControllerIntegration:
    """Integration tests for risk controller."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        positions = create_sample_positions(10)
        stop_losses = {
            f"{p.market}.{p.code}": p.market_price * 0.92
            for p in positions[:5]  # Half have stop-losses
        }

        controller = RiskController()
        result = controller.analyze_positions(positions, stop_losses=stop_losses)

        # Verify all components are populated
        assert result.diagnostic is not None
        assert result.risk_metrics is not None
        assert result.alerts is not None

        # Verify diagnostic
        assert result.diagnostic.total_positions == 10

        # Verify risk metrics
        assert result.risk_metrics.concentration is not None
        assert result.risk_metrics.stop_loss is not None
        assert result.risk_metrics.leverage is not None

        # Verify we can generate report
        report = generate_risk_report(result)
        assert len(report) > 100

    def test_diversified_vs_concentrated(self):
        """Test that diversified portfolio scores better than concentrated."""
        diversified = create_sample_positions(20)  # 20 equal positions
        concentrated = create_concentrated_positions()  # 3 positions, one dominant

        controller = RiskController()

        diversified_result = controller.analyze_positions(diversified)
        concentrated_result = controller.analyze_positions(concentrated)

        # Diversified should have higher diversification score
        assert diversified_result.risk_metrics.concentration.diversification_score >= concentrated_result.risk_metrics.concentration.diversification_score

    def test_consistent_results(self):
        """Test that analysis is consistent."""
        positions = create_sample_positions(5)
        controller = RiskController()

        result1 = controller.analyze_positions(positions)
        result2 = controller.analyze_positions(positions)

        assert result1.health_score == result2.health_score
        assert result1.risk_score == result2.risk_score
