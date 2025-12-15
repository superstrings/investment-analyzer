# Workflow Engine Skill

工作流引擎技能 - 每日工作流、月度工作流、自动化调度

## 概述

Workflow Engine Skill 是投资分析系统的自动化协调模块，负责编排和执行各种分析任务：

1. **每日工作流** (DailyWorkflow) - 盘前/盘后自动化分析
2. **月度工作流** (MonthlyWorkflow) - 月末复盘与总结
3. **调度器** (Scheduler) - 时间管理与任务调度
4. **工作流引擎** (WorkflowEngine) - 统一入口与协调

## 功能清单

### 1. 每日工作流

#### 盘前阶段 (Pre-Market)
- 市场观察: 全球市场隔夜动态、风险提示
- 技术分析: 持仓股票分析更新
- 风险检查: 当前风险状态评估
- 交易计划: 生成今日操作计划

#### 盘后阶段 (Post-Market)
- 市场总结: 今日市场表现汇总
- 风险报告: 持仓风险评估
- 交易复盘: 今日交易心理分析

### 2. 月度工作流

- 月度风险报告
- 持仓月度评估
- 月度交易复盘
- 复利教育课程

### 3. 调度器功能

- 市场时间感知 (港股/美股/A股)
- 工作流阶段自动检测
- 交易日判断
- 月末最后交易日检测

## 使用方式

### Python API

```python
from skills.workflow import (
    WorkflowEngine,
    DailyWorkflow,
    MonthlyWorkflow,
    run_workflow,
    run_daily_workflow,
    run_monthly_workflow,
)
from skills.shared import DataProvider, SkillContext

# 方式一：使用快捷函数
# 自动检测工作流
report = run_workflow(user_id=1, workflow_type="auto", markets=["HK"])
print(report)

# 每日工作流 (指定阶段)
report = run_daily_workflow(user_id=1, phase="pre_market", markets=["HK"])
print(report)

# 月度工作流
report = run_monthly_workflow(user_id=1, markets=["HK"], force=True)
print(report)

# 方式二：使用类接口
provider = DataProvider()
engine = WorkflowEngine(data_provider=provider)

context = SkillContext(
    user_id=1,
    request_type="auto",  # daily, monthly, auto
    markets=["HK"],
    parameters={"phase": "pre_market"},
)

result = engine.execute(context)
if result.success:
    print(result.report_content)

# 获取调度信息
schedule_info = engine.get_schedule_info(market="HK")
print(f"Current phase: {schedule_info['current_phase']}")
print(f"Is trading day: {schedule_info['is_trading_day']}")
```

### CLI 命令

```bash
# 自动工作流 (根据时间自动选择)
python main.py workflow run --user dyson

# 每日工作流
python main.py workflow daily --user dyson --phase pre_market
python main.py workflow daily --user dyson --phase post_market

# 月度工作流
python main.py workflow monthly --user dyson
python main.py workflow monthly --user dyson --force  # 强制执行 (非月末)

# 查看调度信息
python main.py workflow status --market HK
```

## 数据结构

### WorkflowPhase (工作流阶段)

| 阶段 | 值 | 说明 |
|------|-----|------|
| PRE_MARKET | pre_market | 盘前准备 |
| MARKET_OPEN | market_open | 盘中交易 |
| POST_MARKET | post_market | 盘后复盘 |
| CLOSED | closed | 休市 |

### ScheduledTask (调度任务)

```python
@dataclass
class ScheduledTask:
    task_id: str           # 任务ID
    name: str              # 任务名称
    phase: WorkflowPhase   # 执行阶段
    skill_type: str        # 技能类型 (analyst, risk, coach, observer)
    request_type: str      # 请求类型
    priority: int          # 优先级 (1-10, 越大越优先)
    markets: list[str]     # 适用市场
    dependencies: list[str] # 依赖任务ID
    enabled: bool          # 是否启用
```

### TaskResult (任务结果)

```python
@dataclass
class TaskResult:
    task_id: str                    # 任务ID
    task_name: str                  # 任务名称
    success: bool                   # 是否成功
    skill_result: SkillResult       # 技能执行结果
    error_message: str              # 错误信息
    execution_time_ms: float        # 执行时间
    started_at: datetime            # 开始时间
    completed_at: datetime          # 完成时间
```

### WorkflowResult (工作流结果)

