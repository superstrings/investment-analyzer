"""
Moving Average (MA) indicators.

Provides various moving average calculations:
- SMA: Simple Moving Average
- EMA: Exponential Moving Average
- WMA: Weighted Moving Average

Usage:
    from analysis.indicators import MA, SMA, EMA

    # Calculate single MA
    result = SMA(20).calculate(df)
    ma20 = result.values

    # Calculate multiple MAs
    result = MA().calculate(df, periods=[5, 10, 20, 60])
    ma_df = result.values  # DataFrame with MA5, MA10, MA20, MA60 columns

    # Calculate EMA
    result = EMA(12).calculate(df)
"""

from typing import Optional, Union

import pandas as pd

from .base import BaseIndicator, IndicatorResult, validate_period


class SMA(BaseIndicator):
    """
    Simple Moving Average (SMA).

    SMA = Sum(Close, n) / n
    """

    name = "SMA"

    def __init__(self, period: int = 20):
        """
        Initialize SMA indicator.

        Args:
            period: Number of periods for the moving average
        """
        validate_period(period)
        self.period = period

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate Simple Moving Average.

        Args:
            df: DataFrame with price data
            column: Column to calculate MA on (default: close)

        Returns:
            IndicatorResult with SMA values
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        sma = prices.rolling(window=self.period).mean()

        return IndicatorResult(
            name=f"SMA{self.period}",
            values=sma,
            params={"period": self.period, "column": column},
        )


class EMA(BaseIndicator):
    """
    Exponential Moving Average (EMA).

    EMA gives more weight to recent prices.
    """

    name = "EMA"

    def __init__(self, period: int = 20):
        """
        Initialize EMA indicator.

        Args:
            period: Number of periods for the moving average
        """
        validate_period(period)
        self.period = period

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        adjust: bool = True,
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate Exponential Moving Average.

        Args:
            df: DataFrame with price data
            column: Column to calculate EMA on (default: close)
            adjust: Whether to use adjusted calculation (default: True)

        Returns:
            IndicatorResult with EMA values
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        ema = prices.ewm(span=self.period, adjust=adjust).mean()

        return IndicatorResult(
            name=f"EMA{self.period}",
            values=ema,
            params={"period": self.period, "column": column, "adjust": adjust},
        )


class WMA(BaseIndicator):
    """
    Weighted Moving Average (WMA).

    WMA assigns linearly increasing weights to more recent data.
    """

    name = "WMA"

    def __init__(self, period: int = 20):
        """
        Initialize WMA indicator.

        Args:
            period: Number of periods for the moving average
        """
        validate_period(period)
        self.period = period

    def calculate(
        self,
        df: pd.DataFrame,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate Weighted Moving Average.

        Args:
            df: DataFrame with price data
            column: Column to calculate WMA on (default: close)

        Returns:
            IndicatorResult with WMA values
        """
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        # Create weights: 1, 2, 3, ..., period
        weights = list(range(1, self.period + 1))

        def weighted_avg(x):
            return sum(x * weights) / sum(weights)

        wma = prices.rolling(window=self.period).apply(weighted_avg, raw=True)

        return IndicatorResult(
            name=f"WMA{self.period}",
            values=wma,
            params={"period": self.period, "column": column},
        )


class MA(BaseIndicator):
    """
    Multiple Moving Averages calculator.

    Calculates multiple MAs at once for efficiency.
    """

    name = "MA"

    def __init__(self, ma_type: str = "sma"):
        """
        Initialize MA calculator.

        Args:
            ma_type: Type of MA ("sma", "ema", "wma")
        """
        self.ma_type = ma_type.lower()
        if self.ma_type not in ("sma", "ema", "wma"):
            raise ValueError(f"Invalid ma_type: {ma_type}. Use 'sma', 'ema', or 'wma'")

    def calculate(
        self,
        df: pd.DataFrame,
        periods: list[int] = None,
        column: str = "close",
        **kwargs,
    ) -> IndicatorResult:
        """
        Calculate multiple Moving Averages.

        Args:
            df: DataFrame with price data
            periods: List of periods to calculate (default: [5, 10, 20, 60])
            column: Column to calculate MAs on (default: close)

        Returns:
            IndicatorResult with DataFrame containing all MAs
        """
        periods = periods or [5, 10, 20, 60]
        self._validate_dataframe(df, [column])
        prices = self._get_column(df, column)

        result_df = pd.DataFrame(index=df.index)

        for period in periods:
            validate_period(period)
            col_name = f"MA{period}"

            if self.ma_type == "sma":
                result_df[col_name] = prices.rolling(window=period).mean()
            elif self.ma_type == "ema":
                result_df[col_name] = prices.ewm(span=period, adjust=True).mean()
            elif self.ma_type == "wma":
                weights = list(range(1, period + 1))

                def weighted_avg(x):
                    return sum(x * weights) / sum(weights)

                result_df[col_name] = prices.rolling(window=period).apply(
                    weighted_avg, raw=True
                )

        return IndicatorResult(
            name="MA",
            values=result_df,
            params={"periods": periods, "ma_type": self.ma_type, "column": column},
        )


def calculate_sma(
    prices: pd.Series,
    period: int,
) -> pd.Series:
    """
    Calculate Simple Moving Average.

    Convenience function for quick calculations.

    Args:
        prices: Price series
        period: MA period

    Returns:
        SMA series
    """
    validate_period(period)
    return prices.rolling(window=period).mean()


def calculate_ema(
    prices: pd.Series,
    period: int,
    adjust: bool = True,
) -> pd.Series:
    """
    Calculate Exponential Moving Average.

    Convenience function for quick calculations.

    Args:
        prices: Price series
        period: EMA period
        adjust: Whether to use adjusted calculation

    Returns:
        EMA series
    """
    validate_period(period)
    return prices.ewm(span=period, adjust=adjust).mean()
