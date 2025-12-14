"""
MACD (Moving Average Convergence Divergence) indicator.

MACD is a trend-following momentum indicator that shows the relationship
between two moving averages of a security's price.

Components:
- MACD Line: EMA(12) - EMA(26)
- Signal Line: EMA(9) of MACD Line
- Histogram: MACD Line - Signal Line

Usage:
    from analysis.indicators import MACD

    # Calculate MACD with default parameters (12, 26, 9)
    result = MACD().calculate(df)
    macd_df = result.values  # Contains MACD, signal, histogram columns

    # Custom parameters
    result = MACD(fast=8, slow=21, signal=5).calculate(df)
"""

from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult, validate_period


class MACD(BaseIndicator):
    """
    MACD (Moving Average Convergence Divergence) indicator.

    MACD is calculated by subtracting the longer-term EMA from the
    shorter-term EMA. The signal line is an EMA of the MACD line.
    The histogram shows the difference between MACD and signal line.
    """

    name = "MACD"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ):
        """
        Initialize MACD indicator.

        Args:
            fast: Fast EMA period (default: 12)
            slow: Slow EMA period (default: 26)
            signal: Signal line EMA period (default: 9)
        """
        validate_period(fast)
        validate_period(slow)
        validate_period(signal)

        if fast >= slow:
            raise ValueError(
                f"Fast period ({fast}) must be less than slow period ({slow})"
            )

        self.fast = fast
        self.slow = slow
        self.signal = signal

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate MACD, signal line, and histogram.

        Args:
            df: DataFrame with price data
            column: Column to calculate MACD on (default: close)

        Returns:
            IndicatorResult with DataFrame containing:
            - MACD: MACD line
            - signal: Signal line
            - histogram: MACD - Signal
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        # Calculate EMAs
        ema_fast = prices.ewm(span=self.fast, adjust=False).mean()
        ema_slow = prices.ewm(span=self.slow, adjust=False).mean()

        # Calculate MACD components
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal, adjust=False).mean()
        histogram = macd_line - signal_line

        # Create result DataFrame
        result_df = pd.DataFrame(index=df.index)
        result_df["MACD"] = macd_line
        result_df["signal"] = signal_line
        result_df["histogram"] = histogram

        return IndicatorResult(
            name="MACD",
            values=result_df,
            params={
                "fast": self.fast,
                "slow": self.slow,
                "signal": self.signal,
                "column": column,
            },
        )


class MACDCrossover(BaseIndicator):
    """
    MACD Crossover signal detector.

    Identifies bullish and bearish crossovers:
    - Bullish crossover: MACD crosses above signal line
    - Bearish crossover: MACD crosses below signal line
    """

    name = "MACD_Crossover"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ):
        """
        Initialize MACD Crossover detector.

        Args:
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
        """
        self.macd = MACD(fast=fast, slow=slow, signal=signal)

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Detect MACD crossovers.

        Args:
            df: DataFrame with price data
            column: Column to calculate MACD on

        Returns:
            IndicatorResult with DataFrame containing:
            - MACD, signal, histogram (from MACD)
            - crossover: 1 for bullish, -1 for bearish, 0 for none
        """
        macd_result = self.macd.calculate(df, column=column)
        macd_df = macd_result.values

        # Detect crossovers
        macd_line = macd_df["MACD"]
        signal_line = macd_df["signal"]

        # Current and previous differences
        diff = macd_line - signal_line
        diff_prev = diff.shift(1)

        # Crossover signals
        crossover = pd.Series(0, index=df.index)
        crossover[(diff > 0) & (diff_prev <= 0)] = 1  # Bullish crossover
        crossover[(diff < 0) & (diff_prev >= 0)] = -1  # Bearish crossover

        macd_df["crossover"] = crossover

        return IndicatorResult(
            name="MACD_Crossover",
            values=macd_df,
            params=macd_result.params,
        )


class MACDHistogramDivergence(BaseIndicator):
    """
    MACD Histogram Divergence detector.

    Identifies divergences between price and MACD histogram:
    - Bullish: Price makes lower low, histogram makes higher low
    - Bearish: Price makes higher high, histogram makes lower high
    """

    name = "MACD_Histogram_Divergence"

    def __init__(
        self,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
        lookback: int = 5,
    ):
        """
        Initialize MACD Histogram Divergence detector.

        Args:
            fast: Fast EMA period
            slow: Slow EMA period
            signal: Signal line EMA period
            lookback: Period for detecting divergences
        """
        self.macd = MACD(fast=fast, slow=slow, signal=signal)
        validate_period(lookback)
        self.lookback = lookback

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Detect MACD histogram divergences.

        Args:
            df: DataFrame with price data
            column: Column to calculate MACD on

        Returns:
            IndicatorResult with divergence signals
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        macd_result = self.macd.calculate(df, column=column)
        histogram = macd_result.values["histogram"]

        # Rolling min/max
        price_min = prices.rolling(window=self.lookback).min()
        price_max = prices.rolling(window=self.lookback).max()
        hist_min = histogram.rolling(window=self.lookback).min()
        hist_max = histogram.rolling(window=self.lookback).max()

        # Detect divergences
        divergence = pd.Series(0, index=df.index)

        # Bullish: price at low, histogram not at low
        bullish = (prices == price_min) & (histogram > hist_min)
        divergence[bullish] = 1

        # Bearish: price at high, histogram not at high
        bearish = (prices == price_max) & (histogram < hist_max)
        divergence[bearish] = -1

        result_df = macd_result.values.copy()
        result_df["divergence"] = divergence

        return IndicatorResult(
            name="MACD_Histogram_Divergence",
            values=result_df,
            params={**macd_result.params, "lookback": self.lookback},
        )


def calculate_macd(
    prices: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD components.

    Convenience function for quick calculations.

    Args:
        prices: Price series
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period

    Returns:
        Tuple of (macd_line, signal_line, histogram)
    """
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram
