"""
RSI (Relative Strength Index) indicator.

RSI is a momentum oscillator that measures the speed and magnitude of
recent price changes to evaluate overbought or oversold conditions.

RSI ranges from 0 to 100:
- RSI > 70: Overbought (potential sell signal)
- RSI < 30: Oversold (potential buy signal)

Usage:
    from analysis.indicators import RSI

    # Calculate RSI with default period (14)
    result = RSI().calculate(df)
    rsi_values = result.values

    # Custom period
    result = RSI(period=21).calculate(df)
"""

from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult, validate_period


class RSI(BaseIndicator):
    """
    RSI (Relative Strength Index) indicator.

    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss over the period
    """

    name = "RSI"

    def __init__(
        self,
        period: int = 14,
        overbought: float = 70.0,
        oversold: float = 30.0,
    ):
        """
        Initialize RSI indicator.

        Args:
            period: RSI calculation period (default: 14)
            overbought: Overbought threshold (default: 70)
            oversold: Oversold threshold (default: 30)
        """
        validate_period(period)
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        method: str = "ewm",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate RSI.

        Args:
            df: DataFrame with price data
            column: Column to calculate RSI on (default: close)
            method: Smoothing method ("ewm" or "sma", default: "ewm")

        Returns:
            IndicatorResult with RSI values
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        # Calculate price changes
        delta = prices.diff()

        # Separate gains and losses
        gains = delta.where(delta > 0, 0.0)
        losses = (-delta).where(delta < 0, 0.0)

        # Calculate average gains and losses
        if method == "ewm":
            avg_gain = gains.ewm(span=self.period, adjust=False).mean()
            avg_loss = losses.ewm(span=self.period, adjust=False).mean()
        else:  # SMA
            avg_gain = gains.rolling(window=self.period).mean()
            avg_loss = losses.rolling(window=self.period).mean()

        # Calculate RS and RSI
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        # Handle division by zero
        rsi = rsi.replace([np.inf, -np.inf], np.nan)

        return IndicatorResult(
            name=f"RSI{self.period}",
            values=rsi,
            params={
                "period": self.period,
                "column": column,
                "method": method,
                "overbought": self.overbought,
                "oversold": self.oversold,
            },
        )


class StochasticRSI(BaseIndicator):
    """
    Stochastic RSI indicator.

    Applies the Stochastic oscillator formula to RSI values
    to generate a more sensitive indicator.

    StochRSI = (RSI - Lowest RSI) / (Highest RSI - Lowest RSI)
    """

    name = "StochRSI"

    def __init__(
        self,
        rsi_period: int = 14,
        stoch_period: int = 14,
        k_period: int = 3,
        d_period: int = 3,
    ):
        """
        Initialize Stochastic RSI indicator.

        Args:
            rsi_period: Period for RSI calculation
            stoch_period: Period for stochastic calculation
            k_period: Smoothing period for %K
            d_period: Smoothing period for %D
        """
        validate_period(rsi_period)
        validate_period(stoch_period)
        validate_period(k_period)
        validate_period(d_period)

        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.k_period = k_period
        self.d_period = d_period

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate Stochastic RSI.

        Args:
            df: DataFrame with price data
            column: Column to calculate on

        Returns:
            IndicatorResult with DataFrame containing %K and %D
        """
        # Calculate RSI first
        rsi_indicator = RSI(period=self.rsi_period)
        rsi_result = rsi_indicator.calculate(df, column=column)
        rsi = rsi_result.values

        # Calculate Stochastic RSI
        rsi_min = rsi.rolling(window=self.stoch_period).min()
        rsi_max = rsi.rolling(window=self.stoch_period).max()

        stoch_rsi = (rsi - rsi_min) / (rsi_max - rsi_min) * 100
        stoch_rsi = stoch_rsi.replace([np.inf, -np.inf], np.nan)

        # Calculate %K and %D
        k = stoch_rsi.rolling(window=self.k_period).mean()
        d = k.rolling(window=self.d_period).mean()

        result_df = pd.DataFrame(index=df.index)
        result_df["StochRSI"] = stoch_rsi
        result_df["K"] = k
        result_df["D"] = d

        return IndicatorResult(
            name="StochRSI",
            values=result_df,
            params={
                "rsi_period": self.rsi_period,
                "stoch_period": self.stoch_period,
                "k_period": self.k_period,
                "d_period": self.d_period,
            },
        )


class RSIDivergence(BaseIndicator):
    """
    RSI Divergence detector.

    Identifies bullish and bearish divergences between price and RSI:
    - Bullish: Price makes lower low, RSI makes higher low
    - Bearish: Price makes higher high, RSI makes lower high
    """

    name = "RSI_Divergence"

    def __init__(
        self,
        period: int = 14,
        lookback: int = 5,
    ):
        """
        Initialize RSI Divergence detector.

        Args:
            period: RSI period
            lookback: Period for detecting divergences
        """
        self.rsi = RSI(period=period)
        validate_period(lookback)
        self.lookback = lookback

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Detect RSI divergences.

        Args:
            df: DataFrame with price data
            column: Column to use

        Returns:
            IndicatorResult with divergence signals
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        rsi_result = self.rsi.calculate(df, column=column)
        rsi = rsi_result.values

        # Rolling min/max
        price_min = prices.rolling(window=self.lookback).min()
        price_max = prices.rolling(window=self.lookback).max()
        rsi_min = rsi.rolling(window=self.lookback).min()
        rsi_max = rsi.rolling(window=self.lookback).max()

        # Detect divergences
        divergence = pd.Series(0, index=df.index)

        # Bullish: price at low, RSI not at low
        bullish = (prices == price_min) & (rsi > rsi_min)
        divergence[bullish] = 1

        # Bearish: price at high, RSI not at high
        bearish = (prices == price_max) & (rsi < rsi_max)
        divergence[bearish] = -1

        result_df = pd.DataFrame(index=df.index)
        result_df["RSI"] = rsi
        result_df["divergence"] = divergence

        return IndicatorResult(
            name="RSI_Divergence",
            values=result_df,
            params={**rsi_result.params, "lookback": self.lookback},
        )


def calculate_rsi(
    prices: pd.Series,
    period: int = 14,
    method: str = "ewm",
) -> pd.Series:
    """
    Calculate RSI.

    Convenience function for quick calculations.

    Args:
        prices: Price series
        period: RSI period
        method: Smoothing method ("ewm" or "sma")

    Returns:
        RSI series
    """
    delta = prices.diff()
    gains = delta.where(delta > 0, 0.0)
    losses = (-delta).where(delta < 0, 0.0)

    if method == "ewm":
        avg_gain = gains.ewm(span=period, adjust=False).mean()
        avg_loss = losses.ewm(span=period, adjust=False).mean()
    else:
        avg_gain = gains.rolling(window=period).mean()
        avg_loss = losses.rolling(window=period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return rsi.replace([np.inf, -np.inf], np.nan)
