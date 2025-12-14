"""
Data fetchers module for Investment Analyzer.

This module provides data fetching capabilities from various sources:
- FutuFetcher: Fetches trading data from Futu OpenD
- KlineFetcher: Fetches K-line data from akshare

Usage:
    from fetchers import FutuFetcher, KlineFetcher, FetchResult

    # FutuFetcher - Using context manager (recommended)
    with FutuFetcher(host="127.0.0.1", port=11111) as fetcher:
        fetcher.unlock_trade("password")
        result = fetcher.get_positions(acc_id=123456)
        if result.success:
            for pos in result.data:
                print(pos.code, pos.qty)

    # KlineFetcher - Fetch K-line data
    kline_fetcher = KlineFetcher()
    result = kline_fetcher.fetch("HK.00700", days=120)
    if result.success:
        for kline in result.data:
            print(kline.trade_date, kline.close)
"""

from .base import (
    AccountInfo,
    AccountType,
    BaseFetcher,
    FetchResult,
    Market,
    PositionInfo,
    PositionSide,
    TradeInfo,
    TradeSide,
)
from .futu_fetcher import FutuFetcher, create_futu_fetcher
from .kline_fetcher import (
    KlineData,
    KlineFetchResult,
    KlineFetcher,
    create_kline_fetcher,
)

__all__ = [
    # Base classes and types
    "BaseFetcher",
    "FetchResult",
    "Market",
    "TradeSide",
    "AccountType",
    "PositionSide",
    # Data classes
    "AccountInfo",
    "PositionInfo",
    "TradeInfo",
    "KlineData",
    "KlineFetchResult",
    # Fetchers
    "FutuFetcher",
    "create_futu_fetcher",
    "KlineFetcher",
    "create_kline_fetcher",
]
