"""Tests for VCP (Volatility Contraction Pattern) indicator."""

import numpy as np
import pandas as pd
import pytest

from analysis.indicators.vcp import (
    VCP,
    Contraction,
    VCPConfig,
    VCPResult,
    VCPScanner,
    detect_vcp,
    scan_vcp,
)


def create_sample_df(n: int = 100) -> pd.DataFrame:
    """Create sample OHLCV DataFrame."""
    np.random.seed(42)
    dates = pd.date_range("2024-01-01", periods=n)
    close = 100 + np.cumsum(np.random.randn(n) * 2)
    high = close + np.abs(np.random.randn(n)) * 2
    low = close - np.abs(np.random.randn(n)) * 2
    open_ = close + np.random.randn(n)
    volume = np.random.randint(1000000, 10000000, n).astype(float)

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


def create_vcp_pattern_df() -> pd.DataFrame:
    """
    Create a DataFrame with a clear VCP pattern.

    VCP characteristics:
    - Initial uptrend
    - Series of contractions with decreasing depth
    - Decreasing volume during consolidation
    """
    n = 120
    dates = pd.date_range("2024-01-01", periods=n)

    # Phase 1: Initial uptrend (days 0-30)
    uptrend = np.linspace(50, 100, 30)

    # Phase 2: First contraction - 20% pullback (days 30-50)
    contraction1_high = 100
    contraction1_low = 80
    contraction1 = np.concatenate(
        [
            np.linspace(100, 80, 10),  # Down
            np.linspace(80, 95, 10),  # Recovery
        ]
    )

    # Phase 3: Second contraction - 12% pullback (days 50-70)
    contraction2 = np.concatenate(
        [
            np.linspace(95, 84, 10),  # Down
            np.linspace(84, 93, 10),  # Recovery
        ]
    )

    # Phase 4: Third contraction - 6% pullback (days 70-90)
    contraction3 = np.concatenate(
        [
            np.linspace(93, 88, 10),  # Down
            np.linspace(88, 95, 10),  # Recovery
        ]
    )

    # Phase 5: Tight consolidation near pivot (days 90-120)
    consolidation = 95 + np.random.randn(30) * 1.5

    close = np.concatenate(
        [uptrend, contraction1, contraction2, contraction3, consolidation]
    )

    # High/Low with decreasing volatility
    volatility = np.concatenate(
        [
            np.full(30, 3),  # Uptrend volatility
            np.full(20, 4),  # First contraction
            np.full(20, 3),  # Second contraction
            np.full(20, 2),  # Third contraction
            np.full(30, 1),  # Tight consolidation
        ]
    )

    high = close + volatility
    low = close - volatility
    open_ = close + np.random.randn(n) * 0.5

    # Volume decreasing during consolidation
    volume = np.concatenate(
        [
            np.full(30, 5000000),  # Uptrend volume
            np.full(20, 4000000),  # First contraction
            np.full(20, 3000000),  # Second contraction
            np.full(20, 2000000),  # Third contraction
            np.full(30, 1500000),  # Low volume consolidation
        ]
    )

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume.astype(float),
        }
    )


def create_non_vcp_df() -> pd.DataFrame:
    """Create a DataFrame without VCP pattern (random walk)."""
    n = 100
    dates = pd.date_range("2024-01-01", periods=n)
    np.random.seed(123)

    # Random walk with no clear pattern
    close = 100 + np.cumsum(np.random.randn(n) * 3)
    high = close + np.abs(np.random.randn(n)) * 5
    low = close - np.abs(np.random.randn(n)) * 5
    open_ = close + np.random.randn(n)
    volume = np.random.randint(1000000, 10000000, n).astype(float)

    return pd.DataFrame(
        {
            "date": dates,
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        }
    )


class TestContraction:
    """Tests for Contraction dataclass."""

    def test_contraction_creation(self):
        """Test creating a Contraction."""
        c = Contraction(
            start_idx=10,
            end_idx=20,
            high_price=100.0,
            low_price=85.0,
            depth_pct=15.0,
            duration=10,
            avg_volume=5000000.0,
        )
        assert c.start_idx == 10
        assert c.end_idx == 20
        assert c.high_price == 100.0
        assert c.low_price == 85.0
        assert c.depth_pct == 15.0
        assert c.duration == 10
        assert c.avg_volume == 5000000.0


