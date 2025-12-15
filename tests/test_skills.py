"""
Tests for Skills framework components.
"""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from skills.shared import (
    BaseSkill,
    DataProvider,
    MarketState,
    ReportBuilder,
    ReportFormat,
    SkillContext,
    SkillResult,
)
from skills.shared.base import (
    DEFAULT_SCHEDULE,
    MarketSchedule,
    RiskLevel,
    SignalType,
)
from skills.shared.data_provider import KlineData, PositionData, WatchlistData
from skills.shared.report_builder import (
    TableColumn,
    format_currency,
    format_percentage,
    format_score,
)

# =============================================================================
# BaseSkill Tests
# =============================================================================


class ConcreteSkill(BaseSkill):
    """Concrete implementation for testing."""

    def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult.ok(
            skill_name=self.name,
            result_type="test",
            data={"test": True},
        )

    def get_capabilities(self) -> list[str]:
        return ["test_capability"]


class TestBaseSkill:
    """Tests for BaseSkill abstract class."""

    def test_init(self):
        """Test skill initialization."""
        skill = ConcreteSkill("test_skill", "A test skill")
        assert skill.name == "test_skill"
        assert skill.description == "A test skill"
        assert skill._initialized is False

    def test_initialize(self):
        """Test skill initialization method."""
        skill = ConcreteSkill("test", "Test")
        skill.initialize()
        assert skill._initialized is True

    def test_context_manager(self):
        """Test skill as context manager."""
        skill = ConcreteSkill("test", "Test")
        with skill as s:
            assert s._initialized is True
        # After exit, cleanup should have been called

    def test_execute(self):
        """Test skill execution."""
        skill = ConcreteSkill("test", "Test")
        context = SkillContext(user_id=1, request_type="test")
        result = skill.execute(context)
        assert result.success is True
        assert result.skill_name == "test"

    def test_get_capabilities(self):
        """Test getting skill capabilities."""
        skill = ConcreteSkill("test", "Test")
        caps = skill.get_capabilities()
        assert "test_capability" in caps

    def test_validate_context_valid(self):
        """Test context validation with valid context."""
        skill = ConcreteSkill("test", "Test")
        context = SkillContext(user_id=1, request_type="test")
        is_valid, error = skill.validate_context(context)
        assert is_valid is True
        assert error == ""

    def test_validate_context_invalid(self):
        """Test context validation with invalid user_id."""
        skill = ConcreteSkill("test", "Test")
        context = SkillContext(user_id=0, request_type="test")
        is_valid, error = skill.validate_context(context)
        assert is_valid is False
        assert "user_id" in error


class TestSkillContext:
    """Tests for SkillContext dataclass."""

    def test_default_values(self):
        """Test default values."""
        ctx = SkillContext(user_id=1, request_type="test")
        assert ctx.user_id == 1
        assert ctx.request_type == "test"
        assert ctx.parameters == {}
        assert ctx.market_state == MarketState.CLOSED
        assert ctx.markets == ["HK", "US", "A"]
        assert ctx.codes == []

    def test_get_param(self):
        """Test getting parameter."""
        ctx = SkillContext(user_id=1, request_type="test", parameters={"days": 120})
        assert ctx.get_param("days") == 120
        assert ctx.get_param("missing") is None
        assert ctx.get_param("missing", 30) == 30


class TestSkillResult:
    """Tests for SkillResult dataclass."""

    def test_ok_result(self):
        """Test creating successful result."""
        result = SkillResult.ok(
            skill_name="test",
            result_type="analysis",
            data={"value": 100},
            report_content="# Report",
            next_actions=["action1"],
        )
        assert result.success is True
        assert result.skill_name == "test"
        assert result.result_type == "analysis"
        assert result.data == {"value": 100}
        assert result.report_content == "# Report"
        assert result.next_actions == ["action1"]

    def test_error_result(self):
        """Test creating error result."""
        result = SkillResult.error("test", "Something went wrong")
        assert result.success is False
        assert result.skill_name == "test"
        assert result.result_type == "error"
        assert result.error_message == "Something went wrong"


class TestMarketState:
    """Tests for MarketState enum."""

    def test_values(self):
        """Test enum values."""
        assert MarketState.PRE_MARKET.value == "pre_market"
        assert MarketState.OPEN.value == "open"
        assert MarketState.CLOSED.value == "closed"
        assert MarketState.POST_MARKET.value == "post_market"


class TestSignalType:
    """Tests for SignalType enum."""

    def test_values(self):
        """Test enum values."""
        assert SignalType.BUY.value == "buy"
        assert SignalType.SELL.value == "sell"
        assert SignalType.HOLD.value == "hold"
        assert SignalType.WATCH.value == "watch"


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_values(self):
        """Test enum values."""
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"


