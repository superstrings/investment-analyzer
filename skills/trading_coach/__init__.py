"""
Trading Coach Skill package.

Provides trading plan generation, psychology coaching, and compound education.
"""

from .compound_educator import (
    CompoundEducator,
    CompoundLesson,
    CompoundProjection,
    TradingMath,
)
from .plan_generator import (
    ActionItem,
    ActionPriority,
    ActionType,
    ChecklistItem,
    PlanGenerator,
    PositionAction,
    TradingPlan,
)
from .psychology_coach import (
    BehaviorAnalysis,
    BehaviorPattern,
    EmotionAssessment,
    EmotionType,
    PsychologyCoach,
    PsychologyTrigger,
    TradePattern,
)
from .trading_coach import CoachingResult, TradingCoach, generate_coaching_report

__all__ = [
    # Main controller
    "TradingCoach",
    "CoachingResult",
    "generate_coaching_report",
    # Plan generator
    "PlanGenerator",
    "TradingPlan",
    "ActionItem",
    "ActionPriority",
    "ActionType",
    "ChecklistItem",
    "PositionAction",
    # Compound educator
    "CompoundEducator",
    "CompoundProjection",
    "CompoundLesson",
    "TradingMath",
    # Psychology coach
    "PsychologyCoach",
    "EmotionType",
    "EmotionAssessment",
    "BehaviorPattern",
    "BehaviorAnalysis",
    "TradePattern",
    "PsychologyTrigger",
]
