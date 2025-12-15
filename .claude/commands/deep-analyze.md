# 深度分析命令

对指定市场或股票进行全面深度分析。

## 参数

$ARGUMENTS - 市场代码 (HK/US/A) 或股票代码 (如 HK.00700)

## 执行步骤

### 1. 解析参数

判断参数类型：
- `HK` / `US` / `A` - 批量分析该市场
- `HK.00700` 格式 - 单只股票分析
- 无参数 - 分析所有市场

### 2. 执行分析

#### 单只股票分析

```bash
python main.py deep-analyze -u dyson -c $ARGUMENTS
```

#### 市场批量分析

```bash
# 港股
python main.py deep-analyze -u dyson -m HK --save

# 美股
python main.py deep-analyze -u dyson -m US --save

# A股
python main.py deep-analyze -u dyson -m A --save
```

#### 全市场分析

```bash
python main.py deep-analyze -u dyson -m HK -s
python main.py deep-analyze -u dyson -m US -s
python main.py deep-analyze -u dyson -m A -s
```

### 3. 读取并展示报告

分析完成后，读取生成的报告文件并展示关键信息：

```bash
# 报告位置
ls reports/output/deep_analysis_*.md
```

### 4. 汇总分析结果

输出结构化的分析汇总：
- 各评级股票数量分布
- Buy 评级股票列表（推荐关注）
- Sell 评级股票列表（风险警示）
- 持仓股票的评级和建议

## 分析维度

| 维度 | 权重 | 内容 |
|------|------|------|
| 技术分析 | 40% | OBV趋势、VCP形态 |
| 基本面 | 30% | PE/PB、市值、52周区间 |
| 行业分析 | 20% | 行业趋势、政策影响 |
| 消息面 | 10% | 近期新闻、市场情绪 |

## 评分标准

| 分数 | 评级 | 建议 |
|------|------|------|
| 60+ | Buy | 可考虑买入 |
| 40-59 | Hold | 持有观望 |
| < 40 | Sell | 建议卖出 |

## 输出格式

```
## 深度分析报告 - [市场/股票]

### 分析概览
- 分析股票数: [X] 只
- Buy: [X] 只 | Hold: [X] 只 | Sell: [X] 只

### 推荐关注 (Buy)
| 排名 | 代码 | 名称 | 评分 | 亮点 |
|------|------|------|------|------|

### 风险警示 (Sell)
| 代码 | 名称 | 评分 | 风险点 |
|------|------|------|--------|

### 持仓股票状态
| 代码 | 名称 | 评分 | 盈亏 | 建议 |
|------|------|------|------|------|

### 详细报告
报告已保存至: reports/output/deep_analysis_[market]_[date].md
```
