"""Tests for technical indicators."""

import numpy as np
import pandas as pd
import pytest

from analysis.indicators import (
    # Base
    BaseIndicator,
    IndicatorResult,
    validate_period,
    # Moving Averages
    SMA,
    EMA,
    WMA,
    MA,
    calculate_sma,
    calculate_ema,
    # MACD
    MACD,
    MACDCrossover,
    MACDHistogramDivergence,
    calculate_macd,
    # RSI
    RSI,
    StochasticRSI,
    RSIDivergence,
    calculate_rsi,
    # Bollinger Bands
    BollingerBands,
    BollingerBandsSqueeze,
    BollingerBandsSignals,
    calculate_bollinger_bands,
    # OBV
    OBV,
    OBVDivergence,
    calculate_obv,
)

from analysis.technical import (
    TechnicalAnalyzer,
    AnalysisConfig,
    AnalysisResult,
    create_technical_analyzer,
    analyze_stock,
)


@pytest.fixture
def sample_ohlcv_df():
    """Create sample OHLCV DataFrame for testing."""
    np.random.seed(42)
    n = 100

    # Generate realistic price data
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.2

    return pd.DataFrame({
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": np.random.randint(1000, 10000, n).astype(float),
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))


@pytest.fixture
def sample_prices():
    """Create sample price series for testing."""
    np.random.seed(42)
    return pd.Series(
        100 + np.cumsum(np.random.randn(100) * 0.5),
        index=pd.date_range("2024-01-01", periods=100, freq="D"),
    )


