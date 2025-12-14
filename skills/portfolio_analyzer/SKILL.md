# 投资组合分析师 (Portfolio Analyzer)

## 能力描述
分析用户的投资组合，评估仓位配置、风险暴露、盈亏状况，生成详细的组合分析报告。

## 数据来源
- 数据库表: `positions`, `accounts`, `account_snapshots`
- Python 模块: `analysis.portfolio`

## 使用方法

### 方法 1: Python API (推荐)

```python
from analysis import (
    PortfolioAnalyzer,
    PositionData,
    AccountData,
    analyze_portfolio,
    analyze_positions_from_db,
)
from db import get_session, Position, Account, AccountSnapshot

# 从数据库获取持仓
with get_session() as session:
    positions = (
        session.query(Position)
        .join(Account)
        .filter(Account.user_id == user_id)
        .all()
    )
    snapshot = (
        session.query(AccountSnapshot)
        .filter(AccountSnapshot.account_id == account_id)
        .order_by(AccountSnapshot.snapshot_date.desc())
        .first()
    )

# 分析组合
result = analyze_positions_from_db(positions, snapshot)

# 查看摘要
print(f"持仓数量: {result.summary.position_count}")
print(f"总市值: {result.summary.total_market_value:,.2f}")
print(f"总盈亏: {result.summary.total_pl_value:,.2f}")
print(f"胜率: {result.summary.win_rate:.1f}%")

# 查看市场配比
for alloc in result.market_allocation:
    print(f"{alloc.market}: {alloc.weight:.1f}% (P&L: {alloc.pl_value:,.2f})")

# 查看风险指标
print(f"集中度风险: {result.risk_metrics.concentration_risk.value}")
print(f"HHI指数: {result.risk_metrics.hhi_index:.0f}")
print(f"分散化得分: {result.risk_metrics.diversification_score:.1f}")

# 查看信号
for signal in result.signals:
    print(f"⚠️ {signal}")
```

### 方法 2: CLI 命令

```bash
# 查看持仓概览
python main.py account info --user dyson

# 生成组合报告
python main.py report portfolio --user dyson
```

## 分析维度

### 1. 仓位分析
- **市场配比**: 港股/美股/A股分布
- **个股权重**: 每只股票占组合比例
- **集中度**: 前5大持仓占比
- **现金比例**: 现金在总资产中的比例

### 2. 盈亏分析
- **总体盈亏**: 总P&L金额和比例
- **持仓盈亏排名**: Top/Bottom performers
- **胜率**: 盈利持仓占比
- **盈亏贡献度**: 各持仓对总盈亏的贡献

### 3. 风险评估
- **集中度风险** (RiskLevel: LOW/MEDIUM/HIGH/VERY_HIGH)
  - 单一持仓 > 20%: HIGH
  - 单一持仓 > 30%: VERY_HIGH
- **HHI指数**: 赫芬达尔-赫希曼指数 (0-10000)
  - < 1500: 分散
  - 1500-2500: 中等集中
  - > 2500: 高度集中
- **分散化得分**: 0-100 (越高越分散)
- **最大亏损持仓**: 跟踪最大亏损

## 输出数据结构

```python
@dataclass
class PortfolioAnalysisResult:
    analysis_date: date
    summary: PortfolioSummary
    positions: list[PositionMetrics]
    market_allocation: list[MarketAllocation]
    risk_metrics: RiskMetrics
    top_performers: list[PositionMetrics]
    bottom_performers: list[PositionMetrics]
    signals: list[str]
```

## 风险信号示例
- "High concentration risk: largest position is 44.2%"
- "Portfolio is highly concentrated (HHI: 3607)"
- "Low diversification: fewer than 5 positions"
- "Top 5 positions represent 100.0% of portfolio"
- "Large loss position: HK.09988 (-27.3%)"

## 建议输出格式

### 持仓明细表
| 股票 | 市场 | 数量 | 成本价 | 现价 | 市值 | 盈亏 | 盈亏% | 权重 |
|------|------|------|--------|------|------|------|-------|------|
| 00700 | HK | 100 | 350 | 380 | 38,000 | 3,000 | 8.6% | 44.2% |

### 市场配比
| 市场 | 持仓数 | 市值 | 权重 | P&L |
|------|--------|------|------|-----|
| HK | 2 | 56,000 | 65.1% | 1,000 |
| US | 1 | 30,000 | 34.9% | 5,000 |

### 风险评分 (1-10)
根据以下因素计算:
- 集中度风险: 权重 30%
- HHI指数: 权重 25%
- 亏损比例: 权重 25%
- 持仓数量: 权重 20%
