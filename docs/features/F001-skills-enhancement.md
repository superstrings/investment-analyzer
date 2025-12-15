# F001 - Skills 体系增强与智能投资顾问

## 概述

完善 investment-analyzer 系统的 skills 体系，新增分析师、风控师、交易导师、市场观察员四大角色，实现盘前盘后自动分析、持仓风险监控、定期交易复盘等核心功能。

## 背景

### 现状分析

当前系统已具备的能力：
- **数据采集**: FutuFetcher (持仓/交易) + KlineFetcher (K线)
- **技术分析**: MA/MACD/RSI/BB/OBV/VCP 等指标计算
- **形态识别**: VCP、杯柄、头肩顶底、三角形等
- **图表生成**: mplfinance K线图
- **报告系统**: Portfolio/Technical/Daily/Weekly 四类报告
- **现有 Skills**: portfolio_analyzer, technical_analyzer, report_generator

### 痛点问题

1. **缺乏主动性**: 现有系统被动响应，缺乏主动分析和提醒能力
2. **缺乏角色分工**: 分析、风控、指导混在一起，职责不清
3. **缺乏时间维度**: 没有盘前/盘后/月度等时间节点的专门处理
4. **缺乏心理辅导**: 没有复利思维教育和交易心理辅导

### 设计理念

参考 Claude Code 产品哲学：
1. **工具的终极形态是消失**: 减少用户操作，自动化分析流程
2. **减少选择增加能力**: 提供明确建议而非多个选项
3. **双重用户设计**: 既服务人类用户，也服务 AI 协作

复利思维融入：
- 早开始、长期持有
- 克服即时满足偏好、线性思维、恐惧贪婪

---

## 需求详情

### 功能需求

#### FR-1: 分析师 (Analyst) Skill

**职责**: 个股技术分析、量价诊断、投资建议

**核心理念**: 技术指标在精不在多，专注 **OBV + VCP** 双核心体系

**为什么选择 OBV + VCP**:
- **OBV (能量潮)**: 量在价先，资金动向的先行指标
  - OBV 上升 + 价格横盘 = 主力吸筹，准备上涨
  - OBV 下降 + 价格横盘 = 主力出货，准备下跌
  - OBV 背离是重要的趋势反转信号
- **VCP (波动收缩形态)**: Mark Minervini 的经典突破形态
  - 价格波动逐渐收窄，成交量持续萎缩
  - 突破收缩区间 + 放量 = 大行情起点
  - 成功率高，风险收益比优秀

**能力清单**:
- FR-1.1: OBV 分析
  - OBV 趋势判断 (上升/下降/横盘)
  - OBV 与价格背离检测
  - OBV 突破确认 (OBV 创新高配合价格突破)
- FR-1.2: VCP 形态识别
  - 收缩次数与幅度 (理想: 3-4次收缩，幅度递减)
  - 成交量萎缩确认
  - 突破点位计算 (Pivot Point)
  - VCP 评分 (0-100)
- FR-1.3: 买卖信号生成
  - 买入信号: VCP 突破 + OBV 确认 + 放量
  - 卖出信号: OBV 背离 + 跌破支撑
- FR-1.4: 目标价/止损价计算
  - 止损: 突破点下方 5-8%
  - 目标: 基于前期高点或收缩幅度的 2-3 倍
- FR-1.5: 关注列表批量筛选与排序

**输入**:
- 股票代码 (单个或列表)
- 分析周期 (默认120日)

**输出**:
```python
@dataclass
class StockAnalysisResult:
    code: str
    name: str
    analysis_date: date
    price_info: PriceInfo

    # OBV 分析
    obv_trend: str           # "上升" / "下降" / "横盘"
    obv_divergence: str      # "顶背离" / "底背离" / "无"
    obv_score: float         # 0-100

    # VCP 分析
    vcp_detected: bool       # 是否检测到 VCP
    vcp_contractions: int    # 收缩次数
    vcp_tightness: float     # 最后收缩幅度 (%)
    vcp_pivot: float         # 突破点位
    vcp_score: float         # 0-100

    # 综合
    overall_score: float     # OBV(40%) + VCP(60%)
    signal: str              # "买入" / "持有" / "卖出" / "观望"
    stop_loss: float         # 止损价
    target_price: float      # 目标价
    action_note: str         # 操作建议说明
```

#### FR-2: 风控师 (Risk Controller) Skill

**职责**: 持仓监控、风险预警、仓位管理

