"""Tests for price alert service."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from db.models import Base, PriceAlert, User
from services import (
    AlertResult,
    AlertService,
    AlertSummary,
    AlertType,
    create_alert_service,
)


@pytest.fixture(scope="module")
def engine():
    """Create in-memory database."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def session(engine):
    """Create a session for each test."""
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Clear data
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()

    yield session
    session.close()


@pytest.fixture
def test_user(session):
    """Create a test user."""
    user = User(username="test_user")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


class TestAlertService:
    """Tests for AlertService."""

    def test_create_alert_service(self, session):
        """Test creating alert service."""
        service = AlertService(session=session)
        assert service is not None

    def test_create_alert_service_factory(self):
        """Test factory function."""
        service = create_alert_service()
        assert service is not None


class TestCreateAlert:
    """Tests for creating alerts."""

    def test_create_above_alert(self, session, test_user):
        """Test creating ABOVE price alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
            stock_name="腾讯控股",
            notes="测试提醒",
        )

        assert alert.id is not None
        assert alert.user_id == test_user.id
        assert alert.market == "HK"
        assert alert.code == "00700"
        assert alert.alert_type == "ABOVE"
        assert float(alert.target_price) == 400.0
        assert alert.stock_name == "腾讯控股"
        assert alert.is_active is True
        assert alert.is_triggered is False

    def test_create_below_alert(self, session, test_user):
        """Test creating BELOW price alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.BELOW,
            target_price=300.0,
        )

        assert alert.alert_type == "BELOW"
        assert float(alert.target_price) == 300.0

    def test_create_change_up_alert(self, session, test_user):
        """Test creating CHANGE_UP percentage alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="US",
            code="NVDA",
            alert_type=AlertType.CHANGE_UP,
            target_change_pct=0.10,  # 10% increase
            base_price=500.0,
        )

        assert alert.alert_type == "CHANGE_UP"
        assert float(alert.target_change_pct) == 0.10
        assert float(alert.base_price) == 500.0

    def test_create_change_down_alert(self, session, test_user):
        """Test creating CHANGE_DOWN percentage alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="09988",
            alert_type=AlertType.CHANGE_DOWN,
            target_change_pct=0.05,  # 5% decrease
            base_price=80.0,
        )

        assert alert.alert_type == "CHANGE_DOWN"
        assert float(alert.target_change_pct) == 0.05

    def test_create_above_alert_missing_price(self, session, test_user):
        """Test that ABOVE alert requires target_price."""
        service = AlertService(session=session)
        with pytest.raises(ValueError) as exc:
            service.create_alert(
                user_id=test_user.id,
                market="HK",
                code="00700",
                alert_type=AlertType.ABOVE,
            )
        assert "target_price is required" in str(exc.value)

    def test_create_change_alert_missing_pct(self, session, test_user):
        """Test that CHANGE alert requires target_change_pct."""
        service = AlertService(session=session)
        with pytest.raises(ValueError) as exc:
            service.create_alert(
                user_id=test_user.id,
                market="HK",
                code="00700",
                alert_type=AlertType.CHANGE_UP,
            )
        assert "target_change_pct is required" in str(exc.value)


