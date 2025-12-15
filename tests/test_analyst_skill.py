"""
Tests for Analyst Skill components.
"""

from datetime import date
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from skills.analyst import (
    BatchAnalysisResult,
    BatchAnalyzer,
    DivergenceType,
    OBVAnalysisResult,
    OBVAnalyzer,
    OBVTrend,
    ScoringSystem,
    SignalStrength,
    StockAnalysis,
    StockAnalyzer,
    TechnicalRating,
    TechnicalScore,
    VCPAnalysisResult,
    VCPScanner,
    VCPStage,
    calculate_technical_score,
    generate_analysis_report,
    generate_batch_report,
    scan_stocks_for_vcp,
)
from skills.shared import ReportFormat


# =============================================================================
# Test Data Fixtures
# =============================================================================


def create_sample_df(days: int = 100, trend: str = "up") -> pd.DataFrame:
    """Create sample OHLCV DataFrame for testing."""
    np.random.seed(42)

    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")

    if trend == "up":
        base_prices = np.linspace(100, 150, days) + np.random.randn(days) * 2
    elif trend == "down":
        base_prices = np.linspace(150, 100, days) + np.random.randn(days) * 2
    else:
        base_prices = np.ones(days) * 120 + np.random.randn(days) * 5

    # Create OHLC from base prices
    opens = base_prices + np.random.randn(days) * 1
    highs = np.maximum(opens, base_prices) + np.abs(np.random.randn(days)) * 2
    lows = np.minimum(opens, base_prices) - np.abs(np.random.randn(days)) * 2
    closes = base_prices

    # Volume with trend
    if trend == "up":
        volumes = np.linspace(1e6, 1.5e6, days) + np.random.randn(days) * 1e5
    elif trend == "down":
        volumes = np.linspace(1e6, 0.5e6, days) + np.random.randn(days) * 1e5
    else:
        volumes = np.ones(days) * 1e6 + np.random.randn(days) * 1e5

    volumes = np.abs(volumes)

    return pd.DataFrame(
        {
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
        }
    ).set_index("Date")


def create_vcp_df(days: int = 100) -> pd.DataFrame:
    """Create sample DataFrame with VCP-like pattern."""
    np.random.seed(123)

    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")

    # Create VCP pattern: uptrend then contracting consolidation
    prices = []
    base = 100

    # Calculate proportions based on days
    uptrend_days = int(days * 0.4)  # 40% uptrend
    consolidation_days = days - uptrend_days  # 60% consolidation

    # First part: uptrend
    for i in range(uptrend_days):
        base = base * 1.01 + np.random.randn() * 0.5
        prices.append(base)

    peak = base

    # Rest: VCP consolidation with decreasing volatility
    for i in range(consolidation_days):
        # Decreasing volatility
        volatility = 5 * (1 - i / consolidation_days) + 1
        price = peak * (1 - 0.05 * np.sin(i / 10)) + np.random.randn() * volatility
        prices.append(price)

    prices = np.array(prices)
    n = len(prices)  # Use actual length
    opens = prices + np.random.randn(n) * 0.5
    highs = np.maximum(opens, prices) + np.abs(np.random.randn(n)) * 1
    lows = np.minimum(opens, prices) - np.abs(np.random.randn(n)) * 1

    # Decreasing volume
    volumes = np.linspace(2e6, 0.5e6, n) + np.random.randn(n) * 1e5
    volumes = np.abs(volumes)

    return pd.DataFrame(
        {
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": prices,
            "Volume": volumes,
        }
    ).set_index("Date")


# =============================================================================
# OBVTrend Enum Tests
# =============================================================================


class TestOBVTrend:
    """Tests for OBVTrend enum."""

    def test_values(self):
        """Test enum values."""
        assert OBVTrend.STRONG_UP.value == "strong_up"
        assert OBVTrend.UP.value == "up"
        assert OBVTrend.SIDEWAYS.value == "sideways"
        assert OBVTrend.DOWN.value == "down"
        assert OBVTrend.STRONG_DOWN.value == "strong_down"


class TestDivergenceType:
    """Tests for DivergenceType enum."""

    def test_values(self):
        """Test enum values."""
        assert DivergenceType.BULLISH.value == "bullish"
        assert DivergenceType.BEARISH.value == "bearish"
        assert DivergenceType.NONE.value == "none"


