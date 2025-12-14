# CLAUDE.md

> Claude Code 核心指令文件 - 保持精简，详细信息见 `PLANNING.md`

## 项目概述

**Investment Analyzer (投资分析自动化系统)** - 本地化投资分析工具

| 特性 | 说明 |
|------|------|
| **数据源** | 富途 OpenAPI + akshare |
| **数据库** | PostgreSQL 17 (Homebrew) |
| **图表** | mplfinance |
| **分析** | 技术指标 (MA/OBV/VCP/MACD/RSI) |
| **交互** | CLI + Claude Code Skills (无 Web 界面) |

---

## 会话工作流

### 1. 会话开始检查清单

```bash
# 1. 确认工作目录
pwd

# 2. 阅读项目规划 (必读!)
cat PLANNING.md

# 3. 查看最近进展
cat claude-progress.txt | tail -50

# 4. 查看当前任务
cat TASKS.md

# 5. 查看最近提交
git log --oneline -10
```

### 2. 任务规划流程

1. **检查 TASKS.md**: 确认任务是否已存在
2. **新任务**: 添加到 `TASKS.md` 并记录日期
3. **使用 TodoWrite**: 规划复杂任务时必须使用 TodoWrite 分解任务
4. **同步更新**: TodoWrite 和 TASKS.md 保持同步

### 3. 会话结束检查清单

```bash
# 1. 确保代码可运行
python -m pytest tests/ -v

# 2. 检查代码规范
python -m black --check .
python -m isort --check .

# 3. 检查所有变更文件
git status
git ls-files --others --exclude-standard

# 4. 更新任务状态
#    - 标记 TASKS.md 中已完成的任务为 completed
#    - 将已完成任务添加到 TASKS_DONE.md (表格格式)

# 5. 更新进度日志
echo "[$(date)] 完成xxx功能" >> claude-progress.txt

# 6. 提交变更 (必须!)
git add .
git commit -m "描述性消息"
```

**重要**:
- 任务完成后必须主动提交 git，不要等用户要求
- SQL 迁移文件需确保已添加到 git

---

## 核心文件导航

| 文件 | 用途 | 更新频率 |
|------|------|---------|
| `PLANNING.md` | 项目结构、开发流程、Agent 职责 | 低 |
| `TASKS.md` | 当前任务列表 (JSON 格式) | 高 |
| `TASKS_DONE.md` | 已完成任务归档 | 中 |
| `claude-progress.txt` | 会话进度日志 | 高 |

## 文档目录

```
docs/
├── design/            # 设计文档
│   └── investment-analyzer-design.md  # 需求与设计
├── api/               # API 接口文档
├── database/          # 数据库设计
└── reports/           # 分析报告输出
```

---

## 系统组件

| 组件 | 代码路径 | 说明 |
|-----|---------|------|
| Config | `config/` | 全局配置管理 |
| Database | `db/` | SQLAlchemy ORM 模型 |
| Fetchers | `fetchers/` | 数据采集 (富途/akshare) |
| Analysis | `analysis/` | 技术指标计算 |
| Charts | `charts/` | K线图生成 |
| Reports | `reports/` | 报告生成 |
| Services | `services/` | 业务逻辑服务层 |
| Skills | `skills/` | Claude Code Skills |

## 技术栈

```yaml
语言: Python 3.12.x (asdf 管理)
数据库: PostgreSQL 17 (Homebrew)
ORM: SQLAlchemy 2.0+
富途API: futu-api 9.0+
行情数据: akshare 1.10+
图表: mplfinance + matplotlib
报告: Jinja2 模板
AI助手: Claude Code
交互方式: CLI + Claude Code Skills (无 Web 界面)
```

---

## 常用命令

### 快速命令 (日常使用)

```bash
# 环境管理 (asdf)
asdf local python 3.12.7     # 设置项目 Python 版本
python -m venv .venv         # 创建虚拟环境
source .venv/bin/activate    # 激活虚拟环境
pip install -r requirements.txt  # 安装依赖

# 数据库
python scripts/init_db.py    # 初始化数据库
python main.py db-migrate    # 运行迁移

# 数据同步
python main.py sync --user dyson --type all
python main.py sync --user dyson --type positions
python main.py sync --user dyson --type klines --codes "HK.00700,US.NVDA"

# 图表生成
python main.py chart --code HK.00700 --days 120 --indicators ma,obv
python main.py chart --watchlist --user dyson

# 报告生成
python main.py report --user dyson --type portfolio
python main.py report --user dyson --type technical --codes "HK.00700"
```

### 测试命令

```bash
# 运行测试
python -m pytest tests/ -v
python -m pytest tests/ -v --cov=.

# 代码质量
python -m black .
python -m isort .
python -m flake8 .
```

---

## 专用 Agents (Sub-agents)

