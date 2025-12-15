"""
Workflow Scheduler for Investment Analyzer.

Manages timing and scheduling of workflow phases.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from enum import Enum
from typing import Optional

from skills.shared.base import MarketSchedule, MarketState

logger = logging.getLogger(__name__)


class WorkflowPhase(Enum):
    """Workflow phases for different times of day."""

    PRE_MARKET = "pre_market"  # Before market opens
    MARKET_OPEN = "market_open"  # Market is open
    POST_MARKET = "post_market"  # After market closes
    CLOSED = "closed"  # Market is closed (weekend/holiday)


@dataclass
class ScheduledTask:
    """A scheduled workflow task."""

    task_id: str
    name: str
    phase: WorkflowPhase
    skill_type: str  # analyst, risk, coach, observer
    request_type: str  # The specific request type for the skill
    priority: int = 5  # 1-10, higher = more urgent
    markets: list[str] = field(default_factory=lambda: ["HK"])
    dependencies: list[str] = field(default_factory=list)  # Task IDs that must complete first
    enabled: bool = True


@dataclass
class WorkflowSchedule:
    """Schedule for a workflow."""

    name: str
    tasks: list[ScheduledTask]
    created_at: datetime = field(default_factory=datetime.now)


# Default schedule configurations
DEFAULT_HK_SCHEDULE = {
    WorkflowPhase.PRE_MARKET: time(8, 30),
    WorkflowPhase.MARKET_OPEN: time(9, 30),
    WorkflowPhase.POST_MARKET: time(16, 30),
}

DEFAULT_US_SCHEDULE = {
    WorkflowPhase.PRE_MARKET: time(20, 0),
    WorkflowPhase.MARKET_OPEN: time(21, 30),
    WorkflowPhase.POST_MARKET: time(5, 0),  # Next day
}

DEFAULT_A_SCHEDULE = {
    WorkflowPhase.PRE_MARKET: time(9, 0),
    WorkflowPhase.MARKET_OPEN: time(9, 30),
    WorkflowPhase.POST_MARKET: time(15, 30),
}


class WorkflowScheduler:
    """
    Workflow scheduler.

    Manages the timing and scheduling of workflow phases and tasks.
    """

    def __init__(self):
        """Initialize workflow scheduler."""
        self.market_schedule = MarketSchedule()
        self.schedules = {
            "HK": DEFAULT_HK_SCHEDULE,
            "US": DEFAULT_US_SCHEDULE,
            "A": DEFAULT_A_SCHEDULE,
        }

    def get_current_phase(self, market: str = "HK") -> WorkflowPhase:
        """
        Get the current workflow phase for a market.

        Args:
            market: Market code (HK, US, A)

        Returns:
            Current WorkflowPhase
        """
        market_state = self.market_schedule.get_market_state(market)

        phase_map = {
            MarketState.PRE_MARKET: WorkflowPhase.PRE_MARKET,
            MarketState.OPEN: WorkflowPhase.MARKET_OPEN,
            MarketState.POST_MARKET: WorkflowPhase.POST_MARKET,
            MarketState.CLOSED: WorkflowPhase.CLOSED,
        }

        return phase_map.get(market_state, WorkflowPhase.CLOSED)

    def get_phase_start_time(
        self,
        phase: WorkflowPhase,
        market: str = "HK",
    ) -> Optional[time]:
        """
        Get the start time for a workflow phase.

        Args:
            phase: Workflow phase
            market: Market code

        Returns:
            Start time or None
        """
        schedule = self.schedules.get(market, DEFAULT_HK_SCHEDULE)
        return schedule.get(phase)

    def should_run_phase(
        self,
        phase: WorkflowPhase,
        market: str = "HK",
        tolerance_minutes: int = 30,
    ) -> bool:
        """
        Check if a workflow phase should run now.

        Args:
            phase: Workflow phase to check
            market: Market code
            tolerance_minutes: Time tolerance in minutes

        Returns:
            True if phase should run
        """
        current_phase = self.get_current_phase(market)
        return current_phase == phase

    def get_next_phase_time(
        self,
        market: str = "HK",
    ) -> tuple[WorkflowPhase, Optional[datetime]]:
        """
        Get the next workflow phase and its start time.

        Args:
            market: Market code

        Returns:
            Tuple of (next phase, datetime) or (current phase, None)
        """
        current_phase = self.get_current_phase(market)
        now = datetime.now()

        # Determine next phase
        phase_order = [
            WorkflowPhase.PRE_MARKET,
            WorkflowPhase.MARKET_OPEN,
            WorkflowPhase.POST_MARKET,
            WorkflowPhase.CLOSED,
        ]

        try:
            current_idx = phase_order.index(current_phase)
            next_idx = (current_idx + 1) % len(phase_order)
            next_phase = phase_order[next_idx]
        except ValueError:
            return current_phase, None

        # Get next phase start time
        next_time = self.get_phase_start_time(next_phase, market)
        if next_time is None:
            return next_phase, None

        # Build datetime for next phase
        next_datetime = datetime.combine(now.date(), next_time)

        # If time has passed, move to next day
        if next_datetime <= now:
            next_datetime += timedelta(days=1)

        return next_phase, next_datetime

    def is_trading_day(self, check_date: date = None, market: str = "HK") -> bool:
        """
        Check if a date is a trading day.

        Args:
            check_date: Date to check (default: today)
            market: Market code

        Returns:
            True if trading day
        """
        if check_date is None:
            check_date = date.today()

        # Basic weekday check
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # TODO: Add holiday calendar integration
        return True

    def get_last_trading_day_of_month(
        self,
        year: int = None,
        month: int = None,
        market: str = "HK",
    ) -> date:
        """
        Get the last trading day of a month.

        Args:
            year: Year (default: current)
            month: Month (default: current)
            market: Market code

        Returns:
            Last trading day of month
        """
        if year is None:
            year = date.today().year
        if month is None:
            month = date.today().month

        # Get last day of month
        if month == 12:
            next_month = date(year + 1, 1, 1)
        else:
            next_month = date(year, month + 1, 1)

        last_day = next_month - timedelta(days=1)

        # Find last trading day
        while not self.is_trading_day(last_day, market):
            last_day -= timedelta(days=1)

        return last_day

    def create_daily_schedule(
        self,
        user_id: int,
        markets: list[str] = None,
    ) -> WorkflowSchedule:
        """
        Create a daily workflow schedule.

        Args:
            user_id: User ID
            markets: Markets to include

        Returns:
            WorkflowSchedule for daily tasks
        """
        if markets is None:
            markets = ["HK"]

        tasks = []

        # Pre-market tasks
        tasks.extend([
            ScheduledTask(
                task_id="pre_market_observation",
                name="盘前市场观察",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="observer",
                request_type="pre_market",
                priority=10,
                markets=markets,
            ),
            ScheduledTask(
                task_id="pre_market_analysis",
                name="持仓技术分析更新",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="analyst",
                request_type="batch",
                priority=8,
                markets=markets,
                dependencies=["pre_market_observation"],
            ),
            ScheduledTask(
                task_id="pre_market_risk",
                name="风险状态检查",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="risk",
                request_type="check",
                priority=9,
                markets=markets,
                dependencies=["pre_market_observation"],
            ),
            ScheduledTask(
                task_id="daily_plan",
                name="今日交易计划",
                phase=WorkflowPhase.PRE_MARKET,
                skill_type="coach",
                request_type="daily_plan",
                priority=7,
                markets=markets,
                dependencies=["pre_market_analysis", "pre_market_risk"],
            ),
        ])

        # Post-market tasks
        tasks.extend([
            ScheduledTask(
                task_id="post_market_observation",
                name="盘后市场总结",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="observer",
                request_type="post_market",
                priority=10,
                markets=markets,
            ),
            ScheduledTask(
                task_id="post_market_risk",
                name="风险报告生成",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="risk",
                request_type="report",
                priority=8,
                markets=markets,
                dependencies=["post_market_observation"],
            ),
            ScheduledTask(
                task_id="daily_review",
                name="今日交易复盘",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="coach",
                request_type="psychology_check",
                priority=7,
                markets=markets,
                dependencies=["post_market_observation", "post_market_risk"],
            ),
        ])

        return WorkflowSchedule(
            name=f"daily_workflow_{date.today()}",
            tasks=tasks,
        )

    def create_monthly_schedule(
        self,
        user_id: int,
        markets: list[str] = None,
    ) -> WorkflowSchedule:
        """
        Create a monthly workflow schedule.

        Args:
            user_id: User ID
            markets: Markets to include

        Returns:
            WorkflowSchedule for monthly tasks
        """
        if markets is None:
            markets = ["HK"]

        tasks = [
            ScheduledTask(
                task_id="monthly_risk_report",
                name="月度风险报告",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="risk",
                request_type="monthly_report",
                priority=10,
                markets=markets,
            ),
            ScheduledTask(
                task_id="monthly_analysis",
                name="持仓月度评估",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="analyst",
                request_type="monthly_batch",
                priority=9,
                markets=markets,
            ),
            ScheduledTask(
                task_id="monthly_review",
                name="月度交易复盘",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="coach",
                request_type="full_coaching",
                priority=8,
                markets=markets,
                dependencies=["monthly_risk_report", "monthly_analysis"],
            ),
            ScheduledTask(
                task_id="compound_lesson",
                name="复利教育",
                phase=WorkflowPhase.POST_MARKET,
                skill_type="coach",
                request_type="compound_lesson",
                priority=5,
                markets=markets,
            ),
        ]

        return WorkflowSchedule(
            name=f"monthly_workflow_{date.today()}",
            tasks=tasks,
        )
