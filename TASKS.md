# 任务追踪

> JSON 格式任务列表，Agent 只能修改 `status` 和 `progress` 字段

## 使用说明

- **status**: `pending` | `in_progress` | `completed` | `blocked`
- **priority**: `P0` (最高) | `P1` (高) | `P2` (中) | `P3` (低)
- **progress**: 0-100 百分比
- 完成的任务移动到 `TASKS_DONE.md`

---

## 当前阶段: M1 - 基础框架

```json
{
  "phase": "M1_foundation",
  "description": "基础框架搭建 (参考 docs/investment-analyzer-design.md)",
  "start_date": "2025-12-14",
  "tasks": [
    {
      "id": "T001",
      "category": "setup",
      "title": "项目目录结构创建",
      "description": "创建完整的项目目录结构，包括所有模块目录",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "创建 config/ 目录 + __init__.py",
        "创建 db/ 目录 + migrations/ + __init__.py",
        "创建 fetchers/ 目录 + __init__.py",
        "创建 analysis/ 目录 + indicators/ + __init__.py",
        "创建 charts/ 目录 + output/ + __init__.py",
        "创建 reports/ 目录 + templates/ + output/ + __init__.py",
        "创建 services/ 目录 + __init__.py",
        "创建 skills/ 目录 + 3个 SKILL.md",
        "创建 scripts/ 目录",
        "创建 tests/ 目录 + __init__.py",
        "创建 main.py CLI 入口"
      ],
      "files": [
        "config/__init__.py",
        "db/__init__.py",
        "fetchers/__init__.py",
        "analysis/__init__.py",
        "analysis/indicators/__init__.py",
        "charts/__init__.py",
        "reports/__init__.py",
        "services/__init__.py",
        "tests/__init__.py",
        "skills/*/SKILL.md",
        "main.py"
      ]
    },
    {
      "id": "T002",
      "category": "setup",
      "title": "Python 环境配置",
      "description": "配置 Python 3.12.x (asdf) 虚拟环境和依赖管理",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "设置 asdf set python 3.12.7",
        "创建 .tool-versions 文件",
        "创建 .venv 虚拟环境",
        "创建 requirements.txt (所有依赖)",
        "创建 .env.example (环境变量模板)",
        "创建 pyproject.toml (项目配置)",
        "配置 pytest (pyproject.toml)",
        "配置 black/isort (pyproject.toml)",
        "创建 .gitignore",
        "安装核心依赖 (click, pyyaml, python-dotenv)",
        "安装开发依赖 (pytest, black, isort, flake8)",
        "创建 tests/test_main.py (5个测试用例)",
        "验证所有测试通过"
      ],
      "files": [
        ".tool-versions",
        "requirements.txt",
        ".env.example",
        "pyproject.toml",
        ".gitignore",
        "tests/test_main.py"
      ]
    },
    {
      "id": "T003",
      "category": "config",
      "title": "配置管理模块",
      "description": "实现配置加载和管理功能",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 settings.py 全局配置 (dataclass + dotenv)",
        "实现 users.yaml 用户配置",
        "实现 users.py 配置加载器",
        "实现环境变量加载 (DATABASE_URL, FUTU_PWD_*)",
        "实现配置验证 (端口范围、市场、kline_days)",
        "创建 tests/test_config.py (22个测试用例)",
        "验证所有测试通过 (27 passed)"
      ],
      "files": [
        "config/__init__.py",
        "config/settings.py",
        "config/users.py",
        "config/users.yaml",
        "tests/test_config.py"
      ]
    },
    {
      "id": "T004",
      "category": "database",
      "title": "数据库模型定义",
      "description": "使用 SQLAlchemy 定义所有数据库模型",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 database.py 连接管理 (engine, session, pool)",
        "实现 users 表模型",
        "实现 accounts 表模型",
        "实现 positions 表模型",
        "实现 trades 表模型",
        "实现 account_snapshots 表模型",
        "实现 klines 表模型 (含预计算指标)",
        "实现 watchlist 表模型",
        "实现 sync_logs 表模型",
        "创建 tests/test_db.py (22个测试用例)",
        "验证所有测试通过 (49 passed)"
      ],
      "files": [
        "db/__init__.py",
        "db/database.py",
        "db/models.py",
        "tests/test_db.py"
      ],
      "reference": "docs/investment-analyzer-design.md#四数据库设计"
    },
    {
      "id": "T005",
      "category": "database",
      "title": "数据库初始化脚本",
      "description": "创建数据库初始化和迁移脚本",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "创建 init_schema.sql (8表 + 触发器 + 索引)",
        "创建 init_db.py CLI 脚本 (7个命令)",
        "实现 create-db/drop-db 数据库管理",
        "实现 init/reset 表初始化",
        "实现 check/status 连接检查",
        "实现 seed 测试数据填充",
        "测试数据库连接 (PostgreSQL 17.7)",
        "创建 tests/test_init_db.py (11个测试用例)",
        "验证所有测试通过 (60 passed)"
      ],
      "files": [
        "db/migrations/init_schema.sql",
        "scripts/init_db.py",
        "tests/test_init_db.py"
      ]
    },
    {
      "id": "T006",
      "category": "setup",
      "title": "主程序入口",
      "description": "创建 CLI 主程序入口",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 main.py CLI 框架 (Click)",
        "实现 sync 命令组 (all/positions/trades/klines)",
        "实现 chart 命令组 (single/watchlist/positions)",
        "实现 report 命令组 (portfolio/technical)",
        "实现 account 命令组 (list/info)",
        "实现 db 命令组 (check/init/seed/migrate)",
        "实现 config 命令组 (show/users)",
        "实现用户验证 (validate_user callback)",
        "实现 verbose 模式 (-v flag)",
        "创建 tests/test_main.py (42个测试用例)",
        "验证所有测试通过 (293 passed)"
      ],
      "files": [
        "main.py",
        "tests/test_main.py"
      ]
    }
  ]
}
```

