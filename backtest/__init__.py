"""
Backtest framework for Investment Analyzer.

Provides strategy backtesting functionality including:
- Strategy base class for custom strategies
- Backtest engine for running simulations
- Built-in strategies (MA crossover, VCP breakout)
- Performance metrics calculation
- Report generation

Usage:
    from backtest import (
        BacktestEngine, run_backtest,
        MACrossStrategy, MACrossConfig,
        VCPBreakoutStrategy, VCPBreakoutConfig,
        generate_report, ReportFormat,
    )

    # Create strategy
    config = MACrossConfig(fast_period=10, slow_period=30)
    strategy = MACrossStrategy(config)

    # Run backtest
    result = run_backtest(strategy, data, symbol="HK.00700")

    # Generate report
    report = generate_report(result, format=ReportFormat.MARKDOWN)
"""

from .engine import BacktestEngine, run_backtest
from .report import ReportFormat, generate_report
from .strategies import (
    MACrossConfig,
    MACrossStrategy,
    VCPBreakoutConfig,
    VCPBreakoutStrategy,
)
from .strategy import (
    BacktestMetrics,
    BacktestResult,
    Position,
    PositionSide,
    Signal,
    SignalType,
    Strategy,
    StrategyConfig,
    Trade,
)

__all__ = [
    # Engine
    "BacktestEngine",
    "run_backtest",
    # Base classes
    "Strategy",
    "StrategyConfig",
    "Signal",
    "SignalType",
    "Trade",
    "Position",
    "PositionSide",
    "BacktestResult",
    "BacktestMetrics",
    # Built-in strategies
    "MACrossStrategy",
    "MACrossConfig",
    "VCPBreakoutStrategy",
    "VCPBreakoutConfig",
    # Reporting
    "generate_report",
    "ReportFormat",
]