```python
@dataclass
class WorkflowResult:
    workflow_name: str              # 工作流名称
    phase: WorkflowPhase            # 执行阶段
    execution_date: date            # 执行日期
    task_results: list[TaskResult]  # 任务结果列表
    total_tasks: int                # 总任务数
    successful_tasks: int           # 成功任务数
    failed_tasks: int               # 失败任务数
    total_time_ms: float            # 总执行时间
    summary_report: str             # 汇总报告
```

## 市场时间表

### 港股 (北京时间)

| 阶段 | 时间 |
|------|------|
| 盘前 | 08:30 |
| 开盘 | 09:30 |
| 午休 | 12:00-13:00 |
| 收盘 | 16:00 |
| 盘后 | 16:30 |

### 美股 (北京时间，夏令时)

| 阶段 | 时间 |
|------|------|
| 盘前 | 20:00 |
| 开盘 | 21:30 |
| 收盘 | 次日 04:00 |
| 盘后 | 次日 05:00 |

### A股 (北京时间)

| 阶段 | 时间 |
|------|------|
| 盘前 | 09:00 |
| 开盘 | 09:30 |
| 午休 | 11:30-13:00 |
| 收盘 | 15:00 |
| 盘后 | 15:30 |

## 任务依赖图

### 盘前工作流

```
pre_market_observation (市场观察)
    │
    ├──> pre_market_analysis (技术分析)
    │         │
    │         └──> daily_plan (交易计划)
    │                   ^
    └──> pre_market_risk (风险检查)
              │
              └─────────┘
```

### 盘后工作流

```
post_market_observation (市场总结)
    │
    ├──> post_market_risk (风险报告)
    │         │
    │         └──> daily_review (交易复盘)
    │                   ^
    └─────────────────┘
```

### 月度工作流

```
monthly_risk_report (风险报告)
    │
    └──> monthly_review (月度复盘)
              ^
monthly_analysis (持仓评估)
    │
    └─────────┘

compound_lesson (复利教育) [独立任务]
```

## 文件结构

```
skills/workflow/
├── __init__.py              # 模块导出
├── SKILL.md                 # 本文档
├── scheduler.py             # 调度器
├── daily_workflow.py        # 每日工作流
├── monthly_workflow.py      # 月度工作流
└── workflow_engine.py       # 工作流引擎
```

## 与其他 Skills 集成

```
                    ┌─────────────────┐
                    │ Workflow Engine │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        v                    v                    v
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ Daily Workflow│  │Monthly Workflow│  │   Scheduler   │
└───────┬───────┘  └───────┬───────┘  └───────────────┘
        │                  │
        ├──────────────────┤
        │                  │
        v                  v
┌───────────────────────────────────────────────────────┐
│                    Skills Layer                       │
├─────────────┬─────────────┬─────────────┬────────────┤
│   Analyst   │    Risk     │    Coach    │  Observer  │
│ (技术分析)  │  (风控师)   │  (交易导师) │ (市场观察) │
└─────────────┴─────────────┴─────────────┴────────────┘
```

## 执行策略

### 任务优先级

| 优先级 | 范围 | 说明 |
|--------|------|------|
| 10 | 最高 | 市场观察、风险评估 |
| 8-9 | 高 | 技术分析、风险报告 |
| 6-7 | 中 | 交易计划、复盘 |
| 1-5 | 低 | 教育内容、辅助任务 |

### 依赖处理

1. 任务按优先级和依赖关系排序
2. 依赖未满足的任务将被跳过
3. 失败任务不影响独立任务执行
4. 成功率低于 50% 视为工作流失败

### 错误处理

1. 单任务失败不终止工作流
2. 记录所有错误信息
3. 生成包含成功/失败状态的汇总报告
4. 提供下一步操作建议

## 最佳实践

### 每日使用

1. **盘前**：8:30-9:00 执行盘前工作流
2. **盘中**：关注风控提醒
3. **盘后**：16:30 后执行盘后工作流

### 月度使用

1. 月末最后交易日自动触发月度工作流
2. 可手动使用 `--force` 参数随时执行
3. 结合月度报告制定下月计划

### 自动化建议

1. 使用 cron 或系统任务调度器定时执行
2. 配置通知推送关键报告
3. 定期检查工作流执行日志

---

*版本: 1.0*
*创建日期: 2025-12-15*
*作者: Python Expert Agent*
