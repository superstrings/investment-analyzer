# Claude Code 开发指南

> Investment Analyzer - "自动化工厂" 开发模式

## 1. 概述

本项目采用 Claude Code "自动化工厂" 开发模式，通过结构化的指令文件、任务管理和子代理系统，实现 AI 辅助的高效开发。

### 1.1 核心理念

- **指令驱动**: 通过 `CLAUDE.md` 定义 AI 行为准则
- **任务追踪**: 使用 `TASKS.md` JSON 格式管理任务
- **进度记录**: `claude-progress.txt` 记录会话进展
- **专业分工**: 子代理处理不同领域任务

### 1.2 文件结构

```
investment-analyzer/
├── CLAUDE.md           # 核心指令文件 (必读)
├── PLANNING.md         # 项目规划总览
├── TASKS.md            # 任务列表 (JSON 格式)
├── TASKS_DONE.md       # 已完成任务归档
├── claude-progress.txt # 会话进度日志
└── .claude/
    ├── agents/         # 子代理定义
    │   ├── python-expert.md
    │   ├── database-expert.md
    │   ├── data-analyst.md
    │   └── ...
    ├── commands/       # Slash 命令
    │   ├── init-session.md
    │   ├── next-task.md
    │   ├── commit-work.md
    │   └── ...
    └── settings.local.json  # 本地权限配置
```

## 2. 核心文件说明

### 2.1 CLAUDE.md

Claude Code 的核心指令文件，定义:

- 项目概述和技术栈
- 会话工作流程 (开始/结束检查清单)
- 常用命令
- 子代理列表
- 开发原则
- AI 行为准则

**重要**: 每次会话开始时 Claude 会自动读取此文件。

### 2.2 TASKS.md

JSON 格式的任务列表，结构:

```json
{
  "phase": "M1_foundation",
  "description": "基础框架搭建",
  "tasks": [
    {
      "id": "T001",
      "category": "setup",
      "title": "项目目录结构创建",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [...],
      "files": [...]
    }
  ]
}
```

**状态值**:
- `pending`: 待开始
- `in_progress`: 进行中
- `completed`: 已完成
- `blocked`: 已阻塞

**优先级**:
- `P0`: 最高 (阻塞性任务)
- `P1`: 高 (核心功能)
- `P2`: 中 (增强功能)
- `P3`: 低 (优化/文档)

### 2.3 claude-progress.txt

会话进度日志，格式:

```
[2025-12-14 22:53] T006 完成 - 实现 main.py CLI 入口, 42 tests
[2025-12-14 23:06] T010 完成 - 实现 CSV 数据导入, 75 tests
```

每次会话结束时追加记录。

### 2.4 TASKS_DONE.md

已完成任务归档，表格格式:

```markdown
| ID | 任务 | 完成日期 | 主要产出 |
|----|------|---------|---------|
| T001 | 项目目录结构创建 | 2025-12-14 | 10个模块目录 |
```

## 3. Slash 命令

### 3.1 会话管理

| 命令 | 说明 |
|------|------|
| `/init-session` | 会话初始化，读取进度和任务 |
| `/next-task` | 获取下一个待办任务 |
| `/commit-work` | 提交工作并更新进度日志 |

### 3.2 开发命令

| 命令 | 说明 |
|------|------|
| `/dev-python [task]` | 调用 Python 专家执行任务 |
| `/run-tests [pkg]` | 运行指定包的测试 |
| `/review-code [path]` | 代码审查 |

### 3.3 数据命令

| 命令 | 说明 |
|------|------|
| `/sync-data [type]` | 同步数据 |
| `/fetch-klines [codes]` | 获取 K 线 |
| `/gen-chart [code]` | 生成图表 |
| `/gen-report [type]` | 生成报告 |

## 4. 子代理系统

### 4.1 可用代理

| 代理 | Model | 用途 |
|------|-------|------|
| `python-expert` | Opus | Python 后端开发 |
| `database-expert` | Opus | PostgreSQL 设计 |
| `data-analyst` | Opus | 数据分析可视化 |
| `requirements-analyst` | Opus | 需求分析 |
| `code-reviewer` | Opus | 代码审查 |
| `codebase-explorer` | Sonnet | 代码搜索 |

