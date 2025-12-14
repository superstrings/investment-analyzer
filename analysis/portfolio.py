"""
Portfolio analysis module for Investment Analyzer.

Provides comprehensive portfolio analysis including:
- Position analysis (weights, concentration, sector allocation)
- P&L analysis (profit/loss calculations, performance metrics)
- Risk assessment (volatility, drawdown, VaR)
- Account summary (total assets, cash position, margin usage)

Usage:
    from analysis.portfolio import PortfolioAnalyzer, analyze_portfolio

    # Using the analyzer class
    analyzer = PortfolioAnalyzer()
    result = analyzer.analyze(positions, account_snapshot)

    # Using convenience function
    result = analyze_portfolio(positions)
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class PositionMetrics:
    """Metrics for a single position."""

    code: str
    market: str
    name: Optional[str]
    qty: float
    cost_price: Optional[float]
    market_price: Optional[float]
    market_value: float
    cost_value: Optional[float]
    pl_value: Optional[float]  # Profit/Loss value
    pl_ratio: Optional[float]  # Profit/Loss ratio (percentage)
    weight: float  # Weight in portfolio (percentage)
    position_side: str  # LONG/SHORT

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
            "market_price": self.market_price,
            "market_value": self.market_value,
            "cost_value": self.cost_value,
            "pl_value": self.pl_value,
            "pl_ratio": self.pl_ratio,
            "weight": self.weight,
            "position_side": self.position_side,
        }


@dataclass
class PortfolioSummary:
    """Summary of portfolio metrics."""

    total_market_value: float = 0.0
    total_cost_value: float = 0.0
    total_pl_value: float = 0.0
    total_pl_ratio: float = 0.0
    position_count: int = 0
    long_count: int = 0
    short_count: int = 0
    profitable_count: int = 0
    losing_count: int = 0
    win_rate: float = 0.0  # Percentage of profitable positions
    largest_position_weight: float = 0.0
    top5_concentration: float = 0.0  # Total weight of top 5 positions
    avg_position_size: float = 0.0
    cash_balance: Optional[float] = None
    total_assets: Optional[float] = None
    cash_weight: Optional[float] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_market_value": self.total_market_value,
            "total_cost_value": self.total_cost_value,
            "total_pl_value": self.total_pl_value,
            "total_pl_ratio": self.total_pl_ratio,
            "position_count": self.position_count,
            "long_count": self.long_count,
            "short_count": self.short_count,
            "profitable_count": self.profitable_count,
            "losing_count": self.losing_count,
            "win_rate": self.win_rate,
            "largest_position_weight": self.largest_position_weight,
            "top5_concentration": self.top5_concentration,
            "avg_position_size": self.avg_position_size,
            "cash_balance": self.cash_balance,
            "total_assets": self.total_assets,
            "cash_weight": self.cash_weight,
        }


@dataclass
class MarketAllocation:
    """Market allocation breakdown."""

    market: str
    position_count: int
    market_value: float
    weight: float
    pl_value: float
    pl_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "market": self.market,
            "position_count": self.position_count,
            "market_value": self.market_value,
            "weight": self.weight,
            "pl_value": self.pl_value,
            "pl_ratio": self.pl_ratio,
        }


@dataclass
class RiskMetrics:
    """Portfolio risk metrics."""

    concentration_risk: RiskLevel = RiskLevel.LOW
    diversification_score: float = 0.0  # 0-100, higher is more diversified
    largest_loss_position: Optional[str] = None
    largest_loss_ratio: float = 0.0
    total_unrealized_loss: float = 0.0
    positions_at_loss_ratio: float = 0.0  # Percentage of positions at loss
    hhi_index: float = 0.0  # Herfindahl-Hirschman Index for concentration
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "concentration_risk": self.concentration_risk.value,
            "diversification_score": self.diversification_score,
            "largest_loss_position": self.largest_loss_position,
            "largest_loss_ratio": self.largest_loss_ratio,
            "total_unrealized_loss": self.total_unrealized_loss,
            "positions_at_loss_ratio": self.positions_at_loss_ratio,
            "hhi_index": self.hhi_index,
            "signals": self.signals,
        }


@dataclass
class PortfolioAnalysisResult:
    """Complete portfolio analysis result."""

    analysis_date: date
    summary: PortfolioSummary
    positions: list[PositionMetrics]
    market_allocation: list[MarketAllocation]
    risk_metrics: RiskMetrics
    top_performers: list[PositionMetrics] = field(default_factory=list)
    bottom_performers: list[PositionMetrics] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "analysis_date": self.analysis_date.isoformat(),
            "summary": self.summary.to_dict(),
            "positions": [p.to_dict() for p in self.positions],
            "market_allocation": [m.to_dict() for m in self.market_allocation],
            "risk_metrics": self.risk_metrics.to_dict(),
            "top_performers": [p.to_dict() for p in self.top_performers],
            "bottom_performers": [p.to_dict() for p in self.bottom_performers],
            "signals": self.signals,
        }


@dataclass
class PositionData:
    """Input position data structure."""

    market: str
    code: str
    stock_name: Optional[str] = None
    qty: float = 0.0
    cost_price: Optional[float] = None
    market_price: Optional[float] = None
    market_val: Optional[float] = None
    pl_val: Optional[float] = None
    pl_ratio: Optional[float] = None
    position_side: str = "LONG"


@dataclass
class AccountData:
    """Input account data structure."""

    total_assets: Optional[float] = None
    cash: Optional[float] = None
    market_val: Optional[float] = None
    buying_power: Optional[float] = None
    currency: str = "HKD"


class PortfolioAnalyzer:
    """
    Portfolio analyzer for investment analysis.

    Analyzes portfolio positions to provide metrics on:
    - Position weights and concentration
    - Profit/loss performance
    - Market allocation
    - Risk assessment

    Usage:
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze(positions, account_data)

        print(f"Total P&L: {result.summary.total_pl_value}")
        print(f"Win Rate: {result.summary.win_rate}%")
    """

    def __init__(
        self,
        top_n_performers: int = 5,
        concentration_threshold: float = 20.0,
        high_concentration_threshold: float = 30.0,
    ):
        """
        Initialize portfolio analyzer.

        Args:
            top_n_performers: Number of top/bottom performers to track
            concentration_threshold: Position weight threshold for concentration warning (%)
            high_concentration_threshold: High concentration threshold (%)
        """
        self.top_n_performers = top_n_performers
        self.concentration_threshold = concentration_threshold
        self.high_concentration_threshold = high_concentration_threshold

    def analyze(
        self,
        positions: list[PositionData],
        account: Optional[AccountData] = None,
        analysis_date: Optional[date] = None,
    ) -> PortfolioAnalysisResult:
        """
        Analyze portfolio positions.

        Args:
            positions: List of position data
            account: Optional account data for cash/assets info
            analysis_date: Date of analysis (defaults to today)

        Returns:
            PortfolioAnalysisResult with complete analysis
        """
        analysis_date = analysis_date or date.today()

        # Filter positions with non-zero quantity
        active_positions = [p for p in positions if p.qty and abs(p.qty) > 0]

        if not active_positions:
            return self._empty_result(analysis_date, account)

        # Calculate position metrics
        position_metrics = self._calculate_position_metrics(active_positions)

        # Calculate summary
        summary = self._calculate_summary(position_metrics, account)

        # Calculate market allocation
        market_allocation = self._calculate_market_allocation(position_metrics)

        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(position_metrics, summary)

        # Get top/bottom performers
        sorted_by_pl = sorted(
            [p for p in position_metrics if p.pl_ratio is not None],
            key=lambda x: x.pl_ratio or 0,
            reverse=True,
        )
        top_performers = sorted_by_pl[: self.top_n_performers]
        bottom_performers = sorted_by_pl[-self.top_n_performers :][::-1]

        # Generate signals
        signals = self._generate_signals(summary, risk_metrics, position_metrics)

        return PortfolioAnalysisResult(
            analysis_date=analysis_date,
            summary=summary,
            positions=position_metrics,
            market_allocation=market_allocation,
            risk_metrics=risk_metrics,
            top_performers=top_performers,
            bottom_performers=bottom_performers,
            signals=signals,
        )

    def _empty_result(
        self, analysis_date: date, account: Optional[AccountData]
    ) -> PortfolioAnalysisResult:
        """Create empty result when no positions."""
        summary = PortfolioSummary()
        if account:
            summary.cash_balance = account.cash
            summary.total_assets = account.total_assets
            if account.total_assets and account.total_assets > 0:
                summary.cash_weight = (
                    (account.cash / account.total_assets * 100) if account.cash else 0
                )

        return PortfolioAnalysisResult(
            analysis_date=analysis_date,
            summary=summary,
            positions=[],
            market_allocation=[],
            risk_metrics=RiskMetrics(signals=["No active positions"]),
            signals=["No active positions in portfolio"],
        )

    def _calculate_position_metrics(
        self, positions: list[PositionData]
    ) -> list[PositionMetrics]:
        """Calculate metrics for each position."""
        # Calculate total market value first
        total_mv = sum(self._get_market_value(p) for p in positions)

        metrics = []
        for p in positions:
            mv = self._get_market_value(p)
            cost_val = self._get_cost_value(p)

            # Calculate P&L
            pl_val = p.pl_val
            pl_ratio = p.pl_ratio
            if pl_val is None and cost_val and mv:
                pl_val = mv - cost_val
            if pl_ratio is None and cost_val and cost_val != 0:
                pl_ratio = (pl_val / cost_val * 100) if pl_val else 0

            # Calculate weight
            weight = (mv / total_mv * 100) if total_mv > 0 else 0

            metrics.append(
                PositionMetrics(
                    code=p.code,
                    market=p.market,
                    name=p.stock_name,
                    qty=p.qty,
                    cost_price=p.cost_price,
                    market_price=p.market_price,
                    market_value=mv,
                    cost_value=cost_val,
                    pl_value=pl_val,
                    pl_ratio=pl_ratio,
                    weight=weight,
                    position_side=p.position_side,
                )
            )

        return metrics

    def _get_market_value(self, p: PositionData) -> float:
        """Get market value for a position."""
        if p.market_val is not None:
            return float(p.market_val)
        if p.market_price and p.qty:
            return float(p.market_price) * float(p.qty)
        return 0.0

    def _get_cost_value(self, p: PositionData) -> Optional[float]:
        """Get cost value for a position."""
        if p.cost_price and p.qty:
            return float(p.cost_price) * float(p.qty)
        return None

    def _calculate_summary(
        self,
        positions: list[PositionMetrics],
        account: Optional[AccountData],
    ) -> PortfolioSummary:
        """Calculate portfolio summary."""
        summary = PortfolioSummary()

        # Basic counts
        summary.position_count = len(positions)
        summary.long_count = sum(1 for p in positions if p.position_side == "LONG")
        summary.short_count = sum(1 for p in positions if p.position_side == "SHORT")

        # P&L counts
        summary.profitable_count = sum(
            1 for p in positions if p.pl_value is not None and p.pl_value > 0
        )
        summary.losing_count = sum(
            1 for p in positions if p.pl_value is not None and p.pl_value < 0
        )

        # Win rate
        positions_with_pl = sum(1 for p in positions if p.pl_value is not None)
        if positions_with_pl > 0:
            summary.win_rate = summary.profitable_count / positions_with_pl * 100

        # Total values
        summary.total_market_value = sum(p.market_value for p in positions)
        summary.total_cost_value = sum(
            p.cost_value for p in positions if p.cost_value is not None
        )
        summary.total_pl_value = sum(
            p.pl_value for p in positions if p.pl_value is not None
        )

        # Total P&L ratio
        if summary.total_cost_value > 0:
            summary.total_pl_ratio = (
                summary.total_pl_value / summary.total_cost_value * 100
            )

        # Concentration metrics
        sorted_by_weight = sorted(positions, key=lambda x: x.weight, reverse=True)
        if sorted_by_weight:
            summary.largest_position_weight = sorted_by_weight[0].weight
            summary.top5_concentration = sum(
                p.weight for p in sorted_by_weight[: min(5, len(sorted_by_weight))]
            )

        # Average position size
        if summary.position_count > 0:
            summary.avg_position_size = (
                summary.total_market_value / summary.position_count
            )

        # Account info
        if account:
            summary.cash_balance = account.cash
            summary.total_assets = account.total_assets

            if account.total_assets and account.total_assets > 0:
                summary.cash_weight = (
                    (account.cash / account.total_assets * 100) if account.cash else 0
                )

        return summary

    def _calculate_market_allocation(
        self, positions: list[PositionMetrics]
    ) -> list[MarketAllocation]:
        """Calculate market allocation breakdown."""
        total_mv = sum(p.market_value for p in positions)

        market_groups: dict[str, list[PositionMetrics]] = {}
        for p in positions:
            if p.market not in market_groups:
                market_groups[p.market] = []
            market_groups[p.market].append(p)

        allocations = []
        for market, group in market_groups.items():
            mv = sum(p.market_value for p in group)
            pl = sum(p.pl_value for p in group if p.pl_value is not None)
            cost = sum(p.cost_value for p in group if p.cost_value is not None)

            allocations.append(
                MarketAllocation(
                    market=market,
                    position_count=len(group),
                    market_value=mv,
                    weight=(mv / total_mv * 100) if total_mv > 0 else 0,
                    pl_value=pl,
                    pl_ratio=(pl / cost * 100) if cost and cost > 0 else 0,
                )
            )

        # Sort by market value descending
        allocations.sort(key=lambda x: x.market_value, reverse=True)
        return allocations

    def _calculate_risk_metrics(
        self,
        positions: list[PositionMetrics],
        summary: PortfolioSummary,
    ) -> RiskMetrics:
        """Calculate risk metrics."""
        risk = RiskMetrics()

        # HHI Index (concentration measure)
        weights = [p.weight / 100 for p in positions]  # Convert to decimals
        risk.hhi_index = sum(w**2 for w in weights) * 10000  # Scale to 0-10000

        # Diversification score (inverse of HHI, normalized to 0-100)
        # Lower HHI = better diversification
        # Perfectly diversified: HHI = 10000/n where n is number of positions
        min_hhi = 10000 / len(positions) if positions else 10000
        if risk.hhi_index > min_hhi:
            risk.diversification_score = max(
                0, 100 * (1 - (risk.hhi_index - min_hhi) / (10000 - min_hhi))
            )
        else:
            risk.diversification_score = 100

        # Concentration risk level
        if summary.largest_position_weight > self.high_concentration_threshold:
            risk.concentration_risk = RiskLevel.VERY_HIGH
        elif summary.largest_position_weight > self.concentration_threshold:
            risk.concentration_risk = RiskLevel.HIGH
        elif summary.top5_concentration > 80:
            risk.concentration_risk = RiskLevel.MEDIUM
        else:
            risk.concentration_risk = RiskLevel.LOW

        # Largest loss position
        losing_positions = [p for p in positions if p.pl_ratio and p.pl_ratio < 0]
        if losing_positions:
            worst = min(losing_positions, key=lambda x: x.pl_ratio or 0)
            risk.largest_loss_position = worst.full_code
            risk.largest_loss_ratio = worst.pl_ratio or 0

        # Total unrealized loss
        risk.total_unrealized_loss = sum(
            p.pl_value for p in positions if p.pl_value and p.pl_value < 0
        )

        # Positions at loss ratio
        if positions:
            risk.positions_at_loss_ratio = len(losing_positions) / len(positions) * 100

        # Add risk signals
        if risk.concentration_risk in [RiskLevel.HIGH, RiskLevel.VERY_HIGH]:
            risk.signals.append(
                f"High concentration risk: largest position is {summary.largest_position_weight:.1f}%"
            )

        if risk.hhi_index > 2500:
            risk.signals.append(
                f"Portfolio is highly concentrated (HHI: {risk.hhi_index:.0f})"
            )

        if risk.positions_at_loss_ratio > 50:
            risk.signals.append(
                f"{risk.positions_at_loss_ratio:.0f}% of positions are at loss"
            )

        if risk.largest_loss_ratio < -20:
            risk.signals.append(
                f"Large loss position: {risk.largest_loss_position} "
                f"({risk.largest_loss_ratio:.1f}%)"
            )

        return risk

    def _generate_signals(
        self,
        summary: PortfolioSummary,
        risk: RiskMetrics,
        positions: list[PositionMetrics],
    ) -> list[str]:
        """Generate analysis signals."""
        signals = []

        # Performance signals
        if summary.total_pl_ratio > 20:
            signals.append(
                f"Strong performance: {summary.total_pl_ratio:.1f}% total gain"
            )
        elif summary.total_pl_ratio < -10:
            signals.append(f"Underperforming: {summary.total_pl_ratio:.1f}% total loss")

        # Win rate signals
        if summary.win_rate >= 70:
            signals.append(
                f"High win rate: {summary.win_rate:.0f}% profitable positions"
            )
        elif summary.win_rate <= 30:
            signals.append(
                f"Low win rate: {summary.win_rate:.0f}% profitable positions"
            )

        # Diversification signals
        if summary.position_count < 5:
            signals.append("Low diversification: fewer than 5 positions")
        elif summary.position_count > 30:
            signals.append("High position count: consider consolidating")

        # Cash position signals
        if summary.cash_weight is not None:
            if summary.cash_weight > 50:
                signals.append(f"High cash position: {summary.cash_weight:.1f}%")
            elif summary.cash_weight < 5:
                signals.append(f"Low cash reserve: {summary.cash_weight:.1f}%")

        # Top concentration
        if summary.top5_concentration > 80:
            signals.append(
                f"Top 5 positions represent {summary.top5_concentration:.1f}% of portfolio"
            )

        # Include risk signals
        signals.extend(risk.signals)

        return signals


def analyze_portfolio(
    positions: list[PositionData],
    account: Optional[AccountData] = None,
    analysis_date: Optional[date] = None,
) -> PortfolioAnalysisResult:
    """
    Convenience function to analyze portfolio.

    Args:
        positions: List of position data
        account: Optional account data
        analysis_date: Date of analysis

    Returns:
        PortfolioAnalysisResult

    Example:
        positions = [
            PositionData(market="HK", code="00700", qty=100, cost_price=350, market_price=380),
            PositionData(market="US", code="NVDA", qty=50, cost_price=500, market_price=600),
        ]
        result = analyze_portfolio(positions)
        print(f"Total P&L: ${result.summary.total_pl_value:.2f}")
    """
    analyzer = PortfolioAnalyzer()
    return analyzer.analyze(positions, account, analysis_date)


def analyze_positions_from_db(
    positions_list: list,
    account_snapshot: Optional[object] = None,
) -> PortfolioAnalysisResult:
    """
    Analyze portfolio from database model objects.

    Args:
        positions_list: List of Position model objects
        account_snapshot: Optional AccountSnapshot model object

    Returns:
        PortfolioAnalysisResult
    """
    position_data = []
    for p in positions_list:
        position_data.append(
            PositionData(
                market=p.market,
                code=p.code,
                stock_name=p.stock_name,
                qty=float(p.qty) if p.qty else 0,
                cost_price=float(p.cost_price) if p.cost_price else None,
                market_price=float(p.market_price) if p.market_price else None,
                market_val=float(p.market_val) if p.market_val else None,
                pl_val=float(p.pl_val) if p.pl_val else None,
                pl_ratio=float(p.pl_ratio) if p.pl_ratio else None,
                position_side=p.position_side or "LONG",
            )
        )

    account_data = None
    if account_snapshot:
        account_data = AccountData(
            total_assets=(
                float(account_snapshot.total_assets)
                if account_snapshot.total_assets
                else None
            ),
            cash=float(account_snapshot.cash) if account_snapshot.cash else None,
            market_val=(
                float(account_snapshot.market_val)
                if account_snapshot.market_val
                else None
            ),
            buying_power=(
                float(account_snapshot.buying_power)
                if account_snapshot.buying_power
                else None
            ),
            currency=account_snapshot.currency or "HKD",
        )

    return analyze_portfolio(position_data, account_data)


def create_portfolio_analyzer(
    top_n_performers: int = 5,
    concentration_threshold: float = 20.0,
    high_concentration_threshold: float = 30.0,
) -> PortfolioAnalyzer:
    """
    Factory function to create a PortfolioAnalyzer.

    Args:
        top_n_performers: Number of top/bottom performers to track
        concentration_threshold: Position weight threshold for concentration warning (%)
        high_concentration_threshold: High concentration threshold (%)

    Returns:
        PortfolioAnalyzer instance
    """
    return PortfolioAnalyzer(
        top_n_performers=top_n_performers,
        concentration_threshold=concentration_threshold,
        high_concentration_threshold=high_concentration_threshold,
    )
