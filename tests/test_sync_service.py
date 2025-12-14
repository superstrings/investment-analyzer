"""Tests for SyncService module.

Tests the data synchronization service with mocked fetchers and database.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from fetchers import FetchResult, Market, PositionSide, TradeSide
from fetchers.base import AccountInfo, AccountType, PositionInfo, TradeInfo
from fetchers.kline_fetcher import KlineData, KlineFetchResult
from services import SyncResult, SyncService, create_sync_service


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_ok_result(self):
        """Test creating successful result."""
        result = SyncResult.ok(
            sync_type="POSITIONS",
            records_synced=10,
            records_skipped=2,
            duration=1.5,
            details={"accounts": {123: {"synced": 10}}},
        )
        assert result.success is True
        assert result.sync_type == "POSITIONS"
        assert result.records_synced == 10
        assert result.records_skipped == 2
        assert result.duration_seconds == 1.5
        assert result.error_message == ""

    def test_error_result(self):
        """Test creating error result."""
        result = SyncResult.error("TRADES", "Connection failed")
        assert result.success is False
        assert result.sync_type == "TRADES"
        assert result.error_message == "Connection failed"
        assert result.records_synced == 0

    def test_ok_result_defaults(self):
        """Test OK result with defaults."""
        result = SyncResult.ok("KLINES", records_synced=5)
        assert result.success is True
        assert result.records_skipped == 0
        assert result.duration_seconds == 0.0
        assert result.details == {}


class TestSyncServiceInit:
    """Tests for SyncService initialization."""

    def test_default_init(self):
        """Test default initialization."""
        service = SyncService()
        assert service.futu_fetcher is None
        assert service.kline_fetcher is not None

    def test_init_with_fetchers(self):
        """Test initialization with fetchers."""
        mock_futu = MagicMock()
        mock_kline = MagicMock()
        service = SyncService(futu_fetcher=mock_futu, kline_fetcher=mock_kline)
        assert service.futu_fetcher is mock_futu
        assert service.kline_fetcher is mock_kline


class TestSyncServicePositions:
    """Tests for sync_positions method."""

    def test_no_futu_fetcher(self):
        """Test error when FutuFetcher not configured."""
        service = SyncService()
        result = service.sync_positions(user_id=1)
        assert result.success is False
        assert "FutuFetcher not configured" in result.error_message

    @patch("services.sync_service.get_session")
    def test_user_not_found(self, mock_get_session):
        """Test error when user not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_futu = MagicMock()
        service = SyncService(futu_fetcher=mock_futu)
        result = service.sync_positions(user_id=999)

        assert result.success is False
        assert "User 999 not found" in result.error_message

    @patch("services.sync_service.get_session")
    def test_no_accounts(self, mock_get_session):
        """Test error when no active accounts."""
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_session.get.return_value = mock_user
        mock_session.scalars.return_value.all.return_value = []
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_futu = MagicMock()
        service = SyncService(futu_fetcher=mock_futu)
        result = service.sync_positions(user_id=1)

        assert result.success is False
        assert "No active accounts" in result.error_message

    @patch("services.sync_service.get_session")
    def test_sync_positions_success(self, mock_get_session):
        """Test successful position sync."""
        # Setup mock session
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_account.futu_acc_id = 123456

        mock_session.get.return_value = mock_user
        mock_session.scalars.return_value.all.return_value = [mock_account]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Setup mock Futu fetcher
        mock_futu = MagicMock()
        mock_positions = [
            PositionInfo(
                market=Market.HK,
                code="00700",
                stock_name="腾讯控股",
                qty=Decimal("100"),
                cost_price=Decimal("350.00"),
                market_price=Decimal("380.00"),
                market_val=Decimal("38000"),
                pl_val=Decimal("3000"),
                pl_ratio=Decimal("0.0857"),
            )
        ]
        mock_futu.get_positions.return_value = FetchResult.ok(mock_positions)
        mock_futu.get_account_info.return_value = FetchResult.ok(
            [
                AccountInfo(
                    acc_id=123456,
                    account_type=AccountType.REAL,
                    market=Market.HK,
                    total_assets=Decimal("100000"),
                    cash=Decimal("62000"),
                )
            ]
        )

        service = SyncService(futu_fetcher=mock_futu)
        result = service.sync_positions(user_id=1)

        assert result.success is True
        assert result.sync_type == "POSITIONS"
        assert result.records_synced >= 0