---

## 阶段 M2: 数据采集

```json
{
  "phase": "M2_data_fetching",
  "description": "数据采集模块开发",
  "tasks": [
    {
      "id": "T007",
      "category": "fetcher",
      "title": "富途数据采集器",
      "description": "实现 FutuFetcher 类，从富途 API 获取持仓和交易数据",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 fetchers/base.py 基类和数据类型",
        "实现连接管理 (connect/disconnect/context manager)",
        "实现 unlock_trade() 解锁交易",
        "实现 get_account_list() 获取账户列表",
        "实现 get_positions() 获取持仓",
        "实现 get_account_info() 获取账户资金",
        "实现 get_today_deals() 获取今日成交",
        "实现 get_history_deals() 获取历史成交",
        "实现 create_futu_fetcher() 工厂函数",
        "创建 tests/test_fetchers.py (31个测试用例)",
        "验证所有测试通过 (91 passed)"
      ],
      "files": [
        "fetchers/__init__.py",
        "fetchers/base.py",
        "fetchers/futu_fetcher.py",
        "tests/test_fetchers.py"
      ]
    },
    {
      "id": "T008",
      "category": "fetcher",
      "title": "K线数据采集器",
      "description": "实现 KlineFetcher 类，从 akshare 获取K线数据",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 KlineData 数据类 (OHLCV + 额外指标)",
        "实现 KlineFetchResult 扩展结果类",
        "实现港股K线获取 (_fetch_hk)",
        "实现美股K线获取 (_fetch_us)",
        "实现A股K线获取 (_fetch_a_share)",
        "实现市场自动识别 (_parse_code, detect_market)",
        "实现数据格式标准化 (各市场列名映射)",
        "实现批量获取 (fetch_batch)",
        "实现 create_kline_fetcher() 工厂函数",
        "创建 tests/test_kline_fetcher.py (34个测试用例)",
        "验证所有测试通过 (125 passed)"
      ],
      "files": [
        "fetchers/kline_fetcher.py",
        "tests/test_kline_fetcher.py"
      ]
    },
    {
      "id": "T009",
      "category": "service",
      "title": "数据同步服务",
      "description": "实现 SyncService，协调数据同步流程",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 SyncResult 数据类",
        "实现 SyncService 类",
        "实现 sync_positions() 持仓同步",
        "实现 sync_trades() 交易同步",
        "实现 sync_klines() K线同步",
        "实现 sync_watchlist_klines() 关注列表K线",
        "实现 sync_position_klines() 持仓K线",
        "实现 sync_all() 全量同步",
        "实现增量同步 (通过deal_id/日期去重)",
        "实现同步日志记录 (SyncLog)",
        "实现 get_last_sync() 查询最近同步",
        "实现 create_sync_service() 工厂函数",
        "创建 tests/test_sync_service.py (24个测试用例)",
        "验证所有测试通过 (149 passed)"
      ],
      "files": [
        "services/__init__.py",
        "services/sync_service.py",
        "tests/test_sync_service.py"
      ]
    },
    {
      "id": "T010",
      "category": "script",
      "title": "CSV 数据导入",
      "description": "创建现有 CSV 数据导入脚本",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 scripts/import_csv.py 导入脚本",
        "实现 import_watchlist() 关注列表导入",
        "实现 import_positions() 持仓导入",
        "实现 import_trades() 交易记录导入",
        "实现灵活的列名映射 (中英文别名)",
        "实现多种日期格式支持",
        "实现 ImportResult 数据类",
        "实现代码格式自动识别 (HK/US/A股)",
        "添加 main.py import 命令组 (watchlist/positions/trades/formats)",
        "创建 tests/test_import_csv.py (63个测试用例)",
        "更新 tests/test_main.py (12个新测试用例)",
        "验证所有测试通过 (366 passed)"
      ],
      "files": [
        "scripts/import_csv.py",
        "main.py",
        "tests/test_import_csv.py",
        "tests/test_main.py"
      ]
    }
  ]
}
```

