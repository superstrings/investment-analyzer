"""
Analyst Skill - Technical Analysis with OBV + VCP.

Provides comprehensive technical analysis focusing on:
- OBV (On-Balance Volume): 量价关系分析
- VCP (Volatility Contraction Pattern): 波动收缩形态

Scoring: OBV (40%) + VCP (60%) = Technical Score

Usage:
    from skills.analyst import StockAnalyzer, BatchAnalyzer

    # Single stock analysis
    analyzer = StockAnalyzer()
    result = analyzer.analyze_from_db("HK", "00700", days=120)
    print(f"Score: {result.technical_score.final_score}")

    # Batch analysis
    batch = BatchAnalyzer()
    results = batch.analyze_user_stocks(user_id=1)
    for stock in results.top_overall:
        print(f"{stock.code}: {stock.technical_score.rating.value}")
"""

from .batch_analyzer import BatchAnalyzer, BatchAnalysisResult, generate_batch_report
from .obv_analyzer import (
    DivergenceType,
    OBVAnalysisResult,
    OBVAnalyzer,
    OBVTrend,
)
from .scoring import (
    ScoringSystem,
    SignalStrength,
    TechnicalRating,
    TechnicalScore,
    calculate_technical_score,
)
from .stock_analyzer import (
    StockAnalysis,
    StockAnalyzer,
    generate_analysis_report,
)
from .vcp_scanner import (
    VCPAnalysisResult,
    VCPScanner,
    VCPStage,
    scan_stocks_for_vcp,
)

__all__ = [
    # Main analyzers
    "StockAnalyzer",
    "BatchAnalyzer",
    # OBV
    "OBVAnalyzer",
    "OBVAnalysisResult",
    "OBVTrend",
    "DivergenceType",
    # VCP
    "VCPScanner",
    "VCPAnalysisResult",
    "VCPStage",
    "scan_stocks_for_vcp",
    # Scoring
    "ScoringSystem",
    "TechnicalScore",
    "TechnicalRating",
    "SignalStrength",
    "calculate_technical_score",
    # Results
    "StockAnalysis",
    "BatchAnalysisResult",
    # Report generation
    "generate_analysis_report",
    "generate_batch_report",
]
