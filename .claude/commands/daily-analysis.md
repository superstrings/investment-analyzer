# 每日分析命令

执行每日投资分析工作流（自动识别盘前/盘后）。

## 执行步骤

### 1. 判断当前时段

根据当前时间判断执行盘前还是盘后分析：
- **盘前** (开市前): 数据同步 + 深度分析 + 机会筛选
- **盘后** (收市后): 交易同步 + 持仓复盘 + 风险检查

### 2. 盘前分析流程

```bash
# 1. 同步最新数据
python main.py sync all -u dyson

# 2. 港股深度分析
python main.py deep-analyze -u dyson --market HK --batch

# 3. 美股深度分析
python main.py deep-analyze -u dyson --market US --batch

# 4. A股深度分析 (如有数据)
python main.py deep-analyze -u dyson --market A --batch
```

分析完成后：
- 汇总各市场 Buy 评级股票
- 列出风险预警 (Sell 评级)
- 给出当日操作建议

### 3. 盘后分析流程

```bash
# 1. 同步交易记录
python main.py sync trades -u dyson

# 2. 同步最新K线
python main.py sync klines -u dyson

# 3. 查看持仓状态
python main.py account info -u dyson
```

分析完成后：
- 检查今日交易执行情况
- 更新持仓盈亏状态
- 检查止损触发情况
- 总结当日操作得失

### 4. 输出分析报告

汇总所有分析结果，输出结构化报告。

## 输出格式

```
## 每日分析报告 - [日期]

### 时段: [盘前/盘后]

### 数据同步
- 持仓: [X] 条
- 交易: [X] 条
- K线: [X] 只股票

### 市场分析

#### 港股
- Buy: [股票列表]
- 风险: [股票列表]

#### 美股
- Buy: [股票列表]
- 风险: [股票列表]

### 持仓状态
| 股票 | 盈亏 | 评级 | 建议 |
|------|------|------|------|

### 今日操作建议
1. [建议1]
2. [建议2]
```

## 注意事项

- 盘前分析建议在开市前 30 分钟完成
- 盘后分析建议在收市后 1 小时内完成
- 周末执行时默认为盘后模式