---

## 阶段 M3: 图表生成

```json
{
  "phase": "M3_charts",
  "description": "图表生成模块开发",
  "tasks": [
    {
      "id": "T011",
      "category": "chart",
      "title": "K线图生成器",
      "description": "实现 ChartGenerator 类，生成K线图",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 ChartStyle 样式配置类",
        "实现预定义样式 (dark/light/chinese/western)",
        "实现 ChartConfig 图表配置类",
        "实现 ChartGenerator 类",
        "实现基础K线图 (mplfinance)",
        "实现均线叠加 (MA5/10/20/60等)",
        "实现成交量叠加面板",
        "实现自定义样式 (颜色/字体/尺寸)",
        "实现 PNG 导出",
        "实现批量图表生成 (generate_batch)",
        "实现 KlineData 转 DataFrame",
        "实现 create_chart_generator() 工厂函数",
        "创建 tests/test_charts.py (38个测试用例)",
        "验证所有测试通过 (187 passed)"
      ],
      "files": [
        "charts/__init__.py",
        "charts/generator.py",
        "charts/styles.py",
        "tests/test_charts.py"
      ]
    },
    {
      "id": "T012",
      "category": "chart",
      "title": "批量图表生成",
      "description": "支持批量生成多只股票图表",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 ChartService 服务类",
        "实现 ChartResult 和 BatchChartConfig 数据类",
        "实现 generate_watchlist_charts() 关注列表图表生成",
        "实现 generate_position_charts() 持仓股票图表生成",
        "实现 generate_charts_for_codes() 通用批量生成",
        "实现 create_chart_service() 工厂函数",
        "更新 services/__init__.py 导出 ChartService",
        "重构 main.py chart watchlist/positions 使用 ChartService",
        "创建 tests/test_chart_service.py (20个测试用例)",
        "验证所有测试通过 (386 passed)"
      ],
      "files": [
        "services/chart_service.py",
        "services/__init__.py",
        "main.py",
        "tests/test_chart_service.py"
      ]
    }
  ]
}
```

---

## 阶段 M4: 分析模块

```json
{
  "phase": "M4_analysis",
  "description": "技术分析模块开发",
  "tasks": [
    {
      "id": "T013",
      "category": "analysis",
      "title": "技术指标计算",
      "description": "实现常用技术指标计算",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 BaseIndicator 基类和 IndicatorResult 数据类",
        "实现 MA (移动平均线): SMA, EMA, WMA, MA 类",
        "实现 OBV (能量潮): OBV, OBVDivergence 类",
        "实现 MACD: MACD, MACDCrossover, MACDHistogramDivergence 类",
        "实现 RSI: RSI, StochasticRSI, RSIDivergence 类",
        "实现布林带: BollingerBands, BollingerBandsSqueeze, BollingerBandsSignals 类",
        "实现 TechnicalAnalyzer 聚合分析器",
        "实现 AnalysisConfig, AnalysisResult 配置和结果类",
        "实现便捷函数 (calculate_sma, calculate_ema, calculate_rsi 等)",
        "创建 tests/test_indicators.py (69个测试用例)",
        "验证所有测试通过 (256 passed)"
      ],
      "files": [
        "analysis/__init__.py",
        "analysis/technical.py",
        "analysis/indicators/__init__.py",
        "analysis/indicators/base.py",
        "analysis/indicators/ma.py",
        "analysis/indicators/obv.py",
        "analysis/indicators/macd.py",
        "analysis/indicators/rsi.py",
        "analysis/indicators/bollinger.py",
        "tests/test_indicators.py"
      ]
    },
    {
      "id": "T014",
      "category": "analysis",
      "title": "VCP 形态识别",
      "description": "实现 VCP (波动收缩形态) 识别",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "subtasks": [
        "定义 VCP 识别规则",
        "实现形态扫描",
        "实现评分系统"
      ],
      "files": [
        "analysis/indicators/vcp.py"
      ]
    },
    {
      "id": "T015",
      "category": "analysis",
      "title": "组合分析",
      "description": "实现投资组合分析功能",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "subtasks": [
        "实现仓位分析",
        "实现盈亏分析",
        "实现风险评估",
        "实现账户汇总"
      ],
      "files": [
        "analysis/portfolio.py"
      ]
    }
  ]
}
```