class TestVCPResult:
    """Tests for VCPResult dataclass."""

    def test_default_values(self):
        """Test default VCPResult values."""
        result = VCPResult()
        assert result.is_vcp is False
        assert result.contractions == []
        assert result.contraction_count == 0
        assert result.depth_sequence == []
        assert result.volume_trend == 0.0
        assert result.range_contraction == 0.0
        assert result.pivot_price is None
        assert result.pivot_distance_pct == 0.0
        assert result.score == 0.0
        assert result.signals == []

    def test_to_dict(self):
        """Test VCPResult to_dict method."""
        result = VCPResult(
            is_vcp=True,
            contraction_count=3,
            depth_sequence=[20.0, 12.0, 6.0],
            score=75.0,
        )
        d = result.to_dict()
        assert d["is_vcp"] is True
        assert d["contraction_count"] == 3
        assert d["depth_sequence"] == [20.0, 12.0, 6.0]
        assert d["score"] == 75.0


class TestVCPConfig:
    """Tests for VCPConfig dataclass."""

    def test_default_config(self):
        """Test default VCPConfig values."""
        config = VCPConfig()
        assert config.min_contractions == 2
        assert config.max_contractions == 5
        assert config.min_depth_pct == 3.0
        assert config.max_first_depth_pct == 35.0
        assert config.depth_decrease_ratio == 0.7
        assert config.swing_period == 5
        assert config.min_swing_distance == 3
        assert config.volume_lookback == 20
        assert config.atr_period == 14

    def test_custom_config(self):
        """Test custom VCPConfig values."""
        config = VCPConfig(
            min_contractions=3,
            max_first_depth_pct=25.0,
            depth_decrease_ratio=0.6,
        )
        assert config.min_contractions == 3
        assert config.max_first_depth_pct == 25.0
        assert config.depth_decrease_ratio == 0.6


