"""
Business services module for Investment Analyzer.

Provides high-level services for data synchronization, chart generation, and reporting.

Usage:
    from services import SyncService, SyncResult, create_sync_service
    from services import ChartService, ChartResult, BatchChartConfig, create_chart_service
    from fetchers import FutuFetcher, KlineFetcher

    # Create sync service with fetchers
    futu = FutuFetcher()
    kline = KlineFetcher()
    sync = SyncService(futu_fetcher=futu, kline_fetcher=kline)

    # Sync all data for a user
    results = sync.sync_all(user_id=1)

    # Create chart service
    chart_service = ChartService(kline_fetcher=kline)

    # Generate watchlist charts
    result = chart_service.generate_watchlist_charts(user_id=1)
"""

from .chart_service import (
    BatchChartConfig,
    ChartResult,
    ChartService,
    create_chart_service,
)
from .sync_service import SyncResult, SyncService, create_sync_service

__all__ = [
    # Sync service
    "SyncService",
    "SyncResult",
    "create_sync_service",
    # Chart service
    "ChartService",
    "ChartResult",
    "BatchChartConfig",
    "create_chart_service",
]
