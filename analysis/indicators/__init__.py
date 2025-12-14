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

# Bollinger Bands
from .bollinger import (
    BollingerBands,
    BollingerBandsSignals,
    BollingerBandsSqueeze,
    calculate_bollinger_bands,
)

# Moving Averages
from .ma import (
    EMA,
    MA,
    SMA,
    WMA,
    calculate_ema,
    calculate_sma,
)

# MACD
from .macd import (
    MACD,
    MACDCrossover,
    MACDHistogramDivergence,
    calculate_macd,
)

# On-Balance Volume
from .obv import (
    OBV,
    OBVDivergence,
    calculate_obv,
)

# RSI
from .rsi import (
    RSI,
    RSIDivergence,
    StochasticRSI,
    calculate_rsi,
)

# VCP (Volatility Contraction Pattern)
from .vcp import (
    VCP,
    Contraction,
    VCPConfig,
    VCPResult,
    VCPScanner,
    detect_vcp,
    scan_vcp,
)

# Chart Patterns
from .patterns import (
    PatternType,
    PatternBias,
    PatternResult,
    CupAndHandle,
    HeadAndShoulders,
    DoubleTopBottom,
    TrianglePattern,
    PatternScanner,
    detect_patterns,
)

# Support and Resistance
from .support_resistance import (
    LevelType,
    LevelStrength,
    PriceLevel,
    SupportResistanceResult,
    SRConfig,
    SupportResistance,
    find_support_resistance,
    get_key_levels,
)

# Trendlines
from .trendline import (
    TrendDirection,
    TrendlineType,
    Trendline,
    TrendlineResult,
    TrendlineConfig,
    TrendlineDetector,
    detect_trendlines,
    get_trend_direction,
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
    # Chart Patterns
    "PatternType",
    "PatternBias",
    "PatternResult",
    "CupAndHandle",
    "HeadAndShoulders",
    "DoubleTopBottom",
    "TrianglePattern",
    "PatternScanner",
    "detect_patterns",
    # Support and Resistance
    "LevelType",
    "LevelStrength",
    "PriceLevel",
    "SupportResistanceResult",
    "SRConfig",
    "SupportResistance",
    "find_support_resistance",
    "get_key_levels",
    # Trendlines
    "TrendDirection",
    "TrendlineType",
    "Trendline",
    "TrendlineResult",
    "TrendlineConfig",
    "TrendlineDetector",
    "detect_trendlines",
    "get_trend_direction",
]