class TestSyncServiceTrades:
    """Tests for sync_trades method."""

    def test_no_futu_fetcher(self):
        """Test error when FutuFetcher not configured."""
        service = SyncService()
        result = service.sync_trades(user_id=1)
        assert result.success is False
        assert "FutuFetcher not configured" in result.error_message

    @patch("services.sync_service.get_session")
    def test_user_not_found(self, mock_get_session):
        """Test error when user not found."""
        mock_session = MagicMock()
        mock_session.get.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_futu = MagicMock()
        service = SyncService(futu_fetcher=mock_futu)
        result = service.sync_trades(user_id=999)

        assert result.success is False
        assert "User 999 not found" in result.error_message

    @patch("services.sync_service.get_session")
    def test_sync_trades_success(self, mock_get_session):
        """Test successful trades sync."""
        # Setup mock session
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_account.futu_acc_id = 123456

        mock_session.get.return_value = mock_user
        mock_session.scalars.return_value.all.return_value = [mock_account]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Setup mock Futu fetcher
        mock_futu = MagicMock()
        mock_trades = [
            TradeInfo(
                deal_id="DEAL001",
                market=Market.HK,
                code="00700",
                stock_name="腾讯控股",
                trd_side=TradeSide.BUY,
                qty=Decimal("100"),
                price=Decimal("350.00"),
                trade_time=datetime(2025, 12, 14, 10, 30, 0),
            )
        ]
        mock_futu.get_history_deals.return_value = FetchResult.ok(mock_trades)

        service = SyncService(futu_fetcher=mock_futu)
        result = service.sync_trades(user_id=1, days=30)

        assert result.success is True
        assert result.sync_type == "TRADES"


