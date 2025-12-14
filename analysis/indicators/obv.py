"""
On-Balance Volume (OBV) indicator.

OBV measures buying and selling pressure using volume flow.
It adds volume on up days and subtracts volume on down days.

Usage:
    from analysis.indicators import OBV

    # Calculate OBV
    result = OBV().calculate(df)
    obv_values = result.values

    # Calculate OBV with signal line
    result = OBV(signal_period=20).calculate(df)
    obv_df = result.values  # Contains OBV and OBV_signal columns
"""

from typing import Optional

import numpy as np
import pandas as pd

from .base import BaseIndicator, IndicatorResult, validate_period


class OBV(BaseIndicator):
    """
    On-Balance Volume (OBV) indicator.

    OBV is a cumulative indicator that uses volume flow to predict
    changes in stock price. The theory is that volume precedes price movement.

    Rules:
    - If close > previous close: OBV = previous OBV + volume
    - If close < previous close: OBV = previous OBV - volume
    - If close = previous close: OBV = previous OBV
    """

    name = "OBV"

    def __init__(self, signal_period: Optional[int] = None):
        """
        Initialize OBV indicator.

        Args:
            signal_period: Optional period for OBV signal line (EMA of OBV)
        """
        if signal_period is not None:
            validate_period(signal_period)
        self.signal_period = signal_period

    def calculate(
        self,
        df: pd.DataFrame,
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate On-Balance Volume.

        Args:
            df: DataFrame with close and volume columns

        Returns:
            IndicatorResult with OBV values (and optional signal line)
        """
        self._validate_dataframe(df, ["close", "volume"])

        close = self._get_column(df, "close")
        volume = self._get_column(df, "volume")

        # Calculate price changes
        close_diff = close.diff()

        # Assign signed volume
        signed_volume = pd.Series(index=df.index, dtype=float)
        signed_volume[close_diff > 0] = volume[close_diff > 0]
        signed_volume[close_diff < 0] = -volume[close_diff < 0]
        signed_volume[close_diff == 0] = 0
        signed_volume.iloc[0] = volume.iloc[0]  # First value

        # Cumulative sum
        obv = signed_volume.cumsum()

        # Create result
        if self.signal_period:
            result_df = pd.DataFrame(index=df.index)
            result_df["OBV"] = obv
            result_df["OBV_signal"] = obv.ewm(span=self.signal_period, adjust=True).mean()

            return IndicatorResult(
                name="OBV",
                values=result_df,
                params={"signal_period": self.signal_period},
            )
        else:
            return IndicatorResult(
                name="OBV",
                values=obv,
                params={},
            )


class OBVDivergence(BaseIndicator):
    """
    OBV Divergence detector.

    Identifies bullish and bearish divergences between OBV and price.
    - Bullish divergence: Price makes lower low, OBV makes higher low
    - Bearish divergence: Price makes higher high, OBV makes lower high
    """

    name = "OBV_Divergence"

    def __init__(self, lookback: int = 14):
        """
        Initialize OBV Divergence detector.

        Args:
            lookback: Period for detecting divergences
        """
        validate_period(lookback)
        self.lookback = lookback

    def calculate(
        self,
        df: pd.DataFrame,
        **kwargs,
    ) -> IndicatorResult:
        """
        Detect OBV divergences.

        Args:
            df: DataFrame with close and volume columns

        Returns:
            IndicatorResult with divergence signals
            - 1: Bullish divergence
            - -1: Bearish divergence
            - 0: No divergence
        """
        self._validate_dataframe(df, ["close", "volume"])

        close = self._get_column(df, "close")
        volume = self._get_column(df, "volume")

        # Calculate OBV
        close_diff = close.diff()
        signed_volume = pd.Series(index=df.index, dtype=float)
        signed_volume[close_diff > 0] = volume[close_diff > 0]
        signed_volume[close_diff < 0] = -volume[close_diff < 0]
        signed_volume[close_diff == 0] = 0
        signed_volume.iloc[0] = volume.iloc[0]
        obv = signed_volume.cumsum()

        # Rolling min/max for detecting divergences
        price_min = close.rolling(window=self.lookback).min()
        price_max = close.rolling(window=self.lookback).max()
        obv_min = obv.rolling(window=self.lookback).min()
        obv_max = obv.rolling(window=self.lookback).max()

        # Detect divergences
        divergence = pd.Series(0, index=df.index)

        # Bullish divergence: price at new low, OBV not at new low
        bullish = (close == price_min) & (obv > obv_min)
        divergence[bullish] = 1

        # Bearish divergence: price at new high, OBV not at new high
        bearish = (close == price_max) & (obv < obv_max)
        divergence[bearish] = -1

        result_df = pd.DataFrame(index=df.index)
        result_df["OBV"] = obv
        result_df["divergence"] = divergence

        return IndicatorResult(
            name="OBV_Divergence",
            values=result_df,
            params={"lookback": self.lookback},
        )


def calculate_obv(
    close: pd.Series,
    volume: pd.Series,
) -> pd.Series:
    """
    Calculate On-Balance Volume.

    Convenience function for quick calculations.

    Args:
        close: Close price series
        volume: Volume series

    Returns:
        OBV series
    """
    close_diff = close.diff()
    signed_volume = pd.Series(index=close.index, dtype=float)
    signed_volume[close_diff > 0] = volume[close_diff > 0]
    signed_volume[close_diff < 0] = -volume[close_diff < 0]
    signed_volume[close_diff == 0] = 0
    signed_volume.iloc[0] = volume.iloc[0]

    return signed_volume.cumsum()
