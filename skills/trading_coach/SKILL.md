# Trading Coach Skill

交易导师技能 - 提供交易计划、心理辅导和复利教育

## 概述

Trading Coach Skill 是投资分析系统的交易指导模块，包含三大核心功能：
1. **计划生成** (PlanGenerator) - 今日交易计划、检查清单、持仓建议
2. **心理辅导** (PsychologyCoach) - 情绪评估、行为模式分析、交易格言
3. **复利教育** (CompoundEducator) - 复利计算、投资数学、财富规划

## 功能清单

### 1. 交易计划生成

- 今日必做操作（止损/止盈）
- 建议执行操作
- 关注列表
- 禁止操作清单
- 盘前/盘中检查清单
- 持仓操作建议

### 2. 心理辅导

- 交易行为模式检测
  - 频繁交易 (Overtrading)
  - 追涨杀跌 (Loss Chasing)
  - 报复性交易 (Revenge Trading)
  - 死扛亏损 (Holding Losers)
  - 仓位集中 (Concentration Risk)
  - FOMO 心理
- 情绪状态评估
  - 恐惧/贪婪/侥幸/后悔
  - 过度自信/恐慌/狂喜
- 针对性干预建议
- 每日交易箴言

### 3. 复利教育

- 复利增长计算
- 投资年限规划
- 交易数学模型
- 胜率与盈亏比分析
- 财富目标规划
- 名人名言启发

## 使用方式

### Python API

```python
from skills.trading_coach import TradingCoach, generate_coaching_report
from skills.shared import DataProvider, SkillContext

# 方式一：使用快捷函数
report = generate_coaching_report(
    user_id=1,
    request_type="full_coaching",  # daily_plan, psychology_check, compound_lesson
)
print(report)

# 方式二：使用类接口
provider = DataProvider()
coach = TradingCoach(data_provider=provider)

context = SkillContext(
    user_id=1,
    request_type="daily_plan",
    markets=["HK", "US"],
)

result = coach.execute(context)
if result.success:
    print(result.report_content)
    print(f"建议操作: {result.next_actions}")
```

### CLI 命令

```bash
# 运行完整教练会话
python main.py skill run coach

# 生成今日交易计划
python main.py skill run coach --type daily_plan

# 心理状态检查
python main.py skill run coach --type psychology_check

# 复利课程
python main.py skill run coach --type compound_lesson
```

## 数据结构

### CoachingResult

```python
@dataclass
class CoachingResult:
    """教练分析结果"""
    trading_plan: TradingPlan          # 交易计划
    position_actions: list[PositionAction]  # 持仓建议
    trade_pattern: TradePattern        # 交易模式
    behavior_analysis: BehaviorAnalysis  # 行为分析
    emotion_assessment: EmotionAssessment  # 情绪评估
    compound_projection: CompoundProjection  # 复利预测
    trading_math: TradingMath          # 交易数学
    coaching_date: date                # 日期
    user_id: int                       # 用户ID
```

### TradingPlan

```python
@dataclass
class TradingPlan:
    """今日交易计划"""
    plan_date: date
    market_overview: str               # 市场概览
    must_do_actions: list[ActionItem]  # 必须执行
    should_do_actions: list[ActionItem]  # 建议执行
    watch_list: list[ActionItem]       # 关注列表
    forbidden_actions: list[ActionItem]  # 禁止操作
    checklist: list[ChecklistItem]     # 检查清单
    notes: list[str]                   # 备注
    risk_warnings: list[str]           # 风险警示
```

### BehaviorPattern 行为模式

| 模式 | 说明 | 触发条件 |
|------|------|----------|
| OVERTRADING | 频繁交易 | 日交易 >= 5 次 |
| LOSS_CHASING | 追涨杀跌 | 高买低卖模式 |
| REVENGE_TRADING | 报复性交易 | 连续亏损后加仓 |
| HOLDING_LOSERS | 死扛亏损 | 持有 -15% 以上仓位 |
| CONCENTRATION_RISK | 仓位集中 | 单股占比 >= 25% |
| FOMO | 害怕错过 | 追涨行为 |

### EmotionType 情绪类型

| 情绪 | 说明 | 典型表现 |
|------|------|----------|
| FEAR | 恐惧 | 连续亏损后不敢操作 |
| GREED | 贪婪 | 追涨、不愿止盈 |
| HOPE | 侥幸 | 死扛亏损、不止损 |
| OVERCONFIDENCE | 过度自信 | 频繁交易、重仓 |
| PANIC | 恐慌 | 大跌时恐慌卖出 |
| EUPHORIA | 狂喜 | 大涨后过度乐观 |
| NEUTRAL | 平静 | 正常状态 |

