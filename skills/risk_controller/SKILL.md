# Risk Controller Skill - 风控师

> 投资组合风险管理系统

## 概述

Risk Controller Skill 提供全面的投资组合风险分析和预警功能，包括：

- **持仓诊断** - 逐一检查每个持仓的健康状况
- **风险计算** - 集中度、止损、杠杆分析
- **风险预警** - 生成优先级排序的风险警报

## 核心功能

### 1. 持仓诊断 (Position Monitor)

对每个持仓进行详细诊断：

| 诊断维度 | 说明 |
|---------|------|
| **止损状态** | 是否触发/接近止损，是否设置止损 |
| **仓位大小** | 是否超标/过小 |
| **盈亏状态** | 亏损程度评估 |
| **整体状态** | HEALTHY/ATTENTION/WARNING/CRITICAL |

**持仓状态分类:**
- `healthy`: 健康 - 无需关注
- `attention`: 注意 - 小问题需留意
- `warning`: 警告 - 需要监控
- `critical`: 危急 - 需要立即处理

### 2. 风险计算 (Risk Calculator)

#### 集中度分析
- **HHI 指数** - Herfindahl-Hirschman Index (0-10000)
- **分散度评分** - 0-100，越高越分散
- **仓位权重** - 单一/前3/前5/前10仓位占比

| HHI 范围 | 集中度级别 |
|---------|-----------|
| < 1000 | 良好分散 |
| 1000-1800 | 适度 |
| 1800-2500 | 集中 |
| > 2500 | 高度集中 |

#### 止损分析
- **止损覆盖率** - 有止损的仓位比例
- **组合风险** - 所有止损触发时的最大损失
- **最大单一损失** - 单一仓位最大潜在损失

#### 杠杆分析
- **杠杆倍数** - 总持仓/净资产
- **保证金使用** - 保证金使用情况
- **追保距离** - 距离追保的下跌空间

### 3. 风险预警 (Alert Generator)

生成优先级排序的风险警报：

| 严重级别 | 说明 | 典型场景 |
|---------|------|---------|
| `critical` | 危急 | 止损触发、>30%亏损、杠杆>3x |
| `urgent` | 紧急 | 接近止损、>20%亏损、杠杆>2x |
| `warning` | 警告 | >10%亏损、无止损、仓位过大 |
| `info` | 信息 | 一般性提醒 |

## 评分系统

### 健康评分 (Health Score)

```
健康评分 = 加权平均(持仓状态)

- Healthy: 100分
- Attention: 70分
- Warning: 40分
- Critical: 0分
```

### 风险评分 (Risk Score)

```
风险评分 = 集中度风险 + 止损风险 + 杠杆风险

- 集中度: 0-30分
- 止损覆盖: 0-40分
- 杠杆: 0-30分
```

| 风险评分 | 风险级别 | 说明 |
|---------|---------|------|
| 0-30 | LOW | 风险可控 |
| 30-50 | MEDIUM | 需要关注 |
| 50-70 | HIGH | 需要减仓 |
| 70-100 | VERY_HIGH | 紧急处理 |

## 使用方法

### 基础使用

```python
from skills.risk_controller import RiskController, generate_risk_report

# 创建风控师
controller = RiskController()

# 分析用户组合风险
result = controller.analyze_portfolio_risk(user_id=1)

# 查看结果
print(f"风险级别: {result.overall_risk_level.value}")
print(f"健康评分: {result.health_score:.0f}/100")
print(f"风险评分: {result.risk_score:.0f}/100")

# 查看警报
for alert in result.alerts.alerts:
    print(f"[{alert.severity.value}] {alert.title}")

# 生成报告
report = generate_risk_report(result)
print(report)
```

### 带止损价格分析

```python
from skills.risk_controller import RiskController

controller = RiskController()

# 定义止损价格
stop_losses = {
    "HK.00700": 350.00,  # 腾讯止损价
    "US.NVDA": 120.00,   # 英伟达止损价
    "US.AAPL": 180.00,   # 苹果止损价
}

result = controller.analyze_portfolio_risk(
    user_id=1,
    stop_losses=stop_losses
)

# 检查止损状态
for diag in result.diagnostic.diagnostics:
    print(f"{diag.full_code}: {diag.stop_loss_status.value}")
```

### 仓位计算

```python
from skills.risk_controller import RiskCalculator

calc = RiskCalculator()

# 计算推荐仓位大小
recommendation = calc.calculate_position_size(
    market="HK",
    code="00700",
    current_price=380.00,
    stop_loss_price=350.00,
    portfolio_value=1000000,
    risk_budget_pct=1.0  # 每笔交易风险1%
)

print(f"最大股数: {recommendation.max_shares}")
print(f"最大金额: ${recommendation.max_value:.2f}")
print(f"最大权重: {recommendation.max_weight:.1f}%")
```

