# 报告生成器 (Report Generator)

## 能力描述
整合持仓分析和技术分析，生成完整的投资分析报告，支持多种报告类型和输出格式。

## 数据来源
- 数据库表: `positions`, `klines`, `trades`, `account_snapshots`
- Python 模块: `analysis.portfolio`, `analysis.indicators`, `charts`
- 图表输出: `charts/output/`
- 报告输出: `reports/output/`

## 报告类型

### 1. 持仓报告 (Portfolio Report)
分析当前持仓状况，包含组合分析和风险评估。

```python
from analysis import analyze_positions_from_db
from db import get_session, Position, Account, AccountSnapshot

with get_session() as session:
    positions = session.query(Position).join(Account).filter(Account.user_id == user_id).all()
    snapshot = session.query(AccountSnapshot).order_by(AccountSnapshot.snapshot_date.desc()).first()

result = analyze_positions_from_db(positions, snapshot)

# 生成报告内容
report = f"""
# 投资组合报告
生成时间: {result.analysis_date}

## 组合概览
- 持仓数量: {result.summary.position_count}
- 总市值: ${result.summary.total_market_value:,.2f}
- 总盈亏: ${result.summary.total_pl_value:,.2f} ({result.summary.total_pl_ratio:.1f}%)
- 胜率: {result.summary.win_rate:.1f}%

## 市场配比
{market_allocation_table}

## 持仓明细
{positions_table}

## 风险评估
- 集中度风险: {result.risk_metrics.concentration_risk.value}
- HHI指数: {result.risk_metrics.hhi_index:.0f}
- 最大亏损持仓: {result.risk_metrics.largest_loss_position}

## 信号提醒
{signals_list}
"""
```

### 2. 技术分析报告 (Technical Report)
对指定股票进行全面技术分析。

```python
from fetchers import KlineFetcher
from analysis.indicators import RSI, MACD, BollingerBands, detect_vcp
from charts import ChartGenerator, ChartConfig

# 获取数据
fetcher = KlineFetcher()
df = fetcher.fetch(code, days=120).df

# 计算指标
rsi = RSI(14).calculate(df).values.iloc[-1]
macd_result = MACD().calculate(df).values
vcp = detect_vcp(df)

# 生成图表
generator = ChartGenerator(style="dark")
config = ChartConfig(ma_periods=[5, 10, 20, 60], show_volume=True)
chart_path = generator.generate(df, title=code, output_path=f"charts/output/{code}.png", config=config)

report = f"""
# {code} 技术分析报告

## K线图
![K线图]({chart_path})

## 技术指标
- RSI(14): {rsi:.1f}
- MACD: {macd_result['macd'].iloc[-1]:.2f}
- MACD信号: {macd_result['signal'].iloc[-1]:.2f}

## VCP形态分析
- 状态: {"检测到VCP" if vcp.is_vcp else "未检测到VCP"}
- 得分: {vcp.score:.1f}
- 收缩次数: {vcp.contraction_count}
"""
```

### 3. 每日简报 (Daily Brief)
快速概览当日重要信息。

```python
report = f"""
# 每日投资简报 - {date.today()}

## 持仓变动
- 今日买入: {buy_count} 笔
- 今日卖出: {sell_count} 笔
- 净买入金额: ${net_buy:,.2f}

## 持仓盈亏
- 今日盈亏: ${today_pl:,.2f}
- 累计盈亏: ${total_pl:,.2f}

## 重点关注
{watchlist_alerts}

## 技术信号
- VCP形态: {vcp_stocks}
- MACD金叉: {macd_golden}
- RSI超卖: {rsi_oversold}
"""
```

### 4. 周度回顾 (Weekly Review)
回顾本周交易和表现。

```python
report = f"""
# 周度投资回顾
{week_start} - {week_end}

## 本周交易汇总
- 总交易笔数: {trade_count}
- 买入金额: ${buy_amount:,.2f}
- 卖出金额: ${sell_amount:,.2f}

## 本周盈亏
- 实现盈亏: ${realized_pl:,.2f}
- 浮动盈亏变化: ${unrealized_change:,.2f}

## 持仓变化
{position_changes_table}

## 下周计划
- 关注突破: {breakout_candidates}
- 止盈目标: {profit_targets}
- 止损预警: {stop_loss_alerts}
"""
```

## 使用方法

### CLI 命令

```bash
# 生成持仓报告
python main.py report portfolio --user dyson

# 生成技术分析报告
python main.py report technical --user dyson --codes "HK.00700,US.NVDA"

# 生成每日简报 (未来功能)
python main.py report daily --user dyson

# 生成周度回顾 (未来功能)
python main.py report weekly --user dyson
```

### Python API

```python
from reports import ReportGenerator, ReportConfig, ReportType

generator = ReportGenerator()
config = ReportConfig(
    report_type=ReportType.PORTFOLIO,
    user_id=1,
    include_charts=True,
    output_format="markdown",
)

report = generator.generate(config)
report.save("reports/output/portfolio_2024-12-14.md")
```

## 输出格式

### Markdown (推荐)
- 支持嵌入图表
- GitHub 兼容
- 易于阅读

### JSON
- 结构化数据
- API 集成友好

### HTML
- 丰富的样式
- 可直接浏览

## 报告模板

### 持仓明细表模板
```markdown
| 股票代码 | 名称 | 市场 | 数量 | 成本价 | 现价 | 市值 | 盈亏 | 盈亏% | 权重 |
|----------|------|------|------|--------|------|------|------|-------|------|
| 00700 | 腾讯 | HK | 100 | 350.00 | 380.00 | 38,000 | 3,000 | 8.6% | 44.2% |
```

### 技术指标表模板
```markdown
| 指标 | 当前值 | 信号 | 建议 |
|------|--------|------|------|
| RSI(14) | 58.3 | 中性 | 持有 |
| MACD | 2.35 | 多头 | 看涨 |
| 布林带 | 中轨上方 | 正常 | - |
| VCP | 78.5分 | 接近突破 | 关注 |
```

### 风险评估表模板
```markdown
| 风险类型 | 状态 | 说明 | 建议 |
|----------|------|------|------|
| 集中度风险 | 高 | 最大持仓44.2% | 考虑分散 |
| 流动性风险 | 低 | 主板大盘股 | - |
| 波动风险 | 中 | ATR 8.5% | 注意仓位 |
```

## 图表集成

报告可以嵌入以下图表:
1. **K线图**: 包含均线、成交量
2. **仓位配比饼图**: 市场/行业分布
3. **盈亏柱状图**: 各持仓盈亏对比
4. **收益曲线**: 历史净值走势

```python
from charts import ChartGenerator, ChartConfig
from services import ChartService

# 生成持仓股票图表
chart_service = ChartService()
result = chart_service.generate_position_charts(user_id=1)
print(f"生成了 {result.charts_generated} 张图表")

# 图表路径可嵌入报告
for chart_path in result.generated_files:
    print(f"![图表]({chart_path})")
```

## 最佳实践

1. **定期生成**: 每日收盘后生成简报
2. **版本管理**: 报告存档便于回顾
3. **图表配合**: 图表比数据更直观
4. **信号优先**: 突出重要信号和风险
5. **简洁明了**: 避免信息过载
