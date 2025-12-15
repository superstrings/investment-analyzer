"""
Workflow Engine for Investment Analyzer.

Main entry point for workflow orchestration.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from skills.shared import DataProvider, SkillContext, SkillResult
from skills.shared.base import BaseSkill

from .daily_workflow import DailyWorkflow, run_daily_workflow
from .monthly_workflow import MonthlyWorkflow, run_monthly_workflow
from .scheduler import WorkflowPhase, WorkflowScheduler

logger = logging.getLogger(__name__)


@dataclass
class WorkflowEngineResult:
    """Result from workflow engine execution."""

    workflow_type: str  # daily, monthly, custom
    phase: Optional[str] = None
    execution_date: date = field(default_factory=date.today)
    success: bool = False
    report_content: str = ""
    execution_time_ms: float = 0
    error_message: Optional[str] = None


class WorkflowEngine(BaseSkill):
    """
    Workflow Engine.

    Central orchestrator for all workflow types:
    - Daily workflows (pre-market, post-market)
    - Monthly workflows (month-end review)
    - Custom workflows (user-defined)
    """

    def __init__(self, data_provider: DataProvider = None):
        """
        Initialize workflow engine.

        Args:
            data_provider: Data provider instance
        """
        super().__init__(
            name="workflow_engine",
            description="工作流引擎 - 协调每日/月度自动化分析任务",
        )
        self.data_provider = data_provider or DataProvider()
        self.scheduler = WorkflowScheduler()
        self.daily_workflow = DailyWorkflow(data_provider=self.data_provider)
        self.monthly_workflow = MonthlyWorkflow(data_provider=self.data_provider)

    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute workflow based on context.

        Args:
            context: Execution context

        Returns:
            SkillResult with workflow results
        """
        start_time = datetime.now()

        # Validate context
        is_valid, error = self.validate_context(context)
        if not is_valid:
            return SkillResult.error(self.name, error)

        try:
            workflow_type = context.request_type or "auto"

            if workflow_type == "daily":
                result = self._run_daily(context)
            elif workflow_type == "monthly":
                result = self._run_monthly(context)
            elif workflow_type == "auto":
                result = self._run_auto(context)
            else:
                return SkillResult.error(
                    self.name,
                    f"Unknown workflow type: {workflow_type}",
                )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return SkillResult(
                success=result.success,
                skill_name=self.name,
                result_type=result.workflow_type,
                data=result,
                report_content=result.report_content,
                execution_time_ms=elapsed,
                next_actions=self._get_next_actions(result),
            )

        except Exception as e:
            logger.exception("Workflow engine execution failed")
            return SkillResult.error(self.name, str(e))

    def get_capabilities(self) -> list[str]:
        """Get workflow capabilities."""
        return [
            "daily",  # Daily workflow
            "monthly",  # Monthly workflow
            "auto",  # Auto-detect based on time
        ]

    def _run_daily(self, context: SkillContext) -> WorkflowEngineResult:
        """Run daily workflow."""
        result = self.daily_workflow.execute(context)

        phase = context.get_param("phase", "auto")

        return WorkflowEngineResult(
            workflow_type="daily",
            phase=phase,
            execution_date=date.today(),
            success=result.success,
            report_content=result.report_content,
            execution_time_ms=result.execution_time_ms,
            error_message=result.error_message,
        )

    def _run_monthly(self, context: SkillContext) -> WorkflowEngineResult:
        """Run monthly workflow."""
        result = self.monthly_workflow.execute(context)

        return WorkflowEngineResult(
            workflow_type="monthly",
            execution_date=date.today(),
            success=result.success,
            report_content=result.report_content,
            execution_time_ms=result.execution_time_ms,
            error_message=result.error_message,
        )

    def _run_auto(self, context: SkillContext) -> WorkflowEngineResult:
        """Auto-detect and run appropriate workflow."""
        markets = context.markets if context.markets else ["HK"]
        market = markets[0]

        # Check if it's month end
        last_trading_day = self.scheduler.get_last_trading_day_of_month(market=market)
        if date.today() == last_trading_day:
            # Run both monthly and daily post-market
            monthly_result = self._run_monthly(context)

            # If monthly succeeded, append daily
            if monthly_result.success:
                daily_context = SkillContext(
                    user_id=context.user_id,
                    request_type="daily",
                    markets=markets,
                    parameters={"phase": "post_market"},
                )
                daily_result = self._run_daily(daily_context)

                # Combine reports
                combined_report = monthly_result.report_content
                combined_report += "\n\n---\n\n"
                combined_report += daily_result.report_content

                return WorkflowEngineResult(
                    workflow_type="monthly+daily",
                    execution_date=date.today(),
                    success=monthly_result.success and daily_result.success,
                    report_content=combined_report,
                    execution_time_ms=monthly_result.execution_time_ms + daily_result.execution_time_ms,
                )

            return monthly_result

        # Regular daily workflow
        # Detect current phase
        current_phase = self.scheduler.get_current_phase(market)

        phase_context = SkillContext(
            user_id=context.user_id,
            request_type="daily",
            markets=markets,
            parameters={"phase": current_phase.value},
        )

        return self._run_daily(phase_context)

    def _get_next_actions(self, result: WorkflowEngineResult) -> list[str]:
        """Get suggested next actions."""
        actions = []

        if not result.success:
            actions.append("检查工作流执行错误")
        elif result.workflow_type == "daily":
            if result.phase == "pre_market":
                actions.append("查看今日交易计划")
                actions.append("确认风险提示")
            elif result.phase == "post_market":
                actions.append("复盘今日交易")
                actions.append("更新明日计划")
        elif result.workflow_type == "monthly":
            actions.append("复盘本月表现")
            actions.append("制定下月计划")

        if not actions:
            actions.append("继续执行交易计划")

        return actions

    def get_schedule_info(self, market: str = "HK") -> dict:
        """
        Get current schedule information.

        Args:
            market: Market code

        Returns:
            Schedule info dict
        """
        current_phase = self.scheduler.get_current_phase(market)
        next_phase, next_time = self.scheduler.get_next_phase_time(market)
        is_trading_day = self.scheduler.is_trading_day(market=market)
        is_month_end = date.today() == self.scheduler.get_last_trading_day_of_month(
            market=market
        )

        return {
            "market": market,
            "current_phase": current_phase.value,
            "next_phase": next_phase.value,
            "next_phase_time": next_time.isoformat() if next_time else None,
            "is_trading_day": is_trading_day,
            "is_month_end": is_month_end,
        }


def run_workflow(
    user_id: int,
    workflow_type: str = "auto",
    markets: list[str] = None,
    **params,
) -> str:
    """
    Convenience function to run workflow.

    Args:
        user_id: User ID
        workflow_type: Type of workflow (daily, monthly, auto)
        markets: List of markets
        **params: Additional parameters

    Returns:
        Markdown report
    """
    if markets is None:
        markets = ["HK"]

    provider = DataProvider()
    engine = WorkflowEngine(data_provider=provider)

    context = SkillContext(
        user_id=user_id,
        request_type=workflow_type,
        markets=markets,
        parameters=params,
    )

    result = engine.execute(context)

    if result.success:
        return result.report_content
    else:
        return f"Error: {result.error_message}"