**能力清单**:
- FR-2.1: 实时持仓诊断 (盈亏/仓位/集中度)
- FR-2.2: 仓位集中度预警 (单股>20%, 板块>40%)
- FR-2.3: 止损预警 (跌破止损线提醒)
- FR-2.4: 止盈建议 (+30%减1/3, +50%减1/2, +100%保留1/3)
- FR-2.5: 现金比例监控 (最低15%)
- FR-2.6: 杠杆率监控 (不超过1.94倍)
- FR-2.7: 风险信号汇总与优先级排序
- FR-2.8: VIX 恐慌指数策略应用

**风险等级定义**:
```python
class RiskAlert(Enum):
    CRITICAL = "critical"    # 立即处理: 单股>30%, 亏损>15%
    HIGH = "high"            # 当日处理: 单股>25%, 亏损>10%
    MEDIUM = "medium"        # 本周处理: 单股>20%, 需要优化
    LOW = "low"              # 持续关注: 正常范围内的提醒
```

**输出**:
```python
@dataclass
class RiskControlReport:
    report_date: date
    portfolio_summary: PortfolioSummary
    risk_alerts: list[RiskAlert]
    position_diagnosis: list[PositionDiagnosis]
    action_items: list[ActionItem]  # 按优先级排序的操作建议
    concentration_matrix: ConcentrationMatrix  # 股票/板块/市场集中度
```

#### FR-3: 交易导师 (Trading Coach) Skill

**职责**: 交易指导、复利教育、心理辅导

**能力清单**:
- FR-3.1: 交易计划制定 (今日必做/挂单设置/禁止操作)
- FR-3.2: 复利思维教育
  - 复利公式可视化 (年收益率 vs 时间 vs 倍数)
  - 命中率与盈亏比的关系
  - 长期视角的重要性
- FR-3.3: 交易心理辅导
  - 识别恐惧/贪婪情绪信号
  - 提供理性决策框架
  - 强化纪律执行
- FR-3.4: 操作检查清单生成
- FR-3.5: 交易格言与感悟推送
- FR-3.6: 错误交易复盘与教训总结

**复利教育数据模型**:
```python
@dataclass
class CompoundInterestLesson:
    """复利课程数据"""
    annual_return_rate: float  # 年收益率
    years: int                  # 投资年限
    initial_capital: float      # 初始资金
    final_value: float          # 最终价值
    multiplier: float           # 增长倍数

    # 按照复利公式图表中的参数
    trades_per_year: int        # 年交易次数 (如10次)
    win_rate: float             # 胜率 (如60%)
    profit_per_trade: float     # 单次盈利比例 (如7%)
    loss_per_trade: float       # 单次亏损比例 (如2.33%)
```

**心理辅导触发条件**:
- 连续亏损超过3笔
- 单日亏损超过5%
- 频繁交易 (日内交易超过5笔)
- 重仓单一股票
- 追涨杀跌行为检测

#### FR-4: 市场观察员 (Market Observer) Skill

**职责**: 盘前/盘后分析、市场综述、事件跟踪

**能力清单**:
- FR-4.1: 盘前分析 (Pre-market Analysis)
  - 隔夜全球市场回顾
  - 今日重大事件提醒 (财报/经济数据/政策)
  - 持仓股票盘前走势
  - 今日操作计划确认
- FR-4.2: 盘后总结 (Post-market Summary)
  - 今日市场综述
  - 持仓盈亏统计
  - 交易执行复盘
  - 异动股票分析
  - 次日关注重点
- FR-4.3: 板块轮动分析
  - 强势板块 Top5
  - 弱势板块预警
  - 资金流向监控
- FR-4.4: 情绪温度计 (1-100分)
  - VIX 指数影响
  - 涨跌比分析
  - 成交量活跃度
  - 融资余额变化

**时间触发机制**:
```python
@dataclass
class MarketSchedule:
    """市场时间表"""
    # 港股
    hk_pre_market: time = time(8, 30)   # 盘前分析
    hk_open: time = time(9, 30)
    hk_close: time = time(16, 0)
    hk_post_market: time = time(16, 30) # 盘后总结

    # 美股 (北京时间)
    us_pre_market: time = time(20, 0)   # 盘前分析 (夏令时)
    us_open: time = time(21, 30)
    us_close: time = time(4, 0)         # 次日
    us_post_market: time = time(5, 0)   # 次日盘后总结
```

#### FR-5: 自动化工作流

**FR-5.1: 每日工作流**

