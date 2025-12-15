"""
Tests for Deep Analyzer skill.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from unittest.mock import Mock, patch

import pandas as pd

from skills.deep_analyzer import (
    DeepAnalyzer,
    DeepAnalysisResult,
    EnhancedTechnicalAnalyzer,
    EnhancedTechnicalResult,
    WebDataFetcher,
    FundamentalData,
    IndustryData,
    NewsItem,
    generate_deep_analysis_report,
)
from skills.deep_analyzer.technical_analyzer import (
    TrendAnalysis,
    SupportResistance,
    MACDSignal,
    RSIAnalysis,
)
from skills.deep_analyzer.deep_analyzer import InvestmentRecommendation


class TestEnhancedTechnicalAnalyzer:
    """Tests for EnhancedTechnicalAnalyzer."""

    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV DataFrame."""
        dates = pd.date_range(start="2024-01-01", periods=120, freq="D")
        data = {
            "Open": [100 + i * 0.1 for i in range(120)],
            "High": [101 + i * 0.1 for i in range(120)],
            "Low": [99 + i * 0.1 for i in range(120)],
            "Close": [100.5 + i * 0.1 for i in range(120)],
            "Volume": [1000000 + i * 1000 for i in range(120)],
        }
        df = pd.DataFrame(data, index=dates)
        df.index.name = "Date"
        return df

    @pytest.fixture
    def mock_data_provider(self, sample_df):
        """Create mock data provider."""
        provider = Mock()
        provider.get_klines_df.return_value = sample_df
        return provider

    def test_analyzer_initialization(self):
        """Test analyzer can be initialized."""
        analyzer = EnhancedTechnicalAnalyzer()
        assert analyzer is not None
        assert analyzer.data_provider is not None

    def test_analyze_with_valid_data(self, mock_data_provider):
        """Test analysis with valid data."""
        analyzer = EnhancedTechnicalAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze("HK", "00700", "腾讯控股")

        assert result is not None
        assert isinstance(result, EnhancedTechnicalResult)
        assert result.market == "HK"
        assert result.code == "00700"
        assert result.technical_score >= 0 and result.technical_score <= 100
        assert result.technical_rating in ["strong_buy", "buy", "hold", "sell", "strong_sell"]

    def test_analyze_with_insufficient_data(self, mock_data_provider):
        """Test analysis with insufficient data."""
        # Return DataFrame with only 30 rows
        mock_data_provider.get_klines_df.return_value = mock_data_provider.get_klines_df.return_value.head(30)
        analyzer = EnhancedTechnicalAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze("HK", "00700", "腾讯控股")

        assert result is None  # Should return None for insufficient data

    def test_analyze_with_empty_data(self, mock_data_provider):
        """Test analysis with empty data."""
        mock_data_provider.get_klines_df.return_value = pd.DataFrame()
        analyzer = EnhancedTechnicalAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze("HK", "00700", "腾讯控股")

        assert result is None

    def test_trend_analysis_result(self, mock_data_provider):
        """Test that trend analysis produces valid results."""
        analyzer = EnhancedTechnicalAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze("HK", "00700", "腾讯控股")

        assert result is not None
        assert isinstance(result.trend, TrendAnalysis)
        assert result.trend.short_term in ["up", "down", "sideways"]
        assert result.trend.medium_term in ["up", "down", "sideways"]
        assert result.trend.long_term in ["up", "down", "sideways"]
        assert result.trend.strength >= 0 and result.trend.strength <= 100

    def test_support_resistance_levels(self, mock_data_provider):
        """Test support and resistance calculation."""
        analyzer = EnhancedTechnicalAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze("HK", "00700", "腾讯控股")

        assert result is not None
        assert isinstance(result.levels, SupportResistance)
        assert result.levels.support_1 < result.levels.pivot
        assert result.levels.resistance_1 > result.levels.pivot


class TestWebDataFetcher:
    """Tests for WebDataFetcher."""

    def test_fetcher_initialization(self):
        """Test fetcher can be initialized."""
        fetcher = WebDataFetcher()
        assert fetcher is not None

    def test_fetch_sync_without_web_functions(self):
        """Test fetch_sync returns result even without web functions."""
        fetcher = WebDataFetcher()
        result = fetcher.fetch_sync("HK", "00700", "腾讯控股")

        assert result is not None
        assert result.market == "HK"
        assert result.code == "00700"
        assert result.success is True


class TestDeepAnalyzer:
    """Tests for DeepAnalyzer."""

    @pytest.fixture
    def sample_df(self):
        """Create sample OHLCV DataFrame."""
        dates = pd.date_range(start="2024-01-01", periods=120, freq="D")
        data = {
            "Open": [100 + i * 0.1 for i in range(120)],
            "High": [101 + i * 0.1 for i in range(120)],
            "Low": [99 + i * 0.1 for i in range(120)],
            "Close": [100.5 + i * 0.1 for i in range(120)],
            "Volume": [1000000 + i * 1000 for i in range(120)],
        }
        df = pd.DataFrame(data, index=dates)
        df.index.name = "Date"
        return df

    @pytest.fixture
    def mock_data_provider(self, sample_df):
        """Create mock data provider."""
        provider = Mock()
        provider.get_klines_df.return_value = sample_df
        provider.get_positions.return_value = []
        return provider

    def test_analyzer_initialization(self):
        """Test analyzer can be initialized."""
        analyzer = DeepAnalyzer()
        assert analyzer is not None
        assert analyzer.technical_analyzer is not None
        assert analyzer.web_fetcher is not None

    def test_analyze_produces_result(self, mock_data_provider):
        """Test that analyze produces a result."""
        analyzer = DeepAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            include_web_data=False,
        )

        assert result is not None
        assert isinstance(result, DeepAnalysisResult)
        assert result.market == "HK"
        assert result.code == "00700"
        assert result.success is True

    def test_analyze_includes_technical(self, mock_data_provider):
        """Test that analysis includes technical results."""
        analyzer = DeepAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            include_web_data=False,
        )

        assert result.technical is not None
        assert isinstance(result.technical, EnhancedTechnicalResult)

    def test_analyze_generates_recommendation(self, mock_data_provider):
        """Test that analysis generates a recommendation."""
        analyzer = DeepAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            include_web_data=False,
        )

        assert result.recommendation is not None
        assert result.recommendation.short_term_action in ["buy", "sell", "hold"]
        assert result.recommendation.medium_term_action in ["buy", "sell", "hold"]
        assert result.recommendation.long_term_action in ["buy", "sell", "hold"]

    def test_analyze_calculates_overall_score(self, mock_data_provider):
        """Test that analysis calculates overall score."""
        analyzer = DeepAnalyzer(data_provider=mock_data_provider)
        result = analyzer.analyze(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            include_web_data=False,
        )

        assert result.overall_score >= 0 and result.overall_score <= 100
        assert result.overall_rating in ["strong_buy", "buy", "hold", "sell", "strong_sell"]


