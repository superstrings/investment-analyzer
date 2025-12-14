"""
Technical indicators submodule.

This module provides various technical analysis indicators for financial data.

Indicators included:
- Moving Averages (SMA, EMA, WMA)
- MACD (Moving Average Convergence Divergence)
- RSI (Relative Strength Index)
- Bollinger Bands
- OBV (On-Balance Volume)

Usage:
    from analysis.indicators import RSI, MACD, BollingerBands

    # Calculate RSI
    result = RSI(period=14).calculate(df)
    rsi_values = result.values

    # Calculate MACD
    result = MACD().calculate(df)
    macd_df = result.values  # DataFrame with MACD, signal, histogram
"""

from .base import BaseIndicator, IndicatorResult, validate_period

# Moving Averages
from .ma import (
    SMA,
    EMA,
    WMA,
    MA,
    calculate_sma,
    calculate_ema,
)

# MACD
from .macd import (
    MACD,
    MACDCrossover,
    MACDHistogramDivergence,
    calculate_macd,
)

# RSI
from .rsi import (
    RSI,
    StochasticRSI,
    RSIDivergence,
    calculate_rsi,
)

# Bollinger Bands
from .bollinger import (
    BollingerBands,
    BollingerBandsSqueeze,
    BollingerBandsSignals,
    calculate_bollinger_bands,
)

# On-Balance Volume
from .obv import (
    OBV,
    OBVDivergence,
    calculate_obv,
)

# VCP (Volatility Contraction Pattern)
from .vcp import (
    VCP,
    VCPScanner,
    VCPConfig,
    VCPResult,
    Contraction,
    detect_vcp,
    scan_vcp,
)

__all__ = [
    # Base
    "BaseIndicator",
    "IndicatorResult",
    "validate_period",
    # Moving Averages
    "SMA",
    "EMA",
    "WMA",
    "MA",
    "calculate_sma",
    "calculate_ema",
    # MACD
    "MACD",
    "MACDCrossover",
    "MACDHistogramDivergence",
    "calculate_macd",
    # RSI
    "RSI",
    "StochasticRSI",
    "RSIDivergence",
    "calculate_rsi",
    # Bollinger Bands
    "BollingerBands",
    "BollingerBandsSqueeze",
    "BollingerBandsSignals",
    "calculate_bollinger_bands",
    # OBV
    "OBV",
    "OBVDivergence",
    "calculate_obv",
    # VCP
    "VCP",
    "VCPScanner",
    "VCPConfig",
    "VCPResult",
    "Contraction",
    "detect_vcp",
    "scan_vcp",
]
