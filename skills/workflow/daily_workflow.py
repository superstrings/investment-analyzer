"""
Daily Workflow for Investment Analyzer.

Orchestrates daily analysis tasks across all skills.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

from skills.shared import DataProvider, SkillContext, SkillResult
from skills.shared.base import BaseSkill

from .scheduler import ScheduledTask, WorkflowPhase, WorkflowScheduler

logger = logging.getLogger(__name__)


@dataclass
class TaskResult:
    """Result from executing a scheduled task."""

    task_id: str
    task_name: str
    success: bool
    skill_result: Optional[SkillResult] = None
    error_message: Optional[str] = None
    execution_time_ms: float = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class WorkflowResult:
    """Result from executing a workflow."""

    workflow_name: str
    phase: WorkflowPhase
    execution_date: date
    task_results: list[TaskResult] = field(default_factory=list)
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    total_time_ms: float = 0
    summary_report: str = ""

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks * 100


class DailyWorkflow(BaseSkill):
    """
    Daily workflow orchestrator.

    Coordinates daily analysis tasks across all skills:
    - Pre-market: observation, analysis, risk check, plan generation
    - Post-market: summary, risk report, trading review
    """

    def __init__(self, data_provider: DataProvider = None):
        """
        Initialize daily workflow.

        Args:
            data_provider: Data provider instance
        """
        super().__init__(
            name="daily_workflow",
            description="每日工作流 - 协调盘前盘后分析任务",
        )
        self.data_provider = data_provider or DataProvider()
        self.scheduler = WorkflowScheduler()
        self._skills_cache = {}

    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute daily workflow.

        Args:
            context: Execution context with phase and markets

        Returns:
            SkillResult with workflow results
        """
        start_time = datetime.now()

        # Validate context
        is_valid, error = self.validate_context(context)
        if not is_valid:
            return SkillResult.error(self.name, error)

        try:
            # Get workflow phase
            phase_str = context.get_param("phase", "auto")
            markets = context.markets if context.markets else ["HK"]

            if phase_str == "auto":
                # Auto-detect based on market time
                phase = self.scheduler.get_current_phase(markets[0])
            else:
                phase = WorkflowPhase(phase_str)

            # Create schedule
            schedule = self.scheduler.create_daily_schedule(
                user_id=context.user_id,
                markets=markets,
            )

            # Filter tasks for current phase
            phase_tasks = [t for t in schedule.tasks if t.phase == phase and t.enabled]

            # Execute tasks
            result = self._execute_phase(
                phase=phase,
                tasks=phase_tasks,
                context=context,
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return SkillResult(
                success=result.success_rate >= 50,  # At least 50% success
                skill_name=self.name,
                result_type=phase.value,
                data=result,
                report_content=result.summary_report,
                execution_time_ms=elapsed,
                next_actions=self._get_next_actions(result),
            )

        except Exception as e:
            logger.exception("Daily workflow execution failed")
            return SkillResult.error(self.name, str(e))

    def get_capabilities(self) -> list[str]:
        """Get workflow capabilities."""
        return [
            "pre_market",
            "post_market",
            "full",  # Run all phases
            "auto",  # Auto-detect phase
        ]

    def _execute_phase(
        self,
        phase: WorkflowPhase,
        tasks: list[ScheduledTask],
        context: SkillContext,
    ) -> WorkflowResult:
        """
        Execute all tasks for a workflow phase.

        Args:
            phase: Workflow phase
            tasks: Tasks to execute
            context: Execution context

        Returns:
            WorkflowResult
        """
        result = WorkflowResult(
            workflow_name=f"daily_{phase.value}",
            phase=phase,
            execution_date=date.today(),
            total_tasks=len(tasks),
        )

        # Sort by priority (higher first) and dependencies
        sorted_tasks = self._sort_tasks_by_priority(tasks)

        completed_task_ids = set()
        start_time = datetime.now()

        for task in sorted_tasks:
            # Check dependencies
            if not self._dependencies_satisfied(task, completed_task_ids):
                logger.warning(
                    f"Skipping task {task.task_id} - dependencies not satisfied"
                )
                result.failed_tasks += 1
                result.task_results.append(TaskResult(
                    task_id=task.task_id,
                    task_name=task.name,
                    success=False,
                    error_message="Dependencies not satisfied",
                ))
                continue

            # Execute task
            task_result = self._execute_task(task, context)
            result.task_results.append(task_result)

            if task_result.success:
                result.successful_tasks += 1
                completed_task_ids.add(task.task_id)
            else:
                result.failed_tasks += 1

        result.total_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        result.summary_report = self._generate_summary_report(result)

        return result

    def _execute_task(
        self,
        task: ScheduledTask,
        context: SkillContext,
    ) -> TaskResult:
        """
        Execute a single scheduled task.

        Args:
            task: Task to execute
            context: Execution context

        Returns:
            TaskResult
        """
        start_time = datetime.now()

        try:
            # Get or create skill instance
            skill = self._get_skill(task.skill_type)

            if skill is None:
                return TaskResult(
                    task_id=task.task_id,
                    task_name=task.name,
                    success=False,
                    error_message=f"Unknown skill type: {task.skill_type}",
                    started_at=start_time,
                    completed_at=datetime.now(),
                )

            # Create task-specific context
            task_context = SkillContext(
                user_id=context.user_id,
                request_type=task.request_type,
                markets=task.markets,
                parameters=context.parameters.copy() if context.parameters else {},
            )

            # Execute skill
            skill_result = skill.execute(task_context)

            completed_at = datetime.now()
            elapsed = (completed_at - start_time).total_seconds() * 1000

            return TaskResult(
                task_id=task.task_id,
                task_name=task.name,
                success=skill_result.success,
                skill_result=skill_result,
                error_message=skill_result.error_message if not skill_result.success else None,
                execution_time_ms=elapsed,
                started_at=start_time,
                completed_at=completed_at,
            )

        except Exception as e:
            logger.exception(f"Task {task.task_id} execution failed")
            return TaskResult(
                task_id=task.task_id,
                task_name=task.name,
                success=False,
                error_message=str(e),
                started_at=start_time,
                completed_at=datetime.now(),
            )

    def _get_skill(self, skill_type: str):
        """Get or create a skill instance."""
        if skill_type in self._skills_cache:
            return self._skills_cache[skill_type]

        skill = None

        if skill_type == "analyst":
            from skills.analyst import StockAnalyzer
            skill = StockAnalyzer(data_provider=self.data_provider)
        elif skill_type == "risk":
            from skills.risk_controller import RiskController
            skill = RiskController(data_provider=self.data_provider)
        elif skill_type == "coach":
            from skills.trading_coach import TradingCoach
            skill = TradingCoach(data_provider=self.data_provider)
        elif skill_type == "observer":
            from skills.market_observer import MarketObserver
            skill = MarketObserver(data_provider=self.data_provider)

        if skill:
            self._skills_cache[skill_type] = skill

        return skill

    def _sort_tasks_by_priority(
        self,
        tasks: list[ScheduledTask],
    ) -> list[ScheduledTask]:
        """Sort tasks by priority (higher first) considering dependencies."""
        # Simple topological sort with priority
        sorted_tasks = []
        remaining = list(tasks)
        completed_ids = set()

        while remaining:
            # Find tasks with satisfied dependencies
            ready = [
                t for t in remaining
                if all(d in completed_ids for d in t.dependencies)
            ]

            if not ready:
                # No ready tasks but still have remaining - circular dependency or missing dep
                # Just add remaining in priority order
                ready = remaining

            # Sort ready tasks by priority
            ready.sort(key=lambda t: -t.priority)

            # Take the highest priority ready task
            task = ready[0]
            sorted_tasks.append(task)
            completed_ids.add(task.task_id)
            remaining.remove(task)

        return sorted_tasks

    def _dependencies_satisfied(
        self,
        task: ScheduledTask,
        completed_ids: set[str],
    ) -> bool:
        """Check if all task dependencies are satisfied."""
        return all(dep in completed_ids for dep in task.dependencies)

    def _generate_summary_report(self, result: WorkflowResult) -> str:
        """Generate workflow summary report."""
        phase_names = {
            WorkflowPhase.PRE_MARKET: "盘前",
            WorkflowPhase.MARKET_OPEN: "盘中",
            WorkflowPhase.POST_MARKET: "盘后",
            WorkflowPhase.CLOSED: "休市",
        }
        phase_name = phase_names.get(result.phase, result.phase.value)

        lines = []
        lines.append(f"# 每日工作流 - {phase_name}")
        lines.append("")
        lines.append(f"执行日期: {result.execution_date}")
        lines.append(f"执行时间: {result.total_time_ms:.0f}ms")
        lines.append("")

        # Summary stats
        success_icon = "✅" if result.success_rate >= 80 else "⚠️" if result.success_rate >= 50 else "❌"
        lines.append(f"## 执行结果 {success_icon}")
        lines.append("")
        lines.append(f"- 总任务数: {result.total_tasks}")
        lines.append(f"- 成功: {result.successful_tasks}")
        lines.append(f"- 失败: {result.failed_tasks}")
        lines.append(f"- 成功率: {result.success_rate:.0f}%")
        lines.append("")

        # Task details
        lines.append("## 任务详情")
        lines.append("")

        for task_result in result.task_results:
            icon = "✅" if task_result.success else "❌"
            lines.append(f"### {icon} {task_result.task_name}")
            lines.append(f"- 任务ID: {task_result.task_id}")
            lines.append(f"- 耗时: {task_result.execution_time_ms:.0f}ms")
            if not task_result.success and task_result.error_message:
                lines.append(f"- 错误: {task_result.error_message}")
            lines.append("")

            # Include skill report if available
            if task_result.skill_result and task_result.skill_result.report_content:
                lines.append("<details>")
                lines.append("<summary>详细报告</summary>")
                lines.append("")
                lines.append(task_result.skill_result.report_content)
                lines.append("</details>")
                lines.append("")

        return "\n".join(lines)

    def _get_next_actions(self, result: WorkflowResult) -> list[str]:
        """Get suggested next actions."""
        actions = []

        # Check for failed tasks
        failed_tasks = [t for t in result.task_results if not t.success]
        if failed_tasks:
            actions.append(f"检查 {len(failed_tasks)} 个失败任务")

        # Suggest next phase
        if result.phase == WorkflowPhase.PRE_MARKET:
            actions.append("等待市场开盘")
        elif result.phase == WorkflowPhase.POST_MARKET:
            actions.append("复盘今日操作")

        if not actions:
            actions.append("按计划执行")

        return actions


def run_daily_workflow(
    user_id: int,
    phase: str = "auto",
    markets: list[str] = None,
) -> str:
    """
    Convenience function to run daily workflow.

    Args:
        user_id: User ID
        phase: Workflow phase (auto, pre_market, post_market, full)
        markets: List of markets

    Returns:
        Markdown report
    """
    if markets is None:
        markets = ["HK"]

    provider = DataProvider()
    workflow = DailyWorkflow(data_provider=provider)

    context = SkillContext(
        user_id=user_id,
        request_type="daily",
        markets=markets,
        parameters={"phase": phase},
    )

    result = workflow.execute(context)

    if result.success:
        return result.report_content
    else:
        return f"Error: {result.error_message}"