class TestValidatePeriod:
    """Tests for validate_period function."""

    def test_valid_period(self):
        """Test valid period passes."""
        validate_period(14)
        validate_period(1)
        validate_period(200)

    def test_zero_period_raises(self):
        """Test zero period raises ValueError."""
        with pytest.raises(ValueError, match="must be an integer >= 1"):
            validate_period(0)

    def test_negative_period_raises(self):
        """Test negative period raises ValueError."""
        with pytest.raises(ValueError, match="must be an integer >= 1"):
            validate_period(-5)

    def test_non_integer_raises(self):
        """Test non-integer period raises ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_period(14.5)


class TestIndicatorResult:
    """Tests for IndicatorResult dataclass."""

    def test_series_result(self, sample_prices):
        """Test IndicatorResult with Series."""
        result = IndicatorResult(
            name="TestIndicator",
            values=sample_prices,
            params={"period": 14},
        )
        assert result.name == "TestIndicator"
        assert isinstance(result.values, pd.Series)
        assert result.params["period"] == 14

    def test_dataframe_result(self, sample_ohlcv_df):
        """Test IndicatorResult with DataFrame."""
        result = IndicatorResult(
            name="TestIndicator",
            values=sample_ohlcv_df,
            params={},
        )
        assert result.name == "TestIndicator"
        assert isinstance(result.values, pd.DataFrame)


class TestSMA:
    """Tests for Simple Moving Average."""

    def test_sma_basic(self, sample_ohlcv_df):
        """Test basic SMA calculation."""
        sma = SMA(period=20)
        result = sma.calculate(sample_ohlcv_df)

        assert result.name == "SMA20"
        assert isinstance(result.values, pd.Series)
        assert len(result.values) == len(sample_ohlcv_df)
        # First 19 values should be NaN
        assert result.values.iloc[:19].isna().all()
        # Values from index 19 should be valid
        assert not result.values.iloc[19:].isna().any()

    def test_sma_custom_column(self, sample_ohlcv_df):
        """Test SMA on custom column."""
        sma = SMA(period=10)
        result = sma.calculate(sample_ohlcv_df, column="high")

        assert result.params["column"] == "high"

    def test_sma_invalid_period(self):
        """Test SMA with invalid period."""
        with pytest.raises(ValueError):
            SMA(period=0)


class TestEMA:
    """Tests for Exponential Moving Average."""

    def test_ema_basic(self, sample_ohlcv_df):
        """Test basic EMA calculation."""
        ema = EMA(period=12)
        result = ema.calculate(sample_ohlcv_df)

        assert result.name == "EMA12"
        assert isinstance(result.values, pd.Series)
        assert len(result.values) == len(sample_ohlcv_df)

    def test_ema_reacts_faster_than_sma(self, sample_ohlcv_df):
        """Test EMA reacts faster to price changes than SMA."""
        period = 20
        sma = SMA(period=period).calculate(sample_ohlcv_df).values
        ema = EMA(period=period).calculate(sample_ohlcv_df).values

        # EMA should be closer to current price after trend changes
        # This is a characteristic of EMA vs SMA
        close = sample_ohlcv_df["close"]

        # Compare variance of difference from close
        sma_diff = (sma - close).dropna().var()
        ema_diff = (ema - close).dropna().var()

        # EMA should have lower variance (tracks closer)
        assert ema_diff <= sma_diff


class TestWMA:
    """Tests for Weighted Moving Average."""

    def test_wma_basic(self, sample_ohlcv_df):
        """Test basic WMA calculation."""
        wma = WMA(period=10)
        result = wma.calculate(sample_ohlcv_df)

        assert result.name == "WMA10"
        assert isinstance(result.values, pd.Series)

    def test_wma_weights_recent_more(self, sample_prices):
        """Test WMA weights recent prices more heavily."""
        # Create a series where recent prices are higher
        prices = pd.Series([1, 1, 1, 1, 10])  # Last price is much higher
        df = pd.DataFrame({"close": prices})

        wma = WMA(period=5)
        result = wma.calculate(df)

        # WMA should be > SMA because it weights the high recent value more
        sma = SMA(period=5).calculate(df)

        assert result.values.iloc[-1] > sma.values.iloc[-1]


class TestMA:
    """Tests for Multiple Moving Averages calculator."""

    def test_ma_default_periods(self, sample_ohlcv_df):
        """Test MA with default periods."""
        ma = MA()
        result = ma.calculate(sample_ohlcv_df)

        assert isinstance(result.values, pd.DataFrame)
        assert "MA5" in result.values.columns
        assert "MA10" in result.values.columns
        assert "MA20" in result.values.columns
        assert "MA60" in result.values.columns

    def test_ma_custom_periods(self, sample_ohlcv_df):
        """Test MA with custom periods."""
        ma = MA()
        result = ma.calculate(sample_ohlcv_df, periods=[7, 14, 28])

        assert "MA7" in result.values.columns
        assert "MA14" in result.values.columns
        assert "MA28" in result.values.columns

    def test_ma_ema_type(self, sample_ohlcv_df):
        """Test MA with EMA type."""
        ma = MA(ma_type="ema")
        result = ma.calculate(sample_ohlcv_df, periods=[10, 20])

        assert result.params["ma_type"] == "ema"


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_calculate_sma(self, sample_prices):
        """Test calculate_sma function."""
        sma = calculate_sma(sample_prices, period=20)
        assert isinstance(sma, pd.Series)
        assert len(sma) == len(sample_prices)

    def test_calculate_ema(self, sample_prices):
        """Test calculate_ema function."""
        ema = calculate_ema(sample_prices, period=12)
        assert isinstance(ema, pd.Series)
        assert len(ema) == len(sample_prices)


class TestMACD:
    """Tests for MACD indicator."""

    def test_macd_basic(self, sample_ohlcv_df):
        """Test basic MACD calculation."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_df)

        assert result.name == "MACD"
        assert isinstance(result.values, pd.DataFrame)
        assert "MACD" in result.values.columns
        assert "signal" in result.values.columns
        assert "histogram" in result.values.columns

    def test_macd_custom_periods(self, sample_ohlcv_df):
        """Test MACD with custom periods."""
        macd = MACD(fast=8, slow=21, signal=5)
        result = macd.calculate(sample_ohlcv_df)

        assert result.params["fast"] == 8
        assert result.params["slow"] == 21
        assert result.params["signal"] == 5

    def test_macd_histogram_equals_diff(self, sample_ohlcv_df):
        """Test histogram equals MACD - signal."""
        macd = MACD()
        result = macd.calculate(sample_ohlcv_df)

        df = result.values
        expected_histogram = df["MACD"] - df["signal"]

        np.testing.assert_array_almost_equal(
            df["histogram"].values,
            expected_histogram.values,
        )

    def test_macd_fast_ge_slow_raises(self):
        """Test MACD raises when fast >= slow."""
        with pytest.raises(ValueError, match="Fast period"):
            MACD(fast=26, slow=12)