```
盘前 (HK 8:30 / US 20:00)
  |-- 市场观察员: 生成盘前分析报告
  |-- 分析师: 更新持仓股票技术分析
  |-- 风控师: 检查风险状态
  |-- 交易导师: 生成今日操作计划
  v
盘中 (按需触发)
  |-- 风控师: 价格提醒触发
  |-- 分析师: 形态突破提醒
  v
盘后 (HK 16:30 / US 5:00)
  |-- 市场观察员: 生成盘后总结
  |-- 风控师: 更新风险评估
  |-- 交易导师: 复盘今日操作
  v
夜间 (22:00)
  |-- 分析师: 关注列表批量分析
  |-- 交易导师: 复利教育推送 (每周一次)
```

**FR-5.2: 月度工作流**

```
每月最后一个交易日
  |-- 风控师: 月度风险报告
  |-- 分析师: 持仓股票月度评估
  |-- 交易导师: 月度交易复盘
      |-- 交易统计 (笔数/金额/胜率)
      |-- 盈亏归因分析
      |-- 与基准对比
      |-- 教训总结与改进建议
      |-- 复利进度追踪
```

### 非功能需求

- NFR-1: 所有分析在 30 秒内完成 (单股分析 < 5秒)
- NFR-2: 报告支持 Markdown/JSON/HTML 三种格式
- NFR-3: 支持离线模式 (使用本地数据库数据)
- NFR-4: 日志完整记录所有分析过程
- NFR-5: 配置化的触发时间和参数

---

## 技术设计

### 整体架构

```
skills/
├── analyst/                    # 分析师
│   ├── SKILL.md               # Skill 定义文档
│   ├── __init__.py
│   ├── stock_analyzer.py      # 单股分析
│   ├── batch_analyzer.py      # 批量分析
│   └── scoring.py             # 评分系统
│
├── risk_controller/           # 风控师
│   ├── SKILL.md
│   ├── __init__.py
│   ├── position_monitor.py    # 持仓监控
│   ├── risk_calculator.py     # 风险计算
│   └── alert_generator.py     # 预警生成
│
├── trading_coach/             # 交易导师
│   ├── SKILL.md
│   ├── __init__.py
│   ├── plan_generator.py      # 计划生成
│   ├── compound_educator.py   # 复利教育
│   └── psychology_coach.py    # 心理辅导
│
├── market_observer/           # 市场观察员
│   ├── SKILL.md
│   ├── __init__.py
│   ├── pre_market.py          # 盘前分析
│   ├── post_market.py         # 盘后总结
│   └── sector_rotation.py     # 板块轮动
│
├── workflow/                  # 工作流引擎
│   ├── __init__.py
│   ├── scheduler.py           # 调度器
│   ├── daily_workflow.py      # 每日工作流
│   └── monthly_workflow.py    # 月度工作流
│
└── shared/                    # 共享组件
    ├── __init__.py
    ├── data_provider.py       # 统一数据获取
    └── report_builder.py      # 报告构建器
```

### 数据流设计

```
[数据层]
    Database (positions/trades/klines)
    FutuFetcher (实时数据)
    KlineFetcher (历史数据)
           |
           v
[分析层]
    analysis/ (技术指标/形态识别/组合分析)
           |
           v
[Skills 层]
    Analyst -> 技术分析结果
    RiskController -> 风险评估结果
    TradingCoach -> 操作建议
    MarketObserver -> 市场洞察
           |
           v
[报告层]
    reports/ (Markdown/JSON/HTML)
           |
           v
[交互层]
    CLI 命令
    Claude Code 对话
```

### 核心类设计

```python
# 基础 Skill 接口
class BaseSkill(ABC):
    """所有 Skill 的基类"""

    @abstractmethod
    def execute(self, context: SkillContext) -> SkillResult:
        """执行 Skill"""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[str]:
        """获取能力列表"""
        pass

# Skill 上下文
@dataclass
class SkillContext:
    user_id: int
    request_type: str
    parameters: dict[str, Any]
    market_state: MarketState  # 开盘/收盘/盘中

# Skill 结果
@dataclass
class SkillResult:
    success: bool
    skill_name: str
    result_type: str
    data: Any
    report: Optional[ReportResult]
    next_actions: list[str]  # 建议的后续动作
```

### CLI 命令设计

