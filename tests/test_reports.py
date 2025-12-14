"""Tests for the reports module."""

import json
import tempfile
from datetime import date, datetime
from pathlib import Path

import pytest

from reports import (
    OutputFormat,
    ReportConfig,
    ReportGenerator,
    ReportResult,
    ReportType,
    create_report_generator,
    generate_report,
)


# === Test Data ===


@pytest.fixture
def sample_portfolio_data():
    """Sample portfolio analysis data."""
    return {
        "analysis_date": "2024-12-14",
        "summary": {
            "total_market_value": 100000.0,
            "total_cost_value": 90000.0,
            "total_pl_value": 10000.0,
            "total_pl_ratio": 11.1,
            "position_count": 5,
            "long_count": 5,
            "short_count": 0,
            "profitable_count": 3,
            "losing_count": 2,
            "win_rate": 60.0,
            "largest_position_weight": 35.0,
            "top5_concentration": 100.0,
            "avg_position_size": 20000.0,
            "cash_balance": 15000.0,
            "total_assets": 115000.0,
            "cash_weight": 13.0,
        },
        "positions": [
            {
                "code": "HK.00700",
                "name": "腾讯控股",
                "qty": 100,
                "cost_price": 350.0,
                "market_price": 380.0,
                "market_value": 38000.0,
                "cost_value": 35000.0,
                "pl_value": 3000.0,
                "pl_ratio": 8.6,
                "weight": 38.0,
                "position_side": "LONG",
            },
            {
                "code": "US.NVDA",
                "name": "NVIDIA",
                "qty": 50,
                "cost_price": 500.0,
                "market_price": 600.0,
                "market_value": 30000.0,
                "cost_value": 25000.0,
                "pl_value": 5000.0,
                "pl_ratio": 20.0,
                "weight": 30.0,
                "position_side": "LONG",
            },
        ],
        "market_allocation": [
            {
                "market": "HK",
                "position_count": 2,
                "market_value": 56000.0,
                "weight": 56.0,
                "pl_value": 1000.0,
                "pl_ratio": 1.8,
            },
            {
                "market": "US",
                "position_count": 3,
                "market_value": 44000.0,
                "weight": 44.0,
                "pl_value": 9000.0,
                "pl_ratio": 25.7,
            },
        ],
        "risk_metrics": {
            "concentration_risk": "high",
            "diversification_score": 45.0,
            "largest_loss_position": "HK.09988",
            "largest_loss_ratio": -15.3,
            "total_unrealized_loss": -5000.0,
            "positions_at_loss_ratio": 40.0,
            "hhi_index": 2850.0,
            "signals": [
                "High concentration risk: largest position is 38.0%",
                "Portfolio is highly concentrated (HHI: 2850)",
            ],
        },
        "top_performers": [
            {
                "code": "US.NVDA",
                "name": "NVIDIA",
                "pl_ratio": 20.0,
            },
            {
                "code": "HK.00700",
                "name": "腾讯控股",
                "pl_ratio": 8.6,
            },
        ],
        "bottom_performers": [
            {
                "code": "HK.09988",
                "name": "阿里巴巴",
                "pl_ratio": -15.3,
            },
        ],
        "signals": [
            "High concentration risk: largest position is 38.0%",
            "Low diversification: fewer than 5 positions",
        ],
    }


