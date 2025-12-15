"""Tests for Workflow Engine."""

from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock, patch

import pytest

from skills.shared import SkillContext, SkillResult
from skills.workflow import (
    DailyWorkflow,
    MonthlyStats,
    MonthlyWorkflow,
    ScheduledTask,
    TaskResult,
    WorkflowEngine,
    WorkflowEngineResult,
    WorkflowPhase,
    WorkflowResult,
    WorkflowSchedule,
    WorkflowScheduler,
    run_daily_workflow,
    run_monthly_workflow,
    run_workflow,
)


# =============================================================================
# WorkflowScheduler Tests
# =============================================================================


class TestWorkflowScheduler:
    """Tests for WorkflowScheduler class."""

    def test_init(self):
        """Test scheduler initialization."""
        scheduler = WorkflowScheduler()
        assert scheduler is not None
        assert "HK" in scheduler.schedules
        assert "US" in scheduler.schedules
        assert "A" in scheduler.schedules

    def test_get_current_phase(self):
        """Test getting current workflow phase."""
        scheduler = WorkflowScheduler()

        # Should return a valid phase
        phase = scheduler.get_current_phase("HK")
        assert phase in WorkflowPhase

    def test_get_phase_start_time(self):
        """Test getting phase start time."""
        scheduler = WorkflowScheduler()

        # HK pre-market should be 8:30
        pre_market_time = scheduler.get_phase_start_time(
            WorkflowPhase.PRE_MARKET, "HK"
        )
        assert pre_market_time == time(8, 30)

        # US pre-market should be 20:00
        us_pre_market = scheduler.get_phase_start_time(
            WorkflowPhase.PRE_MARKET, "US"
        )
        assert us_pre_market == time(20, 0)

    def test_is_trading_day_weekday(self):
        """Test trading day detection for weekdays."""
        scheduler = WorkflowScheduler()

        # Find next Monday
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = today + timedelta(days=days_until_monday)

        # Monday should be trading day
        assert scheduler.is_trading_day(next_monday, "HK")

    def test_is_trading_day_weekend(self):
        """Test trading day detection for weekends."""
        scheduler = WorkflowScheduler()

        # Find next Saturday
        today = date.today()
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7
        next_saturday = today + timedelta(days=days_until_saturday)

        # Saturday should not be trading day
        assert not scheduler.is_trading_day(next_saturday, "HK")

    def test_get_last_trading_day_of_month(self):
        """Test getting last trading day of month."""
        scheduler = WorkflowScheduler()

        last_day = scheduler.get_last_trading_day_of_month(2025, 12, "HK")

        # Should be a weekday
        assert last_day.weekday() < 5
        # Should be in December
        assert last_day.month == 12

    def test_create_daily_schedule(self):
        """Test creating daily schedule."""
        scheduler = WorkflowScheduler()

        schedule = scheduler.create_daily_schedule(user_id=1, markets=["HK"])

        assert isinstance(schedule, WorkflowSchedule)
        assert len(schedule.tasks) > 0

        # Check that pre-market and post-market tasks exist
        pre_market_tasks = [t for t in schedule.tasks if t.phase == WorkflowPhase.PRE_MARKET]
        post_market_tasks = [t for t in schedule.tasks if t.phase == WorkflowPhase.POST_MARKET]

        assert len(pre_market_tasks) > 0
        assert len(post_market_tasks) > 0

    def test_create_monthly_schedule(self):
        """Test creating monthly schedule."""
        scheduler = WorkflowScheduler()

        schedule = scheduler.create_monthly_schedule(user_id=1, markets=["HK"])

        assert isinstance(schedule, WorkflowSchedule)
        assert len(schedule.tasks) > 0

    def test_get_next_phase_time(self):
        """Test getting next phase time."""
        scheduler = WorkflowScheduler()

        next_phase, next_time = scheduler.get_next_phase_time("HK")

        assert next_phase in WorkflowPhase
        # next_time may be None or datetime


class TestScheduledTask:
    """Tests for ScheduledTask dataclass."""

    def test_create_task(self):
        """Test creating a scheduled task."""
        task = ScheduledTask(
            task_id="test_task",
            name="Test Task",
            phase=WorkflowPhase.PRE_MARKET,
            skill_type="analyst",
            request_type="batch",
            priority=8,
        )

        assert task.task_id == "test_task"
        assert task.phase == WorkflowPhase.PRE_MARKET
        assert task.priority == 8
        assert task.enabled

    def test_task_with_dependencies(self):
        """Test task with dependencies."""
        task = ScheduledTask(
            task_id="dependent_task",
            name="Dependent Task",
            phase=WorkflowPhase.PRE_MARKET,
            skill_type="coach",
            request_type="daily_plan",
            dependencies=["task1", "task2"],
        )

        assert len(task.dependencies) == 2


