"""
Chart Generator - 图表生成模块

使用 matplotlib 生成各类分析图表：
- 盈亏分布饼图
- 月度盈亏柱状图
- 持仓天数分布直方图
- 盈亏率分布直方图
- 市场分布饼图
- 累计盈亏曲线
"""

import io
from decimal import Decimal
from pathlib import Path
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

from .statistics import TradeStatistics
from .trade_matcher import MatchedTrade


class ChartGenerator:
    """图表生成器"""

    def __init__(self, output_dir: Optional[Path] = None):
        """
        初始化图表生成器

        Args:
            output_dir: 图表输出目录，如果不指定则返回字节流
        """
        self.output_dir = output_dir
        self._setup_chinese_font()

    def _setup_chinese_font(self) -> None:
        """设置中文字体"""
        # 尝试使用系统中文字体
        chinese_fonts = [
            "PingFang SC",
            "Heiti SC",
            "STHeiti",
            "Microsoft YaHei",
            "SimHei",
            "Arial Unicode MS",
        ]

        for font_name in chinese_fonts:
            try:
                font_path = fm.findfont(fm.FontProperties(family=font_name))
                if font_path and "LastResort" not in font_path:
                    plt.rcParams["font.family"] = font_name
                    plt.rcParams["axes.unicode_minus"] = False
                    return
            except Exception:
                continue

        # 如果找不到中文字体，使用默认设置
        plt.rcParams["axes.unicode_minus"] = False

    def _save_or_return(self, fig: plt.Figure, filename: str) -> bytes:
        """保存图表或返回字节流"""
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        data = buf.read()

        if self.output_dir:
            filepath = self.output_dir / filename
            with open(filepath, "wb") as f:
                f.write(data)

        plt.close(fig)
        return data

    def generate_win_loss_pie(self, stats: TradeStatistics) -> bytes:
        """生成盈亏分布饼图"""
        fig, ax = plt.subplots(figsize=(8, 6))

        labels = ["盈利", "亏损", "持平"]
        sizes = [
            stats.winning_trades,
            stats.losing_trades,
            stats.breakeven_trades,
        ]
        colors = ["#4CAF50", "#F44336", "#9E9E9E"]
        explode = (0.05, 0.05, 0)

        # 过滤掉零值
        filtered = [
            (l, s, c, e) for l, s, c, e in zip(labels, sizes, colors, explode) if s > 0
        ]
        if not filtered:
            plt.close(fig)
            return b""

        labels, sizes, colors, explode = zip(*filtered)

        ax.pie(
            sizes,
            explode=explode,
            labels=labels,
            colors=colors,
            autopct=lambda pct: f"{pct:.1f}%\n({int(pct/100*sum(sizes))}笔)",
            shadow=False,
            startangle=90,
        )
        ax.set_title(f"盈亏分布 (共{stats.total_trades}笔交易)")

        return self._save_or_return(fig, "win_loss_pie.png")

    def generate_monthly_profit_bar(self, stats: TradeStatistics) -> bytes:
        """生成月度盈亏柱状图"""
        if not stats.monthly_stats:
            return b""

        fig, ax = plt.subplots(figsize=(12, 6))

        months = list(stats.monthly_stats.keys())
        profits = [float(ms.net_profit) for ms in stats.monthly_stats.values()]

        colors = ["#4CAF50" if p >= 0 else "#F44336" for p in profits]

        bars = ax.bar(months, profits, color=colors)

        # 添加数值标签
        for bar, profit in zip(bars, profits):
            height = bar.get_height()
            ax.annotate(
                f"{profit:,.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3 if height >= 0 else -12),
                textcoords="offset points",
                ha="center",
                va="bottom" if height >= 0 else "top",
                fontsize=8,
            )

        ax.set_xlabel("月份")
        ax.set_ylabel("盈亏额")
        ax.set_title("月度盈亏趋势")
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        return self._save_or_return(fig, "monthly_profit_bar.png")

    def generate_holding_days_hist(self, trades: list[MatchedTrade]) -> bytes:
        """生成持仓天数分布直方图"""
        holding_days = [t.holding_days for t in trades if t.holding_days >= 0]
        if not holding_days:
            return b""

        fig, ax = plt.subplots(figsize=(10, 6))

        ax.hist(holding_days, bins=20, color="#2196F3", edgecolor="white", alpha=0.7)

        ax.set_xlabel("持仓天数")
        ax.set_ylabel("交易笔数")
        ax.set_title(
            f"持仓天数分布 (平均: {sum(holding_days)/len(holding_days):.1f}天)"
        )

        # 添加平均线
        avg_days = sum(holding_days) / len(holding_days)
        ax.axvline(
            x=avg_days, color="red", linestyle="--", label=f"平均: {avg_days:.1f}天"
        )
        ax.legend()

        return self._save_or_return(fig, "holding_days_hist.png")

    def generate_profit_loss_ratio_hist(self, trades: list[MatchedTrade]) -> bytes:
        """生成盈亏率分布直方图"""
        ratios = [float(t.profit_loss_ratio) * 100 for t in trades]
        if not ratios:
            return b""

        fig, ax = plt.subplots(figsize=(10, 6))

        # 限制显示范围在 -100% 到 200%
        ratios_clipped = [max(-100, min(200, r)) for r in ratios]

        ax.hist(ratios_clipped, bins=30, color="#9C27B0", edgecolor="white", alpha=0.7)

        ax.set_xlabel("盈亏率 (%)")
        ax.set_ylabel("交易笔数")
        ax.set_title("盈亏率分布")
        ax.axvline(x=0, color="black", linestyle="-", linewidth=1)

        return self._save_or_return(fig, "profit_loss_ratio_hist.png")

    def generate_market_distribution_pie(self, stats: TradeStatistics) -> bytes:
        """生成市场分布饼图"""
        if not stats.market_stats:
            return b""

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # 左图：交易笔数分布
        markets = list(stats.market_stats.keys())
        trade_counts = [ms.total_trades for ms in stats.market_stats.values()]

        market_labels = {
            "HK": "港股",
            "US": "美股",
            "SH": "沪市",
            "SZ": "深市",
        }
        labels = [market_labels.get(m, m) for m in markets]
        colors = ["#FF9800", "#2196F3", "#E91E63", "#4CAF50"]

        ax1.pie(
            trade_counts,
            labels=labels,
            colors=colors[: len(markets)],
            autopct=lambda pct: f"{pct:.1f}%\n({int(pct/100*sum(trade_counts))}笔)",
            startangle=90,
        )
        ax1.set_title("交易笔数分布")

        # 右图：盈亏额分布（柱状图）
        net_profits = [float(ms.net_profit) for ms in stats.market_stats.values()]
        bar_colors = ["#4CAF50" if p >= 0 else "#F44336" for p in net_profits]

        bars = ax2.bar(labels, net_profits, color=bar_colors)
        ax2.set_xlabel("市场")
        ax2.set_ylabel("净盈亏")
        ax2.set_title("各市场净盈亏")
        ax2.axhline(y=0, color="black", linestyle="-", linewidth=0.5)

        # 添加数值标签
        for bar, profit in zip(bars, net_profits):
            height = bar.get_height()
            ax2.annotate(
                f"{profit:,.0f}",
                xy=(bar.get_x() + bar.get_width() / 2, height),
                xytext=(0, 3 if height >= 0 else -12),
                textcoords="offset points",
                ha="center",
                va="bottom" if height >= 0 else "top",
            )

        plt.tight_layout()
        return self._save_or_return(fig, "market_distribution.png")

    def generate_cumulative_profit_line(self, trades: list[MatchedTrade]) -> bytes:
        """生成累计盈亏曲线"""
        # 按卖出日期排序
        sorted_trades = sorted(
            [t for t in trades if t.sell_date],
            key=lambda t: t.sell_date,
        )

        if not sorted_trades:
            return b""

        fig, ax = plt.subplots(figsize=(12, 6))

        dates = [t.sell_date for t in sorted_trades]
        cumulative_profit = []
        running_total = Decimal("0")

        for trade in sorted_trades:
            running_total += trade.profit_loss
            cumulative_profit.append(float(running_total))

        ax.plot(dates, cumulative_profit, color="#2196F3", linewidth=2)
        ax.fill_between(
            dates,
            cumulative_profit,
            0,
            where=[p >= 0 for p in cumulative_profit],
            color="#4CAF50",
            alpha=0.3,
        )
        ax.fill_between(
            dates,
            cumulative_profit,
            0,
            where=[p < 0 for p in cumulative_profit],
            color="#F44336",
            alpha=0.3,
        )

        ax.set_xlabel("日期")
        ax.set_ylabel("累计盈亏")
        ax.set_title("累计盈亏曲线")
        ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
        plt.xticks(rotation=45)
        plt.tight_layout()

        return self._save_or_return(fig, "cumulative_profit_line.png")

    def generate_profit_loss_bucket_bar(self, stats: TradeStatistics) -> bytes:
        """生成盈亏率区间分布柱状图"""
        if not stats.profit_loss_buckets:
            return b""

        fig, ax = plt.subplots(figsize=(12, 6))

        bucket_names = [b.bucket_name for b in stats.profit_loss_buckets]
        counts = [b.count for b in stats.profit_loss_buckets]

        # 根据是盈利还是亏损区间设置颜色
        colors = []
        for bucket in stats.profit_loss_buckets:
            if bucket.max_ratio <= 0:
                colors.append("#F44336")  # 亏损区间 - 红色
            elif bucket.min_ratio >= 0:
                colors.append("#4CAF50")  # 盈利区间 - 绿色
            else:
                colors.append("#9E9E9E")  # 跨零区间 - 灰色

        bars = ax.bar(bucket_names, counts, color=colors)

        # 添加数值标签
        for bar, count in zip(bars, counts):
            if count > 0:
                height = bar.get_height()
                ax.annotate(
                    f"{count}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=9,
                )

        ax.set_xlabel("盈亏率区间")
        ax.set_ylabel("交易笔数")
        ax.set_title("盈亏率区间分布")
        plt.xticks(rotation=45)
        plt.tight_layout()

        return self._save_or_return(fig, "profit_loss_bucket_bar.png")

    def generate_all_charts(
        self, trades: list[MatchedTrade], stats: TradeStatistics
    ) -> dict[str, bytes]:
        """
        生成所有图表

        Returns:
            字典，键为图表名称，值为 PNG 字节数据
        """
        charts = {}

        charts["win_loss_pie"] = self.generate_win_loss_pie(stats)
        charts["monthly_profit_bar"] = self.generate_monthly_profit_bar(stats)
        charts["holding_days_hist"] = self.generate_holding_days_hist(trades)
        charts["profit_loss_ratio_hist"] = self.generate_profit_loss_ratio_hist(trades)
        charts["market_distribution"] = self.generate_market_distribution_pie(stats)
        charts["cumulative_profit_line"] = self.generate_cumulative_profit_line(trades)
        charts["profit_loss_bucket_bar"] = self.generate_profit_loss_bucket_bar(stats)

        # 过滤掉空图表
        return {k: v for k, v in charts.items() if v}