@pytest.fixture
def sample_technical_data():
    """Sample technical analysis data."""
    return {
        "code": "HK.00700",
        "price_info": {
            "name": "腾讯控股",
            "close": 380.0,
            "open": 375.0,
            "high": 385.0,
            "low": 372.0,
            "volume": 10000000,
            "change_pct": 1.5,
        },
        "indicators": {
            "ma": {
                "MA5": 378.0,
                "MA10": 375.0,
                "MA20": 365.0,
                "MA60": 350.0,
            },
            "ma_alignment": "多头排列",
            "rsi": {
                "RSI(14)": 58.5,
            },
            "macd": {
                "macd": 2.35,
                "signal": 1.82,
                "histogram": 0.53,
                "crossover": 1,
                "position": "above",
            },
            "bollinger": {
                "upper": 395.0,
                "middle": 365.0,
                "lower": 335.0,
                "width": 16.4,
                "position": "中轨上方",
                "squeeze": False,
            },
            "obv": {
                "value": 15000000,
                "trend": "上升",
                "divergence": None,
            },
        },
        "vcp": {
            "is_vcp": True,
            "score": 78.5,
            "contraction_count": 3,
            "depth_sequence": [18.0, 11.0, 5.0],
            "pivot_price": 385.0,
            "pivot_distance_pct": 1.3,
            "volume_trend": -25.0,
            "range_contraction": 72.0,
            "signals": [
                "深度递减良好",
                "接近枢轴价位",
                "成交量萎缩明显",
            ],
        },
        "summary": {
            "trend_score": 75,
            "trend_signal": "看多",
            "momentum_score": 65,
            "momentum_signal": "中性偏强",
            "overall_score": 72,
            "overall_signal": "持有/关注突破",
        },
        "chart_path": "charts/output/HK.00700.png",
    }


@pytest.fixture
def sample_daily_data():
    """Sample daily brief data."""
    return {
        "trades": {
            "buy_count": 2,
            "sell_count": 1,
            "buy_amount": 50000.0,
            "sell_amount": 20000.0,
            "net_buy": 30000.0,
            "details": [
                {
                    "time": "10:30",
                    "code": "HK.00700",
                    "side": "买入",
                    "qty": 100,
                    "price": 375.0,
                    "amount": 37500.0,
                },
            ],
        },
        "pl": {
            "today_pl": 1500.0,
            "today_pl_pct": 1.5,
            "total_pl": 10000.0,
            "total_pl_pct": 11.1,
            "by_position": [
                {"code": "HK.00700", "change_pct": 1.5, "pl_today": 570.0},
                {"code": "US.NVDA", "change_pct": 2.0, "pl_today": 600.0},
            ],
        },
        "watchlist_alerts": [
            "HK.00700 接近突破位 385.00",
            "US.TSLA RSI 超卖反弹",
        ],
        "technical_signals": [
            "HK.00700 VCP形态形成中",
            "US.NVDA MACD金叉",
        ],
    }


@pytest.fixture
def sample_weekly_data():
    """Sample weekly review data."""
    return {
        "trades": {
            "total_count": 8,
            "buy_count": 5,
            "sell_count": 3,
            "buy_amount": 100000.0,
            "sell_amount": 50000.0,
            "net_buy": 50000.0,
        },
        "pl": {
            "realized_pl": 5000.0,
            "unrealized_change": 3000.0,
            "total_change": 8000.0,
            "weekly_return_pct": 2.5,
            "top_gainers": [
                {"code": "US.NVDA", "change_pct": 8.5, "pl": 2500.0},
            ],
            "top_losers": [
                {"code": "HK.09988", "change_pct": -5.0, "pl": -1500.0},
            ],
        },
        "position_changes": [
            {"code": "HK.00700", "type": "加仓", "qty_change": 100, "note": "突破买入"},
            {"code": "US.META", "type": "新建", "qty_change": 50, "note": "新建仓位"},
        ],
        "next_week": {
            "breakout_candidates": ["HK.00700 枢轴 385.00"],
            "profit_targets": ["US.NVDA 目标 650.00"],
            "stop_loss_alerts": ["HK.09988 止损 80.00"],
            "watchlist": ["US.TSLA", "HK.09618"],
        },
    }


# === ReportType Tests ===


class TestReportType:
    """Tests for ReportType enum."""

    def test_report_types_exist(self):
        """Test that all report types exist."""
        assert ReportType.PORTFOLIO.value == "portfolio"
        assert ReportType.TECHNICAL.value == "technical"
        assert ReportType.DAILY.value == "daily"
        assert ReportType.WEEKLY.value == "weekly"

    def test_report_type_count(self):
        """Test the number of report types."""
        assert len(ReportType) == 4


