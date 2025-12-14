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

from .technical import (
    TechnicalAnalyzer,
    AnalysisConfig,
    AnalysisResult,
    create_technical_analyzer,
    analyze_stock,
)

from .portfolio import (
    PortfolioAnalyzer,
    PortfolioAnalysisResult,
    PortfolioSummary,
    PositionMetrics,
    PositionData,
    AccountData,
    MarketAllocation,
    RiskMetrics,
    RiskLevel,
    analyze_portfolio,
    analyze_positions_from_db,
    create_portfolio_analyzer,
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
]