class TestMarketSchedule:
    """Tests for MarketSchedule."""

    def test_default_schedule(self):
        """Test default schedule values."""
        schedule = MarketSchedule()
        assert schedule.hk_open == time(9, 30)
        assert schedule.hk_close == time(16, 0)
        assert schedule.us_open == time(21, 30)
        assert schedule.a_open == time(9, 30)
        assert schedule.a_close == time(15, 0)

    def test_hk_market_state_closed_early(self):
        """Test HK market state before pre-market."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("HK", time(7, 0))
        assert state == MarketState.CLOSED

    def test_hk_market_state_pre_market(self):
        """Test HK market state during pre-market."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("HK", time(9, 0))
        assert state == MarketState.PRE_MARKET

    def test_hk_market_state_open(self):
        """Test HK market state when open."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("HK", time(10, 30))
        assert state == MarketState.OPEN

    def test_hk_market_state_lunch(self):
        """Test HK market state during lunch break."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("HK", time(12, 30))
        assert state == MarketState.CLOSED

    def test_hk_market_state_post_market(self):
        """Test HK market state during post-market."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("HK", time(16, 15))
        assert state == MarketState.POST_MARKET

    def test_a_market_state_open(self):
        """Test A-share market state when open."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("A", time(10, 0))
        assert state == MarketState.OPEN

    def test_a_market_state_lunch(self):
        """Test A-share market state during lunch."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("A", time(12, 0))
        assert state == MarketState.CLOSED

    def test_us_market_state_pre_market(self):
        """Test US market state during pre-market."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("US", time(20, 30))
        assert state == MarketState.PRE_MARKET

    def test_us_market_state_open(self):
        """Test US market state when open."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("US", time(22, 0))
        assert state == MarketState.OPEN

    def test_us_market_state_early_morning(self):
        """Test US market state in early morning (still open)."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("US", time(3, 0))
        assert state == MarketState.OPEN

    def test_unknown_market(self):
        """Test unknown market returns closed."""
        schedule = MarketSchedule()
        state = schedule.get_market_state("UNKNOWN", time(10, 0))
        assert state == MarketState.CLOSED


# =============================================================================
# DataProvider Tests
# =============================================================================


class TestPositionData:
    """Tests for PositionData dataclass."""

    def test_full_code(self):
        """Test full code property."""
        pos = PositionData(
            market="HK",
            code="00700",
            stock_name="Tencent",
            qty=Decimal("100"),
            cost_price=Decimal("350"),
            market_price=Decimal("380"),
            market_val=Decimal("38000"),
            pl_val=Decimal("3000"),
            pl_ratio=Decimal("8.57"),
        )
        assert pos.full_code == "HK.00700"


class TestKlineData:
    """Tests for KlineData dataclass."""

    def test_creation(self):
        """Test KlineData creation."""
        kline = KlineData(
            market="HK",
            code="00700",
            trade_date=date(2024, 1, 15),
            open=Decimal("350"),
            high=Decimal("360"),
            low=Decimal("345"),
            close=Decimal("355"),
            volume=Decimal("1000000"),
        )
        assert kline.market == "HK"
        assert kline.close == Decimal("355")
        assert kline.amount == Decimal("0")  # Default


class TestWatchlistData:
    """Tests for WatchlistData dataclass."""

    def test_full_code(self):
        """Test full code property."""
        item = WatchlistData(
            market="US",
            code="NVDA",
            stock_name="Nvidia",
            group_name="AI",
        )
        assert item.full_code == "US.NVDA"


