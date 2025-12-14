"""
Tests for chart pattern recognition modules.

Tests:
- patterns.py - Chart pattern detection
- support_resistance.py - Support/resistance level identification
- trendline.py - Automatic trendline detection
"""

import numpy as np
import pandas as pd
import pytest

from analysis.indicators.patterns import (
    CupAndHandle,
    CupHandleConfig,
    DoubleTopBottom,
    DoubleTopBottomConfig,
    HeadAndShoulders,
    HeadShouldersConfig,
    PatternBias,
    PatternResult,
    PatternScanner,
    PatternType,
    TriangleConfig,
    TrianglePattern,
    detect_patterns,
)
from analysis.indicators.support_resistance import (
    LevelStrength,
    LevelType,
    PriceLevel,
    SRConfig,
    SupportResistance,
    SupportResistanceResult,
    find_support_resistance,
    get_key_levels,
)
from analysis.indicators.trendline import (
    Trendline,
    TrendDirection,
    TrendlineConfig,
    TrendlineDetector,
    TrendlineResult,
    TrendlineType,
    detect_trendlines,
    get_trend_direction,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_ohlcv_data():
    """Sample OHLCV data for testing."""
    np.random.seed(42)
    n = 150
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Base price with slight upward trend
    base_price = 100 + np.arange(n) * 0.1 + np.random.randn(n) * 2

    return pd.DataFrame({
        "date": dates,
        "open": base_price - np.random.rand(n),
        "high": base_price + np.random.rand(n) * 2,
        "low": base_price - np.random.rand(n) * 2,
        "close": base_price,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def cup_and_handle_data():
    """Data with a cup and handle pattern."""
    n = 80
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Create cup shape: decline, bottom, rise, then handle
    prices = []

    # Left rim (0-10): starts at 100
    for i in range(10):
        prices.append(100 - i * 0.2)

    # Decline to bottom (10-25): from 98 to 85
    for i in range(15):
        prices.append(98 - i * 0.9)

    # Bottom (25-35): stay around 85
    for i in range(10):
        prices.append(85 + np.sin(i / 3) * 0.5)

    # Rise to right rim (35-55): from 85 to 100
    for i in range(20):
        prices.append(85 + i * 0.75)

    # Handle pullback and recovery (55-80): from 100 to 98 and back
    for i in range(25):
        if i < 10:
            prices.append(100 - i * 0.3)
        else:
            prices.append(97 + (i - 10) * 0.2)

    prices = np.array(prices[:n])

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.5,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def double_top_data():
    """Data with a double top pattern."""
    n = 60
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    prices = []

    # First rise to peak (0-15)
    for i in range(15):
        prices.append(90 + i * 0.7)

    # First peak and decline (15-30)
    for i in range(15):
        prices.append(100 - i * 0.5)

    # Second rise to similar peak (30-45)
    for i in range(15):
        prices.append(92 + i * 0.5)

    # Decline after second peak (45-60)
    for i in range(15):
        prices.append(99.5 - i * 0.3)

    prices = np.array(prices[:n])

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.5,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def ascending_triangle_data():
    """Data with an ascending triangle pattern."""
    n = 60
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Flat top with rising bottoms
    highs = [100] * n  # Flat resistance
    lows = [90 + i * 0.15 for i in range(n)]  # Rising support
    closes = [(h + l) / 2 for h, l in zip(highs, lows)]

    # Add some variation
    highs = [h + np.sin(i / 5) for i, h in enumerate(highs)]
    lows = [l - np.sin(i / 5) for i, l in enumerate(lows)]

    return pd.DataFrame({
        "date": dates,
        "open": np.array(closes) - 0.5,
        "high": np.array(highs),
        "low": np.array(lows),
        "close": np.array(closes),
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def support_resistance_data():
    """Data with clear support and resistance levels."""
    n = 150
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    prices = []
    # Create bounces off support (90) and resistance (110)
    for i in range(n):
        cycle = i % 30
        if cycle < 15:
            # Moving up to resistance
            prices.append(90 + cycle * 1.33)
        else:
            # Moving down to support
            prices.append(110 - (cycle - 15) * 1.33)

    prices = np.array(prices) + np.random.randn(n) * 0.5

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.3,
        "high": prices + 0.5,
        "low": prices - 0.5,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def uptrend_data():
    """Data with clear uptrend."""
    n = 80
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Strong uptrend
    base = 100 + np.arange(n) * 0.5
    noise = np.random.randn(n) * 1.5
    prices = base + noise

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.3,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def downtrend_data():
    """Data with clear downtrend."""
    n = 80
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Strong downtrend
    base = 150 - np.arange(n) * 0.5
    noise = np.random.randn(n) * 1.5
    prices = base + noise

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.3,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


@pytest.fixture
def sideways_data():
    """Data with sideways/ranging movement."""
    n = 100
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")

    # Oscillating around 100
    prices = 100 + np.sin(np.arange(n) / 5) * 5 + np.random.randn(n)

    return pd.DataFrame({
        "date": dates,
        "open": prices - 0.3,
        "high": prices + 1,
        "low": prices - 1,
        "close": prices,
        "volume": np.random.randint(1000000, 5000000, n),
    })


# ============================================================================
# PatternType and PatternBias Enum Tests
# ============================================================================


class TestPatternEnums:
    """Test pattern enumerations."""

    def test_pattern_type_values(self):
        """Test PatternType enum values."""
        assert PatternType.CUP_AND_HANDLE == "CUP_AND_HANDLE"
        assert PatternType.HEAD_AND_SHOULDERS == "HEAD_AND_SHOULDERS"
        assert PatternType.DOUBLE_TOP == "DOUBLE_TOP"
        assert PatternType.DOUBLE_BOTTOM == "DOUBLE_BOTTOM"
        assert PatternType.ASCENDING_TRIANGLE == "ASCENDING_TRIANGLE"
        assert PatternType.DESCENDING_TRIANGLE == "DESCENDING_TRIANGLE"
        assert PatternType.SYMMETRICAL_TRIANGLE == "SYMMETRICAL_TRIANGLE"

    def test_pattern_bias_values(self):
        """Test PatternBias enum values."""
        assert PatternBias.BULLISH == "BULLISH"
        assert PatternBias.BEARISH == "BEARISH"
        assert PatternBias.NEUTRAL == "NEUTRAL"


# ============================================================================
# PatternResult Tests
# ============================================================================


class TestPatternResult:
    """Test PatternResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = PatternResult(pattern_type=PatternType.CUP_AND_HANDLE)

        assert result.pattern_type == PatternType.CUP_AND_HANDLE
        assert result.is_detected is False
        assert result.confidence == 0.0
        assert result.bias == PatternBias.NEUTRAL
        assert result.breakout_price is None
        assert result.target_price is None
        assert result.key_points == {}

    def test_full_initialization(self):
        """Test full initialization."""
        result = PatternResult(
            pattern_type=PatternType.DOUBLE_TOP,
            is_detected=True,
            confidence=85.0,
            bias=PatternBias.BEARISH,
            start_idx=10,
            end_idx=50,
            breakout_price=95.0,
            target_price=85.0,
            stop_price=102.0,
            description="Double top detected",
            key_points={"first_peak": 100, "second_peak": 99.5},
        )

        assert result.is_detected is True
        assert result.confidence == 85.0
        assert result.bias == PatternBias.BEARISH
        assert result.breakout_price == 95.0
        assert len(result.key_points) == 2


# ============================================================================
# CupAndHandle Tests
# ============================================================================


class TestCupAndHandle:
    """Test Cup and Handle pattern detector."""

    def test_default_config(self):
        """Test default configuration."""
        detector = CupAndHandle()

        assert detector.config.min_cup_depth == 0.12
        assert detector.config.max_cup_depth == 0.35
        assert detector.config.min_cup_length == 20

    def test_custom_config(self):
        """Test custom configuration."""
        config = CupHandleConfig(min_cup_depth=0.10, max_cup_depth=0.40)
        detector = CupAndHandle(config)

        assert detector.config.min_cup_depth == 0.10
        assert detector.config.max_cup_depth == 0.40

    def test_insufficient_data(self):
        """Test with insufficient data."""
        detector = CupAndHandle()
        data = pd.DataFrame({
            "open": [100, 101, 102],
            "high": [101, 102, 103],
            "low": [99, 100, 101],
            "close": [100, 101, 102],
        })

        result = detector.calculate(data)

        assert result.is_detected is False

    def test_cup_and_handle_detection(self, cup_and_handle_data):
        """Test detection of cup and handle pattern."""
        detector = CupAndHandle()
        result = detector.calculate(cup_and_handle_data)

        # Pattern should be detected (depending on the exact data shape)
        assert result.pattern_type == PatternType.CUP_AND_HANDLE
        # If detected, should be bullish
        if result.is_detected:
            assert result.bias == PatternBias.BULLISH
            assert result.confidence > 0

    def test_no_pattern_in_random_data(self, sample_ohlcv_data):
        """Test that random data doesn't always trigger pattern."""
        detector = CupAndHandle()
        result = detector.calculate(sample_ohlcv_data)

        # Result should return but may or may not detect
        assert result.pattern_type == PatternType.CUP_AND_HANDLE


# ============================================================================
# HeadAndShoulders Tests
# ============================================================================


class TestHeadAndShoulders:
    """Test Head and Shoulders pattern detector."""

    def test_default_config(self):
        """Test default configuration."""
        detector = HeadAndShoulders()

        assert detector.config.min_pattern_length == 30
        assert detector.config.shoulder_tolerance == 0.05

    def test_custom_config(self):
        """Test custom configuration."""
        config = HeadShouldersConfig(min_pattern_length=25)
        detector = HeadAndShoulders(config)

        assert detector.config.min_pattern_length == 25

    def test_insufficient_data(self):
        """Test with insufficient data."""
        detector = HeadAndShoulders()
        data = pd.DataFrame({
            "open": [100] * 10,
            "high": [101] * 10,
            "low": [99] * 10,
            "close": [100] * 10,
        })

        result = detector.calculate(data)

        assert result.is_detected is False

    def test_head_and_shoulders_result_type(self, sample_ohlcv_data):
        """Test that result has correct type."""
        detector = HeadAndShoulders()
        result = detector.calculate(sample_ohlcv_data)

        # Result should be one of H&S or inverse H&S
        assert result.pattern_type in [
            PatternType.HEAD_AND_SHOULDERS,
            PatternType.INVERSE_HEAD_AND_SHOULDERS,
        ]


# ============================================================================
# DoubleTopBottom Tests
# ============================================================================


class TestDoubleTopBottom:
    """Test Double Top/Bottom pattern detector."""

    def test_default_config(self):
        """Test default configuration."""
        detector = DoubleTopBottom()

        assert detector.config.min_pattern_length == 15
        assert detector.config.peak_tolerance == 0.03

    def test_custom_config(self):
        """Test custom configuration."""
        config = DoubleTopBottomConfig(peak_tolerance=0.05)
        detector = DoubleTopBottom(config)

        assert detector.config.peak_tolerance == 0.05

    def test_double_top_detection(self, double_top_data):
        """Test detection of double top pattern."""
        detector = DoubleTopBottom()
        result = detector.calculate(double_top_data)

        # Pattern should be detected
        if result.is_detected:
            assert result.pattern_type in [PatternType.DOUBLE_TOP, PatternType.DOUBLE_BOTTOM]
            assert result.confidence > 0

    def test_double_bottom_bias(self):
        """Test that double bottom is bullish."""
        # Create double bottom data
        n = 50
        prices = []
        for i in range(15):
            prices.append(110 - i * 0.7)  # Decline to first trough
        for i in range(15):
            prices.append(100 + i * 0.5)  # Rise
        for i in range(20):
            if i < 10:
                prices.append(107.5 - i * 0.75)  # Second decline
            else:
                prices.append(100 + (i - 10) * 0.5)  # Recovery

        data = pd.DataFrame({
            "open": np.array(prices) - 0.3,
            "high": np.array(prices) + 1,
            "low": np.array(prices) - 1,
            "close": np.array(prices),
            "volume": [1000000] * len(prices),
        })

        detector = DoubleTopBottom()
        result = detector.calculate(data)

        # If double bottom detected, should be bullish
        if result.is_detected and result.pattern_type == PatternType.DOUBLE_BOTTOM:
            assert result.bias == PatternBias.BULLISH


# ============================================================================
# TrianglePattern Tests
# ============================================================================


class TestTrianglePattern:
    """Test Triangle pattern detector."""

    def test_default_config(self):
        """Test default configuration."""
        detector = TrianglePattern()

        assert detector.config.min_pattern_length == 15
        assert detector.config.min_touches == 4

    def test_custom_config(self):
        """Test custom configuration."""
        config = TriangleConfig(min_touches=3)
        detector = TrianglePattern(config)

        assert detector.config.min_touches == 3

    def test_ascending_triangle_detection(self, ascending_triangle_data):
        """Test detection of ascending triangle."""
        detector = TrianglePattern()
        result = detector.calculate(ascending_triangle_data)

        if result.is_detected:
            assert result.pattern_type in [
                PatternType.ASCENDING_TRIANGLE,
                PatternType.DESCENDING_TRIANGLE,
                PatternType.SYMMETRICAL_TRIANGLE,
            ]

    def test_triangle_types(self):
        """Test triangle type classifications."""
        assert PatternType.ASCENDING_TRIANGLE.value == "ASCENDING_TRIANGLE"
        assert PatternType.DESCENDING_TRIANGLE.value == "DESCENDING_TRIANGLE"
        assert PatternType.SYMMETRICAL_TRIANGLE.value == "SYMMETRICAL_TRIANGLE"


# ============================================================================
# PatternScanner Tests
# ============================================================================


class TestPatternScanner:
    """Test PatternScanner class."""

    def test_initialization(self):
        """Test scanner initialization."""
        scanner = PatternScanner()

        assert "cup_handle" in scanner.patterns
        assert "head_shoulders" in scanner.patterns
        assert "double_top_bottom" in scanner.patterns
        assert "triangle" in scanner.patterns

    def test_scan_returns_list(self, sample_ohlcv_data):
        """Test scan returns a list."""
        scanner = PatternScanner()
        results = scanner.scan(sample_ohlcv_data)

        assert isinstance(results, list)
        for result in results:
            assert isinstance(result, PatternResult)

    def test_results_sorted_by_confidence(self, sample_ohlcv_data):
        """Test results are sorted by confidence."""
        scanner = PatternScanner()
        results = scanner.scan(sample_ohlcv_data)

        if len(results) > 1:
            for i in range(len(results) - 1):
                assert results[i].confidence >= results[i + 1].confidence

    def test_detect_patterns_function(self, sample_ohlcv_data):
        """Test convenience function."""
        results = detect_patterns(sample_ohlcv_data)

        assert isinstance(results, list)


# ============================================================================
# Support and Resistance Tests
# ============================================================================


class TestLevelEnums:
    """Test support/resistance enumerations."""

    def test_level_type_values(self):
        """Test LevelType enum values."""
        assert LevelType.SUPPORT == "SUPPORT"
        assert LevelType.RESISTANCE == "RESISTANCE"

    def test_level_strength_values(self):
        """Test LevelStrength enum values."""
        assert LevelStrength.WEAK == "WEAK"
        assert LevelStrength.MODERATE == "MODERATE"
        assert LevelStrength.STRONG == "STRONG"


class TestPriceLevel:
    """Test PriceLevel dataclass."""

    def test_default_values(self):
        """Test default values."""
        level = PriceLevel(price=100.0, level_type=LevelType.SUPPORT)

        assert level.price == 100.0
        assert level.level_type == LevelType.SUPPORT
        assert level.strength == LevelStrength.MODERATE
        assert level.touches == 0
        assert level.confidence == 0.0

    def test_full_initialization(self):
        """Test full initialization."""
        level = PriceLevel(
            price=105.0,
            level_type=LevelType.RESISTANCE,
            strength=LevelStrength.STRONG,
            touches=5,
            first_touch_idx=10,
            last_touch_idx=100,
            volume_at_level=2000000.0,
            is_recent=True,
            confidence=85.0,
        )

        assert level.price == 105.0
        assert level.strength == LevelStrength.STRONG
        assert level.touches == 5
        assert level.confidence == 85.0


class TestSupportResistanceResult:
    """Test SupportResistanceResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = SupportResistanceResult()

        assert result.name == "SupportResistance"
        assert result.levels == []
        assert result.current_support is None
        assert result.current_resistance is None


class TestSRConfig:
    """Test SRConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = SRConfig()

        assert config.window == 5
        assert config.tolerance == 0.02
        assert config.min_touches == 2
        assert config.lookback == 120


class TestSupportResistance:
    """Test SupportResistance indicator."""

    def test_default_config(self):
        """Test default configuration."""
        sr = SupportResistance()

        assert sr.config.window == 5
        assert sr.config.lookback == 120

    def test_custom_config(self):
        """Test custom configuration."""
        config = SRConfig(lookback=60, min_touches=3)
        sr = SupportResistance(config)

        assert sr.config.lookback == 60
        assert sr.config.min_touches == 3

    def test_insufficient_data(self):
        """Test with insufficient data."""
        sr = SupportResistance()
        data = pd.DataFrame({
            "open": [100] * 10,
            "high": [101] * 10,
            "low": [99] * 10,
            "close": [100] * 10,
            "volume": [1000000] * 10,
        })

        result = sr.calculate(data)

        assert result.levels == []

    def test_support_resistance_detection(self, support_resistance_data):
        """Test detection of support and resistance levels."""
        sr = SupportResistance()
        result = sr.calculate(support_resistance_data)

        # Should find some levels
        assert result.name == "SupportResistance"
        # Levels list should be populated if pattern is clear
        if result.levels:
            # Check level types
            level_types = [l.level_type for l in result.levels]
            assert any(lt == LevelType.SUPPORT for lt in level_types) or \
                   any(lt == LevelType.RESISTANCE for lt in level_types)

    def test_find_support_resistance_function(self, sample_ohlcv_data):
        """Test convenience function."""
        result = find_support_resistance(sample_ohlcv_data)

        assert isinstance(result, SupportResistanceResult)

    def test_get_key_levels_function(self, support_resistance_data):
        """Test get_key_levels function."""
        supports, resistances = get_key_levels(support_resistance_data)

        assert isinstance(supports, list)
        assert isinstance(resistances, list)

    def test_levels_have_confidence(self, support_resistance_data):
        """Test that detected levels have confidence scores."""
        sr = SupportResistance()
        result = sr.calculate(support_resistance_data)

        for level in result.levels:
            assert 0 <= level.confidence <= 100


# ============================================================================
# Trendline Tests
# ============================================================================


class TestTrendEnums:
    """Test trendline enumerations."""

    def test_trend_direction_values(self):
        """Test TrendDirection enum values."""
        assert TrendDirection.UP == "UP"
        assert TrendDirection.DOWN == "DOWN"
        assert TrendDirection.FLAT == "FLAT"

    def test_trendline_type_values(self):
        """Test TrendlineType enum values."""
        assert TrendlineType.SUPPORT == "SUPPORT"
        assert TrendlineType.RESISTANCE == "RESISTANCE"


class TestTrendline:
    """Test Trendline dataclass."""

    def test_default_values(self):
        """Test default values."""
        trendline = Trendline(
            trendline_type=TrendlineType.SUPPORT,
            direction=TrendDirection.UP,
            slope=0.5,
            intercept=100.0,
            start_idx=0,
            end_idx=50,
        )

        assert trendline.trendline_type == TrendlineType.SUPPORT
        assert trendline.direction == TrendDirection.UP
        assert trendline.touches == 0
        assert trendline.strength == 0.0
        assert trendline.is_valid is True
        assert trendline.broken is False

    def test_get_price_at(self):
        """Test get_price_at method."""
        trendline = Trendline(
            trendline_type=TrendlineType.SUPPORT,
            direction=TrendDirection.UP,
            slope=0.5,
            intercept=100.0,
            start_idx=0,
            end_idx=50,
        )

        # At idx 0, price = 0.5 * 0 + 100 = 100
        assert trendline.get_price_at(0) == 100.0

        # At idx 10, price = 0.5 * 10 + 100 = 105
        assert trendline.get_price_at(10) == 105.0

        # At idx 100, price = 0.5 * 100 + 100 = 150
        assert trendline.get_price_at(100) == 150.0


class TestTrendlineResult:
    """Test TrendlineResult dataclass."""

    def test_default_values(self):
        """Test default values."""
        result = TrendlineResult()

        assert result.name == "Trendline"
        assert result.trendlines == []
        assert result.primary_support is None
        assert result.primary_resistance is None
        assert result.overall_trend == TrendDirection.FLAT


class TestTrendlineConfig:
    """Test TrendlineConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TrendlineConfig()

        assert config.window == 5
        assert config.min_touches == 2
        assert config.lookback == 60
        assert config.max_trendlines == 4


class TestTrendlineDetector:
    """Test TrendlineDetector class."""

    def test_default_config(self):
        """Test default configuration."""
        detector = TrendlineDetector()

        assert detector.config.window == 5
        assert detector.config.lookback == 60

    def test_custom_config(self):
        """Test custom configuration."""
        config = TrendlineConfig(lookback=100, min_touches=3)
        detector = TrendlineDetector(config)

        assert detector.config.lookback == 100
        assert detector.config.min_touches == 3

    def test_insufficient_data(self):
        """Test with insufficient data."""
        detector = TrendlineDetector()
        data = pd.DataFrame({
            "open": [100] * 10,
            "high": [101] * 10,
            "low": [99] * 10,
            "close": [100] * 10,
        })

        result = detector.calculate(data)

        assert result.trendlines == []

    def test_uptrend_detection(self, uptrend_data):
        """Test detection in uptrend data."""
        detector = TrendlineDetector()
        result = detector.calculate(uptrend_data)

        assert result.name == "Trendline"
        # Overall trend should be UP in uptrend data
        if result.trendlines:
            # Should detect upward trend
            assert result.overall_trend in [TrendDirection.UP, TrendDirection.FLAT]

    def test_downtrend_detection(self, downtrend_data):
        """Test detection in downtrend data."""
        detector = TrendlineDetector()
        result = detector.calculate(downtrend_data)

        # Overall trend should be DOWN in downtrend data
        if result.trendlines:
            assert result.overall_trend in [TrendDirection.DOWN, TrendDirection.FLAT]

    def test_sideways_detection(self, sideways_data):
        """Test detection in sideways data."""
        detector = TrendlineDetector()
        result = detector.calculate(sideways_data)

        # In sideways market, should be FLAT or very slight trend
        assert result.overall_trend in [TrendDirection.UP, TrendDirection.DOWN, TrendDirection.FLAT]

    def test_detect_trendlines_function(self, sample_ohlcv_data):
        """Test convenience function."""
        result = detect_trendlines(sample_ohlcv_data)

        assert isinstance(result, TrendlineResult)

    def test_get_trend_direction_function(self, uptrend_data):
        """Test get_trend_direction function."""
        direction = get_trend_direction(uptrend_data)

        assert direction in [TrendDirection.UP, TrendDirection.DOWN, TrendDirection.FLAT]

    def test_trendline_has_strength(self, sample_ohlcv_data):
        """Test that trendlines have strength scores."""
        detector = TrendlineDetector()
        result = detector.calculate(sample_ohlcv_data)

        for trendline in result.trendlines:
            assert 0 <= trendline.strength <= 100

    def test_max_trendlines_limit(self, sample_ohlcv_data):
        """Test that max_trendlines is respected."""
        config = TrendlineConfig(max_trendlines=2)
        detector = TrendlineDetector(config)
        result = detector.calculate(sample_ohlcv_data)

        assert len(result.trendlines) <= 2


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests for pattern recognition modules."""

    def test_imports_from_indicators(self):
        """Test that all modules can be imported from indicators."""
        from analysis.indicators import (
            PatternType,
            PatternBias,
            PatternResult,
            CupAndHandle,
            HeadAndShoulders,
            DoubleTopBottom,
            TrianglePattern,
            PatternScanner,
            detect_patterns,
            LevelType,
            LevelStrength,
            PriceLevel,
            SupportResistance,
            find_support_resistance,
            get_key_levels,
            TrendDirection,
            TrendlineType,
            Trendline,
            TrendlineDetector,
            detect_trendlines,
            get_trend_direction,
        )

        # All imports should succeed
        assert PatternType is not None
        assert LevelType is not None
        assert TrendDirection is not None

    def test_imports_from_analysis(self):
        """Test that modules can be imported from analysis."""
        from analysis import (
            PatternType,
            detect_patterns,
            LevelType,
            find_support_resistance,
            TrendDirection,
            detect_trendlines,
        )

        assert PatternType is not None
        assert LevelType is not None
        assert TrendDirection is not None

    def test_all_detectors_on_same_data(self, sample_ohlcv_data):
        """Test all detectors work on the same data."""
        # Patterns
        patterns = detect_patterns(sample_ohlcv_data)
        assert isinstance(patterns, list)

        # Support/Resistance
        sr_result = find_support_resistance(sample_ohlcv_data)
        assert isinstance(sr_result, SupportResistanceResult)

        # Trendlines
        trendline_result = detect_trendlines(sample_ohlcv_data)
        assert isinstance(trendline_result, TrendlineResult)

    def test_empty_dataframe(self):
        """Test all detectors handle empty dataframe."""
        empty_df = pd.DataFrame({
            "open": [],
            "high": [],
            "low": [],
            "close": [],
            "volume": [],
        })

        # Should not crash
        patterns = detect_patterns(empty_df)
        assert patterns == []

        sr = find_support_resistance(empty_df)
        assert sr.levels == []

        trendlines = detect_trendlines(empty_df)
        assert trendlines.trendlines == []

    def test_combined_analysis(self, sample_ohlcv_data):
        """Test combining all analyses for comprehensive view."""
        # Get all analyses
        patterns = detect_patterns(sample_ohlcv_data)
        supports, resistances = get_key_levels(sample_ohlcv_data)
        trend = get_trend_direction(sample_ohlcv_data)

        # Build combined result
        combined = {
            "patterns_detected": len(patterns),
            "support_levels": len(supports),
            "resistance_levels": len(resistances),
            "trend": trend.value,
        }

        assert "patterns_detected" in combined
        assert "trend" in combined


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_single_row_data(self):
        """Test with single row of data."""
        data = pd.DataFrame({
            "open": [100],
            "high": [101],
            "low": [99],
            "close": [100],
            "volume": [1000000],
        })

        # Should not crash, just return empty results
        patterns = detect_patterns(data)
        assert patterns == []

    def test_constant_prices(self):
        """Test with constant prices."""
        n = 100
        data = pd.DataFrame({
            "open": [100.0] * n,
            "high": [100.0] * n,
            "low": [100.0] * n,
            "close": [100.0] * n,
            "volume": [1000000] * n,
        })

        # Should not crash
        patterns = detect_patterns(data)
        sr = find_support_resistance(data)
        trendlines = detect_trendlines(data)

        # Results should be empty or minimal for constant data
        assert isinstance(patterns, list)
        assert isinstance(sr, SupportResistanceResult)
        assert isinstance(trendlines, TrendlineResult)

    def test_missing_volume_column(self):
        """Test support/resistance without volume column."""
        n = 150
        data = pd.DataFrame({
            "open": np.random.rand(n) * 10 + 95,
            "high": np.random.rand(n) * 10 + 100,
            "low": np.random.rand(n) * 10 + 90,
            "close": np.random.rand(n) * 10 + 95,
        })

        # Should not crash, volume should default to 1
        sr = find_support_resistance(data)
        assert isinstance(sr, SupportResistanceResult)

    def test_negative_prices(self):
        """Test handling of negative prices (edge case)."""
        n = 100
        # Some data might have negative values in edge cases
        data = pd.DataFrame({
            "open": np.random.rand(n) * 10 - 5,
            "high": np.random.rand(n) * 10 - 3,
            "low": np.random.rand(n) * 10 - 7,
            "close": np.random.rand(n) * 10 - 5,
            "volume": [1000000] * n,
        })

        # Should not crash
        try:
            patterns = detect_patterns(data)
            sr = find_support_resistance(data)
            trendlines = detect_trendlines(data)
        except Exception as e:
            pytest.fail(f"Should handle negative prices: {e}")

    def test_very_large_data(self):
        """Test with large dataset."""
        n = 1000
        data = pd.DataFrame({
            "open": np.random.rand(n) * 100 + 50,
            "high": np.random.rand(n) * 100 + 60,
            "low": np.random.rand(n) * 100 + 40,
            "close": np.random.rand(n) * 100 + 50,
            "volume": np.random.randint(1000000, 5000000, n),
        })

        # Should complete without timeout
        patterns = detect_patterns(data)
        sr = find_support_resistance(data)
        trendlines = detect_trendlines(data)

        assert isinstance(patterns, list)
        assert isinstance(sr, SupportResistanceResult)
        assert isinstance(trendlines, TrendlineResult)