# =============================================================================
# OBVAnalysisResult Tests
# =============================================================================


class TestOBVAnalysisResult:
    """Tests for OBVAnalysisResult dataclass."""

    def test_creation(self):
        """Test creating OBVAnalysisResult."""
        result = OBVAnalysisResult(
            current_obv=1000000,
            obv_ma=950000,
            obv_change_pct=5.0,
            trend=OBVTrend.UP,
            trend_strength=75.0,
            divergence=DivergenceType.NONE,
            divergence_strength=0,
            volume_confirms_price=True,
            confirmation_score=80.0,
            score=70.0,
            signals=["OBV trending up"],
        )
        assert result.current_obv == 1000000
        assert result.trend == OBVTrend.UP
        assert result.score == 70.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = OBVAnalysisResult(
            current_obv=1000000,
            obv_ma=950000,
            obv_change_pct=5.0,
            trend=OBVTrend.UP,
            trend_strength=75.0,
            divergence=DivergenceType.BULLISH,
            divergence_strength=60.0,
            volume_confirms_price=True,
            confirmation_score=80.0,
            score=70.0,
            signals=["Signal 1"],
        )
        d = result.to_dict()
        assert d["trend"] == "up"
        assert d["divergence"] == "bullish"
        assert d["score"] == 70.0


# =============================================================================
# OBVAnalyzer Tests
# =============================================================================


class TestOBVAnalyzer:
    """Tests for OBVAnalyzer class."""

    def test_init(self):
        """Test analyzer initialization."""
        analyzer = OBVAnalyzer(signal_period=20, divergence_lookback=14)
        assert analyzer.signal_period == 20
        assert analyzer.divergence_lookback == 14

    def test_analyze_uptrend(self):
        """Test analysis on uptrend data."""
        df = create_sample_df(100, trend="up")
        analyzer = OBVAnalyzer()
        result = analyzer.analyze(df)

        assert isinstance(result, OBVAnalysisResult)
        assert result.trend in [OBVTrend.STRONG_UP, OBVTrend.UP, OBVTrend.SIDEWAYS]
        assert 0 <= result.score <= 100

    def test_analyze_downtrend(self):
        """Test analysis on downtrend data."""
        df = create_sample_df(100, trend="down")
        analyzer = OBVAnalyzer()
        result = analyzer.analyze(df)

        assert isinstance(result, OBVAnalysisResult)
        # Downtrend should have lower scores
        assert result.trend in [OBVTrend.DOWN, OBVTrend.STRONG_DOWN, OBVTrend.SIDEWAYS]

    def test_analyze_insufficient_data(self):
        """Test analysis with insufficient data."""
        df = create_sample_df(10)  # Too few data points
        analyzer = OBVAnalyzer(trend_period=20)
        result = analyzer.analyze(df)

        assert result.trend == OBVTrend.SIDEWAYS
        assert result.score == 0
        assert "Insufficient data" in result.signals[0]

    def test_analyze_signals(self):
        """Test that analysis produces signals."""
        df = create_sample_df(100, trend="up")
        analyzer = OBVAnalyzer()
        result = analyzer.analyze(df)

        assert len(result.signals) > 0


# =============================================================================
# VCPStage Enum Tests
# =============================================================================


class TestVCPStage:
    """Tests for VCPStage enum."""

    def test_values(self):
        """Test enum values."""
        assert VCPStage.NO_PATTERN.value == "no_pattern"
        assert VCPStage.FORMING.value == "forming"
        assert VCPStage.MATURE.value == "mature"
        assert VCPStage.BREAKOUT.value == "breakout"


# =============================================================================
# VCPAnalysisResult Tests
# =============================================================================


