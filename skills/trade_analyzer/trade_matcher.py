"""
Trade Matcher - 买卖配对模块

使用 LIFO (后进先出) 算法将买入和卖出记录配对成完整交易。
支持部分成交、多次加仓等复杂场景。
股票与期权分开配对和统计。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional

from db import Trade


@dataclass
class MatchedTrade:
    """配对后的完整交易记录"""

    # 基本信息
    market: str
    code: str
    stock_name: str
    is_option: bool = False

    # 买入信息
    buy_price: Decimal = Decimal("0")
    buy_qty: Decimal = Decimal("0")
    buy_amount: Decimal = Decimal("0")
    buy_date: Optional[datetime] = None
    buy_fee: Decimal = Decimal("0")

    # 卖出信息
    sell_price: Decimal = Decimal("0")
    sell_qty: Decimal = Decimal("0")
    sell_amount: Decimal = Decimal("0")
    sell_date: Optional[datetime] = None
    sell_fee: Decimal = Decimal("0")

    # 计算字段
    profit_loss: Decimal = Decimal("0")  # 盈亏额
    profit_loss_ratio: Decimal = Decimal("0")  # 盈亏率
    holding_days: int = 0  # 持仓天数

    # 原始交易记录引用 (用于调试)
    buy_trade_ids: list[str] = field(default_factory=list)
    sell_trade_ids: list[str] = field(default_factory=list)

    def calculate(self) -> None:
        """计算盈亏和持仓天数"""
        # 盈亏额 = 卖出市值 - 买入市值 - 手续费
        self.profit_loss = (
            self.sell_amount - self.buy_amount - self.buy_fee - self.sell_fee
        )

        # 盈亏率 = 盈亏额 / 买入市值
        if self.buy_amount > 0:
            self.profit_loss_ratio = self.profit_loss / self.buy_amount
        else:
            self.profit_loss_ratio = Decimal("0")

        # 持仓天数
        if self.buy_date and self.sell_date:
            delta = self.sell_date.date() - self.buy_date.date()
            self.holding_days = delta.days
        else:
            self.holding_days = 0

    @property
    def is_profitable(self) -> bool:
        """是否盈利"""
        return self.profit_loss > 0

    @property
    def full_code(self) -> str:
        """完整股票代码"""
        return f"{self.market}.{self.code}"

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "market": self.market,
            "code": self.code,
            "stock_name": self.stock_name,
            "is_option": self.is_option,
            "buy_price": float(self.buy_price),
            "buy_qty": float(self.buy_qty),
            "buy_amount": float(self.buy_amount),
            "buy_date": self.buy_date.isoformat() if self.buy_date else None,
            "buy_fee": float(self.buy_fee),
            "sell_price": float(self.sell_price),
            "sell_qty": float(self.sell_qty),
            "sell_amount": float(self.sell_amount),
            "sell_date": self.sell_date.isoformat() if self.sell_date else None,
            "sell_fee": float(self.sell_fee),
            "profit_loss": float(self.profit_loss),
            "profit_loss_ratio": float(self.profit_loss_ratio),
            "holding_days": self.holding_days,
        }


@dataclass
class BuyRecord:
    """未配对的买入记录（用于 LIFO 栈）"""

    trade_id: str
    trade_time: datetime
    price: Decimal
    qty: Decimal
    remaining_qty: Decimal  # 剩余未配对数量
    fee: Decimal


class TradeMatcher:
    """
    交易配对器

    使用 LIFO（后进先出）算法将买入和卖出记录配对。
    最近买入的股票优先与卖出记录配对。
    """

    def __init__(self):
        self.matched_trades: list[MatchedTrade] = []
        self.unmatched_buys: dict[str, list[BuyRecord]] = {}  # code -> [BuyRecord]
        self.unmatched_sells: list[Trade] = []

    @staticmethod
    def is_option_code(market: str, code: str) -> bool:
        """
        判断是否为期权代码

        HK options: 代码中包含字母 (e.g., SMC260629C75000, TCH260330C650000)
        US options: SYMBOL + YYMMDD + C/P + STRIKE (e.g., MU260116C230000)
        """
        if market == "HK":
            # 港股期权/权证代码中包含字母
            return any(c.isalpha() for c in code)

        if market == "US":
            # 美股期权格式: SYMBOL + YYMMDD + C/P + STRIKE
            return bool(re.match(r"^[A-Z]+\d{6}[CP]\d+$", code))

        return False

    def match_trades(self, trades: list[Trade]) -> list[MatchedTrade]:
        """
        配对交易记录

        Args:
            trades: 按时间排序的交易记录列表

        Returns:
            配对后的完整交易列表
        """
        self.matched_trades = []
        self.unmatched_buys = {}
        self.unmatched_sells = []

        # 按时间排序（确保按交易时间顺序处理）
        sorted_trades = sorted(trades, key=lambda t: t.trade_time)

        for trade in sorted_trades:
            full_code = f"{trade.market}.{trade.code}"

            if trade.trd_side == "BUY":
                self._process_buy(trade, full_code)
            elif trade.trd_side == "SELL":
                self._process_sell(trade, full_code)

        return self.matched_trades

    def _process_buy(self, trade: Trade, full_code: str) -> None:
        """处理买入记录"""
        if full_code not in self.unmatched_buys:
            self.unmatched_buys[full_code] = []

        # 计算单股手续费
        qty = Decimal(str(trade.qty))
        fee_per_share = Decimal(str(trade.fee or 0)) / qty if qty > 0 else Decimal("0")

        buy_record = BuyRecord(
            trade_id=trade.deal_id,
            trade_time=trade.trade_time,
            price=Decimal(str(trade.price)),
            qty=qty,
            remaining_qty=qty,
            fee=Decimal(str(trade.fee or 0)),
        )

        # 添加到买入栈（LIFO 栈顶）
        self.unmatched_buys[full_code].append(buy_record)

    def _process_sell(self, trade: Trade, full_code: str) -> None:
        """处理卖出记录"""
        sell_qty = Decimal(str(trade.qty))
        sell_price = Decimal(str(trade.price))
        sell_fee = Decimal(str(trade.fee or 0))

        if full_code not in self.unmatched_buys or not self.unmatched_buys[full_code]:
            # 没有对应的买入记录
            self.unmatched_sells.append(trade)
            return

        # LIFO: 从栈顶（最近买入）开始配对
        buy_stack = self.unmatched_buys[full_code]
        remaining_sell_qty = sell_qty

        while remaining_sell_qty > 0 and buy_stack:
            # 取栈顶的买入记录
            buy_record = buy_stack[-1]

            # 计算配对数量
            match_qty = min(buy_record.remaining_qty, remaining_sell_qty)

            if match_qty > 0:
                # 创建配对交易
                matched = self._create_matched_trade(
                    trade=trade,
                    buy_record=buy_record,
                    match_qty=match_qty,
                    sell_price=sell_price,
                    sell_fee=sell_fee * match_qty / sell_qty,  # 按比例分摊手续费
                )
                self.matched_trades.append(matched)

                # 更新剩余数量
                buy_record.remaining_qty -= match_qty
                remaining_sell_qty -= match_qty

                # 如果买入记录已完全配对，从栈中移除
                if buy_record.remaining_qty <= 0:
                    buy_stack.pop()

        # 如果卖出数量未完全配对（空头卖出或数据不完整）
        if remaining_sell_qty > 0:
            self.unmatched_sells.append(trade)

    def _create_matched_trade(
        self,
        trade: Trade,
        buy_record: BuyRecord,
        match_qty: Decimal,
        sell_price: Decimal,
        sell_fee: Decimal,
    ) -> MatchedTrade:
        """创建配对后的交易记录"""
        # 计算买入手续费（按比例分摊）
        buy_fee_ratio = match_qty / buy_record.qty
        buy_fee = buy_record.fee * buy_fee_ratio

        matched = MatchedTrade(
            market=trade.market,
            code=trade.code,
            stock_name=trade.stock_name or "",
            is_option=self.is_option_code(trade.market, trade.code),
            buy_price=buy_record.price,
            buy_qty=match_qty,
            buy_amount=buy_record.price * match_qty,
            buy_date=buy_record.trade_time,
            buy_fee=buy_fee,
            sell_price=sell_price,
            sell_qty=match_qty,
            sell_amount=sell_price * match_qty,
            sell_date=trade.trade_time,
            sell_fee=sell_fee,
            buy_trade_ids=[buy_record.trade_id],
            sell_trade_ids=[trade.deal_id],
        )

        # 计算盈亏和持仓天数
        matched.calculate()

        return matched

    def get_unmatched_buys(self) -> list[BuyRecord]:
        """获取未配对的买入记录（当前持仓）"""
        result = []
        for buy_list in self.unmatched_buys.values():
            for buy in buy_list:
                if buy.remaining_qty > 0:
                    result.append(buy)
        return result

    def get_unmatched_sells(self) -> list[Trade]:
        """获取未配对的卖出记录"""
        return self.unmatched_sells

    def get_stock_trades(self) -> list[MatchedTrade]:
        """获取股票交易（非期权）"""
        return [t for t in self.matched_trades if not t.is_option]

    def get_option_trades(self) -> list[MatchedTrade]:
        """获取期权交易"""
        return [t for t in self.matched_trades if t.is_option]