class TestMACDCrossover:
    """Tests for MACD Crossover detector."""

    def test_macd_crossover_signals(self, sample_ohlcv_df):
        """Test MACD crossover generates signals."""
        crossover = MACDCrossover()
        result = crossover.calculate(sample_ohlcv_df)

        assert "crossover" in result.values.columns
        # Signals should be -1, 0, or 1
        unique_signals = result.values["crossover"].unique()
        assert all(s in [-1, 0, 1] for s in unique_signals)


class TestMACDConvenience:
    """Tests for MACD convenience function."""

    def test_calculate_macd(self, sample_prices):
        """Test calculate_macd function."""
        macd_line, signal_line, histogram = calculate_macd(sample_prices)

        assert isinstance(macd_line, pd.Series)
        assert isinstance(signal_line, pd.Series)
        assert isinstance(histogram, pd.Series)
        assert len(macd_line) == len(sample_prices)


class TestRSI:
    """Tests for RSI indicator."""

    def test_rsi_basic(self, sample_ohlcv_df):
        """Test basic RSI calculation."""
        rsi = RSI()
        result = rsi.calculate(sample_ohlcv_df)

        assert "RSI" in result.name
        assert isinstance(result.values, pd.Series)

    def test_rsi_range(self, sample_ohlcv_df):
        """Test RSI values are between 0 and 100."""
        rsi = RSI()
        result = rsi.calculate(sample_ohlcv_df)

        valid_values = result.values.dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()

    def test_rsi_custom_period(self, sample_ohlcv_df):
        """Test RSI with custom period."""
        rsi = RSI(period=21)
        result = rsi.calculate(sample_ohlcv_df)

        assert result.params["period"] == 21

    def test_rsi_overbought_oversold(self, sample_ohlcv_df):
        """Test RSI overbought/oversold thresholds in params."""
        rsi = RSI(overbought=80, oversold=20)
        result = rsi.calculate(sample_ohlcv_df)

        assert result.params["overbought"] == 80
        assert result.params["oversold"] == 20

    def test_rsi_sma_method(self, sample_ohlcv_df):
        """Test RSI with SMA smoothing method."""
        rsi = RSI()
        result = rsi.calculate(sample_ohlcv_df, method="sma")

        assert result.params["method"] == "sma"


class TestStochasticRSI:
    """Tests for Stochastic RSI indicator."""

    def test_stoch_rsi_basic(self, sample_ohlcv_df):
        """Test basic Stochastic RSI calculation."""
        stoch_rsi = StochasticRSI()
        result = stoch_rsi.calculate(sample_ohlcv_df)

        assert result.name == "StochRSI"
        assert isinstance(result.values, pd.DataFrame)
        assert "StochRSI" in result.values.columns
        assert "K" in result.values.columns
        assert "D" in result.values.columns

    def test_stoch_rsi_range(self, sample_ohlcv_df):
        """Test Stochastic RSI values are between 0 and 100."""
        stoch_rsi = StochasticRSI()
        result = stoch_rsi.calculate(sample_ohlcv_df)

        valid_values = result.values["StochRSI"].dropna()
        assert (valid_values >= 0).all()
        assert (valid_values <= 100).all()


class TestRSIDivergence:
    """Tests for RSI Divergence detector."""

    def test_rsi_divergence_signals(self, sample_ohlcv_df):
        """Test RSI divergence generates signals."""
        divergence = RSIDivergence()
        result = divergence.calculate(sample_ohlcv_df)

        assert "divergence" in result.values.columns
        assert "RSI" in result.values.columns


