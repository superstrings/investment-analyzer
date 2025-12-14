"""
Technical analysis module for Investment Analyzer.

This module provides comprehensive technical analysis capabilities including:
- Technical indicators (MA, MACD, RSI, Bollinger Bands, OBV)
- VCP (Volatility Contraction Pattern) detection
- Unified analysis framework (TechnicalAnalyzer)
- Signal generation and divergence detection

Usage:
    # Use individual indicators
    from analysis.indicators import RSI, MACD, BollingerBands

    rsi_result = RSI(period=14).calculate(df)

    # Use VCP pattern detection
    from analysis import detect_vcp, scan_vcp

    vcp_result = detect_vcp(df)
    if vcp_result.is_vcp:
        print(f"VCP Score: {vcp_result.score}")

    # Use the unified analyzer
    from analysis import TechnicalAnalyzer, AnalysisConfig

    analyzer = TechnicalAnalyzer()
    results = analyzer.analyze(df)
    summary = results.summary()
"""

from .technical import (
    TechnicalAnalyzer,
    AnalysisConfig,
    AnalysisResult,
    create_technical_analyzer,
    analyze_stock,
)

from .indicators import (
    # Base
    BaseIndicator,
    IndicatorResult,
    # Moving Averages
    SMA,
    EMA,
    WMA,
    MA,
    # MACD
    MACD,
    MACDCrossover,
    # RSI
    RSI,
    StochasticRSI,
    RSIDivergence,
    # Bollinger Bands
    BollingerBands,
    BollingerBandsSqueeze,
    BollingerBandsSignals,
    # OBV
    OBV,
    OBVDivergence,
    # VCP
    VCP,
    VCPScanner,
    VCPConfig,
    VCPResult,
    Contraction,
    detect_vcp,
    scan_vcp,
)

__all__ = [
    # Technical Analyzer
    "TechnicalAnalyzer",
    "AnalysisConfig",
    "AnalysisResult",
    "create_technical_analyzer",
    "analyze_stock",
    # Base
    "BaseIndicator",
    "IndicatorResult",
    # Moving Averages
    "SMA",
    "EMA",
    "WMA",
    "MA",
    # MACD
    "MACD",
    "MACDCrossover",
    # RSI
    "RSI",
    "StochasticRSI",
    "RSIDivergence",
    # Bollinger Bands
    "BollingerBands",
    "BollingerBandsSqueeze",
    "BollingerBandsSignals",
    # OBV
    "OBV",
    "OBVDivergence",
    # VCP
    "VCP",
    "VCPScanner",
    "VCPConfig",
    "VCPResult",
    "Contraction",
    "detect_vcp",
    "scan_vcp",
]
