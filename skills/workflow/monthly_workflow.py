"""
Monthly Workflow for Investment Analyzer.

Orchestrates monthly analysis and review tasks.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

from skills.shared import DataProvider, SkillContext, SkillResult
from skills.shared.base import BaseSkill

from .daily_workflow import TaskResult, WorkflowResult
from .scheduler import ScheduledTask, WorkflowPhase, WorkflowScheduler

logger = logging.getLogger(__name__)


@dataclass
class MonthlyStats:
    """Monthly trading statistics."""

    month: int
    year: int
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    total_pnl: float = 0.0
    win_rate: float = 0.0
    best_trade: Optional[str] = None
    worst_trade: Optional[str] = None
    portfolio_return: float = 0.0


class MonthlyWorkflow(BaseSkill):
    """
    Monthly workflow orchestrator.

    Coordinates monthly analysis and review tasks:
    - Risk report
    - Portfolio assessment
    - Trading review
    - Compound interest education
    """

    def __init__(self, data_provider: DataProvider = None):
        """
        Initialize monthly workflow.

        Args:
            data_provider: Data provider instance
        """
        super().__init__(
            name="monthly_workflow",
            description="月度工作流 - 协调月度分析与复盘任务",
        )
        self.data_provider = data_provider or DataProvider()
        self.scheduler = WorkflowScheduler()
        self._skills_cache = {}

    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute monthly workflow.

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
            markets = context.markets if context.markets else ["HK"]

            # Check if should run monthly workflow
            force = context.get_param("force", False)
            if not force:
                last_trading_day = self.scheduler.get_last_trading_day_of_month(
                    market=markets[0]
                )
                if date.today() != last_trading_day:
                    logger.info(
                        f"Not last trading day of month. "
                        f"Last trading day: {last_trading_day}"
                    )
                    return SkillResult(
                        success=True,
                        skill_name=self.name,
                        result_type="skip",
                        data={"reason": "not_last_trading_day", "last_day": last_trading_day},
                        report_content=f"月度工作流跳过: 非月末最后交易日 (最后交易日: {last_trading_day})",
                        execution_time_ms=0,
                    )

            # Create monthly schedule
            schedule = self.scheduler.create_monthly_schedule(
                user_id=context.user_id,
                markets=markets,
            )

            # Execute all monthly tasks
            result = self._execute_monthly_tasks(
                tasks=schedule.tasks,
                context=context,
            )

            elapsed = (datetime.now() - start_time).total_seconds() * 1000

            return SkillResult(
                success=result.success_rate >= 50,
                skill_name=self.name,
                result_type="monthly",
                data=result,
                report_content=result.summary_report,
                execution_time_ms=elapsed,
                next_actions=self._get_next_actions(result),
            )

        except Exception as e:
            logger.exception("Monthly workflow execution failed")
            return SkillResult.error(self.name, str(e))

    def get_capabilities(self) -> list[str]:
        """Get workflow capabilities."""
        return [
            "monthly_review",  # Full monthly review
            "risk_report",  # Just risk report
            "trading_stats",  # Just trading statistics
        ]

    def _execute_monthly_tasks(
        self,
        tasks: list[ScheduledTask],
        context: SkillContext,
    ) -> WorkflowResult:
        """
        Execute all monthly tasks.

        Args:
            tasks: Tasks to execute
            context: Execution context

        Returns:
            WorkflowResult
        """
        result = WorkflowResult(
            workflow_name="monthly_workflow",
            phase=WorkflowPhase.POST_MARKET,
            execution_date=date.today(),
            total_tasks=len(tasks),
        )

        # Sort by priority
        sorted_tasks = sorted(tasks, key=lambda t: -t.priority)

        start_time = datetime.now()
        completed_task_ids = set()

        for task in sorted_tasks:
            # Check dependencies
            if not all(d in completed_task_ids for d in task.dependencies):
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
        result.summary_report = self._generate_monthly_report(result, context)

        return result

    def _execute_task(
        self,
        task: ScheduledTask,
        context: SkillContext,
    ) -> TaskResult:
        """Execute a single scheduled task."""
        start_time = datetime.now()

        try:
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

    def _generate_monthly_report(
        self,
        result: WorkflowResult,
        context: SkillContext,
    ) -> str:
        """Generate monthly workflow summary report."""
        today = date.today()
        month_name = today.strftime("%Y年%m月")

        lines = []
        lines.append(f"# 月度分析报告 - {month_name}")
        lines.append("")
        lines.append(f"生成日期: {today}")
        lines.append(f"执行时间: {result.total_time_ms:.0f}ms")
        lines.append("")

        # Summary
        success_icon = "✅" if result.success_rate >= 80 else "⚠️"
        lines.append(f"## 执行摘要 {success_icon}")
        lines.append("")
        lines.append(f"- 总任务: {result.total_tasks}")
        lines.append(f"- 成功: {result.successful_tasks}")
        lines.append(f"- 失败: {result.failed_tasks}")
        lines.append(f"- 成功率: {result.success_rate:.0f}%")
        lines.append("")

        # Task reports
        lines.append("## 分析报告")
        lines.append("")

        for task_result in result.task_results:
            icon = "✅" if task_result.success else "❌"
            lines.append(f"### {icon} {task_result.task_name}")

            if task_result.success and task_result.skill_result:
                if task_result.skill_result.report_content:
                    lines.append("")
                    lines.append(task_result.skill_result.report_content)
            elif task_result.error_message:
                lines.append(f"错误: {task_result.error_message}")
            lines.append("")

        # Monthly summary section
        lines.append("---")
        lines.append("")
        lines.append("## 月度总结")
        lines.append("")
        lines.append("### 本月回顾")
        lines.append("")
        lines.append("- 请结合上述分析报告，回顾本月交易表现")
        lines.append("- 总结成功经验和失败教训")
        lines.append("- 制定下月改进计划")
        lines.append("")

        lines.append("### 下月计划")
        lines.append("")
        lines.append("- [ ] 复盘本月交易记录")
        lines.append("- [ ] 更新风控参数")
        lines.append("- [ ] 调整持仓结构")
        lines.append("- [ ] 设定下月目标")
        lines.append("")

        return "\n".join(lines)

    def _get_next_actions(self, result: WorkflowResult) -> list[str]:
        """Get suggested next actions."""
        actions = []

        if result.failed_tasks > 0:
            actions.append(f"检查 {result.failed_tasks} 个失败的分析任务")

        actions.extend([
            "复盘本月交易表现",
            "更新下月交易计划",
            "检查风控参数设置",
        ])

        return actions


def run_monthly_workflow(
    user_id: int,
    markets: list[str] = None,
    force: bool = False,
) -> str:
    """
    Convenience function to run monthly workflow.

    Args:
        user_id: User ID
        markets: List of markets
        force: Force run even if not month end

    Returns:
        Markdown report
    """
    if markets is None:
        markets = ["HK"]

    provider = DataProvider()
    workflow = MonthlyWorkflow(data_provider=provider)

    context = SkillContext(
        user_id=user_id,
        request_type="monthly",
        markets=markets,
        parameters={"force": force},
    )

    result = workflow.execute(context)

    if result.success:
        return result.report_content
    else:
        return f"Error: {result.error_message}"
