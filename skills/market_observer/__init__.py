"""
Market Observer Skill package.

Provides pre-market analysis, post-market summary, sector rotation, and sentiment.
"""

from .market_observer import (
    MarketObserver,
    MarketObserverResult,
    generate_observation_report,
)
from .post_market import (
    AnomalyStock,
    MarketSummary,
    PositionDailySummary,
    PostMarketReport,
    PostMarketSummarizer,
    TradeSummary,
)
from .pre_market import (
    EventInfo,
    GlobalMarketSnapshot,
    PreMarketAnalyzer,
    PreMarketReport,
    StockPreMarketInfo,
)
from .sector_rotation import (
    MoneyFlowData,
    RotationSignal,
    SectorAnalysisReport,
    SectorPerformance,
    SectorRotationAnalyzer,
)
from .sentiment_meter import (
    MarketIndicators,
    SentimentLevel,
    SentimentMeter,
    SentimentResult,
)

__all__ = [
    # Main controller
    "MarketObserver",
    "MarketObserverResult",
    "generate_observation_report",
    # Pre-market
    "PreMarketAnalyzer",
    "PreMarketReport",
    "GlobalMarketSnapshot",
    "EventInfo",
    "StockPreMarketInfo",
    # Post-market
    "PostMarketSummarizer",
    "PostMarketReport",
    "MarketSummary",
    "PositionDailySummary",
    "TradeSummary",
    "AnomalyStock",
    # Sector rotation
    "SectorRotationAnalyzer",
    "SectorAnalysisReport",
    "SectorPerformance",
    "MoneyFlowData",
    "RotationSignal",
    # Sentiment
    "SentimentMeter",
    "SentimentResult",
    "SentimentLevel",
    "MarketIndicators",
]