class TestOutputFormat:
    """Tests for OutputFormat enum."""

    def test_output_formats_exist(self):
        """Test that all output formats exist."""
        assert OutputFormat.MARKDOWN.value == "markdown"
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.HTML.value == "html"

    def test_output_format_count(self):
        """Test the number of output formats."""
        assert len(OutputFormat) == 3


# === ReportConfig Tests ===


class TestReportConfig:
    """Tests for ReportConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = ReportConfig(report_type=ReportType.PORTFOLIO)
        assert config.report_type == ReportType.PORTFOLIO
        assert config.user_id is None
        assert config.codes is None
        assert config.include_charts is True
        assert config.output_format == OutputFormat.MARKDOWN
        assert config.title is None

    def test_custom_config(self):
        """Test custom configuration."""
        config = ReportConfig(
            report_type=ReportType.TECHNICAL,
            user_id=1,
            codes=["HK.00700"],
            include_charts=False,
            output_format=OutputFormat.JSON,
            title="Custom Report",
        )
        assert config.report_type == ReportType.TECHNICAL
        assert config.user_id == 1
        assert config.codes == ["HK.00700"]
        assert config.include_charts is False
        assert config.output_format == OutputFormat.JSON
        assert config.title == "Custom Report"

    def test_extra_data(self):
        """Test extra data field."""
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            extra_data={"custom_field": "value"},
        )
        assert config.extra_data["custom_field"] == "value"


# === ReportResult Tests ===


class TestReportResult:
    """Tests for ReportResult dataclass."""

    def test_basic_result(self):
        """Test basic report result."""
        result = ReportResult(
            report_type=ReportType.PORTFOLIO,
            content="# Test Report",
            output_format=OutputFormat.MARKDOWN,
            generated_at=datetime.now(),
            title="Test Report",
        )
        assert result.report_type == ReportType.PORTFOLIO
        assert result.content == "# Test Report"
        assert result.output_format == OutputFormat.MARKDOWN
        assert result.title == "Test Report"

    def test_save_report(self):
        """Test saving report to file."""
        result = ReportResult(
            report_type=ReportType.PORTFOLIO,
            content="# Test Report\n\nContent here.",
            output_format=OutputFormat.MARKDOWN,
            generated_at=datetime.now(),
            title="Test Report",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "test_report.md"
            saved_path = result.save(file_path)

            assert saved_path.exists()
            assert saved_path.read_text() == "# Test Report\n\nContent here."

    def test_save_creates_directories(self):
        """Test that save creates parent directories."""
        result = ReportResult(
            report_type=ReportType.PORTFOLIO,
            content="# Test",
            output_format=OutputFormat.MARKDOWN,
            generated_at=datetime.now(),
            title="Test",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "subdir" / "nested" / "report.md"
            saved_path = result.save(file_path)

            assert saved_path.exists()
            assert saved_path.parent.exists()

    def test_to_dict(self):
        """Test converting result to dictionary."""
        now = datetime.now()
        result = ReportResult(
            report_type=ReportType.PORTFOLIO,
            content="# Test",
            output_format=OutputFormat.MARKDOWN,
            generated_at=now,
            title="Test Report",
            metadata={"user_id": 1},
            chart_paths=["chart1.png"],
        )

        d = result.to_dict()
        assert d["report_type"] == "portfolio"
        assert d["content"] == "# Test"
        assert d["output_format"] == "markdown"
        assert d["title"] == "Test Report"
        assert d["metadata"]["user_id"] == 1
        assert d["chart_paths"] == ["chart1.png"]


# === ReportGenerator Tests ===


class TestReportGenerator:
    """Tests for ReportGenerator class."""

    def test_create_generator(self):
        """Test creating a generator."""
        generator = ReportGenerator()
        assert generator is not None
        assert generator.env is not None

    def test_create_generator_with_custom_templates(self):
        """Test creating generator with custom templates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ReportGenerator(templates_dir=Path(tmpdir))
            assert generator.templates_dir == Path(tmpdir)


