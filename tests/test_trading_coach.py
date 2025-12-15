"""Tests for Trading Coach Skill."""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from skills.shared import DataProvider, SkillContext


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def mock_position():
    """Create a mock position."""
    pos = MagicMock()
    pos.market = "HK"
    pos.code = "00700"
    pos.stock_name = "腾讯控股"
    pos.qty = Decimal("100")
    pos.cost_price = Decimal("350")
    pos.market_price = Decimal("380")
    pos.market_val = Decimal("38000")
    pos.pl_val = Decimal("3000")
    pos.pl_ratio = Decimal("8.57")
    pos.position_side = "LONG"
    pos.full_code = "HK.00700"
    return pos


@pytest.fixture
def mock_losing_position():
    """Create a mock losing position."""
    pos = MagicMock()
    pos.market = "US"
    pos.code = "BABA"
    pos.stock_name = "阿里巴巴"
    pos.qty = Decimal("50")
    pos.cost_price = Decimal("100")
    pos.market_price = Decimal("80")
    pos.market_val = Decimal("4000")
    pos.pl_val = Decimal("-1000")
    pos.pl_ratio = Decimal("-20")  # Deep loss: -20% triggers HOLDING_LOSERS
    pos.position_side = "LONG"
    pos.full_code = "US.BABA"
    return pos


@pytest.fixture
def mock_watchlist_item():
    """Create a mock watchlist item."""
    item = MagicMock()
    item.market = "HK"
    item.code = "02318"
    item.stock_name = "中国平安"
    item.group_name = "金融"
    item.full_code = "HK.02318"
    return item


@pytest.fixture
def mock_trade():
    """Create a mock trade."""
    trade = MagicMock()
    trade.market = "HK"
    trade.code = "00700"
    trade.stock_name = "腾讯控股"
    trade.trd_side = "BUY"
    trade.qty = Decimal("100")
    trade.price = Decimal("350")
    trade.trade_time = datetime.now()
    return trade


@pytest.fixture
def mock_data_provider(mock_position, mock_losing_position, mock_watchlist_item, mock_trade):
    """Create a mock data provider."""
    provider = MagicMock(spec=DataProvider)
    provider.get_positions.return_value = [mock_position, mock_losing_position]
    provider.get_watchlist.return_value = [mock_watchlist_item]
    provider.get_trades.return_value = [mock_trade]
    provider.get_user.return_value = MagicMock(id=1, username="test")
    return provider


# =============================================================================
# CompoundEducator Tests
# =============================================================================