```bash
# 分析师命令
python main.py analyze stock --code HK.00700 --depth deep
python main.py analyze watchlist --user dyson --sort score
python main.py analyze portfolio --user dyson

# 风控师命令
python main.py risk check --user dyson
python main.py risk alerts --user dyson --level high
python main.py risk report --user dyson --type monthly

# 交易导师命令
python main.py coach plan --user dyson --date today
python main.py coach review --user dyson --period week
python main.py coach lesson --topic compound

# 市场观察员命令
python main.py market pre --markets hk,us
python main.py market post --markets hk,us
python main.py market sectors --top 5

# 工作流命令
python main.py workflow daily --user dyson --phase pre_market
python main.py workflow monthly --user dyson
```

---

## 文件位置

| 模块 | 路径 | 说明 |
|------|------|------|
| Analyst Skill | `skills/analyst/` | 分析师核心代码 |
| Risk Controller | `skills/risk_controller/` | 风控师核心代码 |
| Trading Coach | `skills/trading_coach/` | 交易导师核心代码 |
| Market Observer | `skills/market_observer/` | 市场观察员核心代码 |
| Workflow | `skills/workflow/` | 工作流引擎 |
| 共享组件 | `skills/shared/` | 跨 Skill 共享代码 |
| 报告模板 | `reports/templates/` | Jinja2 模板 |
| CLI 命令 | `main.py` | 新增命令组 |
| 测试 | `tests/test_skills/` | Skill 单元测试 |

---

## 测试计划

### 单元测试

```
tests/test_skills/
├── test_analyst.py           # 分析师测试
│   ├── test_single_stock_analysis
│   ├── test_batch_analysis
│   ├── test_scoring_system
│   └── test_rating_generation
│
├── test_risk_controller.py   # 风控师测试
│   ├── test_position_diagnosis
│   ├── test_concentration_alerts
│   ├── test_stop_loss_detection
│   └── test_risk_level_calculation
│
├── test_trading_coach.py     # 交易导师测试
│   ├── test_plan_generation
│   ├── test_compound_calculation
│   └── test_psychology_triggers
│
├── test_market_observer.py   # 市场观察员测试
│   ├── test_pre_market_report
│   ├── test_post_market_report
│   └── test_sector_analysis
│
└── test_workflow.py          # 工作流测试
    ├── test_daily_workflow
    └── test_monthly_workflow
```

### 集成测试

1. 完整的每日工作流端到端测试
2. 真实数据的分析准确性验证
3. 报告生成的格式正确性检查

### 验收标准

1. 所有 Skill 的 SKILL.md 文档完整
2. CLI 命令可正常执行
3. 报告输出格式符合预期
4. 单元测试覆盖率 > 80%
5. 性能满足 NFR 要求

---

## 实施计划

### Phase 1: 基础框架 (Week 1)

- [ ] 创建 skills 目录结构
- [ ] 实现 BaseSkill 基类和接口
- [ ] 实现共享组件 (DataProvider, ReportBuilder)
- [ ] 添加 CLI 命令框架

### Phase 2: 分析师 Skill (Week 2)

- [ ] 实现 StockAnalyzer (单股分析)
- [ ] 实现 BatchAnalyzer (批量分析)
- [ ] 实现 ScoringSystem (评分系统)
- [ ] 创建 SKILL.md 文档
- [ ] 添加单元测试

### Phase 3: 风控师 Skill (Week 3)

- [ ] 实现 PositionMonitor (持仓监控)
- [ ] 实现 RiskCalculator (风险计算)
- [ ] 实现 AlertGenerator (预警生成)
- [ ] 创建 SKILL.md 文档
- [ ] 添加单元测试

### Phase 4: 交易导师 Skill (Week 4)

- [ ] 实现 PlanGenerator (计划生成)
- [ ] 实现 CompoundEducator (复利教育)
- [ ] 实现 PsychologyCoach (心理辅导)
- [ ] 创建 SKILL.md 文档
- [ ] 添加单元测试

### Phase 5: 市场观察员 Skill (Week 5)

- [ ] 实现 PreMarketAnalyzer (盘前分析)
- [ ] 实现 PostMarketSummarizer (盘后总结)
- [ ] 实现 SectorRotation (板块轮动)
- [ ] 创建 SKILL.md 文档
- [ ] 添加单元测试

### Phase 6: 工作流与集成 (Week 6)

- [ ] 实现 Scheduler (调度器)
- [ ] 实现 DailyWorkflow (每日工作流)
- [ ] 实现 MonthlyWorkflow (月度工作流)
- [ ] 端到端集成测试
- [ ] 文档完善

---

## 参考资料

### 分析 Prompt 演进

