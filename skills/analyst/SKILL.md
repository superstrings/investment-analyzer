# Analyst Skill - 技术分析师

> OBV + VCP 双核心技术分析系统

## 概述

Analyst Skill 提供基于 **OBV (能量潮)** 和 **VCP (波动收缩形态)** 的技术分析。遵循"技术指标在精不在多"的原则，专注于量价关系和形态突破两个核心维度。

## 核心指标

### OBV (On-Balance Volume) - 40%权重

能量潮指标，用于分析量价关系：

| 分析维度 | 说明 |
|---------|------|
| **趋势分析** | 判断 OBV 趋势方向和强度 |
| **背离检测** | 识别价格与 OBV 的背离 (看涨/看跌) |
| **确认信号** | 验证成交量是否确认价格走势 |

**OBV 趋势分类:**
- `strong_up`: 强势上升 - 机构资金流入
- `up`: 温和上升 - 积累阶段
- `sideways`: 横盘整理
- `down`: 温和下降 - 派发阶段
- `strong_down`: 强势下降 - 机构资金流出

### VCP (Volatility Contraction Pattern) - 60%权重

Mark Minervini 的波动收缩形态，用于识别突破机会：

| 分析维度 | 说明 |
|---------|------|
| **收缩计数** | 统计收缩次数 (理想 3-5 次) |
| **深度递减** | 验证收缩深度是否递减 (如 25% → 15% → 8%) |
| **成交量萎缩** | 检测整理期间成交量是否减少 |
| **突破点位** | 计算 pivot 价格和距离 |

**VCP 阶段:**
- `no_pattern`: 无 VCP 形态
- `forming`: 形成中 (1-2 次收缩)
- `mature`: 成熟 (3+ 次收缩，接近突破)
- `breakout`: 突破中

## 评分系统

```
综合技术评分 = OBV评分 × 40% + VCP评分 × 60%
```

### 评级标准

| 评分范围 | 评级 | 建议 |
|---------|------|------|
| 80-100 | Strong Buy | VCP成熟 + OBV强势，考虑建仓 |
| 65-79 | Buy | 技术面积极，关注入场时机 |
| 45-64 | Hold | 中性，等待更明确信号 |
| 25-44 | Sell | 技术面走弱，考虑减仓 |
| 0-24 | Strong Sell | 技术面很弱，规避 |

### 加分项

- VCP + 看涨背离: +10分
- VCP成熟 + OBV上升: +8分
- 量价确认 + 成交量萎缩: +5分

### 扣分项

- 看跌背离: -10分
- OBV强势下降: -8分

## 使用方法

### 单股分析

```python
from skills.analyst import StockAnalyzer, generate_analysis_report

# 创建分析器
analyzer = StockAnalyzer()

# 从数据库分析
result = analyzer.analyze_from_db(
    market="HK",
    code="00700",
    days=120,
    stock_name="腾讯控股"
)

# 查看结果
print(f"综合评分: {result.technical_score.final_score:.1f}")
print(f"评级: {result.technical_score.rating.value}")
print(f"建议: {result.recommendation}")

# 生成报告
report = generate_analysis_report(result)
print(report)
```

### 批量扫描

```python
from skills.analyst import BatchAnalyzer, generate_batch_report

# 创建批量分析器
batch = BatchAnalyzer(days=120)

# 分析用户的持仓和关注列表
results = batch.analyze_user_stocks(
    user_id=1,
    include_positions=True,
    include_watchlist=True
)

# 查看 Top 5
for stock in results.top_overall:
    print(f"{stock.market}.{stock.code}: {stock.technical_score.final_score:.0f}")

# 查看 VCP 形态股票
for stock in results.top_vcp:
    print(f"{stock.market}.{stock.code}: VCP {stock.vcp_analysis.stage.value}")

# 生成报告
report = generate_batch_report(results)
print(report)
```

### 分析特定代码列表

```python
from skills.analyst import BatchAnalyzer

batch = BatchAnalyzer()
results = batch.analyze_codes([
    "HK.00700",
    "US.NVDA",
    "US.AAPL",
    "A.600519"
])

# 只看强烈买入
for stock in results.strong_buy:
    print(f"{stock.code}: {stock.summary}")
```

## CLI 命令

```bash
# 单股分析
python main.py skill run -t analyst -u dyson -c HK.00700

# 批量扫描 (持仓 + 关注列表)
python main.py skill run -t analyst -u dyson

# 指定市场
python main.py skill run -t analyst -u dyson -m HK

# 输出为 JSON
python main.py skill run -t analyst -u dyson -c HK.00700 -f json

# 保存到文件
python main.py skill run -t analyst -u dyson -o analysis.md
```

## 输出示例

### 单股分析报告

```markdown
# Technical Analysis: HK.00700 (腾讯控股)

## Summary
- **Rating**: BUY
- **Score**: 72.5/100
- **Confidence**: 75%
- **Current Price**: 380.00
- **Price Change (20d)**: +5.26%

**Summary**: Bullish bias. VCP mature (3 contractions). Accumulation.
**Action**: Watch for VCP breakout entry

## Technical Scores
| Component | Score | Status |
|-----------|-------|--------|
| OBV (40%) | 68.0 | up |
| VCP (60%) | 75.0 | mature |
| Combined | 72.5 | buy |

## VCP Analysis
- **Pattern Detected**: Yes
- **Stage**: mature
- **Contractions**: 3
- **Depth Sequence**: 18.5% -> 12.3% -> 6.8%
- **Pivot Price**: 395.00
- **Distance to Pivot**: 3.9%

## Key Levels
- Pivot/Breakout: 395.00
- Stop Loss (8%): 363.40

## Watch Points
- Watch for break above 395.00
- Volume drying up - watch for volume spike on breakout
```

## 数据类

### StockAnalysis

```python
@dataclass
class StockAnalysis:
    market: str
    code: str
    name: str
    analysis_date: date
    current_price: float
    price_change_pct: float
    obv_analysis: OBVAnalysisResult
    vcp_analysis: VCPAnalysisResult
    technical_score: TechnicalScore
    summary: str
    recommendation: str
    confidence: float
    signals: list[str]
```

### TechnicalScore

```python
@dataclass
class TechnicalScore:
    obv_score: float      # 0-100
    vcp_score: float      # 0-100
    final_score: float    # 加权后 0-100
    rating: TechnicalRating
    signal_strength: SignalStrength
    action: str
    key_levels: list[str]
    watch_points: list[str]
```

## 设计原则

1. **指标在精不在多**: 只用 OBV + VCP，避免信号矛盾
2. **量价结合**: OBV 验证资金流向，VCP 捕捉形态突破
3. **可量化评分**: 统一的 0-100 评分系统
4. **可操作建议**: 提供明确的操作建议和关键价位

## 参考资料

- Mark Minervini: *Trade Like a Stock Market Wizard*
- Joseph Granville: *On-Balance Volume Technique*

---

*最后更新: 2025-12-15*