class TestVCP:
    """Tests for VCP indicator."""

    def test_vcp_initialization(self):
        """Test VCP initialization."""
        vcp = VCP()
        assert vcp.name == "VCP"
        assert vcp.config is not None
        assert isinstance(vcp.config, VCPConfig)

    def test_vcp_with_custom_config(self):
        """Test VCP with custom config."""
        config = VCPConfig(min_contractions=3)
        vcp = VCP(config=config)
        assert vcp.config.min_contractions == 3

    def test_calculate_returns_indicator_result(self):
        """Test calculate returns IndicatorResult."""
        df = create_sample_df()
        vcp = VCP()
        result = vcp.calculate(df)

        assert result.name == "VCP"
        assert isinstance(result.values, VCPResult)
        assert "config" in result.params

    def test_calculate_with_insufficient_data(self):
        """Test VCP with insufficient data."""
        df = create_sample_df(n=30)  # Too short
        vcp = VCP()
        result = vcp.calculate(df)

        vcp_result = result.values
        assert vcp_result.is_vcp is False
        assert "Insufficient data" in vcp_result.signals[0]

    def test_validates_required_columns(self):
        """Test that VCP validates required columns."""
        df = pd.DataFrame({"close": [1, 2, 3]})
        vcp = VCP()

        with pytest.raises(ValueError, match="Missing required columns"):
            vcp.calculate(df)

    def test_vcp_pattern_detection(self):
        """Test VCP detection on pattern data."""
        df = create_vcp_pattern_df()
        vcp = VCP()
        result = vcp.calculate(df)

        vcp_result = result.values
        # Should detect some contractions
        assert vcp_result.contraction_count >= 1
        # Should have signals
        assert len(vcp_result.signals) > 0

    def test_non_vcp_pattern(self):
        """Test that non-VCP data is not detected as VCP."""
        df = create_non_vcp_df()
        vcp = VCP()
        result = vcp.calculate(df)

        vcp_result = result.values
        # Should have low score for random data
        assert vcp_result.score < 80

    def test_find_swing_highs(self):
        """Test swing high detection."""
        df = create_sample_df()
        vcp = VCP()
        high = df["high"]
        swing_highs = vcp._find_swing_highs(high)

        # Should find some swing highs
        assert len(swing_highs) > 0
        # All indices should be valid
        assert all(0 <= idx < len(high) for idx in swing_highs)

    def test_find_swing_lows(self):
        """Test swing low detection."""
        df = create_sample_df()
        vcp = VCP()
        low = df["low"]
        swing_lows = vcp._find_swing_lows(low)

        # Should find some swing lows
        assert len(swing_lows) > 0
        # All indices should be valid
        assert all(0 <= idx < len(low) for idx in swing_lows)

    def test_check_depth_decrease(self):
        """Test depth decrease checking."""
        vcp = VCP()

        # Decreasing depths
        contractions_decreasing = [
            Contraction(0, 10, 100, 80, 20.0, 10, 1000000),
            Contraction(15, 25, 100, 88, 12.0, 10, 900000),
            Contraction(30, 40, 100, 94, 6.0, 10, 800000),
        ]
        assert vcp._check_depth_decrease(contractions_decreasing) is True

        # Non-decreasing depths
        contractions_not_decreasing = [
            Contraction(0, 10, 100, 80, 20.0, 10, 1000000),
            Contraction(15, 25, 100, 75, 25.0, 10, 900000),  # Larger than previous
        ]
        assert vcp._check_depth_decrease(contractions_not_decreasing) is False

    def test_analyze_volume_trend(self):
        """Test volume trend analysis."""
        vcp = VCP()
        df = create_sample_df()
        volume = df["volume"]

        # Decreasing volume contractions
        contractions = [
            Contraction(0, 10, 100, 80, 20.0, 10, 5000000),
            Contraction(15, 25, 100, 88, 12.0, 10, 3000000),
            Contraction(30, 40, 100, 94, 6.0, 10, 1000000),
        ]

        trend = vcp._analyze_volume_trend(volume, contractions)
        # Should be negative (decreasing volume)
        assert trend < 0

    def test_analyze_range_contraction(self):
        """Test range contraction analysis."""
        vcp = VCP()

        # Create data with decreasing range
        n = 60
        high = pd.Series(
            np.concatenate(
                [
                    np.linspace(100, 110, 20),  # Wide range
                    np.linspace(105, 108, 20),  # Medium range
                    np.linspace(106, 107, 20),  # Tight range
                ]
            )
        )
        low = pd.Series(
            np.concatenate(
                [
                    np.linspace(90, 85, 20),  # Wide range
                    np.linspace(95, 97, 20),  # Medium range
                    np.linspace(103, 104, 20),  # Tight range
                ]
            )
        )

        contractions = [
            Contraction(0, 19, 100, 85, 15.0, 20, 1000000),
            Contraction(20, 39, 105, 95, 9.5, 20, 900000),
            Contraction(40, 59, 106, 103, 2.8, 20, 800000),
        ]

        contraction_ratio = vcp._analyze_range_contraction(high, low, contractions)
        # Should show significant contraction
        assert contraction_ratio > 0

    def test_find_pivot_price(self):
        """Test pivot price detection."""
        vcp = VCP()

        high = pd.Series([100, 105, 102, 98, 103, 101])

        contractions = [
            Contraction(0, 3, 105.0, 98.0, 6.7, 3, 1000000),
            Contraction(4, 5, 103.0, 101.0, 1.9, 1, 900000),
        ]

        pivot = vcp._find_pivot_price(high, contractions)
        assert pivot == 105.0  # Highest contraction starting price

    def test_score_calculation(self):
        """Test VCP score calculation."""
        vcp = VCP()

        result = VCPResult(
            contraction_count=3,
            depth_sequence=[20.0, 12.0, 6.0],
            volume_trend=-0.5,
            range_contraction=0.6,
            pivot_price=100.0,
            pivot_distance_pct=2.0,
        )

        score = vcp._calculate_score(result, depth_decreasing=True)
        # Good VCP should have high score
        assert score > 50

    def test_case_insensitive_columns(self):
        """Test that column names are case insensitive."""
        df = create_sample_df()
        df.columns = [c.upper() for c in df.columns]

        vcp = VCP()
        result = vcp.calculate(df)
        # Should not raise error
        assert isinstance(result.values, VCPResult)


