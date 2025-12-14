"""Tests for database module.

Uses SQLite in-memory database for testing models without PostgreSQL.
"""

from datetime import date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import (
    Account,
    AccountSnapshot,
    Base,
    Kline,
    Position,
    SyncLog,
    Trade,
    User,
    WatchlistItem,
)


@pytest.fixture
def engine():
    """Create in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Create a test session."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.rollback()
    session.close()


class TestUserModel:
    """Tests for User model."""

    def test_create_user(self, session: Session):
        """Test creating a user."""
        user = User(
            username="testuser",
            display_name="Test User",
            opend_host="127.0.0.1",
            opend_port=11111,
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.is_active is True

    def test_user_defaults(self, session: Session):
        """Test user default values."""
        user = User(username="defaultuser")
        session.add(user)
        session.commit()

        assert user.opend_host == "127.0.0.1"
        assert user.opend_port == 11111
        assert user.is_active is True
        assert user.created_at is not None

    def test_user_repr(self, session: Session):
        """Test user string representation."""
        user = User(username="repruser")
        session.add(user)
        session.commit()

        assert "repruser" in repr(user)
        assert str(user.id) in repr(user)

    def test_user_unique_username(self, session: Session):
        """Test username uniqueness constraint."""
        user1 = User(username="unique")
        session.add(user1)
        session.commit()

        user2 = User(username="unique")
        session.add(user2)
        with pytest.raises(Exception):  # IntegrityError
            session.commit()


class TestAccountModel:
    """Tests for Account model."""

    def test_create_account(self, session: Session):
        """Test creating an account."""
        user = User(username="accountuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            futu_acc_id=123456789,
            account_name="Test Account",
            account_type="REAL",
            market="HK",
            currency="HKD",
        )
        session.add(account)
        session.commit()

        assert account.id is not None
        assert account.futu_acc_id == 123456789
        assert account.market == "HK"

    def test_account_user_relationship(self, session: Session):
        """Test account-user relationship."""
        user = User(username="reluser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            futu_acc_id=111111,
            account_type="SIMULATE",
            market="US",
        )
        session.add(account)
        session.commit()

        # Test relationship
        assert account.user == user
        assert account in user.accounts

    def test_account_repr(self, session: Session):
        """Test account string representation."""
        user = User(username="repraccuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            futu_acc_id=999999,
            account_type="REAL",
            market="HK",
        )
        session.add(account)
        session.commit()

        assert "999999" in repr(account)
        assert "HK" in repr(account)


class TestPositionModel:
    """Tests for Position model."""

    def test_create_position(self, session: Session):
        """Test creating a position."""
        user = User(username="posuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id,
            futu_acc_id=111,
            account_type="REAL",
            market="HK",
        )
        session.add(account)
        session.commit()

        position = Position(
            account_id=account.id,
            snapshot_date=date(2025, 12, 14),
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            qty=Decimal("100"),
            cost_price=Decimal("350.50"),
            market_price=Decimal("380.00"),
            market_val=Decimal("38000.00"),
            pl_val=Decimal("2950.00"),
            pl_ratio=Decimal("0.0842"),
        )
        session.add(position)
        session.commit()

        assert position.id is not None
        assert position.qty == Decimal("100")
        assert position.position_side == "LONG"

    def test_position_repr(self, session: Session):
        """Test position string representation."""
        user = User(username="posrepruser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, futu_acc_id=222, account_type="REAL", market="HK"
        )
        session.add(account)
        session.commit()

        position = Position(
            account_id=account.id,
            snapshot_date=date.today(),
            market="HK",
            code="00700",
            qty=Decimal("50"),
        )
        session.add(position)
        session.commit()

        assert "00700" in repr(position)
        assert "50" in repr(position)


class TestTradeModel:
    """Tests for Trade model."""

    def test_create_trade(self, session: Session):
        """Test creating a trade."""
        user = User(username="tradeuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, futu_acc_id=333, account_type="REAL", market="US"
        )
        session.add(account)
        session.commit()

        trade = Trade(
            account_id=account.id,
            deal_id="DEAL123456",
            order_id="ORDER123",
            trade_time=datetime(2025, 12, 14, 10, 30, 0),
            market="US",
            code="NVDA",
            stock_name="NVIDIA",
            trd_side="BUY",
            qty=Decimal("10"),
            price=Decimal("140.50"),
            amount=Decimal("1405.00"),
            fee=Decimal("1.00"),
            currency="USD",
        )
        session.add(trade)
        session.commit()

        assert trade.id is not None
        assert trade.trd_side == "BUY"
        assert trade.deal_id == "DEAL123456"

    def test_trade_repr(self, session: Session):
        """Test trade string representation."""
        user = User(username="traderepruser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, futu_acc_id=444, account_type="REAL", market="US"
        )
        session.add(account)
        session.commit()

        trade = Trade(
            account_id=account.id,
            deal_id="DEAL789",
            trade_time=datetime.now(),
            market="US",
            code="AAPL",
            trd_side="SELL",
            qty=Decimal("5"),
            price=Decimal("190.00"),
        )
        session.add(trade)
        session.commit()

        assert "DEAL789" in repr(trade)
        assert "SELL" in repr(trade)


class TestAccountSnapshotModel:
    """Tests for AccountSnapshot model."""

    def test_create_snapshot(self, session: Session):
        """Test creating an account snapshot."""
        user = User(username="snapuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, futu_acc_id=555, account_type="REAL", market="HK"
        )
        session.add(account)
        session.commit()

        snapshot = AccountSnapshot(
            account_id=account.id,
            snapshot_date=date(2025, 12, 14),
            total_assets=Decimal("100000.00"),
            cash=Decimal("20000.00"),
            market_val=Decimal("80000.00"),
            buying_power=Decimal("50000.00"),
            currency="HKD",
        )
        session.add(snapshot)
        session.commit()

        assert snapshot.id is not None
        assert snapshot.total_assets == Decimal("100000.00")


class TestKlineModel:
    """Tests for Kline model."""

    def test_create_kline(self, session: Session):
        """Test creating a kline record."""
        kline = Kline(
            market="HK",
            code="00700",
            trade_date=date(2025, 12, 14),
            open=Decimal("370.00"),
            high=Decimal("385.00"),
            low=Decimal("368.00"),
            close=Decimal("380.00"),
            volume=10000000,
            amount=Decimal("3800000000.00"),
            change_pct=Decimal("0.0270"),
        )
        session.add(kline)
        session.commit()

        assert kline.id is not None
        assert kline.close == Decimal("380.00")

    def test_kline_full_code(self, session: Session):
        """Test kline full_code property."""
        kline = Kline(
            market="US",
            code="NVDA",
            trade_date=date.today(),
            open=Decimal("140.00"),
            high=Decimal("145.00"),
            low=Decimal("138.00"),
            close=Decimal("142.00"),
        )
        session.add(kline)
        session.commit()

        assert kline.full_code == "US.NVDA"

    def test_kline_with_indicators(self, session: Session):
        """Test kline with pre-calculated indicators."""
        kline = Kline(
            market="HK",
            code="00700",
            trade_date=date.today(),
            open=Decimal("370.00"),
            high=Decimal("385.00"),
            low=Decimal("368.00"),
            close=Decimal("380.00"),
            ma5=Decimal("375.00"),
            ma10=Decimal("372.00"),
            ma20=Decimal("368.00"),
            ma60=Decimal("360.00"),
            obv=50000000,
        )
        session.add(kline)
        session.commit()

        assert kline.ma5 == Decimal("375.00")
        assert kline.obv == 50000000


class TestWatchlistItemModel:
    """Tests for WatchlistItem model."""

    def test_create_watchlist_item(self, session: Session):
        """Test creating a watchlist item."""
        user = User(username="watchuser")
        session.add(user)
        session.commit()

        item = WatchlistItem(
            user_id=user.id,
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            group_name="科技股",
            notes="关注突破",
        )
        session.add(item)
        session.commit()

        assert item.id is not None
        assert item.group_name == "科技股"
        assert item.is_active is True

    def test_watchlist_full_code(self, session: Session):
        """Test watchlist item full_code property."""
        user = User(username="watchcodeuser")
        session.add(user)
        session.commit()

        item = WatchlistItem(user_id=user.id, market="US", code="AAPL")
        session.add(item)
        session.commit()

        assert item.full_code == "US.AAPL"


class TestSyncLogModel:
    """Tests for SyncLog model."""

    def test_create_sync_log(self, session: Session):
        """Test creating a sync log."""
        user = User(username="syncuser")
        session.add(user)
        session.commit()

        log = SyncLog(
            user_id=user.id,
            sync_type="POSITIONS",
            status="SUCCESS",
            records_count=10,
            started_at=datetime(2025, 12, 14, 10, 0, 0),
            finished_at=datetime(2025, 12, 14, 10, 0, 5),
        )
        session.add(log)
        session.commit()

        assert log.id is not None
        assert log.status == "SUCCESS"

    def test_sync_log_duration(self, session: Session):
        """Test sync log duration calculation."""
        log = SyncLog(
            sync_type="KLINES",
            status="SUCCESS",
            started_at=datetime(2025, 12, 14, 10, 0, 0),
            finished_at=datetime(2025, 12, 14, 10, 0, 30),
        )
        session.add(log)
        session.commit()

        assert log.duration_seconds == 30.0

    def test_sync_log_duration_none(self, session: Session):
        """Test sync log duration when not finished."""
        log = SyncLog(
            sync_type="TRADES",
            status="FAILED",
            started_at=datetime.now(),
            error_message="Connection timeout",
        )
        session.add(log)
        session.commit()

        assert log.duration_seconds is None


class TestRelationships:
    """Tests for model relationships."""

    def test_user_cascade_delete(self, session: Session):
        """Test cascade delete from user to related models."""
        user = User(username="cascadeuser")
        session.add(user)
        session.commit()

        # Add related records
        account = Account(
            user_id=user.id, futu_acc_id=777, account_type="REAL", market="HK"
        )
        watchlist = WatchlistItem(user_id=user.id, market="HK", code="00700")
        sync_log = SyncLog(
            user_id=user.id,
            sync_type="POSITIONS",
            status="SUCCESS",
            started_at=datetime.now(),
        )

        session.add_all([account, watchlist, sync_log])
        session.commit()

        # Delete user
        session.delete(user)
        session.commit()

        # Verify cascade delete
        assert session.query(Account).filter_by(futu_acc_id=777).first() is None
        assert session.query(WatchlistItem).filter_by(code="00700").first() is None

    def test_account_positions_relationship(self, session: Session):
        """Test account to positions relationship."""
        user = User(username="accposuser")
        session.add(user)
        session.commit()

        account = Account(
            user_id=user.id, futu_acc_id=888, account_type="REAL", market="HK"
        )
        session.add(account)
        session.commit()

        # Add multiple positions
        pos1 = Position(
            account_id=account.id,
            snapshot_date=date.today(),
            market="HK",
            code="00700",
            qty=Decimal("100"),
        )
        pos2 = Position(
            account_id=account.id,
            snapshot_date=date.today(),
            market="HK",
            code="09988",
            qty=Decimal("200"),
        )
        session.add_all([pos1, pos2])
        session.commit()

        # Test relationship
        assert len(account.positions) == 2
        assert pos1 in account.positions
        assert pos2 in account.positions
