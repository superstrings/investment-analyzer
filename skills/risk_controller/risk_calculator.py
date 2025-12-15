"""
Risk Calculator for Risk Controller Skill.

Provides portfolio-level risk calculations:
- Concentration risk (HHI index, position weights)
- Stop-loss management (portfolio-wide stop-loss calculation)
- Leverage and margin analysis
- Risk-adjusted position sizing
"""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional

from analysis.portfolio import PositionData, RiskLevel


class ConcentrationLevel(Enum):
    """Portfolio concentration level."""

    WELL_DIVERSIFIED = "well_diversified"  # HHI < 1000
    MODERATE = "moderate"  # HHI 1000-1800
    CONCENTRATED = "concentrated"  # HHI 1800-2500
    HIGHLY_CONCENTRATED = "highly_concentrated"  # HHI > 2500


class LeverageStatus(Enum):
    """Leverage usage status."""

    NONE = "none"  # No leverage
    LOW = "low"  # < 1.5x
    MODERATE = "moderate"  # 1.5x - 2x
    HIGH = "high"  # > 2x
    DANGEROUS = "dangerous"  # > 3x


@dataclass
class ConcentrationMetrics:
    """Portfolio concentration metrics."""

    # HHI Index (Herfindahl-Hirschman Index)
    hhi_index: float  # 0-10000
    concentration_level: ConcentrationLevel

    # Position concentration
    largest_position_weight: float
    top3_weight: float
    top5_weight: float
    top10_weight: float

    # Market concentration
    market_hhi: float
    markets: list[dict]  # [{market, weight, count}]

    # Diversification score (0-100, higher = more diversified)
    diversification_score: float

    # Recommendations
    signals: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "hhi_index": self.hhi_index,
            "concentration_level": self.concentration_level.value,
            "largest_position_weight": self.largest_position_weight,
            "top3_weight": self.top3_weight,
            "top5_weight": self.top5_weight,
            "top10_weight": self.top10_weight,
            "market_hhi": self.market_hhi,
            "markets": self.markets,
            "diversification_score": self.diversification_score,
            "signals": self.signals,
            "recommendations": self.recommendations,
        }


@dataclass
class StopLossMetrics:
    """Portfolio stop-loss metrics."""

    # Portfolio-level metrics
    portfolio_stop_loss_value: float  # Total value at risk if all stops trigger
    portfolio_stop_loss_pct: float  # Percentage of portfolio at risk
    max_single_loss: float  # Maximum loss from single position
    max_single_loss_code: str

    # Coverage metrics
    positions_with_stop: int
    positions_without_stop: int
    coverage_ratio: float  # Percentage with stop-loss

    # Risk-at-stop
    total_value_at_stop: float  # Portfolio value if all stops trigger
    protected_value: float  # Value protected by stop-losses

    # Signals
    signals: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "portfolio_stop_loss_value": self.portfolio_stop_loss_value,
            "portfolio_stop_loss_pct": self.portfolio_stop_loss_pct,
            "max_single_loss": self.max_single_loss,
            "max_single_loss_code": self.max_single_loss_code,
            "positions_with_stop": self.positions_with_stop,
            "positions_without_stop": self.positions_without_stop,
            "coverage_ratio": self.coverage_ratio,
            "total_value_at_stop": self.total_value_at_stop,
            "protected_value": self.protected_value,
            "signals": self.signals,
            "recommendations": self.recommendations,
        }


@dataclass
class LeverageMetrics:
    """Leverage and margin metrics."""

    # Leverage ratio
    leverage_ratio: float  # Total exposure / equity
    leverage_status: LeverageStatus

    # Margin analysis
    margin_used: float
    margin_available: float
    margin_usage_pct: float  # Margin used as % of available

    # Risk metrics
    maintenance_margin_buffer: float  # Distance to margin call
    estimated_margin_call_drop: float  # % portfolio drop to trigger margin call

    # Signals
    signals: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "leverage_ratio": self.leverage_ratio,
            "leverage_status": self.leverage_status.value,
            "margin_used": self.margin_used,
            "margin_available": self.margin_available,
            "margin_usage_pct": self.margin_usage_pct,
            "maintenance_margin_buffer": self.maintenance_margin_buffer,
            "estimated_margin_call_drop": self.estimated_margin_call_drop,
            "signals": self.signals,
            "recommendations": self.recommendations,
        }