class TestVCPScanner:
    """Tests for VCPScanner."""

    def test_scanner_initialization(self):
        """Test VCPScanner initialization."""
        scanner = VCPScanner()
        assert scanner.name == "VCPScanner"
        assert scanner.min_score == 60.0

    def test_scanner_with_custom_min_score(self):
        """Test scanner with custom min score."""
        scanner = VCPScanner(min_score=75.0)
        assert scanner.min_score == 75.0

    def test_scan_method(self):
        """Test scan method."""
        df = create_sample_df()
        scanner = VCPScanner(min_score=50.0)
        result = scanner.scan(df)

        assert isinstance(result, VCPResult)

    def test_scan_applies_min_score_filter(self):
        """Test that scan applies minimum score filter."""
        df = create_non_vcp_df()
        scanner = VCPScanner(min_score=95.0)  # Very high threshold
        result = scanner.scan(df)

        # Should not be detected as VCP due to high threshold
        if result.score < 95.0:
            assert result.is_vcp is False

    def test_calculate_method(self):
        """Test calculate method returns IndicatorResult."""
        df = create_sample_df()
        scanner = VCPScanner()
        result = scanner.calculate(df)

        assert result.name == "VCPScanner"
        assert isinstance(result.values, VCPResult)


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_detect_vcp(self):
        """Test detect_vcp function."""
        df = create_sample_df()
        result = detect_vcp(df)

        assert isinstance(result, VCPResult)
        assert isinstance(result.score, float)

    def test_detect_vcp_with_config(self):
        """Test detect_vcp with custom config."""
        df = create_sample_df()
        config = VCPConfig(min_contractions=3)
        result = detect_vcp(df, config=config)

        assert isinstance(result, VCPResult)

    def test_scan_vcp(self):
        """Test scan_vcp function."""
        df = create_sample_df()
        result = scan_vcp(df, min_score=50.0)

        assert isinstance(result, VCPResult)

    def test_scan_vcp_with_high_threshold(self):
        """Test scan_vcp with high threshold."""
        df = create_non_vcp_df()
        result = scan_vcp(df, min_score=99.0)

        # Random data should not pass high threshold
        if result.score < 99.0:
            assert result.is_vcp is False