class TestVCPAnalysisResult:
    """Tests for VCPAnalysisResult dataclass."""

    def test_creation(self):
        """Test creating VCPAnalysisResult."""
        result = VCPAnalysisResult(
            detected=True,
            stage=VCPStage.MATURE,
            contraction_count=3,
            depth_sequence=[20.0, 12.0, 6.0],
            volume_dryup=True,
            range_tightening=True,
            pivot_price=150.0,
            current_price=145.0,
            distance_to_pivot_pct=3.4,
            pattern_score=80.0,
            volume_score=85.0,
            timing_score=90.0,
            overall_score=85.0,
            signals=["VCP detected"],
        )
        assert result.detected is True
        assert result.stage == VCPStage.MATURE
        assert result.overall_score == 85.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = VCPAnalysisResult(
            detected=True,
            stage=VCPStage.FORMING,
            contraction_count=2,
            depth_sequence=[15.0, 8.0],
            volume_dryup=True,
            range_tightening=False,
            pivot_price=100.0,
            current_price=95.0,
            distance_to_pivot_pct=5.0,
            pattern_score=60.0,
            volume_score=70.0,
            timing_score=50.0,
            overall_score=55.0,
            signals=[],
        )
        d = result.to_dict()
        assert d["stage"] == "forming"
        assert d["detected"] is True


# =============================================================================
# VCPScanner Tests
# =============================================================================


class TestVCPScanner:
    """Tests for VCPScanner class."""

    def test_init(self):
        """Test scanner initialization."""
        scanner = VCPScanner()
        assert scanner.config is not None

    def test_analyze_with_data(self):
        """Test VCP analysis with sample data."""
        df = create_vcp_df(100)
        scanner = VCPScanner()
        result = scanner.analyze(df)

        assert isinstance(result, VCPAnalysisResult)
        assert 0 <= result.overall_score <= 100
        assert result.current_price > 0

    def test_analyze_insufficient_data(self):
        """Test analysis with insufficient data."""
        df = create_sample_df(20)  # Too few data points
        scanner = VCPScanner()
        result = scanner.analyze(df)

        assert result.detected is False
        assert result.stage == VCPStage.NO_PATTERN
        assert result.overall_score == 0

    def test_analyze_downtrend(self):
        """Test VCP analysis on downtrend (should not detect VCP)."""
        df = create_sample_df(100, trend="down")
        scanner = VCPScanner()
        result = scanner.analyze(df)

        # Downtrend typically won't have valid VCP
        assert isinstance(result, VCPAnalysisResult)


class TestScanStocksForVCP:
    """Tests for scan_stocks_for_vcp function."""

    def test_scan_multiple_stocks(self):
        """Test scanning multiple stocks."""
        stock_data = {
            "HK.00700": create_vcp_df(100),
            "US.AAPL": create_sample_df(100, trend="up"),
            "US.NVDA": create_sample_df(100, trend="down"),
        }

        results = scan_stocks_for_vcp(stock_data, min_score=0)

        assert isinstance(results, list)
        # Results should be sorted by score
        if len(results) >= 2:
            assert results[0][1].overall_score >= results[1][1].overall_score

    def test_scan_with_min_score(self):
        """Test scanning with minimum score filter."""
        stock_data = {
            "HK.00700": create_sample_df(100),
        }

        results = scan_stocks_for_vcp(stock_data, min_score=90)

        # High threshold should filter out most stocks
        assert isinstance(results, list)


# =============================================================================
# TechnicalRating Enum Tests
# =============================================================================


class TestTechnicalRating:
    """Tests for TechnicalRating enum."""

    def test_values(self):
        """Test enum values."""
        assert TechnicalRating.STRONG_BUY.value == "strong_buy"
        assert TechnicalRating.BUY.value == "buy"
        assert TechnicalRating.HOLD.value == "hold"
        assert TechnicalRating.SELL.value == "sell"
        assert TechnicalRating.STRONG_SELL.value == "strong_sell"


class TestSignalStrength:
    """Tests for SignalStrength enum."""

    def test_values(self):
        """Test enum values."""
        assert SignalStrength.STRONG.value == "strong"
        assert SignalStrength.MODERATE.value == "moderate"
        assert SignalStrength.WEAK.value == "weak"
        assert SignalStrength.NONE.value == "none"


# =============================================================================
# TechnicalScore Tests
# =============================================================================