class TestPortfolioReport:
    """Tests for portfolio report generation."""

    def test_generate_portfolio_report(self, sample_portfolio_data):
        """Test generating a portfolio report."""
        generator = ReportGenerator()
        result = generator.generate_portfolio_report(sample_portfolio_data)

        assert result.report_type == ReportType.PORTFOLIO
        assert result.output_format == OutputFormat.MARKDOWN
        assert "投资组合报告" in result.title
        assert result.content is not None
        assert len(result.content) > 0

    def test_portfolio_report_contains_sections(self, sample_portfolio_data):
        """Test that portfolio report contains expected sections."""
        generator = ReportGenerator()
        result = generator.generate_portfolio_report(sample_portfolio_data)

        assert "组合概览" in result.content
        assert "市场配比" in result.content
        assert "持仓明细" in result.content
        assert "风险评估" in result.content

    def test_portfolio_report_json_format(self, sample_portfolio_data):
        """Test generating portfolio report in JSON format."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            output_format=OutputFormat.JSON,
        )
        result = generator.generate_portfolio_report(sample_portfolio_data, config)

        assert result.output_format == OutputFormat.JSON
        # Should be valid JSON
        parsed = json.loads(result.content)
        assert "summary" in parsed

    def test_portfolio_report_empty_data(self):
        """Test generating portfolio report with empty data."""
        generator = ReportGenerator()
        result = generator.generate_portfolio_report({})

        assert result.report_type == ReportType.PORTFOLIO
        assert result.content is not None

    def test_portfolio_report_with_custom_title(self, sample_portfolio_data):
        """Test portfolio report with custom title."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            title="My Custom Portfolio Report",
        )
        result = generator.generate_portfolio_report(sample_portfolio_data, config)

        assert result.title == "My Custom Portfolio Report"
        assert "My Custom Portfolio Report" in result.content


class TestTechnicalReport:
    """Tests for technical report generation."""

    def test_generate_technical_report(self, sample_technical_data):
        """Test generating a technical report."""
        generator = ReportGenerator()
        result = generator.generate_technical_report(sample_technical_data)

        assert result.report_type == ReportType.TECHNICAL
        assert result.output_format == OutputFormat.MARKDOWN
        assert "技术分析报告" in result.title
        assert result.content is not None

    def test_technical_report_contains_sections(self, sample_technical_data):
        """Test that technical report contains expected sections."""
        generator = ReportGenerator()
        result = generator.generate_technical_report(sample_technical_data)

        assert "均线系统" in result.content or "RSI" in result.content
        assert "MACD" in result.content or "VCP" in result.content

    def test_technical_report_json_format(self, sample_technical_data):
        """Test generating technical report in JSON format."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.TECHNICAL,
            output_format=OutputFormat.JSON,
        )
        result = generator.generate_technical_report(sample_technical_data, config)

        assert result.output_format == OutputFormat.JSON
        parsed = json.loads(result.content)
        assert "code" in parsed or "indicators" in parsed

    def test_technical_report_includes_chart_path(self, sample_technical_data):
        """Test that technical report includes chart path."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.TECHNICAL,
            include_charts=True,
        )
        result = generator.generate_technical_report(sample_technical_data, config)

        assert len(result.chart_paths) > 0
        assert "HK.00700.png" in result.chart_paths[0]


