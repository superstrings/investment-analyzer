"""
Backtest engine for running strategy simulations.

Provides the core backtesting functionality including:
- Signal processing
- Position management
- Trade execution
- Performance metrics calculation
"""

import math
from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

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


class BacktestEngine:
    """Engine for running backtests on trading strategies."""

    def __init__(
        self,
        strategy: Strategy,
        data: pd.DataFrame,
        symbol: str = "UNKNOWN",
    ):
        """Initialize backtest engine.

        Args:
            strategy: Trading strategy to backtest
            data: DataFrame with OHLCV data (must have date, open, high, low, close, volume)
            symbol: Stock symbol being tested
        """
        self.strategy = strategy
        self.data = self._prepare_data(data)
        self.symbol = symbol

        # State
        self.capital = strategy.config.initial_capital
        self.position: Optional[Position] = None
        self.trades: list[Trade] = []
        self.signals: list[Signal] = []
        self.equity_curve: list[tuple[datetime, float]] = []
        self.daily_returns: list[float] = []

    def _prepare_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Prepare data for backtesting.

        Args:
            data: Raw data

        Returns:
            Cleaned and sorted DataFrame
        """
        df = data.copy()

        # Ensure required columns exist (case-insensitive)
        column_map = {}
        for col in df.columns:
            lower = col.lower()
            if lower in ("date", "datetime", "time"):
                column_map[col] = "date"
            elif lower == "open":
                column_map[col] = "open"
            elif lower == "high":
                column_map[col] = "high"
            elif lower == "low":
                column_map[col] = "low"
            elif lower == "close":
                column_map[col] = "close"
            elif lower in ("volume", "vol"):
                column_map[col] = "volume"

        df = df.rename(columns=column_map)

        # Ensure date column is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").reset_index(drop=True)

        return df

    def run(self) -> BacktestResult:
        """Run the backtest.

        Returns:
            BacktestResult with performance metrics and trade history
        """
        # Generate signals from strategy
        self.signals = self.strategy.generate_signals(self.data)

        # Create signal lookup by date
        signal_map = {s.date.date(): s for s in self.signals}

        # Initialize
        self.capital = self.strategy.config.initial_capital
        self.position = None
        self.trades = []
        self.equity_curve = []
        self.daily_returns = []
        prev_equity = self.capital

        # Process each bar
        for idx, row in self.data.iterrows():
            date = row["date"]
            close = row["close"]
            high = row["high"]
            low = row["low"]

            # Check for stop loss / take profit on existing position
            if self.position:
                should_exit, reason = self.strategy.should_exit(
                    self.position, close, date
                )
                if should_exit:
                    self._close_position(date, close, reason)

            # Check for signal on this date
            signal = signal_map.get(date.date())
            if signal:
                self._process_signal(signal, date, close)

            # Also call on_bar for strategies that use it
            bar_signal = self.strategy.on_bar(
                date,
                row["open"],
                high,
                low,
                close,
                row.get("volume", 0),
                self.position,
            )
            if bar_signal:
                self._process_signal(bar_signal, date, close)

            # Calculate equity
            equity = self.capital
            if self.position:
                self.position.update_price(close)
                equity += self.position.unrealized_pnl

            self.equity_curve.append((date, equity))

            # Calculate daily return
            if prev_equity > 0:
                daily_return = (equity - prev_equity) / prev_equity
                self.daily_returns.append(daily_return)
            prev_equity = equity

        # Close any remaining position at end
        if self.position:
            last_row = self.data.iloc[-1]
            self._close_position(last_row["date"], last_row["close"], "回测结束")

        # Calculate final equity
        final_equity = self.capital
        if self.position:
            self.position.update_price(self.data.iloc[-1]["close"])
            final_equity += self.position.unrealized_pnl

        # Build result
        result = BacktestResult(
            strategy_name=self.strategy.name,
            symbol=self.symbol,
            start_date=self.data.iloc[0]["date"],
            end_date=self.data.iloc[-1]["date"],
            initial_capital=self.strategy.config.initial_capital,
            final_capital=final_equity,
            final_position=self.position,
            trades=self.trades,
            signals=self.signals,
            equity_curve=self.equity_curve,
            daily_returns=self.daily_returns,
        )

        # Calculate metrics
        result.metrics = self._calculate_metrics(result)

        return result

    def _process_signal(self, signal: Signal, date: datetime, price: float):
        """Process a trading signal.

        Args:
            signal: Signal to process
            date: Current date
            price: Current price
        """
        if signal.signal_type == SignalType.BUY:
            if not self.position:
                self._open_position(
                    date, price, signal.quantity, PositionSide.LONG, signal.reason
                )
        elif signal.signal_type == SignalType.SELL:
            if self.position and self.position.side == PositionSide.LONG:
                self._close_position(date, price, signal.reason)

    def _open_position(
        self,
        date: datetime,
        price: float,
        quantity: float,
        side: PositionSide,
        reason: str = "",
    ):
        """Open a new position.

        Args:
            date: Entry date
            price: Entry price
            quantity: Position size
            side: Long or short
            reason: Entry reason
        """
        # Calculate actual quantity based on capital
        actual_quantity = self.strategy.calculate_position_size(self.capital, price)
        if quantity > 0:
            actual_quantity = min(actual_quantity, quantity)

        # Apply commission
        commission = actual_quantity * price * self.strategy.config.commission_rate
        self.capital -= commission

        self.position = Position(
            entry_date=date,
            entry_price=price,
            quantity=actual_quantity,
            side=side,
            current_price=price,
            entry_reason=reason,
        )

    def _close_position(self, date: datetime, price: float, reason: str = ""):
        """Close current position.

        Args:
            date: Exit date
            price: Exit price
            reason: Exit reason
        """
        if not self.position:
            return

        # Calculate PnL
        if self.position.side == PositionSide.LONG:
            pnl = (price - self.position.entry_price) * self.position.quantity
        else:
            pnl = (self.position.entry_price - price) * self.position.quantity

        # Apply commission
        commission = (
            self.position.quantity * price * self.strategy.config.commission_rate
        )
        pnl -= commission
        self.capital += pnl + self.position.entry_price * self.position.quantity

        # Record trade
        trade = Trade(
            entry_date=self.position.entry_date,
            entry_price=self.position.entry_price,
            exit_date=date,
            exit_price=price,
            quantity=self.position.quantity,
            side=self.position.side,
            pnl=pnl,
            entry_reason=self.position.entry_reason,
            exit_reason=reason,
        )
        self.trades.append(trade)

        self.position = None

    def _calculate_metrics(self, result: BacktestResult) -> BacktestMetrics:
        """Calculate performance metrics.

        Args:
            result: Backtest result

        Returns:
            Calculated metrics
        """
        metrics = BacktestMetrics()

        # Basic returns
        initial = result.initial_capital
        final = result.final_capital
        metrics.total_return = final - initial
        metrics.total_return_pct = (final - initial) / initial if initial > 0 else 0

        # Annualized return
        days = (result.end_date - result.start_date).days
        if days > 0:
            years = days / 365.0
            if metrics.total_return_pct > -1:
                metrics.annualized_return = (
                    (1 + metrics.total_return_pct) ** (1 / years) - 1
                    if years > 0
                    else 0
                )

        # Max drawdown
        if result.equity_curve:
            equities = [e[1] for e in result.equity_curve]
            peak = equities[0]
            max_dd = 0
            max_dd_pct = 0
            for equity in equities:
                if equity > peak:
                    peak = equity
                dd = peak - equity
                dd_pct = dd / peak if peak > 0 else 0
                if dd > max_dd:
                    max_dd = dd
                    max_dd_pct = dd_pct
            metrics.max_drawdown = max_dd
            metrics.max_drawdown_pct = max_dd_pct

        # Sharpe ratio (assuming risk-free rate of 0)
        if result.daily_returns:
            returns = np.array(result.daily_returns)
            if len(returns) > 1 and returns.std() > 0:
                metrics.sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)

        # Sortino ratio (downside deviation only)
        if result.daily_returns:
            returns = np.array(result.daily_returns)
            negative_returns = returns[returns < 0]
            if len(negative_returns) > 0:
                downside_std = np.std(negative_returns)
                if downside_std > 0:
                    metrics.sortino_ratio = returns.mean() / downside_std * np.sqrt(252)

        # Calmar ratio (annualized return / max drawdown)
        if metrics.max_drawdown_pct > 0:
            metrics.calmar_ratio = metrics.annualized_return / metrics.max_drawdown_pct

        # Trade statistics
        if result.trades:
            metrics.total_trades = len(result.trades)
            winning = [t for t in result.trades if t.pnl > 0]
            losing = [t for t in result.trades if t.pnl <= 0]

            metrics.winning_trades = len(winning)
            metrics.losing_trades = len(losing)
            metrics.win_rate = len(winning) / len(result.trades) if result.trades else 0

            if winning:
                metrics.avg_win = sum(t.pnl for t in winning) / len(winning)
            if losing:
                metrics.avg_loss = abs(sum(t.pnl for t in losing) / len(losing))

            # Profit factor
            gross_profit = sum(t.pnl for t in winning)
            gross_loss = abs(sum(t.pnl for t in losing))
            if gross_loss > 0:
                metrics.profit_factor = gross_profit / gross_loss

            # Average holding days
            metrics.avg_holding_days = sum(t.holding_days for t in result.trades) / len(
                result.trades
            )

            # Consecutive wins/losses
            current_wins = 0
            current_losses = 0
            max_wins = 0
            max_losses = 0
            for trade in result.trades:
                if trade.pnl > 0:
                    current_wins += 1
                    current_losses = 0
                    max_wins = max(max_wins, current_wins)
                else:
                    current_losses += 1
                    current_wins = 0
                    max_losses = max(max_losses, current_losses)

            metrics.max_consecutive_wins = max_wins
            metrics.max_consecutive_losses = max_losses

            # Expectancy
            metrics.expectancy = (
                metrics.win_rate * metrics.avg_win
                - (1 - metrics.win_rate) * metrics.avg_loss
            )

        return metrics


def run_backtest(
    strategy: Strategy,
    data: pd.DataFrame,
    symbol: str = "UNKNOWN",
) -> BacktestResult:
    """Convenience function to run a backtest.

    Args:
        strategy: Trading strategy
        data: OHLCV data
        symbol: Stock symbol

    Returns:
        Backtest result
    """
    engine = BacktestEngine(strategy, data, symbol)
    return engine.run()