class TestGetAlerts:
    """Tests for getting alerts."""

    def test_get_alert_by_id(self, session, test_user):
        """Test getting alert by ID."""
        service = AlertService(session=session)
        created = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        fetched = service.get_alert(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_alert_not_found(self, session):
        """Test getting non-existent alert."""
        service = AlertService(session=session)
        assert service.get_alert(99999) is None

    def test_get_user_alerts(self, session, test_user):
        """Test getting all alerts for a user."""
        service = AlertService(session=session)

        # Create multiple alerts
        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )
        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="09988",
            alert_type=AlertType.BELOW,
            target_price=70.0,
        )
        service.create_alert(
            user_id=test_user.id,
            market="US",
            code="NVDA",
            alert_type=AlertType.ABOVE,
            target_price=600.0,
        )

        alerts = service.get_user_alerts(test_user.id)
        assert len(alerts) == 3

    def test_get_user_alerts_filter_market(self, session, test_user):
        """Test filtering alerts by market."""
        service = AlertService(session=session)

        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )
        service.create_alert(
            user_id=test_user.id,
            market="US",
            code="NVDA",
            alert_type=AlertType.ABOVE,
            target_price=600.0,
        )

        hk_alerts = service.get_user_alerts(test_user.id, market="HK")
        assert len(hk_alerts) == 1
        assert hk_alerts[0].market == "HK"

    def test_get_user_alerts_active_only(self, session, test_user):
        """Test getting only active alerts."""
        service = AlertService(session=session)

        alert1 = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )
        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="09988",
            alert_type=AlertType.BELOW,
            target_price=70.0,
        )

        # Trigger one alert
        service.trigger_alert(alert1.id, 410.0)

        active_alerts = service.get_user_alerts(test_user.id, active_only=True)
        assert len(active_alerts) == 1

        all_alerts = service.get_user_alerts(test_user.id, active_only=False)
        assert len(all_alerts) == 2


class TestUpdateAlert:
    """Tests for updating alerts."""

    def test_update_alert_price(self, session, test_user):
        """Test updating alert target price."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        updated = service.update_alert(alert.id, target_price=450.0)
        assert float(updated.target_price) == 450.0

    def test_update_alert_notes(self, session, test_user):
        """Test updating alert notes."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        updated = service.update_alert(alert.id, notes="Updated notes")
        assert updated.notes == "Updated notes"

    def test_update_alert_deactivate(self, session, test_user):
        """Test deactivating an alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        updated = service.update_alert(alert.id, is_active=False)
        assert updated.is_active is False

    def test_update_alert_not_found(self, session):
        """Test updating non-existent alert."""
        service = AlertService(session=session)
        assert service.update_alert(99999, target_price=100.0) is None


class TestDeleteAlert:
    """Tests for deleting alerts."""

    def test_delete_alert(self, session, test_user):
        """Test deleting an alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        assert service.delete_alert(alert.id) is True
        assert service.get_alert(alert.id) is None

    def test_delete_alert_not_found(self, session):
        """Test deleting non-existent alert."""
        service = AlertService(session=session)
        assert service.delete_alert(99999) is False


class TestCheckAlert:
    """Tests for checking alerts."""

    def test_check_above_alert_triggered(self, session, test_user):
        """Test ABOVE alert is triggered when price exceeds target."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        result = service.check_alert(alert, 410.0)
        assert result.triggered is True
        assert result.current_price == 410.0
        assert result.target_price == 400.0
        assert "突破" in result.message

    def test_check_above_alert_not_triggered(self, session, test_user):
        """Test ABOVE alert is not triggered when price is below target."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        result = service.check_alert(alert, 390.0)
        assert result.triggered is False

    def test_check_below_alert_triggered(self, session, test_user):
        """Test BELOW alert is triggered when price falls below target."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.BELOW,
            target_price=350.0,
        )

        result = service.check_alert(alert, 340.0)
        assert result.triggered is True
        assert "跌破" in result.message

    def test_check_below_alert_not_triggered(self, session, test_user):
        """Test BELOW alert is not triggered when price is above target."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.BELOW,
            target_price=350.0,
        )

        result = service.check_alert(alert, 360.0)
        assert result.triggered is False

    def test_check_change_up_alert_triggered(self, session, test_user):
        """Test CHANGE_UP alert is triggered when price increases enough."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.CHANGE_UP,
            target_change_pct=0.10,  # 10% increase
            base_price=100.0,
        )

        result = service.check_alert(alert, 112.0)  # 12% increase
        assert result.triggered is True
        assert result.change_pct == pytest.approx(0.12)
        assert "涨幅" in result.message

    def test_check_change_down_alert_triggered(self, session, test_user):
        """Test CHANGE_DOWN alert is triggered when price decreases enough."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.CHANGE_DOWN,
            target_change_pct=0.05,  # 5% decrease
            base_price=100.0,
        )

        result = service.check_alert(alert, 93.0)  # 7% decrease
        assert result.triggered is True
        assert result.change_pct == pytest.approx(-0.07)
        assert "跌幅" in result.message


