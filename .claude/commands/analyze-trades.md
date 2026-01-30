---
description: 分析交易记录并生成统计报告（含 AI 智能建议）
arguments:
  - name: start_date
    description: 开始日期 (YYYY-MM-DD)，可选
  - name: end_date
    description: 结束日期 (YYYY-MM-DD)，可选
---

# 交易记录分析

分析用户 dyson 的交易记录，生成 Excel 统计表和 Word 分析报告，并由 AI 生成智能建议。

## 执行步骤

### 第一步：运行 Python 分析

```bash
source .venv/bin/activate && PYTHONPATH=. python main.py trade-analyze -u dyson {{#if start_date}}--start {{start_date}}{{/if}} {{#if end_date}}--end {{end_date}}{{/if}} --output-context
```

这会生成：
- `output/{year}年美港股交易记录.xlsx` - Excel 统计表
- `output/{year}年美港股交易分析报告.docx` - Word 报告
- `output/{year}年交易分析上下文.md` - AI 分析用的上下文数据

### 第二步：生成 AI 建议

读取 `output/{year}年交易分析上下文.md` 文件，基于数据生成专业的投资建议。

建议应包含以下部分：
1. **核心问题诊断** - 基于胜率、盈亏比、持仓时间等数据识别主要问题
2. **具体改进措施** - 针对问题给出可操作的建议
3. **风险提示** - 基于交易特征的风险警示
4. **下一步行动** - 具体的行动计划

### 第三步：追加 AI 建议到报告

将生成的建议保存为临时文件，然后追加到 Word 报告：

```bash
source .venv/bin/activate && PYTHONPATH=. python scripts/append_ai_recommendations.py "output/{year}年美港股交易分析报告.docx" /tmp/ai_recommendations.md
```

## 输出文件

1. **Excel 文件**: `{year}年美港股交易记录.xlsx`
2. **Word 报告**: `{year}年美港股交易分析报告.docx`（含 AI 智能建议）

## 使用示例

```
/analyze-trades 2025-01-01 2025-12-31
/analyze-trades 2025-06-01
/analyze-trades
```