### 4.2 调用方式

```
使用 Task 工具，指定 subagent_type="python-expert"
```

### 4.3 代理职责

**python-expert**:
- 核心功能实现
- 数据处理
- API 开发
- 性能优化

**database-expert**:
- Schema 设计
- 迁移脚本
- 查询优化
- 索引策略

**data-analyst**:
- 技术指标计算
- K线图生成
- 投资组合分析
- 报告生成

## 5. 工作流程

### 5.1 会话开始

```bash
# Claude 自动执行
1. 读取 CLAUDE.md
2. 读取 PLANNING.md
3. 查看 claude-progress.txt (最近进展)
4. 查看 TASKS.md (当前任务)
5. 查看 git log (最近提交)
```

### 5.2 任务执行

```
1. 选择任务 (从 TASKS.md)
2. 使用 TodoWrite 分解任务
3. 逐步实现功能
4. 编写测试
5. 运行测试验证
6. 更新 TASKS.md 状态
```

### 5.3 会话结束

```bash
# 必须执行
1. python -m pytest tests/ -v  # 验证测试
2. python -m black .           # 格式化
3. python -m isort .           # 排序导入
4. git status                  # 检查变更
5. 更新 TASKS.md               # 标记完成
6. 更新 TASKS_DONE.md          # 归档任务
7. echo "[date] ..." >> claude-progress.txt
8. git add . && git commit -m "..."
```

## 6. 任务管理最佳实践

### 6.1 使用 TodoWrite

复杂任务必须使用 TodoWrite 分解:

```python
# 示例: 实现 VCP 形态识别
TodoWrite([
    {"content": "定义 VCP 数据类", "status": "in_progress"},
    {"content": "实现 swing 检测", "status": "pending"},
    {"content": "实现 contraction 分析", "status": "pending"},
    {"content": "实现评分系统", "status": "pending"},
    {"content": "创建测试用例", "status": "pending"},
])
```

### 6.2 及时更新状态

- 开始任务: 立即标记 `in_progress`
- 完成任务: 立即标记 `completed`
- 发现新工作: 添加到 TASKS.md

### 6.3 归档已完成任务

完成后立即更新:
1. TASKS.md: status=completed, progress=100
2. TASKS_DONE.md: 添加一行记录
3. claude-progress.txt: 追加日志

## 7. Claude Skills

### 7.1 Skills 目录

```
skills/
├── portfolio_analyzer/
│   └── SKILL.md         # 组合分析技能
├── technical_analyzer/
│   └── SKILL.md         # 技术分析技能
└── report_generator/
    └── SKILL.md         # 报告生成技能
```

### 7.2 SKILL.md 结构

```markdown
# 技能名称

## 能力描述
说明此技能的功能

## 数据来源
- 数据库表
- Python 模块
- 输出目录

## 使用方法
### Python API
代码示例

### CLI 命令
命令示例

## 输出格式
示例输出
```

## 8. 开发原则

### 8.1 任务管理

- TodoWrite 必用于复杂任务
- 状态即时同步
- 发现即记录

### 8.2 代码开发

- 增量开发，小步提交
- 测试先行或同步
- 文档同步更新

### 8.3 AI 行为

- 不假设上下文，不确定时提问
- 不虚构依赖，确认路径存在
- 不删除代码，除非明确指示

## 9. 示例工作流

### 9.1 新功能开发

```
1. /next-task              # 获取任务
2. 阅读任务详情
3. TodoWrite 分解任务
4. 实现核心功能
5. 编写测试
6. pytest 验证
7. 更新 TASKS.md
8. /commit-work            # 提交工作
```

### 9.2 Bug 修复

```
1. 分析问题
2. 定位代码
3. 修复问题
4. 添加测试
5. 验证修复
6. 提交变更
```

---

## 附录: 权限配置

`.claude/settings.local.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(python:*)",
      "Bash(pip:*)",
      "Bash(pytest:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)",
      "Bash(git status:*)",
      ...
    ]
  }
}
```

---

*文档版本: 1.0*
*最后更新: 2025-12-14*