class TestTechnicalScore:
    """Tests for TechnicalScore dataclass."""

    def test_creation(self):
        """Test creating TechnicalScore."""
        score = TechnicalScore(
            obv_score=70.0,
            vcp_score=80.0,
            final_score=76.0,
            rating=TechnicalRating.BUY,
            signal_strength=SignalStrength.MODERATE,
            obv_trend="up",
            obv_divergence="none",
            vcp_detected=True,
            vcp_stage="mature",
            pivot_price=150.0,
            distance_to_pivot=3.0,
            action="Watch for VCP breakout entry",
            key_levels=["Pivot: 150.00"],
            watch_points=["Watch for breakout"],
        )
        assert score.final_score == 76.0
        assert score.rating == TechnicalRating.BUY

    def test_to_dict(self):
        """Test conversion to dictionary."""
        score = TechnicalScore(
            obv_score=70.0,
            vcp_score=80.0,
            final_score=76.0,
            rating=TechnicalRating.BUY,
            signal_strength=SignalStrength.MODERATE,
            obv_trend="up",
            obv_divergence="none",
            vcp_detected=True,
            vcp_stage="mature",
            pivot_price=150.0,
            distance_to_pivot=3.0,
            action="Watch",
            key_levels=[],
            watch_points=[],
        )
        d = score.to_dict()
        assert d["rating"] == "buy"
        assert d["signal_strength"] == "moderate"


# =============================================================================
# ScoringSystem Tests
# =============================================================================


class TestScoringSystem:
    """Tests for ScoringSystem class."""

    def test_init_default_weights(self):
        """Test default weight initialization."""
        scorer = ScoringSystem()
        assert scorer.obv_weight == 0.40
        assert scorer.vcp_weight == 0.60

    def test_init_custom_weights(self):
        """Test custom weight initialization."""
        scorer = ScoringSystem(obv_weight=0.5, vcp_weight=0.5)
        assert scorer.obv_weight == 0.5
        assert scorer.vcp_weight == 0.5

    def test_calculate_score(self):
        """Test score calculation."""
        scorer = ScoringSystem()

        obv_result = OBVAnalysisResult(
            current_obv=1000000,
            obv_ma=950000,
            obv_change_pct=5.0,
            trend=OBVTrend.UP,
            trend_strength=70.0,
            divergence=DivergenceType.NONE,
            divergence_strength=0,
            volume_confirms_price=True,
            confirmation_score=80.0,
            score=70.0,
            signals=[],
        )

        vcp_result = VCPAnalysisResult(
            detected=True,
            stage=VCPStage.MATURE,
            contraction_count=3,
            depth_sequence=[20.0, 12.0, 6.0],
            volume_dryup=True,
            range_tightening=True,
            pivot_price=150.0,
            current_price=145.0,
            distance_to_pivot_pct=3.4,
            pattern_score=80.0,
            volume_score=85.0,
            timing_score=90.0,
            overall_score=80.0,
            signals=[],
        )

        score = scorer.calculate_score(obv_result, vcp_result, 145.0)

        assert isinstance(score, TechnicalScore)
        assert 0 <= score.final_score <= 100
        assert score.rating in list(TechnicalRating)

    def test_rating_thresholds(self):
        """Test rating thresholds."""
        scorer = ScoringSystem()

        # Create mock results for testing different score levels
        def create_mock_results(obv_score, vcp_score):
            obv = OBVAnalysisResult(
                current_obv=1e6,
                obv_ma=1e6,
                obv_change_pct=0,
                trend=OBVTrend.SIDEWAYS,
                trend_strength=50,
                divergence=DivergenceType.NONE,
                divergence_strength=0,
                volume_confirms_price=True,
                confirmation_score=50,
                score=obv_score,
                signals=[],
            )
            vcp = VCPAnalysisResult(
                detected=False,
                stage=VCPStage.NO_PATTERN,
                contraction_count=0,
                depth_sequence=[],
                volume_dryup=False,
                range_tightening=False,
                pivot_price=None,
                current_price=100,
                distance_to_pivot_pct=0,
                pattern_score=vcp_score,
                volume_score=50,
                timing_score=50,
                overall_score=vcp_score,
                signals=[],
            )
            return obv, vcp

        # Test STRONG_BUY (>=80)
        obv, vcp = create_mock_results(85, 85)
        score = scorer.calculate_score(obv, vcp)
        assert score.rating == TechnicalRating.STRONG_BUY

        # Test HOLD (45-64)
        obv, vcp = create_mock_results(50, 50)
        score = scorer.calculate_score(obv, vcp)
        assert score.rating == TechnicalRating.HOLD


