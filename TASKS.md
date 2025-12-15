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
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "定义 VCP 识别规则 (波动收缩检测)",
        "实现 Contraction 和 VCPResult 数据类",
        "实现 VCPConfig 配置类",
        "实现 VCP 类 (swing detection, contraction detection)",
        "实现深度递减检测 (depth decrease)",
        "实现成交量趋势分析 (volume dry-up)",
        "实现波动幅度收缩分析",
        "实现 pivot 价格检测",
        "实现 VCP 评分系统 (0-100)",
        "实现 VCPScanner 扫描器",
        "实现便捷函数 (detect_vcp, scan_vcp)",
        "创建 tests/test_vcp.py (43个测试用例)",
        "更新 analysis/indicators/__init__.py 导出",
        "更新 analysis/__init__.py 导出",
        "验证所有测试通过 (429 passed)"
      ],
      "files": [
        "analysis/indicators/vcp.py",
        "analysis/indicators/__init__.py",
        "analysis/__init__.py",
        "tests/test_vcp.py"
      ]
    },
    {
      "id": "T015",
      "category": "analysis",
      "title": "组合分析",
      "description": "实现投资组合分析功能",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 PositionData 和 AccountData 输入数据类",
        "实现 PositionMetrics 持仓指标计算",
        "实现 PortfolioSummary 组合摘要",
        "实现 MarketAllocation 市场分布分析",
        "实现 RiskMetrics 风险评估 (HHI, 集中度, 最大亏损)",
        "实现 PortfolioAnalyzer 核心分析器",
        "实现仓位权重和P&L计算",
        "实现 Top/Bottom performers 排名",
        "实现风险信号生成",
        "实现 analyze_portfolio 便捷函数",
        "实现 analyze_positions_from_db 数据库对象分析",
        "创建 tests/test_portfolio.py (50个测试用例)",
        "验证所有测试通过 (479 passed)"
      ],
      "files": [
        "analysis/portfolio.py",
        "analysis/__init__.py",
        "tests/test_portfolio.py"
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
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "更新 SKILL.md 详细文档",
        "添加 Python API 使用示例",
        "添加 CLI 命令说明",
        "添加分析维度说明 (仓位/盈亏/风险)",
        "添加输出数据结构文档",
        "添加风险信号示例",
        "添加报告模板 (持仓明细/市场配比/风险评分)"
      ],
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
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "更新 SKILL.md 详细文档",
        "添加 Python API 使用示例",
        "添加 CLI 命令说明",
        "添加技术指标文档 (MA/RSI/MACD/BB/OBV/VCP)",
        "添加评分标准说明",
        "添加输出格式模板"
      ],
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
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "更新 SKILL.md 详细文档",
        "添加报告类型说明 (持仓/技术/每日/周度)",
        "添加 Python API 使用示例",
        "添加 CLI 命令说明",
        "添加输出格式说明 (Markdown/JSON/HTML)",
        "添加报告模板 (持仓明细/技术指标/风险评估)",
        "添加图表集成说明"
      ],
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
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 ReportType/OutputFormat 枚举",
        "实现 ReportConfig 和 ReportResult 数据类",
        "实现 ReportGenerator 类",
        "实现 Jinja2 模板引擎集成",
        "实现自定义过滤器 (format_number, format_percent, format_currency, format_date)",
        "实现持仓报告 (generate_portfolio_report)",
        "实现技术分析报告 (generate_technical_report)",
        "实现每日简报 (generate_daily_brief)",
        "实现周度回顾 (generate_weekly_review)",
        "创建 4 个 Jinja2 模板 (portfolio, technical, daily, weekly)",
        "实现 fallback 模板 (当模板文件不存在时)",
        "实现 generate_report 便捷函数",
        "创建 tests/test_reports.py (47个测试用例)",
        "验证所有测试通过 (526 passed)"
      ],
      "files": [
        "reports/__init__.py",
        "reports/generator.py",
        "reports/templates/portfolio.md.j2",
        "reports/templates/technical.md.j2",
        "reports/templates/daily.md.j2",
        "reports/templates/weekly.md.j2",
        "tests/test_reports.py"
      ]
    }
  ]
}
```

---

## 阶段 M7: 质量保障

```json
{
  "phase": "M7_quality",
  "description": "集成测试、真实数据验证、CLI优化",
  "tasks": [
    {
      "id": "T020",
      "category": "testing",
      "title": "端到端集成测试",
      "description": "实现完整数据流程的集成测试",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "创建 tests/integration/ 目录",
        "实现数据采集→存储→分析→图表完整流程测试",
        "实现报告生成集成测试",
        "实现数据一致性验证测试",
        "实现错误处理和恢复测试",
        "创建测试数据固件 (fixtures)",
        "验证所有 29 个集成测试通过"
      ],
      "files": [
        "tests/integration/__init__.py",
        "tests/integration/test_data_flow.py",
        "tests/integration/test_report_flow.py",
        "tests/integration/conftest.py"
      ]
    },
    {
      "id": "T021",
      "category": "testing",
      "title": "富途 API 真实数据测试",
      "description": "使用真实富途 API 进行端到端验证",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "测试 OpenD 连接 (127.0.0.1:11111)",
        "获取账户列表 (2个真实账户, 2个模拟账户)",
        "同步持仓数据 (17条记录)",
        "同步交易记录 (319条记录)",
        "同步K线数据 (656条记录)",
        "验证数据库存储正确性"
      ],
      "files": [
        ".env",
        "config/users.yaml"
      ],
      "note": "需要富途 OpenD 运行环境"
    },
    {
      "id": "T022",
      "category": "cli",
      "title": "CLI 增强优化",
      "description": "改进 CLI 交互体验和功能",
      "priority": "P1",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "添加 rich>=13.0.0 和 tqdm>=4.66.0 依赖",
        "实现 cli/utils.py (OutputFormat, print_success/error/warning/info)",
        "实现 print_table (rich Table 输出)",
        "实现 format_output (JSON/CSV/Table 格式化)",
        "实现 create_progress (rich 进度条)",
        "实现 format_pnl/format_percent 辅助函数",
        "更新 main.py (report/db/account/config 命令使用 rich 输出)",
        "添加 --format 选项 (table/json/csv)",
        "创建 tests/test_cli_utils.py (33个测试用例)",
        "验证所有测试通过"
      ],
      "files": [
        "main.py",
        "cli/__init__.py",
        "cli/utils.py",
        "requirements.txt",
        "tests/test_cli_utils.py"
      ]
    }
  ]
}
```

---

## 阶段 M8: 功能增强

```json
{
  "phase": "M8_enhancement",
  "description": "新功能开发",
  "tasks": [
    {
      "id": "T023",
      "category": "feature",
      "title": "价格提醒系统",
      "description": "实现股票价格提醒功能",
      "priority": "P2",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "添加 PriceAlert 模型到 db/models.py",
        "添加 User.price_alerts 关系",
        "实现 AlertType 枚举 (ABOVE/BELOW/CHANGE_UP/CHANGE_DOWN)",
        "实现 AlertResult 和 AlertSummary 数据类",
        "实现 AlertService 类 (CRUD + check_alert + trigger_alert)",
        "实现 check_all_alerts 批量检查",
        "实现 reset_alert 重置功能",
        "添加 CLI 命令组 (alert add/list/delete/check)",
        "创建 tests/test_alerts.py (37个测试用例)",
        "验证所有 625 个测试通过"
      ],
      "files": [
        "db/models.py",
        "db/__init__.py",
        "services/alert_service.py",
        "services/__init__.py",
        "main.py",
        "tests/test_alerts.py"
      ]
    },
    {
      "id": "T024",
      "category": "feature",
      "title": "回测框架",
      "description": "实现简单的策略回测功能",
      "priority": "P2",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "设计回测引擎架构",
        "实现 Strategy 基类 (Signal, Trade, Position, BacktestResult)",
        "实现 BacktestEngine 引擎",
        "实现回测结果计算 (收益率/夏普/索提诺/卡玛/最大回撤)",
        "实现 MACrossStrategy 均线交叉策略",
        "实现 VCPBreakoutStrategy VCP突破策略",
        "实现回测报告生成 (Text/Markdown/JSON)",
        "添加 CLI 命令组 (backtest run/strategies/compare)",
        "创建 tests/test_backtest.py (30个测试用例)",
        "验证所有 655 个测试通过"
      ],
      "files": [
        "backtest/__init__.py",
        "backtest/engine.py",
        "backtest/strategy.py",
        "backtest/report.py",
        "backtest/strategies/__init__.py",
        "backtest/strategies/ma_cross.py",
        "backtest/strategies/vcp_breakout.py",
        "main.py",
        "tests/test_backtest.py"
      ]
    },
    {
      "id": "T025",
      "category": "analysis",
      "title": "更多技术形态识别",
      "description": "扩展技术形态识别能力",
      "priority": "P2",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现杯柄形态 (CupAndHandle)",
        "实现头肩顶/底形态 (HeadAndShoulders)",
        "实现双顶/双底形态 (DoubleTopBottom)",
        "实现三角形整理形态 (TrianglePattern)",
        "实现支撑阻力位识别 (SupportResistance)",
        "实现趋势线自动绘制 (TrendlineDetector)",
        "创建 PatternScanner 形态扫描器",
        "创建 tests/test_patterns.py (64个测试用例)",
        "验证所有 719 个测试通过"
      ],
      "files": [
        "analysis/indicators/patterns.py",
        "analysis/indicators/support_resistance.py",
        "analysis/indicators/trendline.py",
        "analysis/indicators/__init__.py",
        "analysis/__init__.py",
        "tests/test_patterns.py"
      ]
    },
    {
      "id": "T026",
      "category": "feature",
      "title": "数据导出功能",
      "description": "实现多格式数据导出",
      "priority": "P3",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "实现 ExportFormat 枚举 (CSV/EXCEL/JSON)",
        "实现 ExportConfig/ExportResult/DateRange 数据类",
        "实现 ExportService 类",
        "实现 export_positions() 持仓导出",
        "实现 export_trades() 交易记录导出 (支持日期范围)",
        "实现 export_klines() K线数据导出",
        "实现 export_watchlist() 关注列表导出",
        "实现 export_all() 多工作表 Excel 导出",
        "实现便捷函数 (export_positions_to_csv等)",
        "添加 CLI 命令组 (export positions/trades/klines/watchlist/all)",
        "支持 --format 选项 (csv/xlsx/json)",
        "创建 tests/test_export.py (36个测试用例)",
        "验证所有 755 个测试通过"
      ],
      "files": [
        "services/export_service.py",
        "services/__init__.py",
        "main.py",
        "tests/test_export.py"
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
| T020 | 端到端集成测试 | P0 | ✅ completed | 100% |
| T006 | 主程序入口 | P1 | ✅ completed | 100% |
| T010 | CSV 数据导入 | P1 | ✅ completed | 100% |
| T012 | 批量图表生成 | P1 | ✅ completed | 100% |
| T014 | VCP 形态识别 | P1 | ✅ completed | 100% |
| T015 | 组合分析 | P1 | ✅ completed | 100% |
| T016 | Portfolio Analyzer Skill | P1 | ✅ completed | 100% |
| T017 | Technical Analyzer Skill | P1 | ✅ completed | 100% |
| T018 | Report Generator Skill | P1 | ✅ completed | 100% |
| T019 | 报告生成器 | P1 | ✅ completed | 100% |
| T021 | 富途 API 真实数据测试 | P1 | ✅ completed | 100% |
| T022 | CLI 增强优化 | P1 | ✅ completed | 100% |
| T023 | 价格提醒系统 | P2 | ✅ completed | 100% |
| T024 | 回测框架 | P2 | ✅ completed | 100% |
| T025 | 更多技术形态识别 | P2 | ✅ completed | 100% |
| T026 | 数据导出功能 | P3 | ✅ completed | 100% |

### 按状态

- **已完成**: T001-T026 (26个任务) ✅ 全部完成!
- **进行中**: 无
- **待开始**: 无
- **已阻塞**: 无

### 参考文档

- 详细设计: `docs/investment-analyzer-design.md`

---

## 阶段 M9: Skills 体系增强

```json
{
  "phase": "M9_skills_enhancement",
  "description": "完善 Skills 体系，新增智能投资顾问角色",
  "tasks": [
    {
      "id": "T027",
      "category": "skill",
      "title": "Skills 体系增强需求分析",
      "description": "分析现有系统和参考资料，设计新 Skills 体系架构",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "探索现有 skills 目录结构 (3个 SKILL.md)",
        "分析参考 prompt 演进 (V1-V5)",
        "研究历史分析报告示例",
        "理解复利公式和投资理念",
        "设计 4 大 Skill 角色 (Analyst/RiskController/TradingCoach/MarketObserver)",
        "设计自动化工作流 (盘前/盘后/月度)",
        "创建功能需求文档 F001-skills-enhancement.md",
        "创建设计决策文档 D001-skills-architecture.md"
      ],
      "files": [
        "docs/features/F001-skills-enhancement.md",
        "docs/decisions/D001-skills-architecture.md"
      ]
    },
    {
      "id": "T028",
      "category": "skill",
      "title": "Skills 基础框架",
      "description": "创建 BaseSkill 基类、共享组件和 CLI 命令框架",
      "priority": "P0",
      "status": "completed",
      "progress": 100,
      "completed_items": [
        "创建 skills/shared 目录结构",
        "实现 BaseSkill 抽象基类 (execute/get_capabilities/validate_context)",
        "实现 SkillContext 数据类 (user_id/request_type/parameters/codes/markets)",
        "实现 SkillResult 数据类 (ok/error 工厂方法)",
        "实现 MarketState/SignalType/RiskLevel 枚举",
        "实现 MarketSchedule (HK/US/A-share 交易时段检测)",
        "实现 DataProvider 统一数据获取 (positions/watchlist/klines/trades)",
        "实现缓存机制 (cache_ttl_seconds)",
        "实现 ReportBuilder 报告构建器 (Markdown/JSON/Text/HTML)",
        "实现 TableColumn/ReportSection 数据类",
        "实现 format_percentage/format_currency/format_score 辅助函数",
        "添加 CLI 命令框架 (skill list/run/info)",
        "实现 analyst 基础分析功能占位",
        "创建 tests/test_skills.py (67个测试用例)",
        "验证所有 822 个测试通过"
      ],
      "files": [
        "skills/shared/__init__.py",
        "skills/shared/base.py",
        "skills/shared/data_provider.py",
        "skills/shared/report_builder.py",
        "main.py",
        "tests/test_skills.py"
      ]
    },
    {
      "id": "T029",
      "category": "skill",
      "title": "分析师 (Analyst) Skill",
      "description": "实现 OBV + VCP 双核心技术分析、评分系统",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "design_principle": "技术指标在精不在多，专注 OBV (量价关系) + VCP (波动收缩形态)",
      "estimated_items": [
        "实现 OBVAnalyzer (趋势/背离/突破确认)",
        "实现 VCPScanner (收缩识别/评分/突破点计算)",
        "实现 StockAnalyzer (整合 OBV + VCP 分析)",
        "实现 BatchAnalyzer (关注列表批量筛选排序)",
        "实现 ScoringSystem (OBV 40% + VCP 60%)",
        "创建 SKILL.md 文档",
        "添加单元测试"
      ],
      "files": [
        "skills/analyst/__init__.py",
        "skills/analyst/SKILL.md",
        "skills/analyst/obv_analyzer.py",
        "skills/analyst/vcp_scanner.py",
        "skills/analyst/stock_analyzer.py",
        "skills/analyst/batch_analyzer.py",
        "skills/analyst/scoring.py"
      ]
    },
    {
      "id": "T030",
      "category": "skill",
      "title": "风控师 (Risk Controller) Skill",
      "description": "实现持仓监控、风险预警、仓位管理",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "estimated_items": [
        "实现 PositionMonitor (持仓诊断)",
        "实现 RiskCalculator (集中度/止损/杠杆)",
        "实现 AlertGenerator (风险预警)",
        "创建 SKILL.md 文档",
        "添加单元测试"
      ],
      "files": [
        "skills/risk_controller/__init__.py",
        "skills/risk_controller/SKILL.md",
        "skills/risk_controller/position_monitor.py",
        "skills/risk_controller/risk_calculator.py",
        "skills/risk_controller/alert_generator.py"
      ]
    },
    {
      "id": "T031",
      "category": "skill",
      "title": "交易导师 (Trading Coach) Skill",
      "description": "实现交易计划、复利教育、心理辅导",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "estimated_items": [
        "实现 PlanGenerator (今日操作计划)",
        "实现 CompoundEducator (复利思维教育)",
        "实现 PsychologyCoach (交易心理辅导)",
        "创建 SKILL.md 文档",
        "添加单元测试"
      ],
      "files": [
        "skills/trading_coach/__init__.py",
        "skills/trading_coach/SKILL.md",
        "skills/trading_coach/plan_generator.py",
        "skills/trading_coach/compound_educator.py",
        "skills/trading_coach/psychology_coach.py"
      ]
    },
    {
      "id": "T032",
      "category": "skill",
      "title": "市场观察员 (Market Observer) Skill",
      "description": "实现盘前分析、盘后总结、板块轮动",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "estimated_items": [
        "实现 PreMarketAnalyzer (盘前分析报告)",
        "实现 PostMarketSummarizer (盘后总结报告)",
        "实现 SectorRotation (板块轮动分析)",
        "实现 SentimentMeter (情绪温度计)",
        "创建 SKILL.md 文档",
        "添加单元测试"
      ],
      "files": [
        "skills/market_observer/__init__.py",
        "skills/market_observer/SKILL.md",
        "skills/market_observer/pre_market.py",
        "skills/market_observer/post_market.py",
        "skills/market_observer/sector_rotation.py"
      ]
    },
    {
      "id": "T033",
      "category": "skill",
      "title": "自动化工作流引擎",
      "description": "实现每日/月度自动化工作流",
      "priority": "P1",
      "status": "pending",
      "progress": 0,
      "estimated_items": [
        "实现 Scheduler (调度器)",
        "实现 DailyWorkflow (盘前/盘后)",
        "实现 MonthlyWorkflow (月度复盘)",
        "创建工作流配置 YAML",
        "添加集成测试"
      ],
      "files": [
        "skills/workflow/__init__.py",
        "skills/workflow/scheduler.py",
        "skills/workflow/daily_workflow.py",
        "skills/workflow/monthly_workflow.py",
        "skills/workflow/config/daily.yaml"
      ]
    }
  ]
}
```

---

### 按状态

- **已完成**: T001-T028 (28个任务)
- **进行中**: 无
- **待开始**: T029-T033 (5个任务)
- **已阻塞**: 无

### 参考文档

- 详细设计: `docs/investment-analyzer-design.md`
- Skills 增强设计: `docs/features/F001-skills-enhancement.md`
- 架构决策: `docs/decisions/D001-skills-architecture.md`

---

*最后更新: 2025-12-15*