> 使用 Task 工具调用，指定 `subagent_type`

| Agent | Model | 用途 |
|-------|-------|------|
| `python-expert` | Opus | Python 后端开发 |
| `database-expert` | Opus | PostgreSQL 设计与迁移 |
| `data-analyst` | Opus | 数据分析与可视化 |
| `requirements-analyst` | Opus | 需求分析与设计文档 |
| `code-reviewer` | Opus | 代码审查与重构建议 |
| `codebase-explorer` | Sonnet | 代码搜索与理解 |

**调用示例**:
```
Task tool with subagent_type="python-expert" for Python development
Task tool with subagent_type="database-expert" for DB design
Task tool with subagent_type="data-analyst" for analysis
Task tool with subagent_type="Explore" for codebase exploration
```

---

## Slash Commands

> 位于 `.claude/commands/` 目录

### 会话管理
| 命令 | 说明 |
|------|------|
| `/init-session` | 会话初始化，读取进度和任务 |
| `/next-task` | 获取下一个待办任务 |
| `/commit-work` | 提交工作并更新进度日志 |

### 数据命令
| 命令 | 说明 |
|------|------|
| `/sync-data [type]` | 同步数据 (positions/trades/klines/all) |
| `/fetch-klines [codes]` | 获取指定股票K线数据 |

### 分析命令
| 命令 | 说明 |
|------|------|
| `/gen-chart [code]` | 生成单只股票K线图 |
| `/gen-report [type]` | 生成分析报告 |
| `/analyze-portfolio` | 分析当前持仓 |

### 开发命令
| 命令 | 说明 |
|------|------|
| `/dev-python [task]` | 调用 Python 专家执行开发任务 |
| `/run-tests [pkg]` | 运行指定包的测试 |
| `/review-code [path]` | 代码审查 |

### 文档命令
| 命令 | 说明 |
|------|------|
| `/analyze-feature [desc]` | 功能需求分析 |
| `/create-feature [desc]` | 创建功能需求文档 |

---

## 内置工具

| 工具 | 用途 |
|------|------|
| `Read` | 读取文件内容 |
| `Write` | 创建新文件 |
| `Edit` | 编辑现有文件 |
| `Glob` | 文件模式匹配搜索 |
| `Grep` | 文件内容搜索 |
| `Bash` | 执行 Shell 命令 |
| `Task` | 调用专用 Agent |
| `TodoWrite` | 任务分解与追踪 |
| `WebFetch` | 获取网页内容 |
| `WebSearch` | 网络搜索 |
| `AskUserQuestion` | 向用户提问 |
| `EnterPlanMode` | 进入规划模式 |

---

## 开发原则

### 任务管理

1. **TodoWrite 必用**: 复杂任务必须使用 TodoWrite 分解
2. **状态同步**: TodoWrite 和 TASKS.md 保持同步
3. **即时标记**: 任务完成后立即在 TASKS.md 中标记
4. **归档必做**: 任务完成后必须同时更新 TASKS_DONE.md (表格格式)
5. **发现记录**: 开发中发现的新任务添加到 TASKS.md "发现的工作" 部分

**任务完成检查清单** (每个任务完成后必须执行):
- [ ] TASKS.md 中标记 status: completed, progress: 100
- [ ] TASKS_DONE.md 中添加一行记录 (ID, 任务, 完成日期, 主要产出)
- [ ] claude-progress.txt 中记录进度

### 代码开发

1. **增量开发**: 每次只完成一个功能
2. **测试先行**: 功能必须有测试覆盖
3. **小步提交**: 频繁 commit，保持可回滚
4. **文档同步**: 代码变更同步更新文档

### Python 规范

- Python 3.12.x 特性 (asdf 管理版本)
- 类型注解 (Type Hints)
- 使用 Black 格式化
- 使用 isort 排序导入
- 结构化日志 (logging)
- 错误处理使用自定义异常类

---

## AI 行为准则

1. **不假设上下文**: 不确定时主动提问，必要时使用 Plan Mode
2. **不虚构依赖**: 只使用已知存在的库和函数
3. **确认路径**: 引用文件前确认其存在
4. **不删除代码**: 除非明确指示或 TASKS.md 任务要求
5. **使用相对路径**: 文档引用统一使用相对路径

---

## 数据库配置 (开发环境)

| 配置项 | 值 |
|--------|-----|
| Host | localhost |
| Port | 5432 |
| Database | investment_db |
| User | (见 .env) |
| Password | (见 .env) |

---

## 详细文档索引

- **需求设计**: `docs/investment-analyzer-design.md`
- **数据库 Schema**: `docs/database/schema.md`
- **API 文档**: `docs/api/`

---

*详细信息请查阅 `PLANNING.md` 和对应的 `docs/` 子目录*
*最后更新: 2025-12-14*
