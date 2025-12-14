# 报告生成器

## 能力描述
整合持仓分析和技术分析，生成完整的投资分析报告。

## 报告类型
1. 每日简报
   - 持仓变动
   - 重点关注股票
   - 当日操作建议

2. 周度报告
   - 本周盈亏回顾
   - 技术面变化
   - 下周计划

3. 个股深度报告
   - 基本面概览
   - 技术面详解
   - 买卖点位建议

## 数据来源
- 数据库表: positions, klines, trades
- 图表: charts/output/
- 调用: python main.py report --user {user} --type {type}

## 输出格式
- Markdown 文档
- 嵌入图表（K线图）
- 数据表格
