# Trade Analyzer Skill

交易记录统计分析技能，用于分析历史交易表现并生成报告。

## 功能

- **买卖配对**：使用 LIFO 算法将买入和卖出记录配对成完整交易
- **统计分析**：计算胜率、盈亏比、持仓时间等关键指标
- **图表生成**：生成盈亏分布图、月度趋势图等可视化图表
- **报告导出**：生成 Excel 统计表和 Word 分析报告

## 使用方法

### CLI 命令

```bash
# 分析指定日期范围的交易
python main.py trade-analyze -u dyson --start 2025-01-01 --end 2025-12-31

# 分析最近 N 天的交易
python main.py trade-analyze -u dyson --days 90

# 指定输出目录
python main.py trade-analyze -u dyson --output /path/to/output
```

### Slash Command

```
/analyze-trades [start_date] [end_date]
```

## 输出文件

1. **Excel 文件**：`{year}年美港股交易记录.xlsx`
   - Sheet 1: 股票交易明细
   - Sheet 2: 期权交易明细
   - Sheet 3: 统计汇总

2. **Word 文件**：`{year}年美港股交易分析报告.docx`
   - 整体交易表现
   - 盈亏统计
   - 持仓时间分析
   - 市场分布分析
   - 最佳/最差交易
   - 结论与建议

## 配对算法

使用 **LIFO（后进先出）** 配对算法：
- 最近买入的股票先卖出
- 支持部分成交、多次加仓
- 股票与期权分开配对统计

## 依赖

- openpyxl: Excel 导出
- python-docx: Word 导出
- matplotlib: 图表生成
