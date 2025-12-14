"""
Moving Average Crossover Strategy.

A classic trend-following strategy that generates buy signals when
a fast MA crosses above a slow MA, and sell signals when it crosses below.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from ..strategy import Signal, SignalType, Strategy, StrategyConfig


@dataclass
class MACrossConfig(StrategyConfig):
    """Configuration for MA crossover strategy."""

    fast_period: int = 10  # Fast MA period
    slow_period: int = 30  # Slow MA period
    ma_type: str = "SMA"  # SMA or EMA
    require_volume_confirm: bool = False  # Require volume above average
    volume_ma_period: int = 20  # Period for volume MA


class MACrossStrategy(Strategy):
    """Moving Average Crossover Strategy.

    Generates:
    - BUY signal when fast MA crosses above slow MA
    - SELL signal when fast MA crosses below slow MA

    Optional volume confirmation can be enabled.
    """

    def __init__(self, config: Optional[MACrossConfig] = None):
        """Initialize strategy.

        Args:
            config: Strategy configuration
        """
        self.ma_config = config or MACrossConfig()
        super().__init__(self.ma_config)
        self.name = (
            f"MACross({self.ma_config.fast_period}/{self.ma_config.slow_period})"
        )

    def _calculate_ma(self, series: pd.Series, period: int) -> pd.Series:
        """Calculate moving average.

        Args:
            series: Price series
            period: MA period

        Returns:
            MA series
        """
        if self.ma_config.ma_type.upper() == "EMA":
            return series.ewm(span=period, adjust=False).mean()
        else:  # SMA
            return series.rolling(window=period).mean()

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate buy/sell signals based on MA crossover.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of signals
        """
        signals = []

        # Handle empty data
        if data.empty or "close" not in data.columns:
            return signals

        df = data.copy()

        # Calculate MAs
        df["fast_ma"] = self._calculate_ma(df["close"], self.ma_config.fast_period)
        df["slow_ma"] = self._calculate_ma(df["close"], self.ma_config.slow_period)

        # Calculate volume MA if needed
        if self.ma_config.require_volume_confirm and "volume" in df.columns:
            df["volume_ma"] = (
                df["volume"].rolling(window=self.ma_config.volume_ma_period).mean()
            )

        # Detect crossovers
        df["fast_above"] = df["fast_ma"] > df["slow_ma"]
        df["prev_fast_above"] = df["fast_above"].shift(1)

        # Start from where we have valid MAs
        start_idx = max(self.ma_config.fast_period, self.ma_config.slow_period)

        for idx in range(start_idx, len(df)):
            row = df.iloc[idx]
            prev_row = df.iloc[idx - 1]

            # Check for golden cross (buy signal)
            if row["fast_above"] and not prev_row["fast_above"]:
                # Volume confirmation
                if self.ma_config.require_volume_confirm:
                    if "volume_ma" in df.columns and pd.notna(row["volume_ma"]):
                        if row["volume"] <= row["volume_ma"]:
                            continue

                signal = Signal(
                    date=row["date"],
                    signal_type=SignalType.BUY,
                    price=row["close"],
                    reason=f"金叉: MA{self.ma_config.fast_period}上穿MA{self.ma_config.slow_period}",
                    confidence=0.8,
                )
                signals.append(signal)

            # Check for death cross (sell signal)
            elif not row["fast_above"] and prev_row["fast_above"]:
                signal = Signal(
                    date=row["date"],
                    signal_type=SignalType.SELL,
                    price=row["close"],
                    reason=f"死叉: MA{self.ma_config.fast_period}下穿MA{self.ma_config.slow_period}",
                    confidence=0.8,
                )
                signals.append(signal)

        return signals

    def get_parameters(self) -> dict:
        """Get strategy parameters."""
        params = super().get_parameters()
        params.update(
            {
                "fast_period": self.ma_config.fast_period,
                "slow_period": self.ma_config.slow_period,
                "ma_type": self.ma_config.ma_type,
                "require_volume_confirm": self.ma_config.require_volume_confirm,
            }
        )
        return params
