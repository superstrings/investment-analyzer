"""
Technical Analysis Aggregator.

Provides a unified interface for calculating multiple technical indicators
on financial data. This module combines all individual indicators into
a cohesive analysis framework.

Usage:
    from analysis.technical import TechnicalAnalyzer, AnalysisConfig

    # Create analyzer with default config
    analyzer = TechnicalAnalyzer()

    # Analyze with all default indicators
    results = analyzer.analyze(df)

    # Access individual results
    rsi = results["RSI14"]
    macd = results["MACD"]
    bb = results["BollingerBands"]

    # Custom configuration
    config = AnalysisConfig(
        ma_periods=[5, 10, 20],
        rsi_period=14,
        include_signals=True,
    )
    results = analyzer.analyze(df, config)
"""

from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

from .indicators import (
    EMA,
    MA,
    MACD,
    OBV,
    RSI,
    SMA,
    BollingerBands,
    BollingerBandsSignals,
    BollingerBandsSqueeze,
    IndicatorResult,
    MACDCrossover,
    OBVDivergence,
    RSIDivergence,
    StochasticRSI,
)


@dataclass
class AnalysisConfig:
    """Configuration for technical analysis."""

    # Moving Average settings
    ma_periods: list[int] = field(default_factory=lambda: [5, 10, 20, 60])
    ma_type: str = "sma"  # sma, ema

    # RSI settings
    rsi_period: int = 14
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0

    # MACD settings
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    # Bollinger Bands settings
    bb_period: int = 20
    bb_std_dev: float = 2.0

    # OBV settings
    obv_signal_period: Optional[int] = 20

    # Analysis options
    include_ma: bool = True
    include_rsi: bool = True
    include_macd: bool = True
    include_bollinger: bool = True
    include_obv: bool = True
    include_signals: bool = False
    include_divergences: bool = False

    # Column to use for price calculations
    price_column: str = "close"