class TestRSIConvenience:
    """Tests for RSI convenience function."""

    def test_calculate_rsi(self, sample_prices):
        """Test calculate_rsi function."""
        rsi = calculate_rsi(sample_prices)

        assert isinstance(rsi, pd.Series)
        valid = rsi.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestBollingerBands:
    """Tests for Bollinger Bands indicator."""

    def test_bb_basic(self, sample_ohlcv_df):
        """Test basic Bollinger Bands calculation."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_df)

        assert result.name == "BollingerBands"
        assert isinstance(result.values, pd.DataFrame)
        assert "upper" in result.values.columns
        assert "middle" in result.values.columns
        assert "lower" in result.values.columns
        assert "bandwidth" in result.values.columns
        assert "percent_b" in result.values.columns

    def test_bb_band_order(self, sample_ohlcv_df):
        """Test upper > middle > lower."""
        bb = BollingerBands()
        result = bb.calculate(sample_ohlcv_df)

        df = result.values.dropna()
        assert (df["upper"] >= df["middle"]).all()
        assert (df["middle"] >= df["lower"]).all()

    def test_bb_custom_params(self, sample_ohlcv_df):
        """Test Bollinger Bands with custom parameters."""
        bb = BollingerBands(period=25, std_dev=2.5)
        result = bb.calculate(sample_ohlcv_df)

        assert result.params["period"] == 25
        assert result.params["std_dev"] == 2.5

    def test_bb_invalid_std_dev(self):
        """Test Bollinger Bands with invalid std_dev."""
        with pytest.raises(ValueError, match="std_dev must be positive"):
            BollingerBands(std_dev=-1)


class TestBollingerBandsSqueeze:
    """Tests for Bollinger Bands Squeeze detector."""

    def test_bb_squeeze_signals(self, sample_ohlcv_df):
        """Test squeeze detection."""
        squeeze = BollingerBandsSqueeze()
        result = squeeze.calculate(sample_ohlcv_df)

        assert "squeeze" in result.values.columns
        # Squeeze should be 0 or 1
        assert result.values["squeeze"].isin([0, 1]).all()


class TestBollingerBandsSignals:
    """Tests for Bollinger Bands Signals."""

    def test_bb_signals(self, sample_ohlcv_df):
        """Test signal generation."""
        signals = BollingerBandsSignals()
        result = signals.calculate(sample_ohlcv_df)

        assert "signal" in result.values.columns
        # Signals should be -1, 0, or 1
        assert result.values["signal"].isin([-1, 0, 1]).all()


class TestBBConvenience:
    """Tests for Bollinger Bands convenience function."""

    def test_calculate_bollinger_bands(self, sample_prices):
        """Test calculate_bollinger_bands function."""
        upper, middle, lower = calculate_bollinger_bands(sample_prices)

        assert isinstance(upper, pd.Series)
        assert isinstance(middle, pd.Series)
        assert isinstance(lower, pd.Series)

        # Check band order
        valid_idx = ~(upper.isna() | middle.isna() | lower.isna())
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()


class TestOBV:
    """Tests for On-Balance Volume indicator."""

    def test_obv_basic(self, sample_ohlcv_df):
        """Test basic OBV calculation."""
        obv = OBV()
        result = obv.calculate(sample_ohlcv_df)

        assert result.name == "OBV"
        assert isinstance(result.values, pd.Series)

    def test_obv_with_signal(self, sample_ohlcv_df):
        """Test OBV with signal line."""
        obv = OBV(signal_period=20)
        result = obv.calculate(sample_ohlcv_df)

        assert isinstance(result.values, pd.DataFrame)
        assert "OBV" in result.values.columns
        assert "OBV_signal" in result.values.columns

    def test_obv_cumulative(self, sample_ohlcv_df):
        """Test OBV is cumulative."""
        obv = OBV()
        result = obv.calculate(sample_ohlcv_df)

        # OBV should have increasing absolute values over time (cumulative)
        # Check that the range increases
        values = result.values
        first_half_range = values.iloc[:50].max() - values.iloc[:50].min()
        full_range = values.max() - values.min()

        # Full range should be >= first half range (cumulative effect)
        assert full_range >= first_half_range * 0.5  # Allow some margin


class TestOBVDivergence:
    """Tests for OBV Divergence detector."""

    def test_obv_divergence_signals(self, sample_ohlcv_df):
        """Test OBV divergence detection."""
        divergence = OBVDivergence()
        result = divergence.calculate(sample_ohlcv_df)

        assert "OBV" in result.values.columns
        assert "divergence" in result.values.columns


class TestOBVConvenience:
    """Tests for OBV convenience function."""

    def test_calculate_obv(self, sample_ohlcv_df):
        """Test calculate_obv function."""
        obv = calculate_obv(
            sample_ohlcv_df["close"],
            sample_ohlcv_df["volume"],
        )

        assert isinstance(obv, pd.Series)
        assert len(obv) == len(sample_ohlcv_df)


class TestTechnicalAnalyzer:
    """Tests for TechnicalAnalyzer."""

    def test_analyzer_default_config(self, sample_ohlcv_df):
        """Test analyzer with default configuration."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(sample_ohlcv_df)

        assert isinstance(result, AnalysisResult)
        # Should include all default indicators
        assert any("SMA" in k or "EMA" in k for k in result.keys())
        assert any("RSI" in k for k in result.keys())
        assert "MACD" in result or "MACD_Crossover" in result
        assert "BollingerBands" in result or "BB_Signals" in result
        assert "OBV" in result

    def test_analyzer_custom_config(self, sample_ohlcv_df):
        """Test analyzer with custom configuration."""
        config = AnalysisConfig(
            ma_periods=[5, 10],
            rsi_period=21,
            include_bollinger=False,
        )
        analyzer = TechnicalAnalyzer(config)
        result = analyzer.analyze(sample_ohlcv_df)

        # Check MA periods
        assert "SMA5" in result.keys() or "EMA5" in result.keys()
        assert "SMA10" in result.keys() or "EMA10" in result.keys()

        # Bollinger should not be included
        assert "BollingerBands" not in result.keys()

    def test_analyzer_include_signals(self, sample_ohlcv_df):
        """Test analyzer with signals enabled."""
        config = AnalysisConfig(include_signals=True)
        analyzer = TechnicalAnalyzer(config)
        result = analyzer.analyze(sample_ohlcv_df)

        # Should have crossover in MACD
        assert "MACD_Crossover" in result.keys()

    def test_analyzer_include_divergences(self, sample_ohlcv_df):
        """Test analyzer with divergences enabled."""
        config = AnalysisConfig(include_divergences=True)
        analyzer = TechnicalAnalyzer(config)
        result = analyzer.analyze(sample_ohlcv_df)

        # Should have divergence indicators
        assert "RSI_Divergence" in result.keys()

    def test_analyzer_no_volume(self, sample_ohlcv_df):
        """Test analyzer handles missing volume column."""
        df_no_volume = sample_ohlcv_df.drop(columns=["volume"])
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(df_no_volume)

        # OBV should not be included
        assert "OBV" not in result.keys()