class TestSyncServiceKlines:
    """Tests for sync_klines method."""

    @patch("services.sync_service.get_session")
    def test_sync_klines_success(self, mock_get_session):
        """Test successful K-line sync."""
        # Setup mock session
        mock_session = MagicMock()
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        # Setup mock kline fetcher
        mock_kline = MagicMock()
        mock_kline_data = [
            KlineData(
                market=Market.HK,
                code="00700",
                trade_date=date(2025, 12, 14),
                open=Decimal("380.00"),
                high=Decimal("385.00"),
                low=Decimal("378.00"),
                close=Decimal("382.50"),
                volume=1000000,
            )
        ]
        mock_kline.fetch.return_value = KlineFetchResult.ok_with_df(
            mock_kline_data, MagicMock()
        )

        service = SyncService(kline_fetcher=mock_kline)
        result = service.sync_klines(codes=["HK.00700"], days=5)

        assert result.success is True
        assert result.sync_type == "KLINES"
        mock_kline.fetch.assert_called_once()

    @patch("services.sync_service.get_session")
    def test_sync_klines_fetch_failure(self, mock_get_session):
        """Test K-line sync with fetch failure."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_kline = MagicMock()
        mock_kline.fetch.return_value = KlineFetchResult.error("Network error")

        service = SyncService(kline_fetcher=mock_kline)
        result = service.sync_klines(codes=["HK.00700"], days=5)

        # Should still succeed overall, just with error details
        assert result.success is True
        assert "HK.00700" in result.details.get("codes", {})

    @patch("services.sync_service.get_session")
    def test_sync_multiple_codes(self, mock_get_session):
        """Test syncing multiple stock codes."""
        mock_session = MagicMock()
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_kline = MagicMock()

        def mock_fetch(code, **kwargs):
            return KlineFetchResult.ok_with_df(
                [
                    KlineData(
                        market=Market.HK if "HK" in code else Market.US,
                        code=code.split(".")[-1],
                        trade_date=date(2025, 12, 14),
                        open=Decimal("100"),
                        high=Decimal("110"),
                        low=Decimal("95"),
                        close=Decimal("105"),
                    )
                ],
                MagicMock(),
            )

        mock_kline.fetch.side_effect = mock_fetch

        service = SyncService(kline_fetcher=mock_kline)
        result = service.sync_klines(codes=["HK.00700", "US.NVDA"], days=5)

        assert result.success is True
        assert mock_kline.fetch.call_count == 2


class TestSyncServiceWatchlist:
    """Tests for sync_watchlist_klines method."""

    @patch("services.sync_service.get_session")
    def test_sync_watchlist_klines(self, mock_get_session):
        """Test syncing K-lines for watchlist."""
        mock_session = MagicMock()
        mock_watchlist_item = MagicMock()
        mock_watchlist_item.full_code = "HK.00700"
        mock_session.scalars.return_value.all.return_value = [mock_watchlist_item]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_kline = MagicMock()
        mock_kline.fetch.return_value = KlineFetchResult.ok_with_df([], MagicMock())

        service = SyncService(kline_fetcher=mock_kline)
        result = service.sync_watchlist_klines(user_id=1, days=60)

        assert result.success is True
        assert result.sync_type == "KLINES"


class TestSyncServicePositionKlines:
    """Tests for sync_position_klines method."""

    @patch("services.sync_service.get_session")
    def test_sync_position_klines(self, mock_get_session):
        """Test syncing K-lines for positions."""
        mock_session = MagicMock()
        mock_position = MagicMock()
        mock_position.market = "HK"
        mock_position.code = "00700"
        mock_session.scalars.return_value.all.return_value = [mock_position]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_kline = MagicMock()
        mock_kline.fetch.return_value = KlineFetchResult.ok_with_df([], MagicMock())

        service = SyncService(kline_fetcher=mock_kline)
        result = service.sync_position_klines(user_id=1, days=60)

        assert result.success is True
        assert result.sync_type == "KLINES"


class TestSyncServiceAll:
    """Tests for sync_all method."""

    @patch("services.sync_service.get_session")
    def test_sync_all_no_futu(self, mock_get_session):
        """Test sync_all without FutuFetcher."""
        mock_session = MagicMock()
        mock_session.scalars.return_value.all.return_value = []
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        service = SyncService()
        results = service.sync_all(user_id=1)

        assert "positions" in results
        assert results["positions"].success is False

    @patch("services.sync_service.get_session")
    def test_sync_all_with_fetchers(self, mock_get_session):
        """Test sync_all with all fetchers configured."""
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_account.futu_acc_id = 123456

        mock_session.get.return_value = mock_user
        mock_session.scalars.return_value.all.return_value = [mock_account]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_futu = MagicMock()
        mock_futu.get_positions.return_value = FetchResult.ok([])
        mock_futu.get_history_deals.return_value = FetchResult.ok([])
        mock_futu.get_account_info.return_value = FetchResult.ok([])

        mock_kline = MagicMock()
        mock_kline.fetch.return_value = KlineFetchResult.ok_with_df([], MagicMock())

        service = SyncService(futu_fetcher=mock_futu, kline_fetcher=mock_kline)
        results = service.sync_all(user_id=1, include_klines=True)

        assert "positions" in results
        assert "trades" in results
        assert "position_klines" in results
        assert "watchlist_klines" in results

    @patch("services.sync_service.get_session")
    def test_sync_all_without_klines(self, mock_get_session):
        """Test sync_all without K-line sync."""
        mock_session = MagicMock()
        mock_user = MagicMock()
        mock_account = MagicMock()
        mock_account.id = 1
        mock_account.futu_acc_id = 123456

        mock_session.get.return_value = mock_user
        mock_session.scalars.return_value.all.return_value = [mock_account]
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        mock_futu = MagicMock()
        mock_futu.get_positions.return_value = FetchResult.ok([])
        mock_futu.get_history_deals.return_value = FetchResult.ok([])
        mock_futu.get_account_info.return_value = FetchResult.ok([])

        service = SyncService(futu_fetcher=mock_futu)
        results = service.sync_all(user_id=1, include_klines=False)

        assert "positions" in results
        assert "trades" in results
        assert "position_klines" not in results
        assert "watchlist_klines" not in results


class TestSyncServiceLastSync:
    """Tests for get_last_sync method."""

    @patch("services.sync_service.get_session")
    def test_get_last_sync(self, mock_get_session):
        """Test getting last sync log."""
        mock_session = MagicMock()
        mock_log = MagicMock()
        mock_log.sync_type = "POSITIONS"
        mock_log.status = "SUCCESS"
        mock_session.scalars.return_value.first.return_value = mock_log
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        service = SyncService()
        result = service.get_last_sync(user_id=1, sync_type="POSITIONS")

        assert result is not None
        assert result.sync_type == "POSITIONS"

    @patch("services.sync_service.get_session")
    def test_get_last_sync_none(self, mock_get_session):
        """Test getting last sync log when none exists."""
        mock_session = MagicMock()
        mock_session.scalars.return_value.first.return_value = None
        mock_get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_get_session.return_value.__exit__ = MagicMock(return_value=False)

        service = SyncService()
        result = service.get_last_sync(user_id=1, sync_type="POSITIONS")

        assert result is None


class TestCreateSyncService:
    """Tests for create_sync_service factory function."""

    def test_create_without_args(self):
        """Test creating service without arguments."""
        service = create_sync_service()
        assert service.futu_fetcher is None
        assert service.kline_fetcher is not None

    def test_create_with_fetchers(self):
        """Test creating service with fetchers."""
        mock_futu = MagicMock()
        mock_kline = MagicMock()
        service = create_sync_service(
            futu_fetcher=mock_futu,
            kline_fetcher=mock_kline,
        )
        assert service.futu_fetcher is mock_futu
        assert service.kline_fetcher is mock_kline
