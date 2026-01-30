"""
Statistics - 交易统计计算模块

计算交易表现的各项统计指标：
- 胜率、盈亏比
- 总盈利、总亏损、净利润
- 平均持仓天数
- 市场分布
- 盈亏率分布
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

from .trade_matcher import MatchedTrade


@dataclass
class MarketStats:
    """单个市场的统计数据"""

    market: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: Decimal = Decimal("0")
    total_loss: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def avg_profit_loss(self) -> Decimal:
        """平均盈亏"""
        if self.total_trades == 0:
            return Decimal("0")
        return self.net_profit / self.total_trades


@dataclass
class TradeRanking:
    """交易排名记录"""

    rank: int
    market: str
    code: str
    stock_name: str
    profit_loss: Decimal
    profit_loss_ratio: Decimal
    buy_date: Optional[str]
    sell_date: Optional[str]
    holding_days: int


@dataclass
class StockStats:
    """单个股票的统计数据"""

    market: str
    code: str
    stock_name: str
    trade_count: int = 0
    winning_trades: int = 0
    total_profit: Decimal = Decimal("0")
    total_loss: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.trade_count == 0:
            return 0.0
        return self.winning_trades / self.trade_count

    @property
    def full_code(self) -> str:
        return f"{self.market}.{self.code}"


@dataclass
class ProfitLossBucket:
    """盈亏率区间统计"""

    bucket_name: str  # e.g., "-50%以下", "-50%~-30%", "0~10%"
    min_ratio: float
    max_ratio: float
    count: int = 0
    trades: list[MatchedTrade] = field(default_factory=list)


@dataclass
class MonthlyStats:
    """月度统计数据"""

    year_month: str  # e.g., "2025-01"
    trade_count: int = 0
    winning_trades: int = 0
    total_profit: Decimal = Decimal("0")
    total_loss: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")

    @property
    def win_rate(self) -> float:
        if self.trade_count == 0:
            return 0.0
        return self.winning_trades / self.trade_count


@dataclass
class TradeStatistics:
    """完整的交易统计数据"""

    # 整体统计
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    breakeven_trades: int = 0

    # 盈亏统计
    total_profit: Decimal = Decimal("0")
    total_loss: Decimal = Decimal("0")
    net_profit: Decimal = Decimal("0")
    avg_profit: Decimal = Decimal("0")  # 平均盈利（仅盈利交易）
    avg_loss: Decimal = Decimal("0")  # 平均亏损（仅亏损交易）
    profit_loss_ratio: Decimal = Decimal("0")  # 盈亏比

    # 持仓时间统计
    avg_holding_days: float = 0.0
    avg_winning_holding_days: float = 0.0
    avg_losing_holding_days: float = 0.0
    max_holding_days: int = 0
    min_holding_days: int = 0

    # 市场分布
    market_stats: dict[str, MarketStats] = field(default_factory=dict)

    # 股票统计
    stock_stats: dict[str, StockStats] = field(default_factory=dict)

    # 最佳/最差交易
    top_winners: list[TradeRanking] = field(default_factory=list)
    top_losers: list[TradeRanking] = field(default_factory=list)

    # 盈亏率分布
    profit_loss_buckets: list[ProfitLossBucket] = field(default_factory=list)

    # 月度统计
    monthly_stats: dict[str, MonthlyStats] = field(default_factory=dict)

    # 期权统计（单独计算）
    option_total_trades: int = 0
    option_winning_trades: int = 0
    option_net_profit: Decimal = Decimal("0")

    # 手续费统计
    total_fees: Decimal = Decimal("0")  # 总手续费 (HKD)
    stock_fees: Decimal = Decimal("0")  # 股票手续费 (HKD)
    option_fees: Decimal = Decimal("0")  # 期权手续费 (HKD)

    @property
    def win_rate(self) -> float:
        """胜率"""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades

    @property
    def option_win_rate(self) -> float:
        """期权胜率"""
        if self.option_total_trades == 0:
            return 0.0
        return self.option_winning_trades / self.option_total_trades


class StatisticsCalculator:
    """统计计算器"""

    # 盈亏率区间定义
    PROFIT_LOSS_BUCKETS = [
        ("-50%以下", -float("inf"), -0.5),
        ("-50%~-30%", -0.5, -0.3),
        ("-30%~-20%", -0.3, -0.2),
        ("-20%~-10%", -0.2, -0.1),
        ("-10%~0%", -0.1, 0),
        ("0~10%", 0, 0.1),
        ("10%~20%", 0.1, 0.2),
        ("20%~30%", 0.2, 0.3),
        ("30%~50%", 0.3, 0.5),
        ("50%以上", 0.5, float("inf")),
    ]

    def calculate(self, trades: list[MatchedTrade]) -> TradeStatistics:
        """
        计算所有统计指标

        Args:
            trades: 配对后的交易列表

        Returns:
            完整的统计数据
        """
        stats = TradeStatistics()

        if not trades:
            return stats

        # 分离股票和期权交易
        stock_trades = [t for t in trades if not t.is_option]
        option_trades = [t for t in trades if t.is_option]

        # 计算整体统计（股票）
        self._calculate_overall_stats(stock_trades, stats)

        # 计算期权统计
        self._calculate_option_stats(option_trades, stats)

        # 计算持仓时间统计
        self._calculate_holding_stats(stock_trades, stats)

        # 计算市场分布
        self._calculate_market_stats(stock_trades, stats)

        # 计算股票统计
        self._calculate_stock_stats(stock_trades, stats)

        # 计算最佳/最差交易
        self._calculate_rankings(stock_trades, stats)

        # 计算盈亏率分布
        self._calculate_profit_loss_distribution(stock_trades, stats)

        # 计算月度统计
        self._calculate_monthly_stats(stock_trades, stats)

        return stats

    def _calculate_overall_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算整体统计"""
        stats.total_trades = len(trades)

        total_profit = Decimal("0")
        total_loss = Decimal("0")
        total_fees = Decimal("0")
        winning_count = 0
        losing_count = 0

        for trade in trades:
            # 累计手续费
            total_fees += trade.buy_fee + trade.sell_fee

            if trade.profit_loss > 0:
                winning_count += 1
                total_profit += trade.profit_loss
            elif trade.profit_loss < 0:
                losing_count += 1
                total_loss += abs(trade.profit_loss)
            else:
                stats.breakeven_trades += 1

        stats.winning_trades = winning_count
        stats.losing_trades = losing_count
        stats.total_profit = total_profit
        stats.total_loss = total_loss
        stats.net_profit = total_profit - total_loss
        stats.stock_fees = total_fees

        # 平均盈利/亏损
        if winning_count > 0:
            stats.avg_profit = total_profit / winning_count
        if losing_count > 0:
            stats.avg_loss = total_loss / losing_count

        # 盈亏比
        if stats.avg_loss > 0:
            stats.profit_loss_ratio = stats.avg_profit / stats.avg_loss
        elif stats.avg_profit > 0:
            stats.profit_loss_ratio = Decimal("999")  # 无亏损时用大值表示

    def _calculate_option_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算期权统计"""
        stats.option_total_trades = len(trades)

        winning_count = 0
        net_profit = Decimal("0")
        option_fees = Decimal("0")

        for trade in trades:
            if trade.profit_loss > 0:
                winning_count += 1
            net_profit += trade.profit_loss
            option_fees += trade.buy_fee + trade.sell_fee

        stats.option_winning_trades = winning_count
        stats.option_net_profit = net_profit
        stats.option_fees = option_fees
        stats.total_fees = stats.stock_fees + option_fees

    def _calculate_holding_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算持仓时间统计"""
        if not trades:
            return

        holding_days = [t.holding_days for t in trades if t.holding_days >= 0]
        winning_days = [
            t.holding_days for t in trades if t.is_profitable and t.holding_days >= 0
        ]
        losing_days = [
            t.holding_days
            for t in trades
            if not t.is_profitable and t.profit_loss < 0 and t.holding_days >= 0
        ]

        if holding_days:
            stats.avg_holding_days = sum(holding_days) / len(holding_days)
            stats.max_holding_days = max(holding_days)
            stats.min_holding_days = min(holding_days)

        if winning_days:
            stats.avg_winning_holding_days = sum(winning_days) / len(winning_days)

        if losing_days:
            stats.avg_losing_holding_days = sum(losing_days) / len(losing_days)

    def _calculate_market_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算市场分布统计"""
        market_data: dict[str, MarketStats] = {}

        for trade in trades:
            market = trade.market
            if market not in market_data:
                market_data[market] = MarketStats(market=market)

            ms = market_data[market]
            ms.total_trades += 1

            if trade.profit_loss > 0:
                ms.winning_trades += 1
                ms.total_profit += trade.profit_loss
            elif trade.profit_loss < 0:
                ms.losing_trades += 1
                ms.total_loss += abs(trade.profit_loss)

            ms.net_profit += trade.profit_loss

        stats.market_stats = market_data

    def _calculate_stock_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算单个股票的统计"""
        stock_data: dict[str, StockStats] = {}

        for trade in trades:
            key = f"{trade.market}.{trade.code}"
            if key not in stock_data:
                stock_data[key] = StockStats(
                    market=trade.market,
                    code=trade.code,
                    stock_name=trade.stock_name,
                )

            ss = stock_data[key]
            ss.trade_count += 1

            if trade.profit_loss > 0:
                ss.winning_trades += 1
                ss.total_profit += trade.profit_loss
            elif trade.profit_loss < 0:
                ss.total_loss += abs(trade.profit_loss)

            ss.net_profit += trade.profit_loss

        stats.stock_stats = stock_data

    def _calculate_rankings(
        self, trades: list[MatchedTrade], stats: TradeStatistics, top_n: int = 5
    ) -> None:
        """计算最佳/最差交易排名"""
        # 按盈亏额排序
        sorted_by_profit = sorted(trades, key=lambda t: t.profit_loss, reverse=True)

        # Top winners
        winners = sorted_by_profit[:top_n]
        stats.top_winners = [
            TradeRanking(
                rank=i + 1,
                market=t.market,
                code=t.code,
                stock_name=t.stock_name,
                profit_loss=t.profit_loss,
                profit_loss_ratio=t.profit_loss_ratio,
                buy_date=t.buy_date.strftime("%Y-%m-%d") if t.buy_date else None,
                sell_date=t.sell_date.strftime("%Y-%m-%d") if t.sell_date else None,
                holding_days=t.holding_days,
            )
            for i, t in enumerate(winners)
            if t.profit_loss > 0
        ]

        # Top losers
        losers = sorted_by_profit[-top_n:][::-1]  # 取最后 N 个并反转
        stats.top_losers = [
            TradeRanking(
                rank=i + 1,
                market=t.market,
                code=t.code,
                stock_name=t.stock_name,
                profit_loss=t.profit_loss,
                profit_loss_ratio=t.profit_loss_ratio,
                buy_date=t.buy_date.strftime("%Y-%m-%d") if t.buy_date else None,
                sell_date=t.sell_date.strftime("%Y-%m-%d") if t.sell_date else None,
                holding_days=t.holding_days,
            )
            for i, t in enumerate(losers)
            if t.profit_loss < 0
        ]

    def _calculate_profit_loss_distribution(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算盈亏率分布"""
        buckets = [
            ProfitLossBucket(name, min_r, max_r)
            for name, min_r, max_r in self.PROFIT_LOSS_BUCKETS
        ]

        for trade in trades:
            ratio = float(trade.profit_loss_ratio)
            for bucket in buckets:
                if bucket.min_ratio <= ratio < bucket.max_ratio:
                    bucket.count += 1
                    bucket.trades.append(trade)
                    break

        stats.profit_loss_buckets = buckets

    def _calculate_monthly_stats(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> None:
        """计算月度统计"""
        monthly_data: dict[str, MonthlyStats] = {}

        for trade in trades:
            if not trade.sell_date:
                continue

            year_month = trade.sell_date.strftime("%Y-%m")
            if year_month not in monthly_data:
                monthly_data[year_month] = MonthlyStats(year_month=year_month)

            ms = monthly_data[year_month]
            ms.trade_count += 1

            if trade.profit_loss > 0:
                ms.winning_trades += 1
                ms.total_profit += trade.profit_loss
            elif trade.profit_loss < 0:
                ms.total_loss += abs(trade.profit_loss)

            ms.net_profit += trade.profit_loss

        # 按月份排序
        stats.monthly_stats = dict(sorted(monthly_data.items()))

    def get_top_traded_stocks(
        self, stats: TradeStatistics, top_n: int = 10
    ) -> list[StockStats]:
        """获取交易次数最多的股票"""
        sorted_stocks = sorted(
            stats.stock_stats.values(), key=lambda s: s.trade_count, reverse=True
        )
        return sorted_stocks[:top_n]

    def get_most_profitable_stocks(
        self, stats: TradeStatistics, top_n: int = 10
    ) -> list[StockStats]:
        """获取最盈利的股票"""
        sorted_stocks = sorted(
            stats.stock_stats.values(), key=lambda s: s.net_profit, reverse=True
        )
        return sorted_stocks[:top_n]
