"""
Trade Analyzer - 主控制器

协调各组件完成交易记录分析：
1. 从数据库获取交易记录
2. 使用 TradeMatcher 配对买卖
3. 使用 StatisticsCalculator 计算统计
4. 使用 ChartGenerator 生成图表
5. 使用 ExcelExporter/DocxExporter 导出报告
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from db import Account, Trade, User, get_session

from .chart_generator import ChartGenerator
from .docx_exporter import DocxExporter
from .excel_exporter import ExcelExporter
from .statistics import StatisticsCalculator, TradeStatistics
from .trade_matcher import MatchedTrade, TradeMatcher

logger = logging.getLogger(__name__)


@dataclass
class AnalysisResult:
    """分析结果"""

    # 基本信息
    user_id: int
    start_date: date
    end_date: date
    year: int

    # 交易数据
    total_raw_trades: int  # 原始交易记录数
    matched_trades: list[MatchedTrade]  # 配对后的交易
    stock_trades: list[MatchedTrade]  # 股票交易
    option_trades: list[MatchedTrade]  # 期权交易

    # 统计数据
    statistics: TradeStatistics

    # 输出文件
    excel_path: Optional[Path] = None
    docx_path: Optional[Path] = None

    # 图表数据
    charts: dict[str, bytes] = None

    def __post_init__(self):
        if self.charts is None:
            self.charts = {}


class TradeAnalyzer:
    """
    交易分析器主控制器

    Usage:
        analyzer = TradeAnalyzer()
        result = analyzer.analyze(
            user_id=1,
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            output_dir=Path("output"),
        )
    """

    def __init__(self, session: Optional[Session] = None):
        """
        初始化分析器

        Args:
            session: 可选的数据库会话，如果不提供则自动创建
        """
        self._external_session = session
        self.matcher = TradeMatcher()
        self.calculator = StatisticsCalculator()

    def analyze(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: Optional[int] = None,
        output_dir: Optional[Path] = None,
        generate_excel: bool = True,
        generate_docx: bool = True,
        generate_charts: bool = True,
    ) -> AnalysisResult:
        """
        执行交易分析

        Args:
            user_id: 用户 ID
            start_date: 开始日期
            end_date: 结束日期
            days: 最近 N 天（与 start_date/end_date 二选一）
            output_dir: 输出目录
            generate_excel: 是否生成 Excel
            generate_docx: 是否生成 Word
            generate_charts: 是否生成图表

        Returns:
            AnalysisResult 分析结果
        """
        # 确定日期范围
        if days:
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
        elif not start_date or not end_date:
            # 默认当年
            today = date.today()
            start_date = date(today.year, 1, 1)
            end_date = today

        year = end_date.year

        logger.info(
            f"开始分析 user_id={user_id} 的交易记录 ({start_date} ~ {end_date})"
        )

        # 获取交易记录
        trades = self._fetch_trades(user_id, start_date, end_date)
        logger.info(f"获取到 {len(trades)} 条原始交易记录")

        if not trades:
            logger.warning("没有找到交易记录")
            return AnalysisResult(
                user_id=user_id,
                start_date=start_date,
                end_date=end_date,
                year=year,
                total_raw_trades=0,
                matched_trades=[],
                stock_trades=[],
                option_trades=[],
                statistics=TradeStatistics(),
            )

        # 配对交易
        matched_trades = self.matcher.match_trades(trades)
        stock_trades = self.matcher.get_stock_trades()
        option_trades = self.matcher.get_option_trades()

        logger.info(
            f"配对完成: {len(matched_trades)} 笔交易 "
            f"(股票: {len(stock_trades)}, 期权: {len(option_trades)})"
        )

        # 计算统计
        statistics = self.calculator.calculate(matched_trades)
        logger.info(
            f"统计完成: 胜率={statistics.win_rate:.1%}, "
            f"净利润={float(statistics.net_profit):,.2f}"
        )

        # 创建结果对象
        result = AnalysisResult(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            year=year,
            total_raw_trades=len(trades),
            matched_trades=matched_trades,
            stock_trades=stock_trades,
            option_trades=option_trades,
            statistics=statistics,
        )

        # 生成图表
        if generate_charts:
            chart_gen = ChartGenerator(output_dir=output_dir)
            result.charts = chart_gen.generate_all_charts(stock_trades, statistics)
            logger.info(f"生成了 {len(result.charts)} 张图表")

        # 导出文件
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            if generate_excel:
                excel_path = output_dir / f"{year}年美港股交易记录.xlsx"
                exporter = ExcelExporter()
                exporter.export(matched_trades, statistics, excel_path, year)
                result.excel_path = excel_path
                logger.info(f"Excel 已导出: {excel_path}")

            if generate_docx:
                docx_path = output_dir / f"{year}年美港股交易分析报告.docx"
                exporter = DocxExporter()
                exporter.export(
                    matched_trades, statistics, result.charts, docx_path, year
                )
                result.docx_path = docx_path
                logger.info(f"Word 报告已导出: {docx_path}")

        return result

    def _fetch_trades(
        self, user_id: int, start_date: date, end_date: date
    ) -> list[Trade]:
        """
        从数据库获取交易记录

        Args:
            user_id: 用户 ID
            start_date: 开始日期
            end_date: 结束日期

        Returns:
            交易记录列表
        """
        if self._external_session:
            return self._query_trades(
                self._external_session, user_id, start_date, end_date
            )

        with get_session() as session:
            return self._query_trades(session, user_id, start_date, end_date)

    def _query_trades(
        self, session: Session, user_id: int, start_date: date, end_date: date
    ) -> list[Trade]:
        """执行查询"""
        # 将 date 转换为 datetime 进行比较
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())

        # 获取用户的所有账户
        accounts = session.query(Account).filter(Account.user_id == user_id).all()
        account_ids = [acc.id for acc in accounts]

        if not account_ids:
            logger.warning(f"用户 {user_id} 没有关联的交易账户")
            return []

        # 查询交易记录
        trades = (
            session.query(Trade)
            .filter(
                and_(
                    Trade.account_id.in_(account_ids),
                    Trade.trade_time >= start_dt,
                    Trade.trade_time <= end_dt,
                )
            )
            .order_by(Trade.trade_time)
            .all()
        )

        # 分离查询结果（避免 session 关闭后无法访问）
        return list(trades)

    def analyze_by_username(
        self,
        username: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: Optional[int] = None,
        output_dir: Optional[Path] = None,
        **kwargs,
    ) -> AnalysisResult:
        """
        通过用户名分析交易

        Args:
            username: 用户名
            其他参数同 analyze()

        Returns:
            AnalysisResult
        """
        with get_session() as session:
            user = session.query(User).filter(User.username == username).first()
            if not user:
                raise ValueError(f"用户 '{username}' 不存在")

            return self.analyze(
                user_id=user.id,
                start_date=start_date,
                end_date=end_date,
                days=days,
                output_dir=output_dir,
                **kwargs,
            )

    def get_summary(self, result: AnalysisResult) -> str:
        """
        获取分析结果摘要（用于 CLI 输出）

        Args:
            result: 分析结果

        Returns:
            格式化的摘要字符串
        """
        stats = result.statistics

        lines = [
            f"=== {result.year}年交易分析摘要 ===",
            f"分析期间: {result.start_date} ~ {result.end_date}",
            f"原始交易记录: {result.total_raw_trades} 条",
            f"配对交易笔数: {len(result.matched_trades)} 笔",
            f"  - 股票交易: {len(result.stock_trades)} 笔",
            f"  - 期权交易: {len(result.option_trades)} 笔",
            "",
            "--- 股票交易统计 ---",
            f"胜率: {stats.win_rate:.1%} ({stats.winning_trades}盈/{stats.losing_trades}亏)",
            f"盈亏比: {float(stats.profit_loss_ratio):.2f}",
            f"净利润: {float(stats.net_profit):,.2f}",
            f"  - 总盈利: +{float(stats.total_profit):,.2f}",
            f"  - 总亏损: -{float(stats.total_loss):,.2f}",
            f"平均持仓: {stats.avg_holding_days:.1f} 天",
        ]

        if stats.option_total_trades > 0:
            lines.extend(
                [
                    "",
                    "--- 期权交易统计 ---",
                    f"期权交易: {stats.option_total_trades} 笔",
                    f"期权胜率: {stats.option_win_rate:.1%}",
                    f"期权净盈亏: {float(stats.option_net_profit):,.2f}",
                ]
            )

        if result.excel_path or result.docx_path:
            lines.extend(["", "--- 输出文件 ---"])
            if result.excel_path:
                lines.append(f"Excel: {result.excel_path}")
            if result.docx_path:
                lines.append(f"Word: {result.docx_path}")

        return "\n".join(lines)
