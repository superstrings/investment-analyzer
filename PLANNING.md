# Investment Analyzer - 项目规划总览

> 本文件是 AI Agent 的核心导航文件，定义项目结构、开发流程和 Agent 职责

## 项目概述

**Investment Analyzer (投资分析自动化系统)** - 本地化投资分析工具
- 数据源: 富途 OpenAPI (持仓/成交) + akshare (K线)
- 功能: 自动数据采集、技术分析、K线图生成、报告输出
- 部署: Mac Mini M4 Pro 本地部署
- 交互: CLI + Claude Code Skills (无 Web 界面)

## 系统组件

| 组件 | 路径 | 说明 |
|-----|------|------|
| Config | `config/` | 全局配置 (settings.py, users.yaml) |
| Database | `db/` | SQLAlchemy ORM 模型与迁移 |
| Fetchers | `fetchers/` | 数据采集器 (富途/K线) |
| Analysis | `analysis/` | 技术指标计算 (MA/OBV/VCP) |
| Charts | `charts/` | K线图生成 (mplfinance) |
| Reports | `reports/` | 报告生成 (Jinja2 模板) |
| Services | `services/` | 业务逻辑服务层 |
| Skills | `skills/` | Claude Code Skills 定义 |
| Scripts | `scripts/` | 脚本工具 (初始化/同步) |

## 文档目录结构

```
docs/
├── investment-analyzer-design.md  # 需求与设计文档
├── api/                          # API 接口文档
├── database/                     # 数据库设计
│   └── schema.md
└── reports/                      # 生成的分析报告
```

## 标准开发流程

### 1. 需求分析阶段
- **负责**: Requirements Analyst Agent
- **输入**: 用户需求
- **输出**:
  - 功能概要设计 → `docs/features/`
  - 数据模型设计

### 2. 数据库设计阶段
- **负责**: Database Expert Agent
- **输入**: 详细设计文档
- **输出**:
  - DDL 脚本 → `db/migrations/`
  - 数据库文档 → `docs/database/`

### 3. 后端开发阶段
- **负责**: Python Expert Agent
- **方法**: 测试驱动开发
- **输出**:
  - 代码实现 → 各模块目录
  - 单元测试 → `tests/`

### 4. 集成测试与验证
- **测试**: pytest
- **验证**: 手动数据同步和报告生成

## Agent 会话规范

### 会话开始时
1. 运行 `pwd` 确认工作目录
2. 读取 `claude-progress.txt` 了解最近进展
3. 读取 `git log --oneline -10` 了解最近提交
4. 读取 `TASKS.md` 选择下一个任务

### 会话结束时
1. 确保代码处于可运行状态
2. 提交有描述性的 git commit
3. 更新 `claude-progress.txt` 记录本次工作
4. 更新 `TASKS.md` 任务状态
5. 更新 `TASKS_DONE.md` 归档已完成任务

### 增量开发原则
- **一次只做一件事**: 每次会话只完成一个功能/修复
- **先测试后标记**: 功能必须通过测试才能标记完成
- **小步提交**: 频繁提交，保持可回滚状态
- **文档同步**: 代码变更同步更新相关文档

## 关键文件说明

| 文件 | 用途 | 更新频率 |
|-----|------|---------|
| `CLAUDE.md` | Agent 核心指令 (精简版) | 低 - 架构变更时 |
| `PLANNING.md` | 项目结构与流程 (本文件) | 低 - 流程调整时 |
| `TASKS.md` | 当前任务列表 (JSON) | 高 - 每次会话 |
| `TASKS_DONE.md` | 已完成任务归档 | 中 - 任务完成时 |
| `claude-progress.txt` | 会话进度日志 | 高 - 每次会话 |

## 技术栈速查

```yaml
语言: Python 3.12.x (asdf 管理)
数据库: PostgreSQL 17 (Homebrew)
ORM: SQLAlchemy 2.0+
富途API: futu-api 9.0+
行情数据: akshare 1.10+
图表: mplfinance 0.12+
模板: Jinja2 3.1+
加密: cryptography
测试: pytest
格式化: black, isort
交互: CLI (无 Web 界面)
```

## 常用命令

```bash
# 环境管理 (asdf + venv)
asdf local python 3.12.7
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 数据库
python scripts/init_db.py
python main.py db-migrate

# 同步数据
python main.py sync --user dyson --type all

# 生成图表
python main.py chart --code HK.00700 --days 120

# 生成报告
python main.py report --user dyson --type portfolio

# 测试
python -m pytest tests/ -v
```

## Slash Commands 速查

| 类别 | 命令 | 说明 |
|------|------|------|
| 会话 | `/init-session` | 初始化会话 |
| 会话 | `/next-task` | 获取下一个任务 |
| 会话 | `/commit-work` | 提交工作 |
| 数据 | `/sync-data [type]` | 同步数据 |
| 数据 | `/fetch-klines [codes]` | 获取K线 |
| 分析 | `/gen-chart [code]` | 生成图表 |
| 分析 | `/gen-report [type]` | 生成报告 |
| 分析 | `/analyze-portfolio` | 持仓分析 |
| 开发 | `/dev-python [task]` | Python 开发 |
| 开发 | `/run-tests [pkg]` | 运行测试 |
| 文档 | `/analyze-feature [desc]` | 功能分析 |

## 里程碑规划

| 阶段 | 内容 | 状态 |
|------|------|------|
| **M1: 基础框架** | 项目结构、数据库、配置管理 | pending |
| **M2: 数据采集** | 富途Fetcher、K线Fetcher、数据同步 | pending |
| **M3: 图表生成** | K线图生成、技术指标叠加 | pending |
| **M4: 分析模块** | 技术指标计算、组合分析 | pending |
| **M5: Claude Skills** | 技能定义、集成测试 | pending |
| **M6: 完善优化** | 多用户测试、文档、优化 | pending |

---

*最后更新: 2025-12-14*
