"""
Technical and portfolio analysis module for Investment Analyzer.

This module provides comprehensive analysis capabilities including:
- Technical indicators (MA, MACD, RSI, Bollinger Bands, OBV)
- VCP (Volatility Contraction Pattern) detection
- Portfolio analysis (positions, P&L, risk metrics)
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

    # Use portfolio analysis
    from analysis import PortfolioAnalyzer, PositionData, analyze_portfolio

    positions = [PositionData(market="HK", code="00700", qty=100, cost_price=350)]
    result = analyze_portfolio(positions)
    print(f"Total P&L: {result.summary.total_pl_value}")

    # Use the unified technical analyzer
    from analysis import TechnicalAnalyzer, AnalysisConfig

    analyzer = TechnicalAnalyzer()
    results = analyzer.analyze(df)
    summary = results.summary()
"""

from .indicators import (  # Base; Moving Averages; MACD; RSI; Bollinger Bands; OBV; VCP
    EMA,
    MA,
    MACD,
    OBV,
    RSI,
    SMA,
    VCP,
    WMA,
    BaseIndicator,
    BollingerBands,
    BollingerBandsSignals,
    BollingerBandsSqueeze,
    Contraction,
    IndicatorResult,
    MACDCrossover,
    OBVDivergence,
    RSIDivergence,
    StochasticRSI,
    VCPConfig,
    VCPResult,
    VCPScanner,
    detect_vcp,
    scan_vcp,
    # Chart Patterns
    PatternType,
    PatternBias,
    PatternResult,
    CupAndHandle,
    HeadAndShoulders,
    DoubleTopBottom,
    TrianglePattern,
    PatternScanner,
    detect_patterns,
    # Support and Resistance
    LevelType,
    LevelStrength,
    PriceLevel,
    SupportResistanceResult,
    SRConfig,
    SupportResistance,
    find_support_resistance,
    get_key_levels,
    # Trendlines
    TrendDirection,
    TrendlineType,
    Trendline,
    TrendlineResult,
    TrendlineConfig,
    TrendlineDetector,
    detect_trendlines,
    get_trend_direction,
)
from .portfolio import (
    AccountData,
    MarketAllocation,
    PortfolioAnalysisResult,
    PortfolioAnalyzer,
    PortfolioSummary,
    PositionData,
    PositionMetrics,
    RiskLevel,
    RiskMetrics,
    analyze_portfolio,
    analyze_positions_from_db,
    create_portfolio_analyzer,
)
from .technical import (
    AnalysisConfig,
    AnalysisResult,
    TechnicalAnalyzer,
    analyze_stock,
    create_technical_analyzer,
)

__all__ = [
    # Technical Analyzer
    "TechnicalAnalyzer",
    "AnalysisConfig",
    "AnalysisResult",
    "create_technical_analyzer",
    "analyze_stock",
    # Portfolio Analyzer
    "PortfolioAnalyzer",
    "PortfolioAnalysisResult",
    "PortfolioSummary",
    "PositionMetrics",
    "PositionData",
    "AccountData",
    "MarketAllocation",
    "RiskMetrics",
    "RiskLevel",
    "analyze_portfolio",
    "analyze_positions_from_db",
    "create_portfolio_analyzer",
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