class TestDataProvider:
    """Tests for DataProvider class."""

    def test_init(self):
        """Test provider initialization."""
        provider = DataProvider(cache_ttl_seconds=60)
        assert provider.cache_ttl == timedelta(seconds=60)
        assert provider._cache == {}

    def test_cache_set_and_get(self):
        """Test cache operations."""
        provider = DataProvider(cache_ttl_seconds=300)
        provider._set_cache("test_key", {"data": "value"})
        result = provider._get_cache("test_key")
        assert result == {"data": "value"}

    def test_cache_expired(self):
        """Test expired cache returns None."""
        provider = DataProvider(cache_ttl_seconds=0)  # Immediate expiry
        provider._set_cache("test_key", {"data": "value"})
        # Cache should be expired immediately
        import time

        time.sleep(0.01)
        result = provider._get_cache("test_key")
        assert result is None

    def test_cache_miss(self):
        """Test cache miss returns None."""
        provider = DataProvider()
        result = provider._get_cache("nonexistent")
        assert result is None

    def test_clear_cache(self):
        """Test clearing cache."""
        provider = DataProvider()
        provider._set_cache("key1", "value1")
        provider._set_cache("key2", "value2")
        provider.clear_cache()
        assert provider._cache == {}

    def test_is_individual_stock_a_share(self):
        """Test A-share individual stock detection."""
        provider = DataProvider()
        # Regular A-share stocks
        assert provider._is_individual_stock("A", "600000") is True
        assert provider._is_individual_stock("A", "300001") is True
        # Shanghai index
        assert provider._is_individual_stock("A", "000001") is False

    def test_is_individual_stock_hk(self):
        """Test HK individual stock detection."""
        provider = DataProvider()
        # Regular HK stocks
        assert provider._is_individual_stock("HK", "00700") is True
        assert provider._is_individual_stock("HK", "09988") is True
        # Index
        assert provider._is_individual_stock("HK", "800000") is False
        # Currency
        assert provider._is_individual_stock("HK", "USDCNH") is False

    def test_is_individual_stock_us(self):
        """Test US individual stock detection."""
        provider = DataProvider()
        # Regular US stocks
        assert provider._is_individual_stock("US", "NVDA") is True
        assert provider._is_individual_stock("US", "AAPL") is True
        # Index
        assert provider._is_individual_stock("US", ".SPX") is False
        assert provider._is_individual_stock("US", ".VIX") is False


# =============================================================================
# ReportBuilder Tests
# =============================================================================


class TestReportFormat:
    """Tests for ReportFormat enum."""

    def test_values(self):
        """Test enum values."""
        assert ReportFormat.MARKDOWN.value == "markdown"
        assert ReportFormat.JSON.value == "json"
        assert ReportFormat.TEXT.value == "text"
        assert ReportFormat.HTML.value == "html"


class TestTableColumn:
    """Tests for TableColumn dataclass."""

    def test_default_values(self):
        """Test default values."""
        col = TableColumn(header="Name", key="name")
        assert col.header == "Name"
        assert col.key == "name"
        assert col.align == "left"
        assert col.format_fn is None


