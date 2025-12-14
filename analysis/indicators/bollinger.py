"""
Bollinger Bands indicator.

Bollinger Bands consist of a middle band (SMA) and two outer bands
at standard deviation levels above and below the middle band.

- Middle Band: 20-day SMA
- Upper Band: Middle Band + (2 * Standard Deviation)
- Lower Band: Middle Band - (2 * Standard Deviation)

Usage:
    from analysis.indicators import BollingerBands

    # Calculate with default parameters (20, 2)
    result = BollingerBands().calculate(df)
    bb_df = result.values  # Contains upper, middle, lower, bandwidth, %b

    # Custom parameters
    result = BollingerBands(period=25, std_dev=2.5).calculate(df)
"""

from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult, validate_period


class BollingerBands(BaseIndicator):
    """
    Bollinger Bands indicator.

    Bollinger Bands adapt to volatility - they expand during volatile
    periods and contract during less volatile periods.
    """

    name = "BollingerBands"

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ):
        """
        Initialize Bollinger Bands indicator.

        Args:
            period: Moving average period (default: 20)
            std_dev: Standard deviation multiplier (default: 2.0)
        """
        validate_period(period)
        if std_dev <= 0:
            raise ValueError(f"std_dev must be positive, got {std_dev}")

        self.period = period
        self.std_dev = std_dev

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate Bollinger Bands.

        Args:
            df: DataFrame with price data
            column: Column to calculate bands on (default: close)

        Returns:
            IndicatorResult with DataFrame containing:
            - upper: Upper band
            - middle: Middle band (SMA)
            - lower: Lower band
            - bandwidth: Band width as percentage
            - percent_b: %B indicator (price position within bands)
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        # Calculate middle band (SMA)
        middle = prices.rolling(window=self.period).mean()

        # Calculate standard deviation
        std = prices.rolling(window=self.period).std()

        # Calculate upper and lower bands
        upper = middle + (self.std_dev * std)
        lower = middle - (self.std_dev * std)

        # Calculate bandwidth (percentage)
        bandwidth = ((upper - lower) / middle) * 100

        # Calculate %B (price position relative to bands)
        # %B = (Price - Lower Band) / (Upper Band - Lower Band)
        percent_b = (prices - lower) / (upper - lower)

        # Create result DataFrame
        result_df = pd.DataFrame(index=df.index)
        result_df["upper"] = upper
        result_df["middle"] = middle
        result_df["lower"] = lower
        result_df["bandwidth"] = bandwidth
        result_df["percent_b"] = percent_b

        return IndicatorResult(
            name="BollingerBands",
            values=result_df,
            params={
                "period": self.period,
                "std_dev": self.std_dev,
                "column": column,
            },
        )


class BollingerBandsSqueeze(BaseIndicator):
    """
    Bollinger Bands Squeeze detector.

    The squeeze identifies periods of low volatility, which often
    precede significant price movements.
    """

    name = "BB_Squeeze"

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
        squeeze_threshold: float = 0.05,
    ):
        """
        Initialize Bollinger Bands Squeeze detector.

        Args:
            period: Moving average period
            std_dev: Standard deviation multiplier
            squeeze_threshold: Bandwidth threshold for squeeze (as percentage)
        """
        self.bb = BollingerBands(period=period, std_dev=std_dev)
        self.squeeze_threshold = squeeze_threshold

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Detect Bollinger Bands squeeze.

        Args:
            df: DataFrame with price data
            column: Column to analyze

        Returns:
            IndicatorResult with squeeze signals
        """
        bb_result = self.bb.calculate(df, column=column)
        bb_df = bb_result.values

        # Calculate squeeze threshold based on historical bandwidth
        bandwidth = bb_df["bandwidth"]
        bandwidth_min = bandwidth.rolling(window=self.bb.period * 6).min()

        # Squeeze signal: when bandwidth is near its minimum
        squeeze = bandwidth <= bandwidth_min * (1 + self.squeeze_threshold)

        bb_df["squeeze"] = squeeze.astype(int)

        return IndicatorResult(
            name="BB_Squeeze",
            values=bb_df,
            params={
                **bb_result.params,
                "squeeze_threshold": self.squeeze_threshold,
            },
        )


class BollingerBandsSignals(BaseIndicator):
    """
    Bollinger Bands trading signals generator.

    Generates signals based on price touching or crossing bands:
    - Buy when price touches lower band
    - Sell when price touches upper band
    """

    name = "BB_Signals"

    def __init__(
        self,
        period: int = 20,
        std_dev: float = 2.0,
    ):
        """
        Initialize Bollinger Bands signals generator.

        Args:
            period: Moving average period
            std_dev: Standard deviation multiplier
        """
        self.bb = BollingerBands(period=period, std_dev=std_dev)

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Generate Bollinger Bands signals.

        Args:
            df: DataFrame with price data
            column: Column to analyze

        Returns:
            IndicatorResult with signals:
            - 1: Buy signal (price at/below lower band)
            - -1: Sell signal (price at/above upper band)
            - 0: No signal
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        bb_result = self.bb.calculate(df, column=column)
        bb_df = bb_result.values

        upper = bb_df["upper"]
        lower = bb_df["lower"]

        # Generate signals
        signal = pd.Series(0, index=df.index)

        # Buy signal: price at or below lower band
        signal[prices <= lower] = 1

        # Sell signal: price at or above upper band
        signal[prices >= upper] = -1

        bb_df["signal"] = signal

        return IndicatorResult(
            name="BB_Signals",
            values=bb_df,
            params=bb_result.params,
        )


def calculate_bollinger_bands(
    prices: pd.Series,
    period: int = 20,
    std_dev: float = 2.0,
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands.

    Convenience function for quick calculations.

    Args:
        prices: Price series
        period: Moving average period
        std_dev: Standard deviation multiplier

    Returns:
        Tuple of (upper_band, middle_band, lower_band)
    """
    middle = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return upper, middle, lower
