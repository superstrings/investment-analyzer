"""Tests for Market Observer Skill."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from skills.market_observer import (
    AnomalyStock,
    EventInfo,
    GlobalMarketSnapshot,
    MarketIndicators,
    MarketObserver,
    MarketObserverResult,
    MarketSummary,
    MoneyFlowData,
    PositionDailySummary,
    PostMarketReport,
    PostMarketSummarizer,
    PreMarketAnalyzer,
    PreMarketReport,
    RotationSignal,
    SectorAnalysisReport,
    SectorPerformance,
    SectorRotationAnalyzer,
    SentimentLevel,
    SentimentMeter,
    SentimentResult,
    StockPreMarketInfo,
    TradeSummary,
    generate_observation_report,
)
from skills.shared import SkillContext


# =============================================================================
# SentimentMeter Tests
# =============================================================================


class TestSentimentMeter:
    """Tests for SentimentMeter class."""

    def test_init(self):
        """Test SentimentMeter initialization."""
        meter = SentimentMeter()
        assert meter is not None

    def test_calculate_sentiment_default_indicators(self):
        """Test sentiment calculation with default indicators."""
        meter = SentimentMeter()
        indicators = MarketIndicators()

        result = meter.calculate_sentiment(indicators)

        assert isinstance(result, SentimentResult)
        assert 0 <= result.score <= 100
        assert result.level in SentimentLevel
        assert result.calculation_date is not None

    def test_calculate_sentiment_extreme_fear(self):
        """Test extreme fear sentiment detection."""
        meter = SentimentMeter()
        indicators = MarketIndicators(
            advance_decline_ratio=0.1,  # Very bearish
            new_high_low_ratio=0.1,
            above_ma20_pct=0.15,
            up_volume_ratio=0.2,
            vix_value=40.0,  # High VIX = fear
            market_change_pct=-3.0,
        )

        result = meter.calculate_sentiment(indicators)

        assert result.score < 30
        assert result.level in (SentimentLevel.EXTREME_FEAR, SentimentLevel.FEAR)

    def test_calculate_sentiment_extreme_greed(self):
        """Test extreme greed sentiment detection."""
        meter = SentimentMeter()
        indicators = MarketIndicators(
            advance_decline_ratio=0.9,  # Very bullish (0-1 scale)
            new_high_low_ratio=0.9,
            above_ma20_pct=0.85,
            up_volume_ratio=0.85,
            vix_value=10.0,  # Low VIX = greed
            market_change_pct=3.0,
        )

        result = meter.calculate_sentiment(indicators)

        assert result.score > 70
        assert result.level in (SentimentLevel.EXTREME_GREED, SentimentLevel.GREED)

    def test_calculate_sentiment_neutral(self):
        """Test neutral sentiment detection."""
        meter = SentimentMeter()
        indicators = MarketIndicators(
            advance_decline_ratio=0.5,
            new_high_low_ratio=0.5,
            above_ma20_pct=0.5,
            up_volume_ratio=0.5,
            vix_value=20.0,
            market_change_pct=0.0,
        )

        result = meter.calculate_sentiment(indicators)

        assert 35 <= result.score <= 65
        assert result.level == SentimentLevel.NEUTRAL

    def test_get_vix_interpretation_extreme_low(self):
        """Test VIX interpretation for extreme low values."""
        meter = SentimentMeter()
        level, interpretation = meter.get_vix_interpretation(10.0)

        assert "低" in level or "极低" in level

    def test_get_vix_interpretation_high(self):
        """Test VIX interpretation for high values."""
        meter = SentimentMeter()
        level, interpretation = meter.get_vix_interpretation(35.0)

        assert "高" in level

    def test_generate_sentiment_report(self):
        """Test sentiment report generation."""
        meter = SentimentMeter()
        result = SentimentResult(
            score=45.0,
            level=SentimentLevel.NEUTRAL,
            calculation_date=date.today(),
            components={"advance_decline": 50, "vix": 50},
            interpretation="市场情绪中性",
            trading_implication="保持观望",
        )

        report = meter.generate_sentiment_report(result)

        assert isinstance(report, str)
        assert "情绪指数" in report
        assert "45" in report

    def test_generate_trading_implication(self):
        """Test trading implication generation for different sentiment levels."""
        meter = SentimentMeter()

        # Test all sentiment levels
        for level in SentimentLevel:
            implication = meter._generate_trading_implication(50.0, level)
            assert isinstance(implication, str)
            assert len(implication) > 0


# =============================================================================
# PreMarketAnalyzer Tests
# =============================================================================


class TestPreMarketAnalyzer:
    """Tests for PreMarketAnalyzer class."""

    def test_init(self):
        """Test PreMarketAnalyzer initialization."""
        analyzer = PreMarketAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_data(self):
        """Test analysis with empty data."""
        analyzer = PreMarketAnalyzer()

        report = analyzer.analyze(
            market="HK",
            positions=[],
            watchlist=[],
        )

        assert isinstance(report, PreMarketReport)
        assert report.market == "HK"
        assert report.report_date == date.today()

    def test_analyze_with_global_snapshot(self):
        """Test analysis with global market snapshot."""
        analyzer = PreMarketAnalyzer()

        snapshot = GlobalMarketSnapshot(
            sp500_change=1.5,
            nasdaq_change=2.0,
            dow_change=1.2,
            gold_change=-0.3,
            oil_change=0.5,
            usd_cnh_change=0.1,
            a50_change=0.8,
            hsi_change=1.0,
        )

        report = analyzer.analyze(
            market="HK",
            positions=[],
            watchlist=[],
            global_snapshot=snapshot,
        )

        assert report.global_snapshot == snapshot

    def test_analyze_generates_trading_focus(self):
        """Test that analysis generates trading focus."""
        analyzer = PreMarketAnalyzer()

        # Create mock position with attributes
        mock_position = MagicMock()
        mock_position.full_code = "HK.00700"
        mock_position.code = "00700"
        mock_position.market = "HK"
        mock_position.stock_name = "腾讯控股"
        mock_position.pl_ratio = -5.0

        report = analyzer.analyze(
            market="HK",
            positions=[mock_position],
            watchlist=[],
        )

        assert isinstance(report.trading_focus, list)

    def test_generate_report(self):
        """Test pre-market report generation."""
        analyzer = PreMarketAnalyzer()

        report = PreMarketReport(
            report_date=date.today(),
            market="HK",
            global_snapshot=GlobalMarketSnapshot(),
            market_outlook="市场平稳",
            key_events=[],
            position_alerts=[],
            watchlist_alerts=[],
            risk_warnings=["测试风险"],
            trading_focus=["关注腾讯"],
        )

        report_str = analyzer.generate_report(report)

        assert isinstance(report_str, str)
        assert "盘前分析" in report_str


# =============================================================================
# PostMarketSummarizer Tests
# =============================================================================


class TestPostMarketSummarizer:
    """Tests for PostMarketSummarizer class."""

    def test_init(self):
        """Test PostMarketSummarizer initialization."""
        summarizer = PostMarketSummarizer()
        assert summarizer is not None

    def test_summarize_empty_data(self):
        """Test summarization with empty data."""
        summarizer = PostMarketSummarizer()

        report = summarizer.summarize(
            market="HK",
            positions=[],
            trades=[],
        )

        assert isinstance(report, PostMarketReport)
        assert report.market == "HK"
        assert report.portfolio_pl_today == Decimal("0")

    def test_summarize_with_positions(self):
        """Test summarization with positions."""
        summarizer = PostMarketSummarizer()

        mock_position = MagicMock()
        mock_position.full_code = "HK.00700"
        mock_position.code = "00700"
        mock_position.stock_name = "腾讯控股"
        mock_position.market_price = Decimal("380.00")
        mock_position.market_val = Decimal("38000")
        mock_position.qty = Decimal("100")

        report = summarizer.summarize(
            market="HK",
            positions=[mock_position],
        )

        assert len(report.position_summaries) > 0

    def test_summarize_with_market_summary(self):
        """Test summarization with market summary."""
        summarizer = PostMarketSummarizer()

        market_summary = MarketSummary(
            market="HK",
            index_name="恒生指数",
            index_close=Decimal("20000"),
            index_change=1.5,
            advance_count=1000,
            decline_count=500,
        )

        report = summarizer.summarize(
            market="HK",
            positions=[],
            market_summary=market_summary,
        )

        assert report.market_summary.index_change == 1.5

    def test_generate_report(self):
        """Test post-market report generation."""
        summarizer = PostMarketSummarizer()

        report = PostMarketReport(
            report_date=date.today(),
            market="HK",
            market_summary=MarketSummary(market="HK", index_name="恒生指数"),
            portfolio_change_pct=2.5,
            portfolio_pl_today=Decimal("5000"),
            position_summaries=[],
            trade_summary=TradeSummary(),
            anomaly_stocks=[],
            tomorrow_focus=["关注大盘"],
            lessons_learned=["保持耐心"],
        )

        report_str = summarizer.generate_report(report)

        assert isinstance(report_str, str)
        assert "盘后总结" in report_str
        assert "5,000" in report_str or "5000" in report_str

    def test_find_anomalies_price_spike(self):
        """Test anomaly detection for price spikes."""
        summarizer = PostMarketSummarizer()

        summary = PositionDailySummary(
            code="HK.00700",
            stock_name="腾讯控股",
            open_price=Decimal("360"),
            close_price=Decimal("400"),
            high_price=Decimal("405"),
            low_price=Decimal("358"),
            daily_change_pct=8.0,
        )

        anomalies = summarizer._find_anomalies([summary])

        assert len(anomalies) > 0
        assert anomalies[0].anomaly_type == "price_spike"


# =============================================================================
# SectorRotationAnalyzer Tests
# =============================================================================


class TestSectorRotationAnalyzer:
    """Tests for SectorRotationAnalyzer class."""

    def test_init(self):
        """Test SectorRotationAnalyzer initialization."""
        analyzer = SectorRotationAnalyzer()
        assert analyzer is not None

    def test_analyze_empty_data(self):
        """Test analysis with empty data."""
        analyzer = SectorRotationAnalyzer()

        report = analyzer.analyze(market="HK")

        assert isinstance(report, SectorAnalysisReport)
        assert report.market == "HK"
        assert len(report.top_sectors) == 0

    def test_analyze_with_sector_data(self):
        """Test analysis with sector performance data."""
        analyzer = SectorRotationAnalyzer()

        sectors = [
            SectorPerformance(
                sector_name="科技",
                sector_code="tech",
                change_1d=3.5,
                change_5d=8.0,
                change_20d=15.0,
            ),
            SectorPerformance(
                sector_name="金融",
                sector_code="finance",
                change_1d=-1.2,
                change_5d=-2.0,
                change_20d=-5.0,
            ),
            SectorPerformance(
                sector_name="消费",
                sector_code="consumer",
                change_1d=1.0,
                change_5d=3.0,
                change_20d=8.0,
            ),
        ]

        report = analyzer.analyze(market="HK", sector_data=sectors)

        assert len(report.top_sectors) > 0
        assert report.top_sectors[0].sector_name == "科技"

    def test_analyze_with_money_flow(self):
        """Test analysis with money flow data."""
        analyzer = SectorRotationAnalyzer()

        money_flow = [
            MoneyFlowData(
                sector_name="科技",
                net_inflow=Decimal("1500000000"),
                flow_trend="inflow",
            ),
            MoneyFlowData(
                sector_name="金融",
                net_inflow=Decimal("-800000000"),
                flow_trend="outflow",
            ),
        ]

        sectors = [
            SectorPerformance(
                sector_name="科技",
                sector_code="tech",
                change_1d=2.0,
            ),
        ]

        report = analyzer.analyze(
            market="HK",
            sector_data=sectors,
            money_flow_data=money_flow,
        )

        assert len(report.money_flow) == 2

    def test_detect_rotation_signals(self):
        """Test rotation signal detection."""
        analyzer = SectorRotationAnalyzer()

        sectors = [
            SectorPerformance(
                sector_name="科技",
                sector_code="tech",
                change_1d=3.0,
                change_20d=-5.0,  # Short-term reversal
            ),
            SectorPerformance(
                sector_name="金融",
                sector_code="finance",
                change_1d=-3.0,
                change_20d=12.0,  # Profit taking
            ),
        ]

        signals = analyzer._detect_rotation_signals(sectors, [])

        assert len(signals) > 0

    def test_identify_market_theme(self):
        """Test market theme identification."""
        analyzer = SectorRotationAnalyzer()

        # Tech-led market
        tech_sectors = [
            SectorPerformance(sector_name="科技", sector_code="tech", change_1d=3.0),
        ]
        theme = analyzer._identify_market_theme(tech_sectors, [])
        assert "科技" in theme

    def test_generate_report(self):
        """Test sector analysis report generation."""
        analyzer = SectorRotationAnalyzer()

        report = SectorAnalysisReport(
            report_date=date.today(),
            market="HK",
            top_sectors=[
                SectorPerformance(
                    sector_name="科技",
                    sector_code="tech",
                    change_1d=3.0,
                    change_5d=5.0,
                    change_20d=10.0,
                ),
            ],
            bottom_sectors=[],
            money_flow=[],
            rotation_signals=[],
            market_theme="科技主导",
            sector_recommendation="关注科技板块",
        )

        report_str = analyzer.generate_report(report)

        assert isinstance(report_str, str)
        assert "板块轮动" in report_str
        assert "科技" in report_str

    def test_get_sector_mapping(self):
        """Test sector code to name mapping."""
        analyzer = SectorRotationAnalyzer()

        hk_mapping = analyzer.get_sector_mapping("HK")
        us_mapping = analyzer.get_sector_mapping("US")
        a_mapping = analyzer.get_sector_mapping("A")

        assert "tech" in hk_mapping
        assert "tech" in us_mapping
        assert "tech" in a_mapping


# =============================================================================
# MarketObserver Tests
# =============================================================================


class TestMarketObserver:
    """Tests for MarketObserver main controller."""

    def test_init(self):
        """Test MarketObserver initialization."""
        observer = MarketObserver()
        assert observer is not None
        assert observer.name == "market_observer"

    def test_init_with_data_provider(self):
        """Test MarketObserver initialization with data provider."""
        mock_provider = MagicMock()
        observer = MarketObserver(data_provider=mock_provider)
        assert observer.data_provider == mock_provider

    def test_get_capabilities(self):
        """Test getting skill capabilities."""
        observer = MarketObserver()
        caps = observer.get_capabilities()

        assert "pre_market" in caps
        assert "post_market" in caps
        assert "sector" in caps
        assert "sentiment" in caps
        assert "full" in caps
        assert "auto" in caps

    def test_execute_sentiment_analysis(self):
        """Test executing sentiment analysis."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="sentiment",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data is not None
        assert result.data.observation_type == "sentiment"

    def test_execute_pre_market_analysis(self):
        """Test executing pre-market analysis."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="pre_market",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data.observation_type == "pre_market"

    def test_execute_post_market_analysis(self):
        """Test executing post-market analysis."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_trades.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="post_market",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data.observation_type == "post_market"

    def test_execute_sector_analysis(self):
        """Test executing sector rotation analysis."""
        mock_provider = MagicMock()
        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="sector",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data.observation_type == "sector"

    def test_execute_full_observation(self):
        """Test executing full observation."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []
        mock_provider.get_trades.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="full",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data.observation_type == "full"
        assert result.data.pre_market_report is not None
        assert result.data.post_market_report is not None
        assert result.data.sector_report is not None
        assert result.data.sentiment_result is not None

    def test_execute_auto_detection(self):
        """Test auto detection based on market state."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []
        mock_provider.get_trades.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="auto",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.success
        assert result.data is not None

    def test_execute_generates_report(self):
        """Test that execution generates report content."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="sentiment",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.report_content is not None
        assert len(result.report_content) > 0

    def test_execute_generates_next_actions(self):
        """Test that execution generates next actions."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []

        observer = MarketObserver(data_provider=mock_provider)

        context = SkillContext(
            user_id=1,
            request_type="sentiment",
            markets=["HK"],
        )

        result = observer.execute(context)

        assert result.next_actions is not None
        assert len(result.next_actions) > 0

    def test_execute_invalid_context(self):
        """Test execution with invalid context."""
        observer = MarketObserver()

        # Context without user_id
        context = SkillContext(
            user_id=0,
            request_type="sentiment",
        )

        result = observer.execute(context)

        # Should handle gracefully (may succeed or return error)
        assert result is not None