class TestReportBuilder:
    """Tests for ReportBuilder class."""

    def test_init(self):
        """Test builder initialization."""
        builder = ReportBuilder("Test Report", ReportFormat.MARKDOWN)
        assert builder.title == "Test Report"
        assert builder.format == ReportFormat.MARKDOWN
        assert len(builder.sections) == 0
        assert "title" in builder.metadata
        assert "generated_at" in builder.metadata

    def test_add_section(self):
        """Test adding section."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Introduction", "This is the intro", level=2)
        assert len(builder.sections) == 1
        assert builder.sections[0].title == "Introduction"
        assert builder.sections[0].content == "This is the intro"
        assert builder.sections[0].level == 2

    def test_chaining(self):
        """Test method chaining."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        result = (
            builder.add_section("Section 1")
            .add_line("Line 1")
            .add_blank_line()
            .add_line("Line 2")
        )
        assert result is builder

    def test_add_text(self):
        """Test adding text."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_text("Hello ")
        builder.add_text("World")
        assert "Hello World" in builder.sections[0].content

    def test_add_list_unordered(self):
        """Test adding unordered list."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_list(["Item 1", "Item 2", "Item 3"])
        content = builder.sections[0].content
        assert "- Item 1" in content
        assert "- Item 2" in content

    def test_add_list_ordered(self):
        """Test adding ordered list."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_list(["First", "Second"], ordered=True)
        content = builder.sections[0].content
        assert "1. First" in content
        assert "2. Second" in content

    def test_add_key_value_markdown(self):
        """Test adding key-value pair in markdown."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_key_value("Status", "Active")
        assert "**Status**" in builder.sections[0].content
        assert "Active" in builder.sections[0].content

    def test_add_key_value_text(self):
        """Test adding key-value pair in text format."""
        builder = ReportBuilder("Test", ReportFormat.TEXT)
        builder.add_section("Test")
        builder.add_key_value("Status", "Active")
        assert "Status: Active" in builder.sections[0].content

    def test_add_table_markdown(self):
        """Test adding table in markdown."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        data = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87},
        ]
        builder.add_table(data)
        content = builder.sections[0].content
        assert "| name |" in content
        assert "| Alice |" in content
        assert "| Bob |" in content

    def test_add_table_empty(self):
        """Test adding empty table does nothing."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        initial_content = builder.sections[0].content
        builder.add_table([])
        assert builder.sections[0].content == initial_content

    def test_add_table_with_columns(self):
        """Test adding table with custom columns."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        data = [{"n": "Alice", "s": 95}]
        columns = [
            TableColumn(header="Name", key="n"),
            TableColumn(header="Score", key="s", align="right"),
        ]
        builder.add_table(data, columns)
        content = builder.sections[0].content
        assert "| Name |" in content
        assert "---:" in content  # Right align

    def test_add_code_block_markdown(self):
        """Test adding code block in markdown."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_code_block("print('hello')", language="python")
        content = builder.sections[0].content
        assert "```python" in content
        assert "print('hello')" in content
        assert "```" in content

    def test_add_divider_markdown(self):
        """Test adding divider in markdown."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_divider()
        assert "---" in builder.sections[0].content

    def test_add_alert(self):
        """Test adding alert."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.add_section("Test")
        builder.add_alert("This is important", level="warning")
        content = builder.sections[0].content
        assert "WARNING" in content
        assert "This is important" in content

    def test_set_metadata(self):
        """Test setting metadata."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        builder.set_metadata("author", "Claude")
        assert builder.metadata["author"] == "Claude"

    def test_format_value_none(self):
        """Test formatting None value."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        assert builder._format_value(None) == "-"

    def test_format_value_decimal(self):
        """Test formatting Decimal values."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        assert builder._format_value(Decimal("1234.56")) == "1,234.56"
        assert builder._format_value(Decimal("12.346")) == "12.35"  # Rounds up
        assert builder._format_value(Decimal("0.1234")) == "0.1234"

    def test_format_value_float(self):
        """Test formatting float values."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        assert builder._format_value(1234.56) == "1,234.56"
        assert builder._format_value(12.345) == "12.35"

    def test_format_value_date(self):
        """Test formatting date values."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        assert builder._format_value(date(2024, 1, 15)) == "2024-01-15"

    def test_format_value_bool(self):
        """Test formatting boolean values."""
        builder = ReportBuilder("Test", ReportFormat.MARKDOWN)
        assert builder._format_value(True) == "Yes"
        assert builder._format_value(False) == "No"

    def test_build_markdown(self):
        """Test building markdown report."""
        builder = ReportBuilder("Test Report", ReportFormat.MARKDOWN)
        builder.add_section("Section 1", "Content 1")
        builder.add_section("Section 2", "Content 2")
        report = builder.build()
        assert "# Test Report" in report
        assert "## Section 1" in report
        assert "Content 1" in report
        assert "## Section 2" in report
        assert "Generated:" in report

    def test_build_text(self):
        """Test building text report."""
        builder = ReportBuilder("Test Report", ReportFormat.TEXT)
        builder.add_section("Section 1", "Content 1")
        report = builder.build()
        assert "Test Report" in report
        assert "Section 1" in report
        assert "Content 1" in report

    def test_build_json(self):
        """Test building JSON report."""
        builder = ReportBuilder("Test Report", ReportFormat.JSON)
        builder.add_section("Section 1", "Content 1", data={"key": "value"})
        report = builder.build()
        data = json.loads(report)
        assert "metadata" in data
        assert "sections" in data
        assert data["sections"][0]["title"] == "Section 1"
        assert data["sections"][0]["data"] == {"key": "value"}

    def test_build_html(self):
        """Test building HTML report."""
        builder = ReportBuilder("Test Report", ReportFormat.HTML)
        builder.add_section("Section 1", "Content 1")
        report = builder.build()
        assert "<!DOCTYPE html>" in report
        assert "<title>Test Report</title>" in report
        assert "<h1>Test Report</h1>" in report
        assert "<h2>Section 1</h2>" in report


class TestFormatHelpers:
    """Tests for format helper functions."""

    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(5.5) == "+5.50%"
        assert format_percentage(-3.2) == "-3.20%"
        assert format_percentage(0) == "0.00%"
        assert format_percentage(None) == "-"

    def test_format_percentage_decimals(self):
        """Test percentage with custom decimals."""
        assert format_percentage(5.555, decimals=1) == "+5.6%"
        assert format_percentage(5.555, decimals=3) == "+5.555%"

    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "1,234.56"
        assert format_currency(1234.56, "USD") == "USD 1,234.56"
        assert format_currency(None) == "-"

    def test_format_score(self):
        """Test score formatting."""
        assert format_score(85) == "85.0 (Excellent)"
        assert format_score(65) == "65.0 (Good)"
        assert format_score(45) == "45.0 (Fair)"
        assert format_score(25) == "25.0 (Poor)"
        assert format_score(None) == "-"
