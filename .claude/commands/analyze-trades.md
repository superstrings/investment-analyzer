---
description: 分析交易记录并生成统计报告（含 AI 智能建议）
arguments:
  - name: start_date
    description: 开始日期 (YYYY-MM-DD)，可选
  - name: end_date
    description: 结束日期 (YYYY-MM-DD)，可选
---

# 交易记录分析

分析用户 dyson 的交易记录，生成 Excel 统计表和 Word 分析报告。

**报告包含基于投资框架 V10.10 的智能建议**，由内置的"投资教练"模块自动生成。

## 执行步骤

### 运行交易分析

```bash
source .venv/bin/activate && PYTHONPATH=. python main.py trade-analyze -u dyson {{#if start_date}}--start {{start_date}}{{/if}} {{#if end_date}}--end {{end_date}}{{/if}}
```

这会生成：
- `output/{year}年美港股交易记录.xlsx` - Excel 统计表
- `output/{year}年美港股交易分析报告.docx` - Word 报告（含 AI 智能建议）

## Word 报告内容

报告包含以下章节：

1. **整体交易表现** - 胜率、盈亏比等核心指标
2. **盈亏统计** - 总盈利、总亏损、净利润
3. **持仓时间分析** - 平均持仓天数、盈亏交易持仓对比
4. **市场分布分析** - 港股/美股/A股表现
5. **最佳交易 Top 5** - 盈利最多的交易
6. **最大亏损 Top 5** - 亏损最多的交易
7. **交易标的统计 Top 10** - 交易频次最高的标的
8. **盈亏率分布** - 盈亏幅度分布直方图
9. **月度盈亏趋势** - 月度盈亏柱状图
10. **期权交易统计** - 期权交易专项统计
11. **结论与建议** - **基于 V10.10 框架的智能建议**

## AI 智能建议内容

投资教练模块基于投资分析框架 V10.10 生成专业建议：

- **⚠️ 风险警示** - 高优先级风险提醒
- **✅ 优势** - 交易策略的优点
- **❌ 需改进** - 发现的问题及原因
- **💡 改进建议** - 具体可操作的建议
- **📋 框架核心原则** - V10.10 框架的核心规则

### 框架核心原则

1. 止损优先：股票 -10% 止损，期权 OCO 订单（+30%/-30%）
2. 估值先行：Forward PE + PB-ROE 双重筛选
3. 周期顺势：牛市满仓成长，熊市只做低估值
4. 量价确认：不追涨，等60分钟量价转换确认后入场
5. 完整计划：没有操作计划的交易 = 赌博

## 使用示例

```
/analyze-trades 2025-01-01 2025-12-31   # 指定日期范围
/analyze-trades 2025-06-01              # 从指定日期到今天
/analyze-trades                         # 当年全部交易
```

## 相关文件

- 投资框架: `~/Documents/trade/prompt/daily-analysis-prompt-v10_10.md`
- 投资教练模块: `skills/trade_analyzer/recommendation.py`
- 港股期权乘数: `config/hk_option_multipliers.py`