class TestTriggerAlert:
    """Tests for triggering alerts."""

    def test_trigger_alert(self, session, test_user):
        """Test triggering an alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        triggered = service.trigger_alert(alert.id, 405.0)
        assert triggered.is_triggered is True
        assert triggered.triggered_at is not None
        assert float(triggered.triggered_price) == 405.0

    def test_trigger_alert_not_found(self, session):
        """Test triggering non-existent alert."""
        service = AlertService(session=session)
        assert service.trigger_alert(99999, 100.0) is None


class TestCheckAllAlerts:
    """Tests for checking all alerts."""

    def test_check_all_alerts(self, session, test_user):
        """Test checking all alerts against price data."""
        service = AlertService(session=session)

        # Create alerts
        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )
        service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="09988",
            alert_type=AlertType.BELOW,
            target_price=70.0,
        )

        # Price data
        prices = {
            "HK.00700": 410.0,  # Should trigger
            "HK.09988": 75.0,  # Should not trigger
        }

        summary = service.check_all_alerts(test_user.id, prices)
        assert summary.total_checked == 2
        assert summary.total_triggered == 1
        assert len(summary.results) == 1

    def test_check_all_alerts_no_auto_trigger(self, session, test_user):
        """Test checking alerts without auto-triggering."""
        service = AlertService(session=session)

        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        prices = {"HK.00700": 410.0}
        service.check_all_alerts(test_user.id, prices, auto_trigger=False)

        # Alert should not be triggered in DB
        fetched = service.get_alert(alert.id)
        assert fetched.is_triggered is False


class TestResetAlert:
    """Tests for resetting alerts."""

    def test_reset_alert(self, session, test_user):
        """Test resetting a triggered alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        # Trigger it first
        service.trigger_alert(alert.id, 410.0)

        # Reset
        reset = service.reset_alert(alert.id)
        assert reset.is_triggered is False
        assert reset.triggered_at is None
        assert reset.triggered_price is None
        assert reset.is_active is True

    def test_reset_alert_not_found(self, session):
        """Test resetting non-existent alert."""
        service = AlertService(session=session)
        assert service.reset_alert(99999) is None


class TestAlertProperties:
    """Tests for PriceAlert model properties."""

    def test_full_code(self, session, test_user):
        """Test full_code property."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        assert alert.full_code == "HK.00700"

    def test_target_description_above(self, session, test_user):
        """Test target description for ABOVE alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.ABOVE,
            target_price=400.0,
        )

        assert "above" in alert.target_description.lower()
        assert "400" in alert.target_description

    def test_target_description_change(self, session, test_user):
        """Test target description for CHANGE alert."""
        service = AlertService(session=session)
        alert = service.create_alert(
            user_id=test_user.id,
            market="HK",
            code="00700",
            alert_type=AlertType.CHANGE_UP,
            target_change_pct=0.10,
            base_price=350.0,
        )

        assert "+" in alert.target_description
        assert "10" in alert.target_description or "0.1" in alert.target_description


class TestAlertResultDataclass:
    """Tests for AlertResult dataclass."""

    def test_alert_result_creation(self):
        """Test creating AlertResult."""
        result = AlertResult(
            alert_id=1,
            triggered=True,
            current_price=100.0,
            target_price=95.0,
            message="Test message",
        )

        assert result.alert_id == 1
        assert result.triggered is True
        assert result.current_price == 100.0


class TestAlertSummaryDataclass:
    """Tests for AlertSummary dataclass."""

    def test_alert_summary_creation(self):
        """Test creating AlertSummary."""
        summary = AlertSummary(
            total_checked=5,
            total_triggered=2,
        )

        assert summary.total_checked == 5
        assert summary.total_triggered == 2
        assert summary.results == []

    def test_alert_summary_with_results(self):
        """Test AlertSummary with results."""
        results = [
            AlertResult(alert_id=1, triggered=True),
            AlertResult(alert_id=2, triggered=True),
        ]
        summary = AlertSummary(
            total_checked=5,
            total_triggered=2,
            results=results,
        )

        assert len(summary.results) == 2