## 止损止盈规则

### 止损阶梯

| 股票类型 | 最大亏损 |
|---------|---------|
| 投机股 | -5% |
| 成长股 | -8% |
| 核心股 | -12% |
| 问题股 | 立即清仓 |

### 动态止损

| 盈利区间 | 止损位置 |
|---------|---------|
| 0-10% | -8% |
| 10-20% | -5% (移动止损) |
| 20-50% | 成本价 (保本) |
| >50% | 最高价 -15% |

### 止盈阶梯

| 盈利幅度 | 操作 |
|---------|------|
| +30% | 减仓 1/3 |
| +50% | 减仓 1/2 |
| +100% | 保留 1/3 长持 |

## 复利教育数据

### 复利倍数参考表

| 年限 | 10% | 14% | 18% | 20% | 25% |
|------|-----|-----|-----|-----|-----|
| 10年 | 2.6x | 3.7x | 5.2x | 6.2x | 9.3x |
| 20年 | 6.7x | 13.7x | 27.4x | 38.3x | 86.7x |
| 25年 | 10.8x | 26.5x | 62.7x | 95.4x | 264.7x |
| 30年 | 17.4x | 50.9x | 143.4x | 237.4x | 807.8x |

### 交易数学模型

标准参考模型：
- 年交易次数: 10 次
- 胜率: 60%
- 平均盈利: 7%
- 平均亏损: 2.33%
- **预期年化收益: ~14%**

## 检查清单

### 盘前检查清单

- [ ] 查看隔夜全球市场走势
- [ ] 检查今日重大财经事件/数据发布
- [ ] 复习昨日交易和计划
- [ ] 确认当前仓位和可用资金
- [ ] 检查持仓股票的盘前动态
- [ ] 确认今日止损线位置
- [ ] 确认情绪状态，是否适合交易

### 盘中纪律

- [ ] 买入前确认：这是计划内的交易吗？
- [ ] 买入时设置止损单
- [ ] 不追涨超过3%的股票
- [ ] 单次交易不超过总仓位的20%
- [ ] 避免开盘15分钟内冲动交易
- [ ] 大跌时不恐慌卖出

### 盘后复盘

- [ ] 记录今日所有交易
- [ ] 复盘交易决策：符合计划吗？
- [ ] 检查持仓盈亏变化
- [ ] 更新明日关注列表
- [ ] 总结今日市场特点

## 交易格言

> "赚大钱靠的不是思考，而是坐等。" - 杰西·利弗莫尔

> "在别人恐惧时贪婪，在别人贪婪时恐惧。" - 沃伦·巴菲特

> "复利是世界第八大奇迹。" - 爱因斯坦

> "知道自己不知道什么，比聪明更重要。" - 查理·芒格

> "痛苦+反思=进步。" - Ray Dalio

## 文件结构

```
skills/trading_coach/
├── __init__.py           # 模块导出
├── SKILL.md              # 本文档
├── trading_coach.py      # 主控制器
├── plan_generator.py     # 计划生成器
├── compound_educator.py  # 复利教育
└── psychology_coach.py   # 心理辅导
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| OVERTRADING_THRESHOLD | 5 | 日交易次数上限 |
| CONSECUTIVE_LOSS_THRESHOLD | 3 | 连续亏损警告阈值 |
| DAILY_LOSS_THRESHOLD | 0.05 | 日亏损警告阈值 |
| CONCENTRATION_THRESHOLD | 0.25 | 单股集中度上限 |
| LARGE_LOSS_THRESHOLD | 0.15 | 大额亏损阈值 |

## 与其他 Skills 集成

```
            ┌─────────────┐
            │ Risk Controller │
            └──────┬──────┘
                   │ alerts
                   v
┌───────────┐    ┌─────────────┐    ┌───────────┐
│  Analyst  │───>│ Trading Coach │<───│ Positions │
└───────────┘    └──────┬──────┘    └───────────┘
   signals              │
                        v
               ┌─────────────┐
               │ Trading Plan │
               │ Psychology   │
               │ Compound Ed  │
               └─────────────┘
```

---

*版本: 1.0*
*创建日期: 2025-12-15*
*作者: Python Expert Agent*