class TestCompoundEducator:
    """Tests for CompoundEducator."""

    def test_calculate_compound_growth(self):
        """Test compound growth calculation."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        result = educator.calculate_compound_growth(
            initial_capital=Decimal("100000"),
            annual_return=0.14,
            years=10,
        )

        assert result.annual_return == 0.14
        assert result.years == 10
        assert result.initial_capital == Decimal("100000")
        assert result.multiplier > 3.5  # Should be about 3.7x
        assert result.multiplier < 4.0
        assert len(result.yearly_values) == 10

    def test_calculate_compound_growth_20_years(self):
        """Test 20-year compound growth."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        result = educator.calculate_compound_growth(
            initial_capital=Decimal("100000"),
            annual_return=0.14,
            years=20,
        )

        assert result.multiplier > 13  # Should be about 13.7x
        assert result.multiplier < 15

    def test_calculate_trading_math(self):
        """Test trading math calculation."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        result = educator.calculate_trading_math(
            trades_per_year=10,
            win_rate=0.60,
            avg_profit=0.07,
            avg_loss=0.0233,
        )

        assert result.trades_per_year == 10
        assert result.win_rate == 0.60
        assert result.avg_profit_per_trade == 0.07
        assert result.avg_loss_per_trade == 0.0233
        assert result.expected_annual_return > 0.10  # Should be about 14%
        assert result.expected_multiplier_10y > 3

    def test_find_required_return(self):
        """Test finding required return for target multiplier."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()

        # 10x in 20 years
        required = educator.find_required_return(target_multiplier=10, years=20)
        assert 0.10 < required < 0.15  # Should be about 12%

        # 10x in 10 years
        required_10y = educator.find_required_return(target_multiplier=10, years=10)
        assert required_10y > required  # Should need higher return for shorter period

    def test_find_required_years(self):
        """Test finding required years for target multiplier."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()

        # 10x at 14% annual return
        years = educator.find_required_years(target_multiplier=10, annual_return=0.14)
        assert 15 < years < 20  # Should be about 17-18 years

    def test_get_random_quote(self):
        """Test getting random quote."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        author, quote = educator.get_random_quote()

        assert isinstance(author, str)
        assert isinstance(quote, str)
        assert len(author) > 0
        assert len(quote) > 0

    def test_get_lesson(self):
        """Test getting compound lesson."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()

        lesson = educator.get_lesson("time_value")
        assert lesson.title == "时间的价值"
        assert len(lesson.content) > 0
        assert len(lesson.key_insight) > 0

        lesson = educator.get_lesson("patience")
        assert lesson.title == "耐心的回报"

    def test_get_multiplier_table(self):
        """Test getting multiplier table."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        table = educator.get_multiplier_table()

        assert isinstance(table, dict)
        assert (20, 0.14) in table
        assert table[(20, 0.14)] > 13

    def test_generate_compound_report(self):
        """Test generating compound report."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        report = educator.generate_compound_report(
            initial_capital=Decimal("100000"),
            target_years=20,
        )

        assert "复利教育报告" in report
        assert "复利增长预测" in report
        assert "100,000" in report
        assert "交易数学" in report


# =============================================================================
# PsychologyCoach Tests
# =============================================================================


class TestPsychologyCoach:
    """Tests for PsychologyCoach."""

    def test_analyze_trade_patterns_empty(self):
        """Test analyzing empty trade history."""
        from skills.trading_coach import PsychologyCoach

        coach = PsychologyCoach()
        result = coach.analyze_trade_patterns([], days=30)

        assert result.total_trades == 0
        assert result.winning_trades == 0
        assert result.losing_trades == 0

    def test_analyze_trade_patterns_with_trades(self, mock_trade):
        """Test analyzing trade patterns with trades."""
        from skills.trading_coach import PsychologyCoach

        coach = PsychologyCoach()
        trades = [mock_trade for _ in range(5)]
        result = coach.analyze_trade_patterns(trades, days=30)

        assert result.total_trades == 5

    def test_detect_behavior_patterns_concentration(self, mock_position):
        """Test detecting concentration risk pattern."""
        from skills.trading_coach import BehaviorPattern, PsychologyCoach, TradePattern

        coach = PsychologyCoach()
        trade_pattern = TradePattern(
            total_trades=5,
            winning_trades=3,
            losing_trades=2,
            consecutive_losses=0,
            consecutive_wins=0,
            avg_hold_days=5,
            largest_loss_pct=5,
            largest_win_pct=10,
        )

        # Mock a concentrated position (>25% of portfolio)
        mock_position.market_val = Decimal("30000")
        positions = [mock_position]
        total_value = Decimal("100000")

        result = coach.detect_behavior_patterns(
            trade_pattern=trade_pattern,
            positions=positions,
            total_portfolio_value=total_value,
        )

        assert BehaviorPattern.CONCENTRATION_RISK in result.patterns_detected
        assert result.risk_level in ["medium", "high"]

    def test_detect_behavior_patterns_holding_losers(self, mock_losing_position):
        """Test detecting holding losers pattern."""
        from skills.trading_coach import BehaviorPattern, PsychologyCoach, TradePattern

        coach = PsychologyCoach()
        trade_pattern = TradePattern(
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            consecutive_losses=0,
            consecutive_wins=0,
            avg_hold_days=0,
            largest_loss_pct=0,
            largest_win_pct=0,
        )

        positions = [mock_losing_position]  # -15% loss
        # Use a larger portfolio value to avoid concentration risk detection
        result = coach.detect_behavior_patterns(
            trade_pattern=trade_pattern,
            positions=positions,
            total_portfolio_value=Decimal("100000"),
        )

        assert BehaviorPattern.HOLDING_LOSERS in result.patterns_detected

    def test_detect_behavior_patterns_overtrading(self):
        """Test detecting overtrading pattern."""
        from skills.trading_coach import BehaviorPattern, PsychologyCoach, TradePattern

        coach = PsychologyCoach()
        today = date.today()
        trade_pattern = TradePattern(
            total_trades=10,
            winning_trades=5,
            losing_trades=5,
            consecutive_losses=0,
            consecutive_wins=0,
            avg_hold_days=1,
            largest_loss_pct=5,
            largest_win_pct=5,
            daily_trade_count={today: 7},  # 7 trades in one day
        )

        result = coach.detect_behavior_patterns(
            trade_pattern=trade_pattern,
            positions=[],
            total_portfolio_value=Decimal("100000"),
        )

        assert BehaviorPattern.OVERTRADING in result.patterns_detected

    def test_assess_emotion_neutral(self):
        """Test emotion assessment for neutral state."""
        from skills.trading_coach import (
            BehaviorAnalysis,
            EmotionType,
            PsychologyCoach,
        )

        coach = PsychologyCoach()
        behavior = BehaviorAnalysis(
            patterns_detected=[],
            risk_level="low",
            observations=[],
            coaching_points=[],
        )

        result = coach.assess_emotion(behavior, recent_pl_pct=2.0)

        assert result.emotion == EmotionType.NEUTRAL
        assert result.intensity < 0.5

    def test_assess_emotion_panic(self):
        """Test emotion assessment for panic state."""
        from skills.trading_coach import (
            BehaviorAnalysis,
            EmotionType,
            PsychologyCoach,
        )

        coach = PsychologyCoach()
        behavior = BehaviorAnalysis(
            patterns_detected=[],
            risk_level="low",
            observations=[],
            coaching_points=[],
        )

        result = coach.assess_emotion(behavior, recent_pl_pct=-8.0)

        assert result.emotion == EmotionType.PANIC
        assert result.intensity > 0.5

    def test_get_intervention(self):
        """Test getting intervention content."""
        from skills.trading_coach import BehaviorPattern, PsychologyCoach

        coach = PsychologyCoach()

        intervention = coach.get_intervention(BehaviorPattern.OVERTRADING, count=7)

        assert "频繁交易" in intervention["title"]
        assert len(intervention["advice"]) > 0

    def test_get_random_quote(self):
        """Test getting random trading quote."""
        from skills.trading_coach import PsychologyCoach

        coach = PsychologyCoach()
        author, quote = coach.get_random_quote()

        assert isinstance(author, str)
        assert isinstance(quote, str)

    def test_generate_psychology_check(self):
        """Test generating psychology check report."""
        from skills.trading_coach import (
            BehaviorAnalysis,
            BehaviorPattern,
            EmotionAssessment,
            EmotionType,
            PsychologyCoach,
        )

        coach = PsychologyCoach()
        behavior = BehaviorAnalysis(
            patterns_detected=[BehaviorPattern.OVERTRADING],
            risk_level="medium",
            observations=["频繁交易检测"],
            coaching_points=["建议减少交易频率"],
        )
        emotion = EmotionAssessment(
            emotion=EmotionType.OVERCONFIDENCE,
            intensity=0.6,
            triggers=["频繁交易"],
            recommendations=["冷静"],
        )

        report = coach.generate_psychology_check(behavior, emotion)

        assert "交易心理检查报告" in report
        assert "情绪状态" in report
        assert "行为模式分析" in report

    def test_get_daily_affirmation(self):
        """Test getting daily affirmation."""
        from skills.trading_coach import PsychologyCoach

        coach = PsychologyCoach()
        affirmation = coach.get_daily_affirmation()

        assert isinstance(affirmation, str)
        assert len(affirmation) > 0


# =============================================================================
# PlanGenerator Tests
# =============================================================================


class TestPlanGenerator:
    """Tests for PlanGenerator."""

    def test_generate_daily_plan_empty(self):
        """Test generating plan with no data."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()
        plan = generator.generate_daily_plan(
            positions=[],
            watchlist=[],
        )

        assert plan.plan_date == date.today()
        assert len(plan.must_do_actions) == 0
        assert len(plan.checklist) > 0

    def test_generate_daily_plan_with_stop_loss(self, mock_losing_position):
        """Test generating plan with stop loss needed."""
        from skills.trading_coach import ActionType, PlanGenerator

        generator = PlanGenerator()
        plan = generator.generate_daily_plan(
            positions=[mock_losing_position],  # -15% loss
            watchlist=[],
        )

        # Should have must-do stop loss action
        assert len(plan.must_do_actions) > 0
        stop_loss_actions = [
            a for a in plan.must_do_actions if a.action_type == ActionType.SELL
        ]
        assert len(stop_loss_actions) > 0

    def test_generate_daily_plan_with_take_profit(self, mock_position):
        """Test generating plan with take profit suggestion."""
        from skills.trading_coach import ActionPriority, PlanGenerator

        # Create a position with +35% gain
        mock_position.pl_ratio = Decimal("35")

        generator = PlanGenerator()
        plan = generator.generate_daily_plan(
            positions=[mock_position],
            watchlist=[],
        )

        # Should have take profit suggestion
        all_actions = plan.should_do_actions + plan.must_do_actions
        take_profit_actions = [
            a for a in all_actions if a.priority in [ActionPriority.SHOULD_DO, ActionPriority.MUST_DO]
        ]
        assert len(take_profit_actions) > 0

    def test_generate_daily_plan_with_watchlist(self, mock_watchlist_item):
        """Test generating plan with watchlist."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()
        plan = generator.generate_daily_plan(
            positions=[],
            watchlist=[mock_watchlist_item],
        )

        assert len(plan.watch_list) > 0

    def test_generate_position_actions(self, mock_position, mock_losing_position):
        """Test generating position action suggestions."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()
        actions = generator.generate_position_actions(
            positions=[mock_position, mock_losing_position]
        )

        assert len(actions) == 2

        # Find the losing position action
        losing_action = next(a for a in actions if a.code == "US.BABA")
        assert "止损" in losing_action.suggested_action

    def test_generate_plan_report(self):
        """Test generating plan report."""
        from skills.trading_coach import PlanGenerator, TradingPlan

        generator = PlanGenerator()
        plan = TradingPlan(
            plan_date=date.today(),
            market_overview="测试市场概览",
            must_do_actions=[],
            should_do_actions=[],
            watch_list=[],
            forbidden_actions=[],
            checklist=[],
            notes=["测试备注"],
            risk_warnings=[],
        )

        report = generator.generate_plan_report(plan)

        assert "今日交易计划" in report
        assert "测试市场概览" in report
        assert "测试备注" in report

    def test_get_trading_rules(self):
        """Test getting trading rules."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()
        rules = generator.get_trading_rules()

        assert len(rules) >= 5
        assert any("止损" in rule for rule in rules)
        assert any("仓位" in rule for rule in rules)


# =============================================================================
# TradingCoach Integration Tests
# =============================================================================


class TestTradingCoach:
    """Tests for TradingCoach main controller."""

    def test_trading_coach_init(self):
        """Test TradingCoach initialization."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach()

        assert coach.name == "trading_coach"
        assert coach.plan_generator is not None
        assert coach.psychology_coach is not None
        assert coach.compound_educator is not None

    def test_trading_coach_capabilities(self):
        """Test TradingCoach capabilities."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach()
        capabilities = coach.get_capabilities()

        assert "daily_plan" in capabilities
        assert "psychology_check" in capabilities
        assert "compound_lesson" in capabilities
        assert "full_coaching" in capabilities

    def test_trading_coach_execute_daily_plan(self, mock_data_provider):
        """Test executing daily plan generation."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="daily_plan",
        )

        result = coach.execute(context)

        assert result.success
        assert result.skill_name == "trading_coach"
        assert result.data is not None
        assert result.data.trading_plan is not None

    def test_trading_coach_execute_psychology_check(self, mock_data_provider):
        """Test executing psychology check."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="psychology_check",
        )

        result = coach.execute(context)

        assert result.success
        assert result.data is not None
        assert result.data.behavior_analysis is not None
        assert result.data.emotion_assessment is not None

    def test_trading_coach_execute_compound_lesson(self, mock_data_provider):
        """Test executing compound lesson."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="compound_lesson",
            parameters={
                "capital": 100000,
                "years": 20,
                "annual_return": 0.14,
            },
        )

        result = coach.execute(context)

        assert result.success
        assert result.data is not None
        assert result.data.compound_projection is not None
        assert result.data.compound_projection.multiplier > 10

    def test_trading_coach_execute_position_review(self, mock_data_provider):
        """Test executing position review."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="position_review",
        )

        result = coach.execute(context)

        assert result.success
        assert result.data is not None
        assert len(result.data.position_actions) == 2  # 2 positions

    def test_trading_coach_execute_full_coaching(self, mock_data_provider):
        """Test executing full coaching session."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="full_coaching",
        )

        result = coach.execute(context)

        assert result.success
        assert result.data is not None
        assert result.data.trading_plan is not None
        assert result.data.behavior_analysis is not None
        assert result.data.compound_projection is not None
        assert len(result.report_content) > 0

    def test_trading_coach_report_generation(self, mock_data_provider):
        """Test report generation."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=1,
            request_type="full_coaching",
        )

        result = coach.execute(context)

        assert "交易导师报告" in result.report_content
        assert "今日箴言" in result.report_content
        assert "交易纪律" in result.report_content

    def test_trading_coach_invalid_user(self, mock_data_provider):
        """Test with invalid user ID."""
        from skills.trading_coach import TradingCoach

        coach = TradingCoach(data_provider=mock_data_provider)
        context = SkillContext(
            user_id=0,  # Invalid
            request_type="daily_plan",
        )

        result = coach.execute(context)

        assert not result.success
        assert "Invalid user_id" in result.error_message


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestGenerateCoachingReport:
    """Tests for generate_coaching_report convenience function."""

    def test_generate_coaching_report(self, mock_data_provider):
        """Test generating coaching report via convenience function."""
        from skills.trading_coach import generate_coaching_report

        with patch("skills.trading_coach.trading_coach.DataProvider") as MockProvider:
            MockProvider.return_value = mock_data_provider

            report = generate_coaching_report(
                user_id=1,
                request_type="full_coaching",
            )

            assert isinstance(report, str)
            assert "交易导师报告" in report


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_compound_growth_zero_capital(self):
        """Test compound growth with zero capital."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        result = educator.calculate_compound_growth(
            initial_capital=Decimal("0"),
            annual_return=0.14,
            years=10,
        )

        assert result.final_value == Decimal("0")
        assert result.multiplier == 0

    def test_compound_growth_negative_return(self):
        """Test compound growth with negative return."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        result = educator.calculate_compound_growth(
            initial_capital=Decimal("100000"),
            annual_return=-0.10,  # 10% loss per year
            years=10,
        )

        assert result.final_value < Decimal("100000")
        assert result.multiplier < 1

    def test_find_required_years_zero_return(self):
        """Test finding required years with zero return."""
        from skills.trading_coach import CompoundEducator

        educator = CompoundEducator()
        years = educator.find_required_years(target_multiplier=10, annual_return=0)

        assert years == 999  # Infinite

    def test_psychology_coach_no_trades(self):
        """Test psychology check with no trades."""
        from skills.trading_coach import PsychologyCoach

        coach = PsychologyCoach()
        pattern = coach.analyze_trade_patterns([], days=30)

        assert pattern.total_trades == 0

    def test_plan_generator_empty_inputs(self):
        """Test plan generator with empty inputs."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()
        plan = generator.generate_daily_plan(positions=[], watchlist=[])

        assert plan is not None
        assert plan.plan_date == date.today()

    def test_position_actions_various_pl_levels(self):
        """Test position actions for various P&L levels."""
        from skills.trading_coach import PlanGenerator

        generator = PlanGenerator()

        # Test different P&L levels - check keyword in action or reason
        test_cases = [
            (-20, "止损"),  # Deep loss
            (-10, "触及止损"),  # At stop loss
            (5, "观察"),  # Small gain
            (35, "减仓"),  # Take profit zone - action is "减仓1/3"
            (60, "减仓"),  # High profit
            (110, "长持"),  # Doubled
        ]

        for pl_pct, expected_keyword in test_cases:
            pos = MagicMock()
            pos.full_code = "HK.00700"
            pos.stock_name = "腾讯"
            pos.market_val = Decimal("10000")
            pos.pl_ratio = Decimal(str(pl_pct))

            actions = generator.generate_position_actions([pos])
            assert len(actions) == 1
            # Check keyword in either action or reason
            action = actions[0]
            combined = action.suggested_action + action.reason
            assert expected_keyword in combined, f"Expected '{expected_keyword}' in action for {pl_pct}%"


