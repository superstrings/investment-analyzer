"""
VCP (Volatility Contraction Pattern) Breakout Strategy.

A momentum strategy that buys when price breaks out of a VCP pattern,
as described by Mark Minervini's SEPA methodology.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

import pandas as pd

from analysis.indicators.vcp import VCP, VCPConfig

from ..strategy import Signal, SignalType, Strategy, StrategyConfig


@dataclass
class VCPBreakoutConfig(StrategyConfig):
    """Configuration for VCP breakout strategy."""

    # VCP detection parameters
    min_contractions: int = 2
    max_contractions: int = 4
    depth_decrease_ratio: float = 0.7  # Each contraction should be <= this * previous
    min_vcp_score: float = 60.0  # Minimum VCP score to trade

    # Breakout parameters
    breakout_buffer: float = 0.01  # Buy above pivot by this percentage
    volume_surge_ratio: float = 1.5  # Volume must be N times average

    # Exit parameters
    exit_below_pivot: bool = True  # Exit if price falls below pivot
    trailing_exit_atr: float = 2.0  # Exit if price falls N ATRs from high

    # Risk management (inherited from StrategyConfig)
    # stop_loss_pct: Optional[float] = 0.08  # 8% stop loss


class VCPBreakoutStrategy(Strategy):
    """VCP Breakout Strategy.

    Generates:
    - BUY signal when a VCP pattern is detected and price breaks above pivot
    - SELL signal when price falls back below pivot or trailing stop

    Based on Mark Minervini's Volatility Contraction Pattern methodology.
    """

    def __init__(self, config: Optional[VCPBreakoutConfig] = None):
        """Initialize strategy.

        Args:
            config: Strategy configuration
        """
        self.vcp_config = config or VCPBreakoutConfig()
        super().__init__(self.vcp_config)
        self.name = "VCPBreakout"

        # VCP detector
        self._vcp = VCP(
            config=VCPConfig(
                min_contractions=self.vcp_config.min_contractions,
                max_contractions=self.vcp_config.max_contractions,
                depth_decrease_ratio=self.vcp_config.depth_decrease_ratio,
            )
        )

        # State for tracking
        self._current_vcp = None
        self._pivot_price = None
        self._entry_high = None

    def generate_signals(self, data: pd.DataFrame) -> list[Signal]:
        """Generate buy/sell signals based on VCP breakouts.

        Args:
            data: DataFrame with OHLCV data

        Returns:
            List of signals
        """
        signals = []
        df = data.copy()

        # Need enough data for VCP detection
        if len(df) < 60:
            return signals

        # Calculate volume MA for surge detection
        df["volume_ma"] = df["volume"].rolling(window=20).mean()

        # Calculate ATR for trailing stop
        df["tr"] = pd.concat(
            [
                df["high"] - df["low"],
                abs(df["high"] - df["close"].shift(1)),
                abs(df["low"] - df["close"].shift(1)),
            ],
            axis=1,
        ).max(axis=1)
        df["atr"] = df["tr"].rolling(window=14).mean()

        # Scan for VCP patterns using rolling window
        window_size = 60
        in_position = False
        entry_price = 0
        pivot_price = 0
        highest_since_entry = 0

        for i in range(window_size, len(df)):
            row = df.iloc[i]
            window_data = df.iloc[i - window_size : i + 1]

            # Check for VCP pattern
            vcp_result = self._vcp.calculate(window_data)

            if not in_position:
                # Look for entry
                if (
                    vcp_result.is_vcp
                    and vcp_result.score >= self.vcp_config.min_vcp_score
                ):
                    pivot = vcp_result.pivot_price
                    breakout_price = pivot * (1 + self.vcp_config.breakout_buffer)

                    # Check for breakout
                    if row["high"] >= breakout_price:
                        # Check volume surge
                        if pd.notna(row["volume_ma"]) and row["volume_ma"] > 0:
                            vol_ratio = row["volume"] / row["volume_ma"]
                            if vol_ratio >= self.vcp_config.volume_surge_ratio:
                                signal = Signal(
                                    date=row["date"],
                                    signal_type=SignalType.BUY,
                                    price=breakout_price,
                                    reason=f"VCP突破 (得分:{vcp_result.score:.0f}, 收缩:{vcp_result.num_contractions}次)",
                                    confidence=min(vcp_result.score / 100, 1.0),
                                )
                                signals.append(signal)
                                in_position = True
                                entry_price = breakout_price
                                pivot_price = pivot
                                highest_since_entry = row["high"]
            else:
                # Look for exit
                highest_since_entry = max(highest_since_entry, row["high"])

                exit_signal = False
                exit_reason = ""

                # Exit if below pivot
                if self.vcp_config.exit_below_pivot and row["close"] < pivot_price:
                    exit_signal = True
                    exit_reason = f"跌破枢轴位 {pivot_price:.2f}"

                # Trailing stop based on ATR
                if pd.notna(row["atr"]) and row["atr"] > 0:
                    trailing_stop = (
                        highest_since_entry
                        - self.vcp_config.trailing_exit_atr * row["atr"]
                    )
                    if row["close"] < trailing_stop:
                        exit_signal = True
                        exit_reason = f"ATR跟踪止损 (最高:{highest_since_entry:.2f})"

                if exit_signal:
                    signal = Signal(
                        date=row["date"],
                        signal_type=SignalType.SELL,
                        price=row["close"],
                        reason=exit_reason,
                    )
                    signals.append(signal)
                    in_position = False
                    pivot_price = 0
                    highest_since_entry = 0

        return signals

    def get_parameters(self) -> dict:
        """Get strategy parameters."""
        params = super().get_parameters()
        params.update(
            {
                "min_contractions": self.vcp_config.min_contractions,
                "max_contractions": self.vcp_config.max_contractions,
                "min_vcp_score": self.vcp_config.min_vcp_score,
                "breakout_buffer": self.vcp_config.breakout_buffer,
                "volume_surge_ratio": self.vcp_config.volume_surge_ratio,
            }
        )
        return params