# =============================================================================
# Data Class Tests
# =============================================================================


class TestMarketIndicators:
    """Tests for MarketIndicators dataclass."""

    def test_default_values(self):
        """Test default indicator values."""
        indicators = MarketIndicators()

        assert indicators.advance_decline_ratio == 0.5
        assert indicators.vix_value is None  # Default is None

    def test_custom_values(self):
        """Test custom indicator values."""
        indicators = MarketIndicators(
            advance_decline_ratio=0.7,
            vix_value=15.0,
            market_change_pct=1.5,
        )

        assert indicators.advance_decline_ratio == 0.7
        assert indicators.vix_value == 15.0
        assert indicators.market_change_pct == 1.5


class TestSentimentResult:
    """Tests for SentimentResult dataclass."""

    def test_create_result(self):
        """Test creating sentiment result."""
        result = SentimentResult(
            score=55.0,
            level=SentimentLevel.NEUTRAL,
            calculation_date=date.today(),
            components={"advance_decline": 50, "vix": 60},
            interpretation="市场情绪中性",
            trading_implication="保持观望",
        )

        assert result.score == 55.0
        assert result.level == SentimentLevel.NEUTRAL


class TestSectorPerformance:
    """Tests for SectorPerformance dataclass."""

    def test_create_performance(self):
        """Test creating sector performance."""
        perf = SectorPerformance(
            sector_name="科技",
            sector_code="tech",
            change_1d=2.5,
            change_5d=5.0,
            change_20d=10.0,
        )

        assert perf.sector_name == "科技"
        assert perf.change_1d == 2.5