# =============================================================================
# DailyWorkflow Tests
# =============================================================================


class TestDailyWorkflow:
    """Tests for DailyWorkflow class."""

    def test_init(self):
        """Test DailyWorkflow initialization."""
        workflow = DailyWorkflow()
        assert workflow is not None
        assert workflow.name == "daily_workflow"

    def test_init_with_data_provider(self):
        """Test DailyWorkflow with custom data provider."""
        mock_provider = MagicMock()
        workflow = DailyWorkflow(data_provider=mock_provider)
        assert workflow.data_provider == mock_provider

    def test_get_capabilities(self):
        """Test getting workflow capabilities."""
        workflow = DailyWorkflow()
        caps = workflow.get_capabilities()

        assert "pre_market" in caps
        assert "post_market" in caps
        assert "auto" in caps

    @patch("skills.workflow.daily_workflow.DailyWorkflow._get_skill")
    def test_execute_pre_market(self, mock_get_skill):
        """Test executing pre-market workflow."""
        # Mock skill
        mock_skill = MagicMock()
        mock_skill.execute.return_value = SkillResult.ok(
            skill_name="test",
            result_type="test",
            data={},
            report_content="Test report",
        )
        mock_get_skill.return_value = mock_skill

        workflow = DailyWorkflow()
        context = SkillContext(
            user_id=1,
            request_type="daily",
            markets=["HK"],
            parameters={"phase": "pre_market"},
        )

        result = workflow.execute(context)

        assert result is not None
        # Note: Success depends on skill execution

    def test_sort_tasks_by_priority(self):
        """Test task sorting by priority."""
        workflow = DailyWorkflow()

        tasks = [
            ScheduledTask(
                task_id="low",
                name="Low Priority",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="coach",
                request_type="lesson",
                priority=3,
            ),
            ScheduledTask(
                task_id="high",
                name="High Priority",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="observer",
                request_type="pre_market",
                priority=10,
            ),
        ]

        sorted_tasks = workflow._sort_tasks_by_priority(tasks)

        assert sorted_tasks[0].task_id == "high"
        assert sorted_tasks[1].task_id == "low"

    def test_dependencies_satisfied(self):
        """Test dependency satisfaction check."""
        workflow = DailyWorkflow()

        task = ScheduledTask(
            task_id="test",
            name="Test",
            phase=WorkflowPhase.PRE_MARKET,
            skill_type="coach",
            request_type="plan",
            dependencies=["dep1", "dep2"],
        )

        # Not satisfied
        assert not workflow._dependencies_satisfied(task, {"dep1"})

        # Satisfied
        assert workflow._dependencies_satisfied(task, {"dep1", "dep2"})

        # No dependencies
        task_no_deps = ScheduledTask(
            task_id="test2",
            name="Test2",
            phase=WorkflowPhase.PRE_MARKET,
            skill_type="analyst",
            request_type="batch",
        )
        assert workflow._dependencies_satisfied(task_no_deps, set())


class TestTaskResult:
    """Tests for TaskResult dataclass."""

    def test_create_successful_result(self):
        """Test creating successful task result."""
        result = TaskResult(
            task_id="test",
            task_name="Test Task",
            success=True,
            execution_time_ms=150.5,
        )

        assert result.success
        assert result.error_message is None

    def test_create_failed_result(self):
        """Test creating failed task result."""
        result = TaskResult(
            task_id="test",
            task_name="Test Task",
            success=False,
            error_message="Something went wrong",
        )

        assert not result.success
        assert result.error_message == "Something went wrong"


class TestWorkflowResult:
    """Tests for WorkflowResult dataclass."""

    def test_success_rate(self):
        """Test success rate calculation."""
        result = WorkflowResult(
            workflow_name="test",
            phase=WorkflowPhase.PRE_MARKET,
            execution_date=date.today(),
            total_tasks=10,
            successful_tasks=8,
            failed_tasks=2,
        )

        assert result.success_rate == 80.0

    def test_success_rate_zero_tasks(self):
        """Test success rate with zero tasks."""
        result = WorkflowResult(
            workflow_name="test",
            phase=WorkflowPhase.PRE_MARKET,
            execution_date=date.today(),
            total_tasks=0,
        )

        assert result.success_rate == 0.0


# =============================================================================
# MonthlyWorkflow Tests
# =============================================================================