## CLI 命令

```bash
# 运行风险分析
python main.py skill run -t risk_controller -u dyson

# 带止损分析 (需要配置文件)
python main.py skill run -t risk_controller -u dyson --stop-losses stops.json

# 输出为 JSON
python main.py skill run -t risk_controller -u dyson -f json

# 保存到文件
python main.py skill run -t risk_controller -u dyson -o risk_report.md
```

## 输出示例

### 风险报告

```markdown
# Portfolio Risk Report

## Risk Summary
- **Analysis Date**: 2025-12-15
- **Portfolio Value**: $1,234,567.89
- **Risk Level**: MEDIUM
- **Health Score**: 72/100
- **Risk Score**: 45/100

**Portfolio risk is MEDIUM. Health score: 72/100. 2 urgent alert(s).**

## Priority Actions
- Set stop-loss for unprotected positions
- Consider reducing largest position

## Risk Alerts
[URGENT] **Approaching Stop-Loss**
  2 position(s) approaching stop-loss level
  Affected: HK.00700, US.TSLA

[WARNING] **Missing Stop-Loss**
  5 position(s) without defined stop-loss
  Affected: US.AAPL, US.MSFT, US.AMZN, HK.09988, HK.02318

## Concentration Analysis
| Metric | Value | Status |
|--------|-------|--------|
| HHI Index | 1850 | concentrated |
| Largest Position | 22.5% | HIGH |
| Top 5 Weight | 68.2% | OK |
| Diversification | 65/100 | |

## Stop-Loss Coverage
- **Coverage**: 60%
- **With Stop**: 6
- **Without Stop**: 4
- **Portfolio Risk**: 6.5%

## Position Health
- **Total Positions**: 10
- **Healthy**: 5
- **Attention**: 3
- **Warning**: 2
- **Critical**: 0
```

## 数据类

### RiskControllerResult

```python
@dataclass
class RiskControllerResult:
    user_id: int
    analysis_date: date
    portfolio_value: float

    diagnostic: PortfolioDiagnostic  # 持仓诊断
    risk_metrics: PortfolioRiskMetrics  # 风险指标
    alerts: AlertSummary  # 风险警报

    overall_risk_level: RiskLevel
    health_score: float  # 0-100
    risk_score: float  # 0-100

    summary: str
    priority_actions: list[str]
```

### PositionDiagnostic

```python
@dataclass
class PositionDiagnostic:
    market: str
    code: str
    name: str
    status: PositionStatus  # healthy/attention/warning/critical
    weight: float  # 仓位权重
    pl_ratio: float  # 盈亏比例
    stop_loss_status: StopLossStatus  # safe/approaching/triggered/not_set
    distance_to_stop: float  # 距离止损百分比
    is_oversized: bool  # 是否超仓
    signals: list[str]  # 诊断信号
    actions: list[str]  # 建议操作
```

### RiskAlert

```python
@dataclass
class RiskAlert:
    category: AlertCategory  # stop_loss/concentration/leverage/pnl
    severity: AlertSeverity  # critical/urgent/warning/info
    title: str
    message: str
    affected_positions: list[str]
    recommended_actions: list[str]
```

## 配置选项

### PositionMonitorConfig

```python
PositionMonitorConfig(
    default_stop_loss_pct=8.0,     # 默认止损比例
    stop_approaching_threshold=2.0, # 接近止损阈值
    max_position_weight=20.0,       # 最大仓位权重
    min_position_weight=2.0,        # 最小有效仓位
    attention_loss_pct=5.0,         # 注意级别亏损
    warning_loss_pct=10.0,          # 警告级别亏损
    critical_loss_pct=15.0,         # 危急级别亏损
)
```

### RiskCalculatorConfig

```python
RiskCalculatorConfig(
    moderate_hhi=1000,              # 适度集中 HHI
    concentrated_hhi=1800,          # 集中 HHI
    highly_concentrated_hhi=2500,   # 高度集中 HHI
    max_single_position_weight=20.0, # 最大单一仓位
    max_portfolio_risk_pct=5.0,     # 最大组合风险
    default_risk_per_trade_pct=1.0, # 单笔交易风险
)
```

## 设计原则

1. **预防优于治疗** - 提前识别风险，防范于未然
2. **量化风险** - 所有风险都有数字化指标
3. **优先级排序** - 警报按严重程度排序
4. **可操作建议** - 每个警报都有明确的行动建议
5. **止损文化** - 强调止损的重要性

## 参考资料

- Mark Minervini: *Trade Like a Stock Market Wizard* (Chapter on Risk Management)
- Van Tharp: *Trade Your Way to Financial Freedom* (Position Sizing)

---

*最后更新: 2025-12-15*
