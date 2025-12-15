"""
Base classes for Skills framework.

Provides abstract base class and data structures for all skills.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime, time
from enum import Enum
from typing import Any, Optional


class MarketState(Enum):
    """Market session state."""

    PRE_MARKET = "pre_market"  # Before market open
    OPEN = "open"  # Market is open
    CLOSED = "closed"  # Market is closed
    POST_MARKET = "post_market"  # After market close


class SignalType(Enum):
    """Trading signal type."""

    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    WATCH = "watch"  # Add to watchlist


class RiskLevel(Enum):
    """Risk alert level."""

    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"  # Same day action
    MEDIUM = "medium"  # This week action
    LOW = "low"  # Monitor


@dataclass
class SkillContext:
    """
    Context passed to skill execution.

    Contains all information needed for a skill to execute.
    """

    user_id: int
    request_type: str  # e.g., "single_stock", "batch", "portfolio"
    parameters: dict[str, Any] = field(default_factory=dict)
    market_state: MarketState = MarketState.CLOSED
    execution_time: datetime = field(default_factory=datetime.now)

    # Optional filters
    markets: list[str] = field(default_factory=lambda: ["HK", "US", "A"])
    codes: list[str] = field(default_factory=list)

    def get_param(self, key: str, default: Any = None) -> Any:
        """Get parameter with default value."""
        return self.parameters.get(key, default)


@dataclass
class SkillResult:
    """
    Result returned from skill execution.

    Contains success status, data, and optional report.
    """

    success: bool
    skill_name: str
    result_type: str  # e.g., "analysis", "risk_report", "trading_plan"
    data: Any = None
    error_message: str = ""
    execution_time_ms: float = 0.0

    # Report output
    report_content: str = ""
    report_format: str = "markdown"  # markdown, json, html

    # Suggested next actions
    next_actions: list[str] = field(default_factory=list)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(
        cls,
        skill_name: str,
        result_type: str,
        data: Any,
        report_content: str = "",
        next_actions: list[str] = None,
    ) -> "SkillResult":
        """Create successful result."""
        return cls(
            success=True,
            skill_name=skill_name,
            result_type=result_type,
            data=data,
            report_content=report_content,
            next_actions=next_actions or [],
        )

    @classmethod
    def error(cls, skill_name: str, message: str) -> "SkillResult":
        """Create error result."""
        return cls(
            success=False,
            skill_name=skill_name,
            result_type="error",
            error_message=message,
        )


class BaseSkill(ABC):
    """
    Abstract base class for all skills.

    All skills must inherit from this class and implement
    the required abstract methods.
    """

    def __init__(self, name: str, description: str):
        """
        Initialize skill.

        Args:
            name: Skill identifier (e.g., "analyst", "risk_controller")
            description: Human-readable description
        """
        self.name = name
        self.description = description
        self._initialized = False

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """
        Execute the skill with given context.

        Args:
            context: Execution context with parameters

        Returns:
            SkillResult with execution outcome
        """
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """
        Get list of capabilities this skill provides.

        Returns:
            List of capability strings (e.g., ["single_stock_analysis", "batch_scan"])
        """
        pass

    def validate_context(self, context: SkillContext) -> tuple[bool, str]:
        """
        Validate execution context.

        Override in subclass for custom validation.

        Args:
            context: Context to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if context.user_id <= 0:
            return False, "Invalid user_id"
        return True, ""

    def initialize(self) -> None:
        """
        Initialize skill resources.

        Override in subclass if initialization is needed.
        Called once before first execution.
        """
        self._initialized = True

    def cleanup(self) -> None:
        """
        Cleanup skill resources.

        Override in subclass if cleanup is needed.
        """
        pass

    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
        return False


# Market schedule configuration
@dataclass
class MarketSchedule:
    """Market trading schedule (Beijing time)."""

    # Hong Kong
    hk_pre_market: time = field(default_factory=lambda: time(8, 30))
    hk_open: time = field(default_factory=lambda: time(9, 30))
    hk_lunch_start: time = field(default_factory=lambda: time(12, 0))
    hk_lunch_end: time = field(default_factory=lambda: time(13, 0))
    hk_close: time = field(default_factory=lambda: time(16, 0))
    hk_post_market: time = field(default_factory=lambda: time(16, 30))

    # US (Beijing time, summer time)
    us_pre_market: time = field(default_factory=lambda: time(20, 0))
    us_open: time = field(default_factory=lambda: time(21, 30))
    us_close: time = field(default_factory=lambda: time(4, 0))  # Next day
    us_post_market: time = field(default_factory=lambda: time(5, 0))  # Next day

    # A-share
    a_pre_market: time = field(default_factory=lambda: time(9, 0))
    a_open: time = field(default_factory=lambda: time(9, 30))
    a_lunch_start: time = field(default_factory=lambda: time(11, 30))
    a_lunch_end: time = field(default_factory=lambda: time(13, 0))
    a_close: time = field(default_factory=lambda: time(15, 0))
    a_post_market: time = field(default_factory=lambda: time(15, 30))

    def get_market_state(self, market: str, current_time: time = None) -> MarketState:
        """
        Get current market state.

        Args:
            market: Market code (HK, US, A)
            current_time: Time to check (default: now)

        Returns:
            MarketState enum value
        """
        if current_time is None:
            current_time = datetime.now().time()

        if market == "HK":
            if current_time < self.hk_pre_market:
                return MarketState.CLOSED
            elif current_time < self.hk_open:
                return MarketState.PRE_MARKET
            elif current_time < self.hk_close:
                # Check lunch break
                if self.hk_lunch_start <= current_time < self.hk_lunch_end:
                    return MarketState.CLOSED
                return MarketState.OPEN
            elif current_time < self.hk_post_market:
                return MarketState.POST_MARKET
            else:
                return MarketState.CLOSED

        elif market == "A":
            if current_time < self.a_pre_market:
                return MarketState.CLOSED
            elif current_time < self.a_open:
                return MarketState.PRE_MARKET
            elif current_time < self.a_close:
                if self.a_lunch_start <= current_time < self.a_lunch_end:
                    return MarketState.CLOSED
                return MarketState.OPEN
            elif current_time < self.a_post_market:
                return MarketState.POST_MARKET
            else:
                return MarketState.CLOSED

        elif market == "US":
            # US market spans midnight, more complex logic
            if self.us_pre_market <= current_time:
                if current_time < self.us_open:
                    return MarketState.PRE_MARKET
                else:
                    return MarketState.OPEN
            elif current_time < self.us_close:
                return MarketState.OPEN
            elif current_time < self.us_post_market:
                return MarketState.POST_MARKET
            else:
                return MarketState.CLOSED

        return MarketState.CLOSED


# Default market schedule instance
DEFAULT_SCHEDULE = MarketSchedule()