class TestMonthlyWorkflow:
    """Tests for MonthlyWorkflow class."""

    def test_init(self):
        """Test MonthlyWorkflow initialization."""
        workflow = MonthlyWorkflow()
        assert workflow is not None
        assert workflow.name == "monthly_workflow"

    def test_get_capabilities(self):
        """Test getting workflow capabilities."""
        workflow = MonthlyWorkflow()
        caps = workflow.get_capabilities()

        assert "monthly_review" in caps
        assert "risk_report" in caps

    @patch("skills.workflow.monthly_workflow.MonthlyWorkflow._get_skill")
    def test_execute_with_force(self, mock_get_skill):
        """Test executing monthly workflow with force flag."""
        mock_skill = MagicMock()
        mock_skill.execute.return_value = SkillResult.ok(
            skill_name="test",
            result_type="test",
            data={},
            report_content="Test report",
        )
        mock_get_skill.return_value = mock_skill

        workflow = MonthlyWorkflow()
        context = SkillContext(
            user_id=1,
            request_type="monthly",
            markets=["HK"],
            parameters={"force": True},
        )

        result = workflow.execute(context)

        assert result is not None

    def test_execute_not_month_end(self):
        """Test execution skip when not month end."""
        # Only works if today is not month end
        workflow = MonthlyWorkflow()

        # Get last trading day
        last_day = workflow.scheduler.get_last_trading_day_of_month()

        if date.today() != last_day:
            context = SkillContext(
                user_id=1,
                request_type="monthly",
                markets=["HK"],
                parameters={"force": False},
            )

            result = workflow.execute(context)

            # Should skip with success
            assert result.success
            assert result.result_type == "skip"


class TestMonthlyStats:
    """Tests for MonthlyStats dataclass."""

    def test_create_stats(self):
        """Test creating monthly stats."""
        stats = MonthlyStats(
            month=12,
            year=2025,
            total_trades=50,
            win_rate=0.65,
            portfolio_return=5.5,
        )

        assert stats.month == 12
        assert stats.win_rate == 0.65


# =============================================================================
# WorkflowEngine Tests
# =============================================================================


class TestWorkflowEngine:
    """Tests for WorkflowEngine class."""

    def test_init(self):
        """Test WorkflowEngine initialization."""
        engine = WorkflowEngine()
        assert engine is not None
        assert engine.name == "workflow_engine"

    def test_get_capabilities(self):
        """Test getting engine capabilities."""
        engine = WorkflowEngine()
        caps = engine.get_capabilities()

        assert "daily" in caps
        assert "monthly" in caps
        assert "auto" in caps

    def test_get_schedule_info(self):
        """Test getting schedule information."""
        engine = WorkflowEngine()
        info = engine.get_schedule_info("HK")

        assert "market" in info
        assert "current_phase" in info
        assert "next_phase" in info
        assert "is_trading_day" in info
        assert "is_month_end" in info

    @patch("skills.workflow.workflow_engine.WorkflowEngine._run_daily")
    def test_execute_daily(self, mock_run_daily):
        """Test executing daily workflow."""
        mock_run_daily.return_value = WorkflowEngineResult(
            workflow_type="daily",
            phase="pre_market",
            success=True,
            report_content="Daily report",
        )

        engine = WorkflowEngine()
        context = SkillContext(
            user_id=1,
            request_type="daily",
            markets=["HK"],
        )

        result = engine.execute(context)

        assert result.success
        mock_run_daily.assert_called_once()

    @patch("skills.workflow.workflow_engine.WorkflowEngine._run_monthly")
    def test_execute_monthly(self, mock_run_monthly):
        """Test executing monthly workflow."""
        mock_run_monthly.return_value = WorkflowEngineResult(
            workflow_type="monthly",
            success=True,
            report_content="Monthly report",
        )

        engine = WorkflowEngine()
        context = SkillContext(
            user_id=1,
            request_type="monthly",
            markets=["HK"],
        )

        result = engine.execute(context)

        assert result.success
        mock_run_monthly.assert_called_once()

    def test_execute_invalid_type(self):
        """Test executing with invalid workflow type."""
        engine = WorkflowEngine()
        context = SkillContext(
            user_id=1,
            request_type="invalid_type",
            markets=["HK"],
        )

        result = engine.execute(context)

        assert not result.success
        assert "Unknown workflow type" in result.error_message


