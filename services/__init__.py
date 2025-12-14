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

from .alert_service import (
    AlertResult,
    AlertService,
    AlertSummary,
    AlertType,
    create_alert_service,
)
from .chart_service import (
    BatchChartConfig,
    ChartResult,
    ChartService,
    create_chart_service,
)
from .export_service import (
    DateRange,
    ExportConfig,
    ExportFormat,
    ExportResult,
    ExportService,
    create_export_service,
    export_all_to_excel,
    export_klines_to_csv,
    export_positions_to_csv,
    export_trades_to_csv,
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
    # Alert service
    "AlertService",
    "AlertResult",
    "AlertSummary",
    "AlertType",
    "create_alert_service",
    # Export service
    "ExportService",
    "ExportResult",
    "ExportConfig",
    "ExportFormat",
    "DateRange",
    "create_export_service",
    "export_positions_to_csv",
    "export_trades_to_csv",
    "export_klines_to_csv",
    "export_all_to_excel",
]