@dataclass
class PositionSizeRecommendation:
    """Recommended position size for a stock."""

    market: str
    code: str
    current_price: float

    # Recommended sizes
    max_shares: int  # Maximum shares based on risk
    max_value: float  # Maximum position value
    max_weight: float  # Maximum weight in portfolio

    # Risk-based sizing
    risk_per_share: float  # Risk per share based on stop-loss
    shares_for_risk_budget: int  # Shares for given risk budget
    value_for_risk_budget: float

    # Rationale
    reasoning: str

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "code": f"{self.market}.{self.code}",
            "current_price": self.current_price,
            "max_shares": self.max_shares,
            "max_value": self.max_value,
            "max_weight": self.max_weight,
            "risk_per_share": self.risk_per_share,
            "shares_for_risk_budget": self.shares_for_risk_budget,
            "value_for_risk_budget": self.value_for_risk_budget,
            "reasoning": self.reasoning,
        }


@dataclass
class PortfolioRiskMetrics:
    """Complete portfolio risk metrics."""

    analysis_date: date
    total_portfolio_value: float

    concentration: ConcentrationMetrics
    stop_loss: StopLossMetrics
    leverage: LeverageMetrics

    # Overall risk score (0-100, higher = more risky)
    risk_score: float
    risk_level: RiskLevel

    # Summary
    summary_signals: list[str] = field(default_factory=list)
    priority_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "total_portfolio_value": self.total_portfolio_value,
            "concentration": self.concentration.to_dict(),
            "stop_loss": self.stop_loss.to_dict(),
            "leverage": self.leverage.to_dict(),
            "risk_score": self.risk_score,
            "risk_level": self.risk_level.value,
            "summary_signals": self.summary_signals,
            "priority_actions": self.priority_actions,
        }


@dataclass
class RiskCalculatorConfig:
    """Configuration for risk calculations."""

    # Concentration thresholds
    moderate_hhi: float = 1000
    concentrated_hhi: float = 1800
    highly_concentrated_hhi: float = 2500

    # Position size limits
    max_single_position_weight: float = 20.0
    max_top3_weight: float = 50.0
    max_top5_weight: float = 70.0

    # Stop-loss defaults
    default_stop_loss_pct: float = 8.0
    max_portfolio_risk_pct: float = 5.0  # Max % of portfolio to risk

    # Leverage thresholds
    low_leverage: float = 1.5
    moderate_leverage: float = 2.0
    high_leverage: float = 3.0

    # Risk budget
    default_risk_per_trade_pct: float = 1.0  # Risk 1% per trade