| 版本 | 日期 | 特点 |
|------|------|------|
| V1.0 | 2025-08-13 | 基础 OBV/VCP 分析 |
| V2.0 | 2025-09-03 | 增加持仓诊断、期权策略、风险管理 |
| V3.0 | 2025-10-29 | 新增生物制造主题、产业链分析 |
| V5.0 | 2025-11-04 | 数据驱动、多周期涨跌幅、VIX策略、情绪温度计 |

### 复利公式关键数据

根据复利公式图表：
- 年化 14% 收益率，30年可增长约 50 倍
- 年化 20% 收益率，25年可增长约 95 倍
- 胜率 60%，单次盈利 7%，单次亏损 2.33%，一年交易 10 次，年化约 14%

### 历史分析报告示例

位置: `/Users/dyson/Documents/trade/分析md文本/`

关键报告参考:
- `portfolio-analysis-20250930.md` - 持仓诊断完整示例
- `stock-report-20250921.md` - 技术分析报告示例

---

## 附录

### A. 评分标准详细说明 (OBV + VCP 双核心)

**技术评分 (0-100)** = OBV评分 × 40% + VCP评分 × 60%

#### OBV 评分 (0-100)

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| OBV 趋势 | 50% | 上升趋势(80-100)、横盘(40-60)、下降趋势(0-30) |
| 量价配合 | 30% | 价涨量增(+30)、价跌量缩(+20)、背离(-20) |
| OBV 位置 | 20% | 创新高(+20)、高位(+15)、中位(+10)、低位(+5) |

**OBV 信号解读**:
- **强势**: OBV 上升 + 创新高 → 资金持续流入，看涨
- **吸筹**: OBV 上升 + 价格横盘 → 主力建仓中，等待突破
- **出货**: OBV 下降 + 价格横盘 → 主力派发中，谨慎
- **顶背离**: 价格新高 + OBV 未新高 → 动能衰竭，危险信号
- **底背离**: 价格新低 + OBV 未新低 → 抛压枯竭，关注反转

#### VCP 评分 (0-100)

| 维度 | 权重 | 评分标准 |
|------|------|----------|
| 收缩次数 | 30% | 3-4次(90-100)、2次(60-80)、1次(30-50)、0次(0) |
| 收缩幅度 | 30% | 递减且最后<10%(90-100)、递减(60-80)、不规则(30-50) |
| 成交量 | 25% | 持续萎缩(90-100)、部分萎缩(60-80)、无萎缩(30-50) |
| 突破就绪 | 15% | 接近突破点<3%(100)、<5%(80)、<10%(50)、>10%(20) |

**VCP 理想形态**:
```
价格收缩:  -15% → -10% → -5% → -3%  (幅度递减)
成交量:    高 → 中 → 低 → 极低      (持续萎缩)
时间:      2-8周                    (不宜过短或过长)
突破:      放量突破收缩区间高点
```

#### 综合信号判定

| 综合评分 | 信号 | 操作建议 |
|----------|------|----------|
| 80-100 | **买入** | VCP 突破在即 + OBV 强势确认，积极介入 |
| 60-79 | **关注** | 形态良好，等待突破确认后介入 |
| 40-59 | **观望** | 形态不明朗，继续观察 |
| 20-39 | **回避** | OBV 走弱或形态破坏，不宜介入 |
| 0-19 | **卖出** | OBV 顶背离或跌破支撑，及时离场 |

**风险评分 (1-10)**

| 分数 | 含义 | 触发条件 |
|------|------|----------|
| 1-3 | 低风险 | 分散良好、盈利稳定、现金充足 |
| 4-6 | 中风险 | 略微集中、部分亏损、需优化 |
| 7-8 | 高风险 | 集中度高、亏损较大、杠杆偏高 |
| 9-10 | 极高风险 | 单股>30%、亏损>15%、杠杆过高 |

### B. 止损止盈规则

**止损阶梯**:
- 投机股: -5%
- 成长股: -8%
- 核心股: -12%
- 问题股: 立即清仓

**动态止损**:
- 盈利 0-10%: 止损 -8%
- 盈利 10-20%: 止损 -5% (移动止损)
- 盈利 20-50%: 止损位 = 成本价 (保本)
- 盈利 >50%: 止损位 = 最高价 -15% (保护利润)

**止盈阶梯**:
- +30%: 减仓 1/3
- +50%: 减仓 1/2
- +100%: 保留 1/3 长持

---

*文档版本: 1.1*
*创建日期: 2025-12-15*
*更新日期: 2025-12-15*
*更新内容: 简化技术分析体系，聚焦 OBV + VCP 双核心*
*作者: Requirements Analyst Agent*