class TestRotationSignal:
    """Tests for RotationSignal dataclass."""

    def test_create_signal(self):
        """Test creating rotation signal."""
        signal = RotationSignal(
            from_sector="金融",
            to_sector="科技",
            strength="strong",
            evidence=["资金流入科技"],
            trading_idea="关注科技龙头",
        )

        assert signal.from_sector == "金融"
        assert signal.strength == "strong"


class TestGlobalMarketSnapshot:
    """Tests for GlobalMarketSnapshot dataclass."""

    def test_default_values(self):
        """Test default snapshot values."""
        snapshot = GlobalMarketSnapshot()

        assert snapshot.sp500_change is None
        assert snapshot.nasdaq_change is None

    def test_custom_values(self):
        """Test custom snapshot values."""
        snapshot = GlobalMarketSnapshot(
            sp500_change=1.5,
            nasdaq_change=2.0,
            gold_change=-0.5,
        )

        assert snapshot.sp500_change == 1.5
        assert snapshot.nasdaq_change == 2.0


# =============================================================================
# Integration Tests
# =============================================================================


class TestGenerateObservationReport:
    """Tests for generate_observation_report convenience function."""

    @patch("skills.market_observer.market_observer.DataProvider")
    def test_generate_pre_market_report(self, mock_provider_class):
        """Test generating pre-market report."""
        mock_provider = MagicMock()
        mock_provider.get_positions.return_value = []
        mock_provider.get_watchlist.return_value = []
        mock_provider_class.return_value = mock_provider

        report = generate_observation_report(
            user_id=1,
            request_type="pre_market",
            market="HK",
        )

        assert isinstance(report, str)
        assert len(report) > 0

    @patch("skills.market_observer.market_observer.DataProvider")
    def test_generate_sentiment_report(self, mock_provider_class):
        """Test generating sentiment report."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        report = generate_observation_report(
            user_id=1,
            request_type="sentiment",
            market="HK",
        )

        assert isinstance(report, str)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_sentiment_with_zero_vix(self):
        """Test sentiment calculation with zero VIX."""
        meter = SentimentMeter()
        indicators = MarketIndicators(vix_value=0.0)

        result = meter.calculate_sentiment(indicators)

        assert result is not None
        assert 0 <= result.score <= 100

    def test_sentiment_with_extreme_values(self):
        """Test sentiment with extreme indicator values."""
        meter = SentimentMeter()
        indicators = MarketIndicators(
            advance_decline_ratio=1.0,  # Max on 0-1 scale
            new_high_low_ratio=1.0,
            above_ma20_pct=1.0,
            vix_value=100.0,
        )

        result = meter.calculate_sentiment(indicators)

        assert result is not None
        assert 0 <= result.score <= 100

    def test_sector_rotation_single_sector(self):
        """Test sector rotation with single sector."""
        analyzer = SectorRotationAnalyzer()

        sectors = [
            SectorPerformance(sector_name="科技", sector_code="tech", change_1d=1.0),
        ]

        report = analyzer.analyze(market="HK", sector_data=sectors)

        assert len(report.rotation_signals) == 0  # No rotation with single sector

    def test_post_market_with_high_volatility(self):
        """Test post-market summary with high volatility positions."""
        summarizer = PostMarketSummarizer()

        summary = PositionDailySummary(
            code="HK.00700",
            stock_name="腾讯控股",
            open_price=Decimal("300"),
            close_price=Decimal("350"),
            high_price=Decimal("360"),
            low_price=Decimal("290"),
            daily_change_pct=16.67,
            volume_ratio=3.0,
        )

        anomalies = summarizer._find_anomalies([summary])

        # Should detect both price spike and volume spike
        anomaly_types = [a.anomaly_type for a in anomalies]
        assert "price_spike" in anomaly_types
        assert "volume_spike" in anomaly_types


class TestSentimentLevelEnum:
    """Tests for SentimentLevel enum."""

    def test_all_levels_exist(self):
        """Test that all sentiment levels exist."""
        assert SentimentLevel.EXTREME_FEAR
        assert SentimentLevel.FEAR
        assert SentimentLevel.NEUTRAL
        assert SentimentLevel.GREED
        assert SentimentLevel.EXTREME_GREED

    def test_level_values(self):
        """Test sentiment level values."""
        assert SentimentLevel.EXTREME_FEAR.value == "extreme_fear"
        assert SentimentLevel.GREED.value == "greed"