class TestReportGenerator:
    """Tests for report generation."""

    @pytest.fixture
    def sample_result(self):
        """Create sample DeepAnalysisResult."""
        return DeepAnalysisResult(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            analysis_date=date.today(),
            analysis_time=datetime.now(),
            current_price=400.0,
            technical=EnhancedTechnicalResult(
                market="HK",
                code="00700",
                stock_name="腾讯控股",
                analysis_date=date.today(),
                current_price=400.0,
                change_1d=1.5,
                change_5d=3.0,
                change_20d=-2.0,
                change_60d=5.0,
                trend=TrendAnalysis(
                    short_term="up",
                    medium_term="sideways",
                    long_term="up",
                    strength=65,
                    description="温和上升趋势",
                ),
                ma5=395.0,
                ma10=390.0,
                ma20=385.0,
                ma60=380.0,
                ma_alignment="bullish",
                obv_trend="up",
                obv_divergence=None,
                obv_score=65,
                vcp_detected=False,
                vcp_stage=None,
                vcp_score=0,
                vcp_contractions=0,
                rsi=RSIAnalysis(value=55, zone="neutral", trend="rising", divergence=None),
                macd=MACDSignal(
                    macd_value=1.5,
                    signal_value=1.2,
                    histogram=0.3,
                    trend="bullish",
                    crossover=None,
                    divergence=None,
                ),
                bb_position="middle",
                bb_width=5.0,
                levels=SupportResistance(
                    support_1=380.0,
                    support_2=370.0,
                    resistance_1=420.0,
                    resistance_2=440.0,
                    pivot=400.0,
                ),
                volume_trend="stable",
                volume_ratio=1.1,
                technical_score=60,
                technical_rating="buy",
                signals=["均线多头排列"],
                warnings=[],
            ),
            recommendation=InvestmentRecommendation(
                short_term_action="buy",
                short_term_reason="技术面强势",
                short_term_confidence=70,
                medium_term_action="buy",
                medium_term_reason="中期趋势向上",
                medium_term_confidence=65,
                long_term_action="hold",
                long_term_reason="估值合理",
                long_term_confidence=60,
                risk_level="medium",
                risk_factors=["波动较大"],
                suggested_entry=395.0,
                stop_loss=380.0,
                target_price_1=420.0,
                target_price_2=440.0,
            ),
            overall_score=60,
            overall_rating="buy",
            summary="Test summary",
        )

    def test_generate_report(self, sample_result):
        """Test that report is generated."""
        report = generate_deep_analysis_report(sample_result)

        assert report is not None
        assert isinstance(report, str)
        assert len(report) > 0

    def test_report_contains_stock_info(self, sample_result):
        """Test that report contains stock info."""
        report = generate_deep_analysis_report(sample_result)

        assert "腾讯控股" in report
        assert "HK.00700" in report
        assert "400.0" in report or "400.00" in report

    def test_report_contains_technical_section(self, sample_result):
        """Test that report contains technical section."""
        report = generate_deep_analysis_report(sample_result)

        assert "技术面分析" in report
        assert "趋势分析" in report
        assert "均线分析" in report

    def test_report_contains_recommendation(self, sample_result):
        """Test that report contains recommendation section."""
        report = generate_deep_analysis_report(sample_result)

        assert "投资建议" in report
        assert "操作建议" in report

    def test_report_contains_risk_section(self, sample_result):
        """Test that report contains risk section."""
        report = generate_deep_analysis_report(sample_result)

        assert "风险评估" in report
        assert "投资提示" in report


class TestDataClasses:
    """Tests for data classes."""

    def test_fundamental_data_creation(self):
        """Test FundamentalData can be created."""
        data = FundamentalData(
            market="HK",
            code="00700",
            stock_name="腾讯控股",
            fetch_date=date.today(),
            pe_ratio=25.5,
            market_cap=4000.0,
        )

        assert data.market == "HK"
        assert data.pe_ratio == 25.5

    def test_news_item_creation(self):
        """Test NewsItem can be created."""
        item = NewsItem(
            title="Test News",
            source="Test Source",
            sentiment="positive",
        )

        assert item.title == "Test News"
        assert item.sentiment == "positive"

    def test_industry_data_creation(self):
        """Test IndustryData can be created."""
        data = IndustryData(
            industry="互联网",
            sector="Technology",
            key_trends=["AI发展", "云计算增长"],
        )

        assert data.industry == "互联网"
        assert len(data.key_trends) == 2