---

## 阶段 M5: Claude Skills

```json
{
  "phase": "M5_skills",
  "description": "Claude Code Skills 开发",
  "tasks": [
    {
      "id": "T016",
      "category": "skill",
      "title": "Portfolio Analyzer Skill",
      "description": "持仓分析技能",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "files": [
        "skills/portfolio_analyzer/SKILL.md"
      ]
    },
    {
      "id": "T017",
      "category": "skill",
      "title": "Technical Analyzer Skill",
      "description": "技术分析技能",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "files": [
        "skills/technical_analyzer/SKILL.md"
      ]
    },
    {
      "id": "T018",
      "category": "skill",
      "title": "Report Generator Skill",
      "description": "报告生成技能",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "files": [
        "skills/report_generator/SKILL.md"
      ]
    }
  ]
}
```

---

## 阶段 M6: 报告生成

```json
{
  "phase": "M6_reports",
  "description": "报告生成模块开发",
  "tasks": [
    {
      "id": "T019",
      "category": "report",
      "title": "报告生成器",
      "description": "实现报告生成功能",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "subtasks": [
        "实现 Jinja2 模板引擎",
        "实现持仓报告模板",
        "实现技术分析报告模板",
        "实现 Markdown 输出"
      ],
      "files": [
        "reports/__init__.py",
        "reports/generator.py",
        "reports/templates/portfolio.md.j2",
        "reports/templates/technical.md.j2"
      ]
    }
  ]
}
```

---

## 快速查看

### 按优先级

| ID | 任务 | 优先级 | 状态 | 进度 |
|----|------|--------|------|------|
| T001 | 项目目录结构创建 | P0 | ✅ completed | 100% |
| T002 | Python 环境配置 (asdf + venv) | P0 | ✅ completed | 100% |
| T003 | 配置管理模块 | P0 | ✅ completed | 100% |
| T004 | 数据库模型定义 | P0 | ✅ completed | 100% |
| T005 | 数据库初始化脚本 | P0 | ✅ completed | 100% |
| T007 | 富途数据采集器 | P0 | ✅ completed | 100% |
| T008 | K线数据采集器 | P0 | ✅ completed | 100% |
| T009 | 数据同步服务 | P0 | ✅ completed | 100% |
| T011 | K线图生成器 | P0 | ✅ completed | 100% |
| T013 | 技术指标计算 | P0 | ✅ completed | 100% |
| T006 | 主程序入口 | P1 | ✅ completed | 100% |
| T010 | CSV 数据导入 | P1 | ✅ completed | 100% |
| T012 | 批量图表生成 | P1 | ✅ completed | 100% |
| T014 | VCP 形态识别 | P1 | pending | 0% |
| T015 | 组合分析 | P1 | pending | 0% |
| T016 | Portfolio Analyzer Skill | P1 | pending | 0% |
| T017 | Technical Analyzer Skill | P1 | pending | 0% |
| T018 | Report Generator Skill | P1 | pending | 0% |
| T019 | 报告生成器 | P1 | pending | 0% |

### 按状态

- **已完成**: T001, T002, T003, T004, T005, T006, T007, T008, T009, T010, T011, T012, T013
- **进行中**: 无
- **待开始**: T014-T019
- **已阻塞**: 无

### 参考文档

- 详细设计: `docs/investment-analyzer-design.md`

---

*最后更新: 2025-12-14*