@dataclass
class AnalysisResult:
    """Container for technical analysis results."""

    results: dict[str, IndicatorResult]
    config: AnalysisConfig
    df: pd.DataFrame

    def __getitem__(self, key: str) -> IndicatorResult:
        """Access indicator result by name."""
        return self.results[key]

    def __contains__(self, key: str) -> bool:
        """Check if indicator result exists."""
        return key in self.results

    def keys(self):
        """Get all indicator names."""
        return self.results.keys()

    def values(self):
        """Get all indicator results."""
        return self.results.values()

    def items(self):
        """Get all indicator name-result pairs."""
        return self.results.items()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Combine all indicator results into a single DataFrame.

        Returns:
            DataFrame with all indicator values merged with original data
        """
        result_df = self.df.copy()

        for name, indicator_result in self.results.items():
            values = indicator_result.values

            if isinstance(values, pd.DataFrame):
                # Prefix column names with indicator name
                for col in values.columns:
                    result_df[f"{name}_{col}"] = values[col]
            else:
                # Single series
                result_df[name] = values

        return result_df

    def get_signals(self) -> pd.DataFrame:
        """
        Extract all signal columns from results.

        Returns:
            DataFrame with only signal columns
        """
        signal_df = pd.DataFrame(index=self.df.index)

        for name, indicator_result in self.results.items():
            values = indicator_result.values

            if isinstance(values, pd.DataFrame):
                # Look for signal-related columns
                for col in values.columns:
                    if col in ("signal", "crossover", "divergence", "squeeze"):
                        signal_df[f"{name}_{col}"] = values[col]

        return signal_df

    def summary(self) -> dict:
        """
        Generate a summary of the latest indicator values.

        Returns:
            Dictionary with latest values for each indicator
        """
        summary = {}

        for name, indicator_result in self.results.items():
            values = indicator_result.values

            if isinstance(values, pd.DataFrame):
                # Get latest row as dict
                latest = values.iloc[-1].to_dict()
                summary[name] = {k: v for k, v in latest.items() if pd.notna(v)}
            else:
                # Get latest value
                latest = values.iloc[-1]
                if pd.notna(latest):
                    summary[name] = latest

        return summary


class TechnicalAnalyzer:
    """
    Technical Analysis Aggregator.

    Calculates multiple technical indicators on financial data
    using a unified interface.
    """

    def __init__(self, config: Optional[AnalysisConfig] = None):
        """
        Initialize TechnicalAnalyzer.

        Args:
            config: Optional default configuration
        """
        self.default_config = config or AnalysisConfig()

    def analyze(
        self,
        df: pd.DataFrame,
        config: Optional[AnalysisConfig] = None,
    ) -> AnalysisResult:
        """
        Run technical analysis on the given DataFrame.

        Args:
            df: DataFrame with OHLCV data
            config: Optional analysis configuration (uses default if not provided)

        Returns:
            AnalysisResult containing all calculated indicators
        """
        config = config or self.default_config
        results: dict[str, IndicatorResult] = {}

        # Moving Averages
        if config.include_ma:
            results.update(self._calculate_ma(df, config))

        # RSI
        if config.include_rsi:
            results.update(self._calculate_rsi(df, config))

        # MACD
        if config.include_macd:
            results.update(self._calculate_macd(df, config))

        # Bollinger Bands
        if config.include_bollinger:
            results.update(self._calculate_bollinger(df, config))

        # OBV
        if config.include_obv:
            results.update(self._calculate_obv(df, config))

        return AnalysisResult(results=results, config=config, df=df)

    def _calculate_ma(
        self,
        df: pd.DataFrame,
        config: AnalysisConfig,
    ) -> dict[str, IndicatorResult]:
        """Calculate Moving Averages."""
        results = {}

        if config.ma_type.lower() == "ema":
            for period in config.ma_periods:
                indicator = EMA(period=period)
                result = indicator.calculate(df, column=config.price_column)
                results[result.name] = result
        else:
            for period in config.ma_periods:
                indicator = SMA(period=period)
                result = indicator.calculate(df, column=config.price_column)
                results[result.name] = result

        return results

    def _calculate_rsi(
        self,
        df: pd.DataFrame,
        config: AnalysisConfig,
    ) -> dict[str, IndicatorResult]:
        """Calculate RSI indicators."""
        results = {}

        # Standard RSI
        rsi = RSI(
            period=config.rsi_period,
            overbought=config.rsi_overbought,
            oversold=config.rsi_oversold,
        )
        result = rsi.calculate(df, column=config.price_column)
        results[result.name] = result

        # Divergence detection
        if config.include_divergences:
            divergence = RSIDivergence(period=config.rsi_period)
            result = divergence.calculate(df, column=config.price_column)
            results[result.name] = result

        return results

    def _calculate_macd(
        self,
        df: pd.DataFrame,
        config: AnalysisConfig,
    ) -> dict[str, IndicatorResult]:
        """Calculate MACD indicators."""
        results = {}

        if config.include_signals:
            # MACD with crossover signals
            macd = MACDCrossover(
                fast=config.macd_fast,
                slow=config.macd_slow,
                signal=config.macd_signal,
            )
        else:
            # Standard MACD
            macd = MACD(
                fast=config.macd_fast,
                slow=config.macd_slow,
                signal=config.macd_signal,
            )

        result = macd.calculate(df, column=config.price_column)
        results[result.name] = result

        return results

    def _calculate_bollinger(
        self,
        df: pd.DataFrame,
        config: AnalysisConfig,
    ) -> dict[str, IndicatorResult]:
        """Calculate Bollinger Bands indicators."""
        results = {}

        if config.include_signals:
            # Bollinger with signals
            bb = BollingerBandsSignals(
                period=config.bb_period,
                std_dev=config.bb_std_dev,
            )
        else:
            # Standard Bollinger Bands
            bb = BollingerBands(
                period=config.bb_period,
                std_dev=config.bb_std_dev,
            )

        result = bb.calculate(df, column=config.price_column)
        results[result.name] = result

        # Squeeze detection
        if config.include_signals:
            squeeze = BollingerBandsSqueeze(
                period=config.bb_period,
                std_dev=config.bb_std_dev,
            )
            result = squeeze.calculate(df, column=config.price_column)
            results[result.name] = result

        return results

    def _calculate_obv(
        self,
        df: pd.DataFrame,
        config: AnalysisConfig,
    ) -> dict[str, IndicatorResult]:
        """Calculate OBV indicators."""
        results = {}

        # Check if volume column exists
        if "volume" not in df.columns:
            return results

        # Standard OBV
        obv = OBV(signal_period=config.obv_signal_period)
        result = obv.calculate(df)
        results[result.name] = result

        # Divergence detection
        if config.include_divergences:
            divergence = OBVDivergence()
            result = divergence.calculate(df)
            results[result.name] = result

        return results

    def quick_analysis(
        self,
        df: pd.DataFrame,
        price_column: str = "close",
    ) -> dict:
        """
        Perform quick analysis and return latest values.

        Simplified interface for getting current indicator readings.

        Args:
            df: DataFrame with OHLCV data
            price_column: Column to use for price

        Returns:
            Dictionary with latest indicator values
        """
        config = AnalysisConfig(
            price_column=price_column,
            include_signals=False,
            include_divergences=False,
        )

        result = self.analyze(df, config)
        return result.summary()


def create_technical_analyzer(
    config: Optional[AnalysisConfig] = None,
) -> TechnicalAnalyzer:
    """
    Factory function to create a TechnicalAnalyzer.

    Args:
        config: Optional analysis configuration

    Returns:
        Configured TechnicalAnalyzer instance
    """
    return TechnicalAnalyzer(config=config)


def analyze_stock(
    df: pd.DataFrame,
    include_signals: bool = False,
    include_divergences: bool = False,
) -> AnalysisResult:
    """
    Convenience function for quick stock analysis.

    Args:
        df: DataFrame with OHLCV data
        include_signals: Whether to include trading signals
        include_divergences: Whether to include divergence detection

    Returns:
        AnalysisResult with all indicators
    """
    config = AnalysisConfig(
        include_signals=include_signals,
        include_divergences=include_divergences,
    )
    analyzer = TechnicalAnalyzer(config)
    return analyzer.analyze(df)