class TestWorkflowEngineResult:
    """Tests for WorkflowEngineResult dataclass."""

    def test_create_result(self):
        """Test creating engine result."""
        result = WorkflowEngineResult(
            workflow_type="daily",
            phase="pre_market",
            success=True,
            report_content="Test report",
            execution_time_ms=1500.5,
        )

        assert result.workflow_type == "daily"
        assert result.success
        assert result.execution_date == date.today()


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    @patch("skills.workflow.workflow_engine.DataProvider")
    def test_run_workflow(self, mock_provider_class):
        """Test run_workflow convenience function."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        # This will execute the workflow
        report = run_workflow(user_id=1, workflow_type="daily")

        assert isinstance(report, str)

    @patch("skills.workflow.daily_workflow.DataProvider")
    def test_run_daily_workflow(self, mock_provider_class):
        """Test run_daily_workflow convenience function."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        report = run_daily_workflow(user_id=1, phase="pre_market")

        assert isinstance(report, str)

    @patch("skills.workflow.monthly_workflow.DataProvider")
    def test_run_monthly_workflow(self, mock_provider_class):
        """Test run_monthly_workflow convenience function."""
        mock_provider = MagicMock()
        mock_provider_class.return_value = mock_provider

        report = run_monthly_workflow(user_id=1, force=True)

        assert isinstance(report, str)


# =============================================================================
# Integration Tests
# =============================================================================


class TestWorkflowIntegration:
    """Integration tests for workflow components."""

    def test_scheduler_creates_valid_daily_schedule(self):
        """Test that scheduler creates valid daily schedule."""
        scheduler = WorkflowScheduler()
        schedule = scheduler.create_daily_schedule(user_id=1)

        # All tasks should have valid skill types
        valid_skill_types = {"analyst", "risk", "coach", "observer"}
        for task in schedule.tasks:
            assert task.skill_type in valid_skill_types

    def test_scheduler_creates_valid_monthly_schedule(self):
        """Test that scheduler creates valid monthly schedule."""
        scheduler = WorkflowScheduler()
        schedule = scheduler.create_monthly_schedule(user_id=1)

        # Monthly schedule should have specific tasks
        task_ids = [t.task_id for t in schedule.tasks]
        assert "monthly_risk_report" in task_ids
        assert "monthly_review" in task_ids

    def test_daily_workflow_report_generation(self):
        """Test daily workflow report generation."""
        workflow = DailyWorkflow()

        result = WorkflowResult(
            workflow_name="test",
            phase=WorkflowPhase.PRE_MARKET,
            execution_date=date.today(),
            total_tasks=3,
            successful_tasks=2,
            failed_tasks=1,
            task_results=[
                TaskResult(
                    task_id="task1",
                    task_name="Task 1",
                    success=True,
                    execution_time_ms=100,
                ),
                TaskResult(
                    task_id="task2",
                    task_name="Task 2",
                    success=True,
                    execution_time_ms=200,
                ),
                TaskResult(
                    task_id="task3",
                    task_name="Task 3",
                    success=False,
                    error_message="Error",
                    execution_time_ms=50,
                ),
            ],
        )

        report = workflow._generate_summary_report(result)

        assert "每日工作流" in report
        assert "盘前" in report
        assert "Task 1" in report
        assert "Error" in report


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_workflow_with_no_tasks(self):
        """Test workflow execution with no tasks."""
        workflow = DailyWorkflow()

        result = workflow._execute_phase(
            phase=WorkflowPhase.PRE_MARKET,
            tasks=[],
            context=SkillContext(user_id=1, request_type="daily"),
        )

        assert result.total_tasks == 0
        assert result.success_rate == 0.0

    def test_scheduler_with_invalid_market(self):
        """Test scheduler with invalid market code."""
        scheduler = WorkflowScheduler()

        # Should fall back to HK
        phase = scheduler.get_current_phase("INVALID")
        assert phase in WorkflowPhase

    def test_task_with_circular_dependency(self):
        """Test handling of circular dependencies."""
        workflow = DailyWorkflow()

        # These tasks have circular dependencies
        tasks = [
            ScheduledTask(
                task_id="a",
                name="Task A",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="analyst",
                request_type="batch",
                dependencies=["b"],
            ),
            ScheduledTask(
                task_id="b",
                name="Task B",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="risk",
                request_type="check",
                dependencies=["a"],
            ),
        ]

        # Should not hang - falls back to priority ordering
        sorted_tasks = workflow._sort_tasks_by_priority(tasks)
        assert len(sorted_tasks) == 2

    def test_workflow_result_with_all_failures(self):
        """Test workflow result when all tasks fail."""
        result = WorkflowResult(
            workflow_name="test",
            phase=WorkflowPhase.PRE_MARKET,
            execution_date=date.today(),
            total_tasks=5,
            successful_tasks=0,
            failed_tasks=5,
        )

        assert result.success_rate == 0.0

    def test_engine_get_schedule_info_all_markets(self):
        """Test getting schedule info for all markets."""
        engine = WorkflowEngine()

        for market in ["HK", "US", "A"]:
            info = engine.get_schedule_info(market)
            assert info["market"] == market
            assert info["current_phase"] is not None