class TestVCPEdgeCases:
    """Tests for VCP edge cases."""

    def test_empty_dataframe(self):
        """Test with empty DataFrame."""
        df = pd.DataFrame(columns=["high", "low", "close", "volume"])
        vcp = VCP()
        result = vcp.calculate(df)

        assert result.values.is_vcp is False

    def test_single_row(self):
        """Test with single row DataFrame."""
        df = pd.DataFrame(
            {
                "high": [100],
                "low": [95],
                "close": [98],
                "volume": [1000000],
            }
        )
        vcp = VCP()
        result = vcp.calculate(df)

        assert result.values.is_vcp is False

    def test_constant_prices(self):
        """Test with constant prices (no volatility)."""
        n = 100
        df = pd.DataFrame(
            {
                "high": [100.0] * n,
                "low": [100.0] * n,
                "close": [100.0] * n,
                "volume": [1000000.0] * n,
            }
        )
        vcp = VCP()
        result = vcp.calculate(df)

        # No swings with constant prices
        assert result.values.contraction_count == 0

    def test_monotonic_uptrend(self):
        """Test with monotonic uptrend (no contractions)."""
        n = 100
        close = np.linspace(50, 150, n)
        df = pd.DataFrame(
            {
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": np.full(n, 1000000.0),
            }
        )
        vcp = VCP()
        result = vcp.calculate(df)

        # Strong uptrend should have few/no contractions
        assert result.values.is_vcp is False or result.values.score < 50

    def test_monotonic_downtrend(self):
        """Test with monotonic downtrend."""
        n = 100
        close = np.linspace(150, 50, n)
        df = pd.DataFrame(
            {
                "high": close + 1,
                "low": close - 1,
                "close": close,
                "volume": np.full(n, 1000000.0),
            }
        )
        vcp = VCP()
        result = vcp.calculate(df)

        # Downtrend is not VCP
        assert result.values.is_vcp is False

    def test_high_volatility(self):
        """Test with very high volatility data."""
        n = 100
        np.random.seed(456)
        close = 100 + np.cumsum(np.random.randn(n) * 10)  # High volatility
        df = pd.DataFrame(
            {
                "high": close + np.abs(np.random.randn(n)) * 10,
                "low": close - np.abs(np.random.randn(n)) * 10,
                "close": close,
                "volume": np.random.randint(1000000, 10000000, n).astype(float),
            }
        )
        vcp = VCP()
        result = vcp.calculate(df)

        # Should process without error
        assert isinstance(result.values, VCPResult)

    def test_with_nan_values(self):
        """Test handling of NaN values."""
        df = create_sample_df()
        df.loc[50, "close"] = np.nan

        vcp = VCP()
        # May raise or handle gracefully depending on implementation
        try:
            result = vcp.calculate(df)
            assert isinstance(result.values, VCPResult)
        except (ValueError, TypeError):
            pass  # Also acceptable

    def test_zero_volume(self):
        """Test with zero volume periods."""
        df = create_sample_df()
        df.loc[40:50, "volume"] = 0

        vcp = VCP()
        result = vcp.calculate(df)
        # Should handle zero volume
        assert isinstance(result.values, VCPResult)


class TestVCPSignals:
    """Tests for VCP signal generation."""

    def test_signals_for_vcp_pattern(self):
        """Test signals generated for VCP pattern."""
        df = create_vcp_pattern_df()
        result = detect_vcp(df)

        # Should have some signals
        assert len(result.signals) > 0

    def test_signals_contain_contraction_info(self):
        """Test that signals mention contractions."""
        df = create_vcp_pattern_df()
        result = detect_vcp(df)

        # Check if contractions are mentioned
        signals_text = " ".join(result.signals)
        # Either mentions VCP or contractions
        assert "contraction" in signals_text.lower() or "VCP" in signals_text

    def test_score_quality_signals(self):
        """Test score quality signals."""
        df = create_vcp_pattern_df()
        result = detect_vcp(df)

        if result.is_vcp:
            signals_text = " ".join(result.signals)
            # Should have quality indicator
            assert any(
                word in signals_text.lower()
                for word in ["strong", "moderate", "weak", "setup"]
            )


class TestVCPIntegration:
    """Integration tests for VCP module."""

    def test_imports_from_analysis(self):
        """Test imports from analysis module."""
        from analysis import VCP, VCPScanner, detect_vcp, scan_vcp

        assert VCP is not None
        assert VCPScanner is not None
        assert detect_vcp is not None
        assert scan_vcp is not None

    def test_imports_from_indicators(self):
        """Test imports from indicators submodule."""
        from analysis.indicators import (
            VCP,
            Contraction,
            VCPConfig,
            VCPResult,
            VCPScanner,
            detect_vcp,
            scan_vcp,
        )

        assert VCP is not None
        assert VCPScanner is not None
        assert VCPConfig is not None
        assert VCPResult is not None
        assert Contraction is not None
        assert detect_vcp is not None
        assert scan_vcp is not None

    def test_full_workflow(self):
        """Test complete VCP analysis workflow."""
        # Create data
        df = create_vcp_pattern_df()

        # Method 1: Using convenience function
        result1 = detect_vcp(df)
        assert isinstance(result1, VCPResult)

        # Method 2: Using VCP class
        vcp = VCP()
        indicator_result = vcp.calculate(df)
        result2 = indicator_result.values
        assert isinstance(result2, VCPResult)

        # Method 3: Using scanner
        scanner = VCPScanner(min_score=50)
        result3 = scanner.scan(df)
        assert isinstance(result3, VCPResult)

        # All methods should give consistent results
        assert result1.contraction_count == result2.contraction_count