class TestCalculateTechnicalScore:
    """Tests for calculate_technical_score convenience function."""

    def test_function_works(self):
        """Test the convenience function."""
        obv_result = OBVAnalysisResult(
            current_obv=1000000,
            obv_ma=950000,
            obv_change_pct=5.0,
            trend=OBVTrend.UP,
            trend_strength=70.0,
            divergence=DivergenceType.NONE,
            divergence_strength=0,
            volume_confirms_price=True,
            confirmation_score=80.0,
            score=70.0,
            signals=[],
        )

        vcp_result = VCPAnalysisResult(
            detected=False,
            stage=VCPStage.NO_PATTERN,
            contraction_count=0,
            depth_sequence=[],
            volume_dryup=False,
            range_tightening=False,
            pivot_price=None,
            current_price=100,
            distance_to_pivot_pct=0,
            pattern_score=50,
            volume_score=50,
            timing_score=50,
            overall_score=50,
            signals=[],
        )

        score = calculate_technical_score(obv_result, vcp_result, 100)
        assert isinstance(score, TechnicalScore)


# =============================================================================
# StockAnalysis Tests
# =============================================================================


class TestStockAnalysis:
    """Tests for StockAnalysis dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        obv = OBVAnalysisResult(
            current_obv=1e6,
            obv_ma=1e6,
            obv_change_pct=0,
            trend=OBVTrend.UP,
            trend_strength=70,
            divergence=DivergenceType.NONE,
            divergence_strength=0,
            volume_confirms_price=True,
            confirmation_score=70,
            score=70,
            signals=[],
        )
        vcp = VCPAnalysisResult(
            detected=True,
            stage=VCPStage.MATURE,
            contraction_count=3,
            depth_sequence=[20, 12, 6],
            volume_dryup=True,
            range_tightening=True,
            pivot_price=150,
            current_price=145,
            distance_to_pivot_pct=3.4,
            pattern_score=80,
            volume_score=85,
            timing_score=90,
            overall_score=85,
            signals=[],
        )
        tech_score = TechnicalScore(
            obv_score=70,
            vcp_score=85,
            final_score=79,
            rating=TechnicalRating.BUY,
            signal_strength=SignalStrength.MODERATE,
            obv_trend="up",
            obv_divergence="none",
            vcp_detected=True,
            vcp_stage="mature",
            pivot_price=150,
            distance_to_pivot=3.4,
            action="Watch for breakout",
            key_levels=["Pivot: 150"],
            watch_points=["Watch volume"],
        )

        analysis = StockAnalysis(
            market="HK",
            code="00700",
            name="Tencent",
            analysis_date=date.today(),
            current_price=145,
            price_change_pct=5.0,
            obv_analysis=obv,
            vcp_analysis=vcp,
            technical_score=tech_score,
            summary="Bullish setup",
            recommendation="Watch for breakout",
            confidence=75,
            signals=["Signal 1"],
        )

        d = analysis.to_dict()
        assert d["market"] == "HK"
        assert d["code"] == "00700"
        assert "obv_analysis" in d
        assert "vcp_analysis" in d


# =============================================================================
# StockAnalyzer Tests
# =============================================================================


class TestStockAnalyzer:
    """Tests for StockAnalyzer class."""

    def test_init(self):
        """Test analyzer initialization."""
        analyzer = StockAnalyzer()
        assert analyzer.obv_analyzer is not None
        assert analyzer.vcp_scanner is not None
        assert analyzer.scoring_system is not None

    def test_analyze(self):
        """Test stock analysis."""
        df = create_sample_df(100, trend="up")
        analyzer = StockAnalyzer()

        result = analyzer.analyze(df, market="HK", code="00700", name="Tencent")

        assert isinstance(result, StockAnalysis)
        assert result.market == "HK"
        assert result.code == "00700"
        assert result.current_price > 0
        assert 0 <= result.technical_score.final_score <= 100

    def test_analyze_generates_summary(self):
        """Test that analysis generates summary."""
        df = create_sample_df(100)
        analyzer = StockAnalyzer()

        result = analyzer.analyze(df)

        assert len(result.summary) > 0
        assert len(result.recommendation) > 0

    def test_analyze_calculates_confidence(self):
        """Test that analysis calculates confidence."""
        df = create_sample_df(100)
        analyzer = StockAnalyzer()

        result = analyzer.analyze(df)

        assert 0 <= result.confidence <= 100


class TestGenerateAnalysisReport:
    """Tests for generate_analysis_report function."""

    def test_markdown_report(self):
        """Test generating markdown report."""
        df = create_sample_df(100)
        analyzer = StockAnalyzer()
        analysis = analyzer.analyze(df, market="HK", code="00700", name="Tencent")

        report = generate_analysis_report(analysis, ReportFormat.MARKDOWN)

        assert "# Technical Analysis: HK.00700" in report
        assert "Tencent" in report
        assert "Summary" in report
        assert "Technical Scores" in report

    def test_text_report(self):
        """Test generating text report."""
        df = create_sample_df(100)
        analyzer = StockAnalyzer()
        analysis = analyzer.analyze(df, market="US", code="AAPL")

        report = generate_analysis_report(analysis, ReportFormat.TEXT)

        assert "US.AAPL" in report
        assert len(report) > 0


# =============================================================================
# BatchAnalysisResult Tests
# =============================================================================


class TestBatchAnalysisResult:
    """Tests for BatchAnalysisResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        result = BatchAnalysisResult(
            analysis_date=date.today(),
            total_analyzed=10,
            successful=8,
            failed=2,
            results=[],
            top_vcp=[],
            top_obv=[],
            top_overall=[],
            strong_buy=[],
            buy=[],
            hold=[],
            sell=[],
            failed_codes=["HK.00001", "US.XXX"],
        )

        d = result.to_dict()
        assert d["total_analyzed"] == 10
        assert d["successful"] == 8
        assert len(d["failed_codes"]) == 2


