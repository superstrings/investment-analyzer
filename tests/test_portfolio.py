"""Tests for portfolio analysis module."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from analysis.portfolio import (
    AccountData,
    MarketAllocation,
    PortfolioAnalyzer,
    PortfolioAnalysisResult,
    PortfolioSummary,
    PositionData,
    PositionMetrics,
    RiskLevel,
    RiskMetrics,
    analyze_portfolio,
    analyze_positions_from_db,
    create_portfolio_analyzer,
)


def create_sample_positions() -> list[PositionData]:
    """Create sample positions for testing."""
    return [
        PositionData(
            market="HK",
            code="00700",
            stock_name="Tencent",
            qty=100,
            cost_price=350.0,
            market_price=380.0,
            market_val=38000.0,
            pl_val=3000.0,
            pl_ratio=8.57,
            position_side="LONG",
        ),
        PositionData(
            market="US",
            code="NVDA",
            stock_name="NVIDIA",
            qty=50,
            cost_price=500.0,
            market_price=600.0,
            market_val=30000.0,
            pl_val=5000.0,
            pl_ratio=20.0,
            position_side="LONG",
        ),
        PositionData(
            market="HK",
            code="09988",
            stock_name="Alibaba",
            qty=200,
            cost_price=100.0,
            market_price=90.0,
            market_val=18000.0,
            pl_val=-2000.0,
            pl_ratio=-10.0,
            position_side="LONG",
        ),
    ]


def create_sample_account() -> AccountData:
    """Create sample account data."""
    return AccountData(
        total_assets=100000.0,
        cash=14000.0,
        market_val=86000.0,
        buying_power=50000.0,
        currency="HKD",
    )


class TestPositionData:
    """Tests for PositionData dataclass."""

    def test_default_values(self):
        """Test default values."""
        p = PositionData(market="HK", code="00700")
        assert p.market == "HK"
        assert p.code == "00700"
        assert p.stock_name is None
        assert p.qty == 0.0
        assert p.cost_price is None
        assert p.market_price is None
        assert p.position_side == "LONG"

    def test_custom_values(self):
        """Test custom values."""
        p = PositionData(
            market="US",
            code="AAPL",
            stock_name="Apple",
            qty=100,
            cost_price=150.0,
            market_price=175.0,
            position_side="LONG",
        )
        assert p.market == "US"
        assert p.code == "AAPL"
        assert p.stock_name == "Apple"
        assert p.qty == 100


class TestAccountData:
    """Tests for AccountData dataclass."""

    def test_default_values(self):
        """Test default values."""
        a = AccountData()
        assert a.total_assets is None
        assert a.cash is None
        assert a.currency == "HKD"

    def test_custom_values(self):
        """Test custom values."""
        a = create_sample_account()
        assert a.total_assets == 100000.0
        assert a.cash == 14000.0
        assert a.currency == "HKD"


class TestPositionMetrics:
    """Tests for PositionMetrics dataclass."""

    def test_full_code(self):
        """Test full_code property."""
        p = PositionMetrics(
            code="00700",
            market="HK",
            name="Tencent",
            qty=100,
            cost_price=350.0,
            market_price=380.0,
            market_value=38000.0,
            cost_value=35000.0,
            pl_value=3000.0,
            pl_ratio=8.57,
            weight=40.0,
            position_side="LONG",
        )
        assert p.full_code == "HK.00700"

    def test_to_dict(self):
        """Test to_dict method."""
        p = PositionMetrics(
            code="00700",
            market="HK",
            name="Tencent",
            qty=100,
            cost_price=350.0,
            market_price=380.0,
            market_value=38000.0,
            cost_value=35000.0,
            pl_value=3000.0,
            pl_ratio=8.57,
            weight=40.0,
            position_side="LONG",
        )
        d = p.to_dict()
        assert d["code"] == "HK.00700"
        assert d["name"] == "Tencent"
        assert d["weight"] == 40.0


class TestPortfolioSummary:
    """Tests for PortfolioSummary dataclass."""

    def test_default_values(self):
        """Test default values."""
        s = PortfolioSummary()
        assert s.total_market_value == 0.0
        assert s.position_count == 0
        assert s.win_rate == 0.0

    def test_to_dict(self):
        """Test to_dict method."""
        s = PortfolioSummary(
            total_market_value=100000.0,
            position_count=10,
            win_rate=70.0,
        )
        d = s.to_dict()
        assert d["total_market_value"] == 100000.0
        assert d["position_count"] == 10
        assert d["win_rate"] == 70.0


class TestMarketAllocation:
    """Tests for MarketAllocation dataclass."""

    def test_to_dict(self):
        """Test to_dict method."""
        m = MarketAllocation(
            market="HK",
            position_count=5,
            market_value=50000.0,
            weight=50.0,
            pl_value=2000.0,
            pl_ratio=4.0,
        )
        d = m.to_dict()
        assert d["market"] == "HK"
        assert d["position_count"] == 5
        assert d["weight"] == 50.0


class TestRiskMetrics:
    """Tests for RiskMetrics dataclass."""

    def test_default_values(self):
        """Test default values."""
        r = RiskMetrics()
        assert r.concentration_risk == RiskLevel.LOW
        assert r.diversification_score == 0.0
        assert r.signals == []

    def test_to_dict(self):
        """Test to_dict method."""
        r = RiskMetrics(
            concentration_risk=RiskLevel.HIGH,
            diversification_score=60.0,
            hhi_index=2500.0,
            signals=["High concentration"],
        )
        d = r.to_dict()
        assert d["concentration_risk"] == "high"
        assert d["diversification_score"] == 60.0
        assert d["hhi_index"] == 2500.0


class TestPortfolioAnalyzer:
    """Tests for PortfolioAnalyzer class."""

    def test_default_init(self):
        """Test default initialization."""
        analyzer = PortfolioAnalyzer()
        assert analyzer.top_n_performers == 5
        assert analyzer.concentration_threshold == 20.0
        assert analyzer.high_concentration_threshold == 30.0

    def test_custom_init(self):
        """Test custom initialization."""
        analyzer = PortfolioAnalyzer(
            top_n_performers=10,
            concentration_threshold=15.0,
            high_concentration_threshold=25.0,
        )
        assert analyzer.top_n_performers == 10
        assert analyzer.concentration_threshold == 15.0

    def test_analyze_empty_positions(self):
        """Test analysis with no positions."""
        analyzer = PortfolioAnalyzer()
        result = analyzer.analyze([])

        assert isinstance(result, PortfolioAnalysisResult)
        assert result.summary.position_count == 0
        assert len(result.positions) == 0
        assert any("No active positions" in s for s in result.signals)

    def test_analyze_with_positions(self):
        """Test analysis with positions."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        assert result.summary.position_count == 3
        assert result.summary.total_market_value == 86000.0
        assert len(result.positions) == 3

    def test_analyze_with_account(self):
        """Test analysis with account data."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        account = create_sample_account()
        result = analyzer.analyze(positions, account)

        assert result.summary.cash_balance == 14000.0
        assert result.summary.total_assets == 100000.0
        assert abs(result.summary.cash_weight - 14.0) < 0.01

    def test_analyze_filters_zero_qty(self):
        """Test that zero quantity positions are filtered."""
        analyzer = PortfolioAnalyzer()
        positions = [
            PositionData(market="HK", code="00700", qty=100, market_val=10000),
            PositionData(market="HK", code="09988", qty=0, market_val=0),
        ]
        result = analyzer.analyze(positions)

        assert result.summary.position_count == 1

    def test_win_rate_calculation(self):
        """Test win rate calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # 2 profitable, 1 losing = 66.67%
        assert result.summary.profitable_count == 2
        assert result.summary.losing_count == 1
        assert abs(result.summary.win_rate - 66.67) < 1

    def test_total_pl_calculation(self):
        """Test total P&L calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # 3000 + 5000 - 2000 = 6000
        assert result.summary.total_pl_value == 6000.0

    def test_market_allocation(self):
        """Test market allocation calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        assert len(result.market_allocation) == 2  # HK and US

        hk_alloc = next(m for m in result.market_allocation if m.market == "HK")
        us_alloc = next(m for m in result.market_allocation if m.market == "US")

        assert hk_alloc.position_count == 2
        assert us_alloc.position_count == 1
        assert hk_alloc.market_value == 56000.0  # 38000 + 18000

    def test_weight_calculation(self):
        """Test position weight calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Total value: 86000
        # 00700: 38000/86000 = 44.19%
        # NVDA: 30000/86000 = 34.88%
        # 09988: 18000/86000 = 20.93%

        tencent = next(p for p in result.positions if p.code == "00700")
        assert abs(tencent.weight - 44.19) < 0.1

    def test_top_performers(self):
        """Test top performers ranking."""
        analyzer = PortfolioAnalyzer(top_n_performers=2)
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Top should be NVDA (20%) and 00700 (8.57%)
        assert len(result.top_performers) == 2
        assert result.top_performers[0].code == "NVDA"
        assert result.top_performers[1].code == "00700"

    def test_bottom_performers(self):
        """Test bottom performers ranking."""
        analyzer = PortfolioAnalyzer(top_n_performers=2)
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Bottom should be 09988 (-10%) and 00700 (8.57%)
        assert len(result.bottom_performers) == 2
        assert result.bottom_performers[0].code == "09988"

    def test_concentration_metrics(self):
        """Test concentration metrics."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Largest position: 00700 at 44.19%
        assert result.summary.largest_position_weight > 40

        # Top 5 (all 3) concentration should be 100%
        assert result.summary.top5_concentration == 100.0

    def test_risk_level_calculation(self):
        """Test risk level calculation."""
        analyzer = PortfolioAnalyzer(
            concentration_threshold=20.0,
            high_concentration_threshold=30.0,
        )
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Largest position is 44.19% > 30% threshold
        assert result.risk_metrics.concentration_risk == RiskLevel.VERY_HIGH

    def test_hhi_index(self):
        """Test HHI index calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # HHI > 0 for non-empty portfolio
        assert result.risk_metrics.hhi_index > 0

    def test_diversification_score(self):
        """Test diversification score."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        # Score should be between 0 and 100
        assert 0 <= result.risk_metrics.diversification_score <= 100

    def test_largest_loss_tracking(self):
        """Test largest loss position tracking."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        assert result.risk_metrics.largest_loss_position == "HK.09988"
        assert result.risk_metrics.largest_loss_ratio == -10.0

    def test_unrealized_loss_calculation(self):
        """Test total unrealized loss calculation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        assert result.risk_metrics.total_unrealized_loss == -2000.0

    def test_signals_generation(self):
        """Test signal generation."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        assert len(result.signals) > 0

    def test_to_dict(self):
        """Test result to_dict method."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        result = analyzer.analyze(positions)

        d = result.to_dict()
        assert "analysis_date" in d
        assert "summary" in d
        assert "positions" in d
        assert "market_allocation" in d
        assert "risk_metrics" in d

    def test_analysis_date(self):
        """Test custom analysis date."""
        analyzer = PortfolioAnalyzer()
        positions = create_sample_positions()
        custom_date = date(2024, 6, 15)
        result = analyzer.analyze(positions, analysis_date=custom_date)

        assert result.analysis_date == custom_date


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_analyze_portfolio(self):
        """Test analyze_portfolio function."""
        positions = create_sample_positions()
        result = analyze_portfolio(positions)

        assert isinstance(result, PortfolioAnalysisResult)
        assert result.summary.position_count == 3

    def test_analyze_portfolio_with_account(self):
        """Test analyze_portfolio with account data."""
        positions = create_sample_positions()
        account = create_sample_account()
        result = analyze_portfolio(positions, account)

        assert result.summary.cash_balance == 14000.0

    def test_create_portfolio_analyzer(self):
        """Test factory function."""
        analyzer = create_portfolio_analyzer(
            top_n_performers=10,
            concentration_threshold=25.0,
        )
        assert isinstance(analyzer, PortfolioAnalyzer)
        assert analyzer.top_n_performers == 10
        assert analyzer.concentration_threshold == 25.0

    def test_analyze_positions_from_db(self):
        """Test analyze_positions_from_db function."""
        # Create mock Position objects
        mock_pos1 = MagicMock()
        mock_pos1.market = "HK"
        mock_pos1.code = "00700"
        mock_pos1.stock_name = "Tencent"
        mock_pos1.qty = 100
        mock_pos1.cost_price = 350
        mock_pos1.market_price = 380
        mock_pos1.market_val = 38000
        mock_pos1.pl_val = 3000
        mock_pos1.pl_ratio = 8.57
        mock_pos1.position_side = "LONG"

        # Create mock AccountSnapshot
        mock_snapshot = MagicMock()
        mock_snapshot.total_assets = 100000
        mock_snapshot.cash = 62000
        mock_snapshot.market_val = 38000
        mock_snapshot.buying_power = 50000
        mock_snapshot.currency = "HKD"

        result = analyze_positions_from_db([mock_pos1], mock_snapshot)

        assert isinstance(result, PortfolioAnalysisResult)
        assert result.summary.position_count == 1
        assert result.summary.cash_balance == 62000


