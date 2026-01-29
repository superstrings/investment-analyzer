"""
Trade Analyzer - 交易记录分析模块

提供交易记录的统计分析功能：
- 买卖配对 (LIFO)
- 统计计算 (胜率、盈亏比、持仓时间等)
- 图表生成 (matplotlib)
- Excel 导出 (openpyxl)
- Word 报告 (python-docx)
"""

from .trade_analyzer import TradeAnalyzer
from .trade_matcher import MatchedTrade, TradeMatcher
from .statistics import TradeStatistics, StatisticsCalculator
from .chart_generator import ChartGenerator
from .excel_exporter import ExcelExporter
from .docx_exporter import DocxExporter

__all__ = [
    "TradeAnalyzer",
    "TradeMatcher",
    "MatchedTrade",
    "TradeStatistics",
    "StatisticsCalculator",
    "ChartGenerator",
    "ExcelExporter",
    "DocxExporter",
]