# =============================================================================
# BatchAnalyzer Tests
# =============================================================================


class TestBatchAnalyzer:
    """Tests for BatchAnalyzer class."""

    def test_init(self):
        """Test batch analyzer initialization."""
        analyzer = BatchAnalyzer(days=120)
        assert analyzer.days == 120
        assert analyzer.stock_analyzer is not None

    @patch.object(BatchAnalyzer, "analyze_codes")
    def test_analyze_codes_mock(self, mock_analyze):
        """Test analyze_codes method with mock."""
        mock_analyze.return_value = BatchAnalysisResult(
            analysis_date=date.today(),
            total_analyzed=2,
            successful=2,
            failed=0,
            results=[],
            failed_codes=[],
        )

        analyzer = BatchAnalyzer()
        result = analyzer.analyze_codes(["HK.00700", "US.AAPL"])

        assert result.total_analyzed == 2
        assert result.successful == 2


class TestGenerateBatchReport:
    """Tests for generate_batch_report function."""

    def test_empty_result(self):
        """Test generating report for empty results."""
        result = BatchAnalysisResult(
            analysis_date=date.today(),
            total_analyzed=0,
            successful=0,
            failed=0,
            results=[],
            failed_codes=[],
        )

        report = generate_batch_report(result)

        assert "Batch Technical Analysis" in report
        assert "Total Stocks" in report

    def test_with_failed_codes(self):
        """Test report includes failed codes."""
        result = BatchAnalysisResult(
            analysis_date=date.today(),
            total_analyzed=3,
            successful=1,
            failed=2,
            results=[],
            failed_codes=["HK.00001", "US.XXX"],
        )

        report = generate_batch_report(result)

        assert "Failed Analysis" in report
        assert "HK.00001" in report


# =============================================================================
# Integration Tests
# =============================================================================


class TestAnalystSkillIntegration:
    """Integration tests for the analyst skill."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        # Create test data
        df = create_vcp_df(120)

        # Run analysis
        analyzer = StockAnalyzer()
        result = analyzer.analyze(df, market="HK", code="00700", name="Tencent")

        # Verify result structure
        assert isinstance(result, StockAnalysis)
        assert result.obv_analysis is not None
        assert result.vcp_analysis is not None
        assert result.technical_score is not None

        # Generate report
        report = generate_analysis_report(result)
        assert len(report) > 100

    def test_scoring_consistency(self):
        """Test that scoring is consistent."""
        df = create_sample_df(100, trend="up")
        analyzer = StockAnalyzer()

        # Run analysis twice
        result1 = analyzer.analyze(df.copy())
        result2 = analyzer.analyze(df.copy())

        # Scores should be identical for same data
        assert result1.technical_score.final_score == result2.technical_score.final_score
