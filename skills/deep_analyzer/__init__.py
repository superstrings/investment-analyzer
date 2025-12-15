"""
Deep Analyzer Skill - Comprehensive Stock Analysis.

Combines technical analysis, fundamental data, news, and industry analysis
to provide comprehensive investment recommendations for trend traders
seeking compound growth opportunities.
"""

from .deep_analyzer import (
    DeepAnalysisResult,
    DeepAnalyzer,
    InvestmentRecommendation,
)
from .report_generator import generate_deep_analysis_report
from .technical_analyzer import (
    EnhancedTechnicalAnalyzer,
    EnhancedTechnicalResult,
    MACDSignal,
    RSIAnalysis,
    SupportResistance,
    TrendAnalysis,
)
from .web_data_fetcher import (
    FundamentalData,
    IndustryData,
    NewsItem,
    WebDataFetcher,
    WebDataResult,
)

__all__ = [
    # Main analyzer
    "DeepAnalyzer",
    "DeepAnalysisResult",
    "InvestmentRecommendation",
    # Technical analysis
    "EnhancedTechnicalAnalyzer",
    "EnhancedTechnicalResult",
    "TrendAnalysis",
    "MACDSignal",
    "RSIAnalysis",
    "SupportResistance",
    # Web data
    "WebDataFetcher",
    "WebDataResult",
    "FundamentalData",
    "NewsItem",
    "IndustryData",
    # Report
    "generate_deep_analysis_report",
]