class TestDailyBrief:
    """Tests for daily brief generation."""

    def test_generate_daily_brief(self, sample_daily_data):
        """Test generating a daily brief."""
        generator = ReportGenerator()
        result = generator.generate_daily_brief(sample_daily_data)

        assert result.report_type == ReportType.DAILY
        assert "每日投资简报" in result.title
        assert result.content is not None

    def test_daily_brief_contains_sections(self, sample_daily_data):
        """Test that daily brief contains expected sections."""
        generator = ReportGenerator()
        result = generator.generate_daily_brief(sample_daily_data)

        assert "持仓变动" in result.content
        assert "持仓盈亏" in result.content

    def test_daily_brief_json_format(self, sample_daily_data):
        """Test generating daily brief in JSON format."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.DAILY,
            output_format=OutputFormat.JSON,
        )
        result = generator.generate_daily_brief(sample_daily_data, config)

        assert result.output_format == OutputFormat.JSON
        parsed = json.loads(result.content)
        assert isinstance(parsed, dict)


class TestWeeklyReview:
    """Tests for weekly review generation."""

    def test_generate_weekly_review(self, sample_weekly_data):
        """Test generating a weekly review."""
        generator = ReportGenerator()
        result = generator.generate_weekly_review(sample_weekly_data)

        assert result.report_type == ReportType.WEEKLY
        assert "周度投资回顾" in result.title
        assert result.content is not None

    def test_weekly_review_contains_sections(self, sample_weekly_data):
        """Test that weekly review contains expected sections."""
        generator = ReportGenerator()
        result = generator.generate_weekly_review(sample_weekly_data)

        assert "本周交易汇总" in result.content
        assert "本周盈亏" in result.content

    def test_weekly_review_with_date_range(self, sample_weekly_data):
        """Test weekly review with custom date range."""
        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.WEEKLY,
            date_range_start=date(2024, 12, 9),
            date_range_end=date(2024, 12, 13),
        )
        result = generator.generate_weekly_review(sample_weekly_data, config)

        assert "12/09" in result.content or "2024-12-09" in result.content


# === Generate Method Tests ===


class TestGenerateMethod:
    """Tests for the unified generate method."""

    def test_generate_portfolio(self, sample_portfolio_data):
        """Test generate method for portfolio report."""
        generator = ReportGenerator()
        config = ReportConfig(report_type=ReportType.PORTFOLIO)
        result = generator.generate(config, sample_portfolio_data)

        assert result.report_type == ReportType.PORTFOLIO

    def test_generate_technical(self, sample_technical_data):
        """Test generate method for technical report."""
        generator = ReportGenerator()
        config = ReportConfig(report_type=ReportType.TECHNICAL)
        result = generator.generate(config, sample_technical_data)

        assert result.report_type == ReportType.TECHNICAL

    def test_generate_daily(self, sample_daily_data):
        """Test generate method for daily brief."""
        generator = ReportGenerator()
        config = ReportConfig(report_type=ReportType.DAILY)
        result = generator.generate(config, sample_daily_data)

        assert result.report_type == ReportType.DAILY

    def test_generate_weekly(self, sample_weekly_data):
        """Test generate method for weekly review."""
        generator = ReportGenerator()
        config = ReportConfig(report_type=ReportType.WEEKLY)
        result = generator.generate(config, sample_weekly_data)

        assert result.report_type == ReportType.WEEKLY


# === Convenience Function Tests ===


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_create_report_generator(self):
        """Test create_report_generator factory function."""
        generator = create_report_generator()
        assert isinstance(generator, ReportGenerator)

    def test_create_report_generator_with_templates(self):
        """Test create_report_generator with custom templates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = create_report_generator(templates_dir=Path(tmpdir))
            assert generator.templates_dir == Path(tmpdir)

    def test_generate_report_function(self, sample_portfolio_data):
        """Test generate_report convenience function."""
        result = generate_report(ReportType.PORTFOLIO, sample_portfolio_data)

        assert result.report_type == ReportType.PORTFOLIO
        assert result.content is not None

    def test_generate_report_with_config(self, sample_portfolio_data):
        """Test generate_report with custom config."""
        config = ReportConfig(
            report_type=ReportType.TECHNICAL,  # Different from actual type
            output_format=OutputFormat.JSON,
        )
        result = generate_report(ReportType.PORTFOLIO, sample_portfolio_data, config)

        # Should use the report_type from first argument
        assert result.report_type == ReportType.PORTFOLIO
        # But should use output_format from config
        assert result.output_format == OutputFormat.JSON


# === Custom Filter Tests ===


