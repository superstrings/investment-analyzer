---
description: 分析交易记录并生成统计报告（含 AI 智能建议）
arguments:
  - name: start_date
    description: 开始日期 (YYYY-MM-DD)，可选
  - name: end_date
    description: 结束日期 (YYYY-MM-DD)，可选
---

# 交易记录分析

分析用户 dyson 的交易记录，生成 Excel 统计表和 Word 分析报告，并由投资教练(LLM)生成智能建议。

## 执行步骤

### 第一步：运行 Python 分析并输出上下文

```bash
source .venv/bin/activate && PYTHONPATH=. python main.py trade-analyze -u dyson {{#if start_date}}--start {{start_date}}{{/if}} {{#if end_date}}--end {{end_date}}{{/if}} --output-context
```

这会生成：
- `output/{year}年美港股交易记录.xlsx` - Excel 统计表
- `output/{year}年美港股交易分析报告.docx` - Word 报告
- `output/{year}年交易分析上下文.md` - AI 分析用的上下文数据

### 第二步：调用投资教练生成建议

读取上下文文件，扮演投资教练角色生成专业建议。

**投资教练角色定位**：
- 目标：帮助用户提高投资能力，获得复利增长
- 风格：严格但关心学生的投资导师，直言不讳
- 依据：投资框架 V10.10 + 具体交易数据

**分析维度**：
1. 止损纪律评估（盈亏比、大幅亏损）
2. 持仓习惯分析（盈利vs亏损持仓时间）
3. 期权使用评估（胜率、仓位）
4. 市场偏好分析（不同市场表现）
5. 交易频率分析（过度交易）

**输出格式**：

```markdown
# 投资教练点评

## 📊 数据概览
[关键指标]

## ⚠️ 核心问题（直言不讳）
[最严重的1-3个问题，附数据证据]

## ✅ 做得好的地方
[值得保持的优点]

## 💡 具体改进建议
### 1. [最重要的改进]
- 问题：...
- 数据：...
- 行动：...
- 框架参考：V10.10 ...

## 🎯 下一步行动清单
□ [具体行动项]

## 📖 教练寄语
[鼓励性的话，但保持严格要求]
```

### 第三步：更新报告的"结论与建议"章节

将生成的建议更新到 Word 报告的"结论与建议"章节。

使用脚本：
```bash
source .venv/bin/activate && python scripts/update_docx_conclusion.py output/{year}年美港股交易分析报告.docx /tmp/coach.md
```

或从标准输入：
```bash
echo "<LLM生成的建议>" | python scripts/update_docx_conclusion.py output/{year}年美港股交易分析报告.docx
```

## 框架核心原则 (V10.10)

| 决策优先级 | 说明 |
|-----------|------|
| 1. 杠杆红线 | >2.0x强制减仓，>1.8x停止加仓 |
| 2. 止损规则 | 股票-10%，期权OCO ±30% |
| 3. 市场周期 | 决定仓位上限 |
| 4. 基本面估值 | Forward PE + PB-ROE |
| 5. 日K技术评分 | OBV + VCP |
| 6. 60分钟量价转换 | 入场时机 |
| 7. 完整操作计划 | 无计划不执行 |

## 使用示例

```
/analyze-trades 2025-01-01 2025-12-31   # 指定日期范围
/analyze-trades 2025-06-01              # 从指定日期到今天
/analyze-trades                         # 当年全部交易
```

## 相关命令

- `/investment-coach` - 单独调用投资教练进行对话式指导
