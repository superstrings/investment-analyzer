"""
Built-in trading strategies for backtesting.

Provides example strategies:
- MACrossStrategy: Moving average crossover
- VCPBreakoutStrategy: VCP pattern breakout
"""

from .ma_cross import MACrossConfig, MACrossStrategy
from .vcp_breakout import VCPBreakoutConfig, VCPBreakoutStrategy

__all__ = [
    "MACrossStrategy",
    "MACrossConfig",
    "VCPBreakoutStrategy",
    "VCPBreakoutConfig",
]
