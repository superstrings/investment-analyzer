"""
Workflow package for Investment Analyzer.

Provides automated workflow orchestration for daily and monthly analysis.
"""

from .daily_workflow import (
    DailyWorkflow,
    TaskResult,
    WorkflowResult,
    run_daily_workflow,
)
from .monthly_workflow import (
    MonthlyStats,
    MonthlyWorkflow,
    run_monthly_workflow,
)
from .scheduler import (
    ScheduledTask,
    WorkflowPhase,
    WorkflowSchedule,
    WorkflowScheduler,
)
from .workflow_engine import (
    WorkflowEngine,
    WorkflowEngineResult,
    run_workflow,
)

__all__ = [
    # Scheduler
    "WorkflowScheduler",
    "WorkflowPhase",
    "WorkflowSchedule",
    "ScheduledTask",
    # Daily workflow
    "DailyWorkflow",
    "TaskResult",
    "WorkflowResult",
    "run_daily_workflow",
    # Monthly workflow
    "MonthlyWorkflow",
    "MonthlyStats",
    "run_monthly_workflow",
    # Engine
    "WorkflowEngine",
    "WorkflowEngineResult",
    "run_workflow",
]