class TestCustomFilters:
    """Tests for custom Jinja2 filters."""

    def test_format_number_filter(self):
        """Test format_number filter."""
        assert ReportGenerator._format_number(1234.567) == "1,234.57"
        assert ReportGenerator._format_number(1234.567, 0) == "1,235"
        assert ReportGenerator._format_number(None) == "-"

    def test_format_percent_filter(self):
        """Test format_percent filter."""
        assert ReportGenerator._format_percent(12.5) == "+12.5%"
        assert ReportGenerator._format_percent(-5.3) == "-5.3%"
        assert ReportGenerator._format_percent(0) == "0.0%"
        assert ReportGenerator._format_percent(None) == "-"

    def test_format_currency_filter(self):
        """Test format_currency filter."""
        assert ReportGenerator._format_currency(1234.56) == "$1,234.56"
        assert ReportGenerator._format_currency(1234.56, "HK$") == "HK$1,234.56"
        assert ReportGenerator._format_currency(None) == "-"

    def test_format_date_filter(self):
        """Test format_date filter."""
        d = date(2024, 12, 14)
        assert ReportGenerator._format_date(d) == "2024-12-14"
        assert ReportGenerator._format_date(d, "%m/%d") == "12/14"
        assert ReportGenerator._format_date(None) == "-"


# === Edge Cases ===


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_data(self):
        """Test generating report with empty data."""
        generator = ReportGenerator()
        result = generator.generate_portfolio_report({})
        assert result.content is not None

    def test_none_data(self):
        """Test generating report with None data."""
        generator = ReportGenerator()
        result = generator.generate_portfolio_report(None)
        assert result.content is not None

    def test_data_with_to_dict_method(self, sample_portfolio_data):
        """Test data object with to_dict method."""

        class MockData:
            def to_dict(self):
                return sample_portfolio_data

        generator = ReportGenerator()
        result = generator.generate_portfolio_report(MockData())
        assert "组合概览" in result.content

    def test_missing_template_uses_fallback(self):
        """Test that missing template uses fallback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create generator with empty templates directory
            generator = ReportGenerator(templates_dir=Path(tmpdir))
            result = generator.generate_portfolio_report({"summary": {}})

            # Should still generate content using fallback
            assert result.content is not None
            assert "组合概览" in result.content

    def test_special_characters_in_data(self):
        """Test data with special characters."""
        data = {
            "summary": {
                "position_count": 1,
                "total_market_value": 10000.0,
                "total_cost_value": 9000.0,
                "total_pl_value": 1000.0,
                "total_pl_ratio": 11.1,
                "win_rate": 100.0,
            },
            "positions": [
                {
                    "code": "HK.00700",
                    "name": "腾讯控股 <test> & 'special' \"chars\"",
                    "qty": 100,
                    "cost_price": 90.0,
                    "market_price": 100.0,
                    "market_value": 10000.0,
                    "cost_value": 9000.0,
                    "pl_value": 1000.0,
                    "pl_ratio": 11.1,
                    "weight": 100.0,
                }
            ],
            "market_allocation": [],
            "risk_metrics": {
                "concentration_risk": "high",
                "hhi_index": 10000.0,
                "diversification_score": 0.0,
                "total_unrealized_loss": 0.0,
                "positions_at_loss_ratio": 0.0,
            },
            "signals": [],
        }
        generator = ReportGenerator()
        result = generator.generate_portfolio_report(data)
        assert result.content is not None


# === Integration Tests ===


class TestIntegration:
    """Integration tests for the reports module."""

    def test_full_workflow(self, sample_portfolio_data):
        """Test full report generation workflow."""
        # Create generator
        generator = create_report_generator()

        # Generate report
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            user_id=1,
            title="Integration Test Report",
        )
        result = generator.generate(config, sample_portfolio_data)

        # Verify result
        assert result.report_type == ReportType.PORTFOLIO
        assert "Integration Test Report" in result.title

        # Save report
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "integration_test.md"
            saved_path = result.save(file_path)

            assert saved_path.exists()
            content = saved_path.read_text()
            assert "Integration Test Report" in content

    def test_multiple_reports_same_generator(
        self, sample_portfolio_data, sample_technical_data
    ):
        """Test generating multiple reports with same generator."""
        generator = ReportGenerator()

        portfolio_result = generator.generate_portfolio_report(sample_portfolio_data)
        technical_result = generator.generate_technical_report(sample_technical_data)

        assert portfolio_result.report_type == ReportType.PORTFOLIO
        assert technical_result.report_type == ReportType.TECHNICAL
        assert portfolio_result.content != technical_result.content