class RiskCalculator:
    """
    Calculate portfolio-level risk metrics.

    Provides comprehensive risk analysis including:
    - Concentration risk (HHI, position weights)
    - Stop-loss coverage and portfolio risk
    - Leverage and margin analysis
    - Position sizing recommendations
    """

    def __init__(self, config: Optional[RiskCalculatorConfig] = None):
        """
        Initialize risk calculator.

        Args:
            config: Calculator configuration
        """
        self.config = config or RiskCalculatorConfig()

    def calculate_risk_metrics(
        self,
        positions: list[PositionData],
        stop_losses: Optional[dict[str, float]] = None,
        total_equity: Optional[float] = None,
        margin_used: Optional[float] = None,
        margin_available: Optional[float] = None,
    ) -> PortfolioRiskMetrics:
        """
        Calculate complete portfolio risk metrics.

        Args:
            positions: List of position data
            stop_losses: Optional dict of code -> stop-loss price
            total_equity: Account equity (for leverage calculation)
            margin_used: Margin currently used
            margin_available: Margin available

        Returns:
            PortfolioRiskMetrics with complete analysis
        """
        stop_losses = stop_losses or {}

        # Filter active positions
        active = [p for p in positions if p.qty and abs(p.qty) > 0]

        if not active:
            return self._empty_metrics()

        # Calculate position values and weights
        position_values = []
        for p in active:
            mv = self._get_market_value(p)
            position_values.append({
                "market": p.market,
                "code": p.code,
                "value": mv,
                "price": float(p.market_price) if p.market_price else 0,
                "qty": float(p.qty),
            })

        total_value = sum(pv["value"] for pv in position_values)

        # Calculate weights
        for pv in position_values:
            pv["weight"] = (pv["value"] / total_value * 100) if total_value > 0 else 0

        # Sort by weight
        position_values.sort(key=lambda x: x["weight"], reverse=True)

        # Calculate metrics
        concentration = self._calculate_concentration(position_values)
        stop_loss_metrics = self._calculate_stop_loss_metrics(
            position_values, stop_losses, total_value
        )
        leverage_metrics = self._calculate_leverage_metrics(
            total_value, total_equity, margin_used, margin_available
        )

        # Calculate overall risk score
        risk_score = self._calculate_risk_score(
            concentration, stop_loss_metrics, leverage_metrics
        )
        risk_level = self._determine_risk_level(risk_score)

        # Generate summary
        summary_signals = []
        priority_actions = []

        # Concentration warnings
        if concentration.concentration_level in [ConcentrationLevel.CONCENTRATED, ConcentrationLevel.HIGHLY_CONCENTRATED]:
            summary_signals.append(f"Portfolio is {concentration.concentration_level.value.replace('_', ' ')}")
            priority_actions.append("Consider diversifying holdings")

        # Stop-loss warnings
        if stop_loss_metrics.coverage_ratio < 50:
            summary_signals.append(f"Only {stop_loss_metrics.coverage_ratio:.0f}% of positions have stop-losses")
            priority_actions.append("Set stop-losses for unprotected positions")

        if stop_loss_metrics.portfolio_stop_loss_pct > self.config.max_portfolio_risk_pct:
            summary_signals.append(f"Portfolio risk at {stop_loss_metrics.portfolio_stop_loss_pct:.1f}% exceeds {self.config.max_portfolio_risk_pct}% limit")
            priority_actions.append("Review position sizes or tighten stop-losses")

        # Leverage warnings
        if leverage_metrics.leverage_status in [LeverageStatus.HIGH, LeverageStatus.DANGEROUS]:
            summary_signals.append(f"High leverage: {leverage_metrics.leverage_ratio:.2f}x")
            priority_actions.append("Consider reducing leverage")

        return PortfolioRiskMetrics(
            analysis_date=date.today(),
            total_portfolio_value=total_value,
            concentration=concentration,
            stop_loss=stop_loss_metrics,
            leverage=leverage_metrics,
            risk_score=risk_score,
            risk_level=risk_level,
            summary_signals=summary_signals,
            priority_actions=priority_actions,
        )

    def calculate_position_size(
        self,
        market: str,
        code: str,
        current_price: float,
        stop_loss_price: float,
        portfolio_value: float,
        risk_budget_pct: Optional[float] = None,
    ) -> PositionSizeRecommendation:
        """
        Calculate recommended position size based on risk.

        Args:
            market: Stock market
            code: Stock code
            current_price: Current stock price
            stop_loss_price: Stop-loss price
            portfolio_value: Total portfolio value
            risk_budget_pct: Risk budget as % of portfolio (default from config)

        Returns:
            PositionSizeRecommendation
        """
        risk_budget_pct = risk_budget_pct or self.config.default_risk_per_trade_pct

        # Risk per share
        risk_per_share = current_price - stop_loss_price
        if risk_per_share <= 0:
            risk_per_share = current_price * (self.config.default_stop_loss_pct / 100)

        # Risk budget in dollars
        risk_budget = portfolio_value * (risk_budget_pct / 100)

        # Shares for risk budget
        shares_for_risk = int(risk_budget / risk_per_share) if risk_per_share > 0 else 0
        value_for_risk = shares_for_risk * current_price

        # Maximum based on position weight limit
        max_value = portfolio_value * (self.config.max_single_position_weight / 100)
        max_shares = int(max_value / current_price) if current_price > 0 else 0

        # Use the smaller of risk-based and weight-based
        final_shares = min(shares_for_risk, max_shares)
        final_value = final_shares * current_price

        reasoning = (
            f"Risk budget {risk_budget_pct}% = ${risk_budget:.2f}. "
            f"Risk per share ${risk_per_share:.2f} (stop at {stop_loss_price:.2f}). "
            f"Max shares: {final_shares} (${final_value:.2f}, "
            f"{(final_value / portfolio_value * 100):.1f}% of portfolio)"
        )

        return PositionSizeRecommendation(
            market=market,
            code=code,
            current_price=current_price,
            max_shares=final_shares,
            max_value=final_value,
            max_weight=(final_value / portfolio_value * 100) if portfolio_value > 0 else 0,
            risk_per_share=risk_per_share,
            shares_for_risk_budget=shares_for_risk,
            value_for_risk_budget=value_for_risk,
            reasoning=reasoning,
        )

    def _calculate_concentration(
        self, position_values: list[dict]
    ) -> ConcentrationMetrics:
        """Calculate concentration metrics."""
        signals = []
        recommendations = []

        # HHI calculation
        weights = [pv["weight"] / 100 for pv in position_values]  # Convert to decimals
        hhi = sum(w**2 for w in weights) * 10000

        # Determine concentration level
        if hhi < self.config.moderate_hhi:
            level = ConcentrationLevel.WELL_DIVERSIFIED
        elif hhi < self.config.concentrated_hhi:
            level = ConcentrationLevel.MODERATE
        elif hhi < self.config.highly_concentrated_hhi:
            level = ConcentrationLevel.CONCENTRATED
            signals.append(f"Concentrated portfolio (HHI: {hhi:.0f})")
            recommendations.append("Consider adding more positions")
        else:
            level = ConcentrationLevel.HIGHLY_CONCENTRATED
            signals.append(f"Highly concentrated portfolio (HHI: {hhi:.0f})")
            recommendations.append("Diversification strongly recommended")

        # Position concentration
        n = len(position_values)
        largest_weight = position_values[0]["weight"] if n > 0 else 0
        top3_weight = sum(pv["weight"] for pv in position_values[:3])
        top5_weight = sum(pv["weight"] for pv in position_values[:5])
        top10_weight = sum(pv["weight"] for pv in position_values[:10])

        if largest_weight > self.config.max_single_position_weight:
            signals.append(f"Largest position ({largest_weight:.1f}%) exceeds {self.config.max_single_position_weight}% limit")
            recommendations.append(f"Consider trimming {position_values[0]['market']}.{position_values[0]['code']}")

        if top3_weight > self.config.max_top3_weight:
            signals.append(f"Top 3 positions = {top3_weight:.1f}% of portfolio")

        # Market concentration
        market_values: dict[str, float] = {}
        for pv in position_values:
            market = pv["market"]
            market_values[market] = market_values.get(market, 0) + pv["value"]

        total_value = sum(pv["value"] for pv in position_values)
        markets = []
        for market, mv in market_values.items():
            weight = (mv / total_value * 100) if total_value > 0 else 0
            count = sum(1 for pv in position_values if pv["market"] == market)
            markets.append({"market": market, "weight": weight, "count": count})

        markets.sort(key=lambda x: x["weight"], reverse=True)

        # Market HHI
        market_weights = [(mv / total_value) for mv in market_values.values()] if total_value > 0 else []
        market_hhi = sum(w**2 for w in market_weights) * 10000

        # Diversification score (inverse of concentration)
        min_hhi = 10000 / n if n > 0 else 10000
        if hhi > min_hhi:
            diversification_score = max(0, 100 * (1 - (hhi - min_hhi) / (10000 - min_hhi)))
        else:
            diversification_score = 100

        return ConcentrationMetrics(
            hhi_index=hhi,
            concentration_level=level,
            largest_position_weight=largest_weight,
            top3_weight=top3_weight,
            top5_weight=top5_weight,
            top10_weight=top10_weight,
            market_hhi=market_hhi,
            markets=markets,
            diversification_score=diversification_score,
            signals=signals,
            recommendations=recommendations,
        )

    def _calculate_stop_loss_metrics(
        self,
        position_values: list[dict],
        stop_losses: dict[str, float],
        total_value: float,
    ) -> StopLossMetrics:
        """Calculate stop-loss metrics."""
        signals = []
        recommendations = []

        with_stop = 0
        without_stop = 0
        portfolio_loss = 0
        max_single_loss = 0
        max_single_loss_code = ""

        for pv in position_values:
            full_code = f"{pv['market']}.{pv['code']}"
            stop_price = stop_losses.get(full_code)

            if stop_price and pv["price"] > 0:
                with_stop += 1
                loss_pct = (pv["price"] - stop_price) / pv["price"]
                position_loss = pv["value"] * loss_pct
                portfolio_loss += position_loss

                if position_loss > max_single_loss:
                    max_single_loss = position_loss
                    max_single_loss_code = full_code
            else:
                without_stop += 1
                # Assume default stop-loss
                default_loss = pv["value"] * (self.config.default_stop_loss_pct / 100)
                portfolio_loss += default_loss

                if default_loss > max_single_loss:
                    max_single_loss = default_loss
                    max_single_loss_code = full_code

        total_positions = with_stop + without_stop
        coverage_ratio = (with_stop / total_positions * 100) if total_positions > 0 else 0
        portfolio_stop_pct = (portfolio_loss / total_value * 100) if total_value > 0 else 0

        if without_stop > 0:
            signals.append(f"{without_stop} position(s) without defined stop-loss")
            recommendations.append("Define stop-loss for all positions")

        if portfolio_stop_pct > self.config.max_portfolio_risk_pct:
            signals.append(f"Portfolio risk ({portfolio_stop_pct:.1f}%) exceeds limit ({self.config.max_portfolio_risk_pct}%)")
            recommendations.append("Reduce position sizes or tighten stops")

        return StopLossMetrics(
            portfolio_stop_loss_value=portfolio_loss,
            portfolio_stop_loss_pct=portfolio_stop_pct,
            max_single_loss=max_single_loss,
            max_single_loss_code=max_single_loss_code,
            positions_with_stop=with_stop,
            positions_without_stop=without_stop,
            coverage_ratio=coverage_ratio,
            total_value_at_stop=total_value - portfolio_loss,
            protected_value=portfolio_loss if with_stop > 0 else 0,
            signals=signals,
            recommendations=recommendations,
        )

    def _calculate_leverage_metrics(
        self,
        total_value: float,
        total_equity: Optional[float],
        margin_used: Optional[float],
        margin_available: Optional[float],
    ) -> LeverageMetrics:
        """Calculate leverage metrics."""
        signals = []
        recommendations = []

        # Leverage ratio
        equity = total_equity or total_value
        leverage_ratio = total_value / equity if equity > 0 else 1.0

        # Determine leverage status
        if leverage_ratio <= 1.0:
            status = LeverageStatus.NONE
        elif leverage_ratio <= self.config.low_leverage:
            status = LeverageStatus.LOW
        elif leverage_ratio <= self.config.moderate_leverage:
            status = LeverageStatus.MODERATE
            signals.append(f"Moderate leverage: {leverage_ratio:.2f}x")
        elif leverage_ratio <= self.config.high_leverage:
            status = LeverageStatus.HIGH
            signals.append(f"High leverage: {leverage_ratio:.2f}x")
            recommendations.append("Consider reducing leverage")
        else:
            status = LeverageStatus.DANGEROUS
            signals.append(f"Dangerous leverage: {leverage_ratio:.2f}x")
            recommendations.append("Urgently reduce leverage")

        # Margin analysis
        used = margin_used or 0
        available = margin_available or equity
        total_margin = used + available
        usage_pct = (used / total_margin * 100) if total_margin > 0 else 0

        # Maintenance margin buffer (assume 25% maintenance requirement)
        maintenance_req = total_value * 0.25
        buffer = equity - maintenance_req
        buffer_pct = (buffer / equity * 100) if equity > 0 else 100

        # Estimated drop to margin call
        if leverage_ratio > 1 and equity > 0:
            # If portfolio drops by X%, equity drops by X% * leverage_ratio
            # Margin call when equity = maintenance_req
            margin_call_drop = buffer_pct / leverage_ratio
        else:
            margin_call_drop = 100  # No margin call possible

        return LeverageMetrics(
            leverage_ratio=leverage_ratio,
            leverage_status=status,
            margin_used=used,
            margin_available=available,
            margin_usage_pct=usage_pct,
            maintenance_margin_buffer=buffer_pct,
            estimated_margin_call_drop=margin_call_drop,
            signals=signals,
            recommendations=recommendations,
        )

    def _calculate_risk_score(
        self,
        concentration: ConcentrationMetrics,
        stop_loss: StopLossMetrics,
        leverage: LeverageMetrics,
    ) -> float:
        """Calculate overall risk score (0-100)."""
        score = 0

        # Concentration component (0-30 points)
        if concentration.concentration_level == ConcentrationLevel.HIGHLY_CONCENTRATED:
            score += 30
        elif concentration.concentration_level == ConcentrationLevel.CONCENTRATED:
            score += 20
        elif concentration.concentration_level == ConcentrationLevel.MODERATE:
            score += 10

        # Stop-loss component (0-40 points)
        # Higher risk if less coverage
        coverage_risk = (100 - stop_loss.coverage_ratio) * 0.2  # 0-20 points
        score += coverage_risk

        # Risk at stop component
        if stop_loss.portfolio_stop_loss_pct > 10:
            score += 20
        elif stop_loss.portfolio_stop_loss_pct > 5:
            score += 10

        # Leverage component (0-30 points)
        if leverage.leverage_status == LeverageStatus.DANGEROUS:
            score += 30
        elif leverage.leverage_status == LeverageStatus.HIGH:
            score += 20
        elif leverage.leverage_status == LeverageStatus.MODERATE:
            score += 10

        return min(100, score)

    def _determine_risk_level(self, risk_score: float) -> RiskLevel:
        """Determine risk level from score."""
        if risk_score >= 70:
            return RiskLevel.VERY_HIGH
        elif risk_score >= 50:
            return RiskLevel.HIGH
        elif risk_score >= 30:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _get_market_value(self, pos: PositionData) -> float:
        """Get market value for a position."""
        if pos.market_val:
            return float(pos.market_val)
        if pos.market_price and pos.qty:
            return float(pos.market_price) * float(pos.qty)
        return 0

    def _empty_metrics(self) -> PortfolioRiskMetrics:
        """Return empty metrics for empty portfolio."""
        return PortfolioRiskMetrics(
            analysis_date=date.today(),
            total_portfolio_value=0,
            concentration=ConcentrationMetrics(
                hhi_index=0,
                concentration_level=ConcentrationLevel.WELL_DIVERSIFIED,
                largest_position_weight=0,
                top3_weight=0,
                top5_weight=0,
                top10_weight=0,
                market_hhi=0,
                markets=[],
                diversification_score=100,
            ),
            stop_loss=StopLossMetrics(
                portfolio_stop_loss_value=0,
                portfolio_stop_loss_pct=0,
                max_single_loss=0,
                max_single_loss_code="",
                positions_with_stop=0,
                positions_without_stop=0,
                coverage_ratio=0,
                total_value_at_stop=0,
                protected_value=0,
            ),
            leverage=LeverageMetrics(
                leverage_ratio=1.0,
                leverage_status=LeverageStatus.NONE,
                margin_used=0,
                margin_available=0,
                margin_usage_pct=0,
                maintenance_margin_buffer=100,
                estimated_margin_call_drop=100,
            ),
            risk_score=0,
            risk_level=RiskLevel.LOW,
            summary_signals=["No positions to analyze"],
            priority_actions=[],
        )