class TestEdgeCases:
    """Tests for edge cases."""

    def test_single_position(self):
        """Test with single position."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                cost_price=350,
                market_price=380,
                market_val=38000,
            )
        ]
        result = analyze_portfolio(positions)

        assert result.summary.position_count == 1
        assert result.summary.largest_position_weight == 100.0

    def test_all_losing_positions(self):
        """Test with all losing positions."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                market_val=30000,
                pl_val=-5000,
                pl_ratio=-14.3,
            ),
            PositionData(
                market="US",
                code="NVDA",
                qty=50,
                market_val=20000,
                pl_val=-3000,
                pl_ratio=-13.0,
            ),
        ]
        result = analyze_portfolio(positions)

        assert result.summary.win_rate == 0.0
        assert result.summary.losing_count == 2
        assert result.summary.total_pl_value == -8000.0

    def test_all_winning_positions(self):
        """Test with all winning positions."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                market_val=40000,
                pl_val=5000,
                pl_ratio=14.3,
            ),
            PositionData(
                market="US",
                code="NVDA",
                qty=50,
                market_val=30000,
                pl_val=10000,
                pl_ratio=50.0,
            ),
        ]
        result = analyze_portfolio(positions)

        assert result.summary.win_rate == 100.0
        assert result.summary.profitable_count == 2

    def test_positions_without_pl_data(self):
        """Test positions without P&L data."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                cost_price=350,
                market_price=380,
            ),
        ]
        result = analyze_portfolio(positions)

        # Should calculate P&L from cost/market price
        assert result.summary.position_count == 1
        pos = result.positions[0]
        assert pos.pl_value is not None
        assert pos.pl_value == 3000.0  # (380-350) * 100

    def test_highly_concentrated_portfolio(self):
        """Test highly concentrated portfolio."""
        positions = [
            PositionData(market="HK", code="00700", qty=100, market_val=95000),
            PositionData(market="US", code="NVDA", qty=10, market_val=5000),
        ]
        result = analyze_portfolio(positions)

        assert result.summary.largest_position_weight == 95.0
        assert result.risk_metrics.concentration_risk == RiskLevel.VERY_HIGH

    def test_well_diversified_portfolio(self):
        """Test well diversified portfolio."""
        positions = [
            PositionData(market="HK", code=f"00{i:03d}", qty=100, market_val=10000)
            for i in range(10)
        ]
        result = analyze_portfolio(positions)

        assert result.summary.largest_position_weight == 10.0
        assert result.risk_metrics.concentration_risk == RiskLevel.LOW

    def test_short_positions(self):
        """Test with short positions."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                market_val=38000,
                position_side="LONG",
            ),
            PositionData(
                market="US",
                code="NVDA",
                qty=-50,
                market_val=30000,
                position_side="SHORT",
            ),
        ]
        result = analyze_portfolio(positions)

        assert result.summary.long_count == 1
        assert result.summary.short_count == 1

    def test_cash_only_account(self):
        """Test account with cash only."""
        account = AccountData(total_assets=100000, cash=100000, market_val=0)
        result = analyze_portfolio([], account)

        assert result.summary.cash_balance == 100000
        assert result.summary.cash_weight == 100.0

    def test_multiple_markets(self):
        """Test portfolio across multiple markets."""
        positions = [
            PositionData(market="HK", code="00700", qty=100, market_val=40000),
            PositionData(market="US", code="NVDA", qty=50, market_val=30000),
            PositionData(market="A", code="600519", qty=10, market_val=20000),
        ]
        result = analyze_portfolio(positions)

        assert len(result.market_allocation) == 3
        markets = [m.market for m in result.market_allocation]
        assert "HK" in markets
        assert "US" in markets
        assert "A" in markets


class TestRiskSignals:
    """Tests for risk signal generation."""

    def test_high_concentration_signal(self):
        """Test high concentration signal."""
        positions = [
            PositionData(market="HK", code="00700", qty=100, market_val=80000),
            PositionData(market="US", code="NVDA", qty=10, market_val=20000),
        ]
        result = analyze_portfolio(positions)

        signals_text = " ".join(result.signals + result.risk_metrics.signals)
        assert "concentration" in signals_text.lower()

    def test_large_loss_signal(self):
        """Test large loss position signal."""
        positions = [
            PositionData(
                market="HK",
                code="00700",
                qty=100,
                market_val=40000,
                pl_val=-15000,
                pl_ratio=-27.3,
            ),
        ]
        result = analyze_portfolio(positions)

        signals_text = " ".join(result.risk_metrics.signals)
        assert "loss" in signals_text.lower()

    def test_low_diversification_signal(self):
        """Test low diversification signal."""
        positions = [
            PositionData(market="HK", code="00700", qty=100, market_val=50000),
            PositionData(market="HK", code="09988", qty=50, market_val=50000),
        ]
        result = analyze_portfolio(positions)

        signals_text = " ".join(result.signals)
        # Should warn about few positions
        assert "diversification" in signals_text.lower() or len(result.signals) > 0


class TestIntegration:
    """Integration tests."""

    def test_imports_from_analysis(self):
        """Test imports from analysis module."""
        from analysis import (
            PortfolioAnalyzer,
            PortfolioAnalysisResult,
            PositionData,
            AccountData,
            analyze_portfolio,
        )

        assert PortfolioAnalyzer is not None
        assert PortfolioAnalysisResult is not None
        assert PositionData is not None
        assert AccountData is not None
        assert analyze_portfolio is not None

    def test_full_workflow(self):
        """Test complete portfolio analysis workflow."""
        # Create positions
        positions = create_sample_positions()

        # Create account
        account = create_sample_account()

        # Analyze
        analyzer = create_portfolio_analyzer(top_n_performers=3)
        result = analyzer.analyze(positions, account)

        # Verify complete result
        assert result.summary.position_count == 3
        assert result.summary.total_market_value == 86000.0
        assert result.summary.cash_balance == 14000.0
        assert len(result.market_allocation) == 2
        assert len(result.top_performers) <= 3
        assert len(result.bottom_performers) <= 3
        assert result.risk_metrics is not None

        # Convert to dict for serialization
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "analysis_date" in d