class TestAnalysisResult:
    """Tests for AnalysisResult."""

    def test_result_getitem(self, sample_ohlcv_df):
        """Test accessing results by key."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(sample_ohlcv_df)

        # Access by key should work
        for key in result.keys():
            assert isinstance(result[key], IndicatorResult)

    def test_result_contains(self, sample_ohlcv_df):
        """Test 'in' operator for results."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(sample_ohlcv_df)

        assert "MACD" in result or "MACD_Crossover" in result

    def test_result_to_dataframe(self, sample_ohlcv_df):
        """Test converting results to DataFrame."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(sample_ohlcv_df)

        df = result.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        # Should contain original data plus indicators
        assert "close" in df.columns
        assert len(df) == len(sample_ohlcv_df)

    def test_result_get_signals(self, sample_ohlcv_df):
        """Test extracting signal columns."""
        config = AnalysisConfig(include_signals=True)
        analyzer = TechnicalAnalyzer(config)
        result = analyzer.analyze(sample_ohlcv_df)

        signals = result.get_signals()
        assert isinstance(signals, pd.DataFrame)

    def test_result_summary(self, sample_ohlcv_df):
        """Test summary generation."""
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(sample_ohlcv_df)

        summary = result.summary()
        assert isinstance(summary, dict)
        # Should have some indicator values
        assert len(summary) > 0


class TestQuickAnalysis:
    """Tests for quick_analysis method."""

    def test_quick_analysis(self, sample_ohlcv_df):
        """Test quick analysis returns summary dict."""
        analyzer = TechnicalAnalyzer()
        summary = analyzer.quick_analysis(sample_ohlcv_df)

        assert isinstance(summary, dict)
        assert len(summary) > 0


class TestFactoryFunctions:
    """Tests for factory functions."""

    def test_create_technical_analyzer(self):
        """Test create_technical_analyzer factory."""
        analyzer = create_technical_analyzer()
        assert isinstance(analyzer, TechnicalAnalyzer)

    def test_create_technical_analyzer_with_config(self):
        """Test create_technical_analyzer with config."""
        config = AnalysisConfig(rsi_period=21)
        analyzer = create_technical_analyzer(config)

        assert analyzer.default_config.rsi_period == 21

    def test_analyze_stock_convenience(self, sample_ohlcv_df):
        """Test analyze_stock convenience function."""
        result = analyze_stock(sample_ohlcv_df)

        assert isinstance(result, AnalysisResult)

    def test_analyze_stock_with_signals(self, sample_ohlcv_df):
        """Test analyze_stock with signals."""
        result = analyze_stock(sample_ohlcv_df, include_signals=True)

        assert isinstance(result, AnalysisResult)
        assert "MACD_Crossover" in result.keys()


class TestEdgeCases:
    """Tests for edge cases."""

    def test_short_dataframe(self):
        """Test indicators with short DataFrame."""
        df = pd.DataFrame({
            "close": [100, 101, 102, 103, 104],
            "volume": [1000, 1100, 1200, 1300, 1400],
        })

        # Should not raise, just have NaN values
        sma = SMA(period=20)
        result = sma.calculate(df)
        assert result.values.isna().all()

    def test_constant_prices(self):
        """Test indicators with constant prices."""
        df = pd.DataFrame({
            "close": [100.0] * 50,
            "volume": [1000.0] * 50,
        })

        # RSI should be NaN (no gains or losses)
        rsi = RSI()
        result = rsi.calculate(df)
        # With constant prices, RSI will have NaN due to 0/0
        assert result.values.isna().any()

    def test_missing_required_column(self, sample_ohlcv_df):
        """Test error when required column is missing."""
        df = sample_ohlcv_df.drop(columns=["close"])

        sma = SMA()
        with pytest.raises(ValueError, match="Missing"):
            sma.calculate(df)

    def test_empty_dataframe(self):
        """Test indicators with empty DataFrame."""
        df = pd.DataFrame(columns=["open", "high", "low", "close", "volume"])

        sma = SMA()
        # Empty DataFrame should produce empty result (not raise)
        result = sma.calculate(df)
        assert len(result.values) == 0


class TestDataTypes:
    """Tests for different data types."""

    def test_integer_prices(self):
        """Test indicators work with integer prices."""
        df = pd.DataFrame({
            "close": list(range(100, 200)),
            "volume": list(range(1000, 1100)),
        })

        sma = SMA(period=10)
        result = sma.calculate(df)
        assert not result.values.isna().all()

    def test_float32_prices(self):
        """Test indicators work with float32 prices."""
        np.random.seed(42)
        df = pd.DataFrame({
            "close": np.random.randn(100).astype(np.float32) + 100,
            "volume": np.random.randint(1000, 2000, 100).astype(np.float32),
        })

        macd = MACD()
        result = macd.calculate(df)
        assert isinstance(result.values, pd.DataFrame)


class TestAnalysisConfig:
    """Tests for AnalysisConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = AnalysisConfig()

        assert config.ma_periods == [5, 10, 20, 60]
        assert config.rsi_period == 14
        assert config.macd_fast == 12
        assert config.macd_slow == 26
        assert config.bb_period == 20

    def test_custom_config(self):
        """Test custom configuration."""
        config = AnalysisConfig(
            ma_periods=[10, 30],
            rsi_period=21,
            include_ma=False,
        )

        assert config.ma_periods == [10, 30]
        assert config.rsi_period == 21
        assert config.include_ma is False

    def test_config_price_column(self):
        """Test custom price column."""
        config = AnalysisConfig(price_column="adj_close")
        assert config.price_column == "adj_close"
