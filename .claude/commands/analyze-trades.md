---
description: 分析交易记录并生成统计报告
arguments:
  - name: start_date
    description: 开始日期 (YYYY-MM-DD)，可选
  - name: end_date
    description: 结束日期 (YYYY-MM-DD)，可选
---

# 交易记录分析

分析用户 dyson 的交易记录，生成 Excel 统计表和 Word 分析报告。

## 参数说明

- `start_date`: 开始日期，格式 YYYY-MM-DD，不指定则为当年 1 月 1 日
- `end_date`: 结束日期，格式 YYYY-MM-DD，不指定则为今天

## 执行命令

```bash
# 如果指定了日期范围
python main.py trade-analyze -u dyson {{#if start_date}}--start {{start_date}}{{/if}} {{#if end_date}}--end {{end_date}}{{/if}}

# 默认分析当年
python main.py trade-analyze -u dyson
```

## 输出文件

分析完成后会在 `output/` 目录生成：

1. **Excel 文件**: `{year}年美港股交易记录.xlsx`
   - 股票交易明细（配对后的完整交易）
   - 期权交易明细（单独统计）
   - 统计汇总

2. **Word 报告**: `{year}年美港股交易分析报告.docx`
   - 整体交易表现
   - 盈亏统计
   - 持仓时间分析
   - 市场分布
   - 最佳/最差交易
   - 结论与建议

## 分析内容

- **胜率**: 盈利交易占总交易的比例
- **盈亏比**: 平均盈利 / 平均亏损
- **持仓分析**: 平均持仓天数，盈利/亏损交易的持仓差异
- **市场分布**: 港股/美股/A股的交易表现对比
- **标的统计**: 交易频次最高的股票

## 使用示例

```
/analyze-trades 2025-01-01 2025-12-31
/analyze-trades 2025-06-01
/analyze-trades
```