# =============================================================================
# Data Class Tests
# =============================================================================


class TestDataClasses:
    """Tests for data classes."""

    def test_coaching_result_defaults(self):
        """Test CoachingResult default values."""
        from skills.trading_coach import CoachingResult

        result = CoachingResult()

        assert result.trading_plan is None
        assert result.position_actions == []
        assert result.coaching_date == date.today()

    def test_trading_plan_structure(self):
        """Test TradingPlan structure."""
        from skills.trading_coach import TradingPlan

        plan = TradingPlan(
            plan_date=date.today(),
            market_overview="Test",
            must_do_actions=[],
            should_do_actions=[],
            watch_list=[],
            forbidden_actions=[],
            checklist=[],
            notes=[],
            risk_warnings=[],
        )

        assert plan.plan_date == date.today()
        assert plan.market_overview == "Test"

    def test_compound_projection_structure(self):
        """Test CompoundProjection structure."""
        from skills.trading_coach import CompoundProjection

        projection = CompoundProjection(
            annual_return=0.14,
            years=20,
            initial_capital=Decimal("100000"),
            final_value=Decimal("1374000"),
            total_gain=Decimal("1274000"),
            multiplier=13.74,
        )

        assert projection.annual_return == 0.14
        assert projection.years == 20
        assert projection.multiplier == 13.74

    def test_behavior_pattern_enum(self):
        """Test BehaviorPattern enum values."""
        from skills.trading_coach import BehaviorPattern

        assert BehaviorPattern.OVERTRADING.value == "overtrading"
        assert BehaviorPattern.LOSS_CHASING.value == "loss_chasing"
        assert BehaviorPattern.FOMO.value == "fomo"

    def test_emotion_type_enum(self):
        """Test EmotionType enum values."""
        from skills.trading_coach import EmotionType

        assert EmotionType.FEAR.value == "fear"
        assert EmotionType.GREED.value == "greed"
        assert EmotionType.NEUTRAL.value == "neutral"

    def test_action_priority_enum(self):
        """Test ActionPriority enum values."""
        from skills.trading_coach import ActionPriority

        assert ActionPriority.MUST_DO.value == "must_do"
        assert ActionPriority.FORBIDDEN.value == "forbidden"
