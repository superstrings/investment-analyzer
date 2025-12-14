# Investment Analyzer

> 本地化投资分析自动化系统 - 整合富途数据、技术分析、图表生成和报告输出

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 功能特性

- **数据采集**: 富途 OpenAPI 持仓/交易 + akshare K线数据
- **技术分析**: MA/MACD/RSI/布林带/OBV 指标计算
- **形态识别**: VCP (波动收缩形态) 自动检测与评分
- **组合分析**: 仓位权重、风险评估、HHI 集中度指数
- **图表生成**: K线图 + 均线 + 成交量 (mplfinance)
- **报告输出**: Markdown/JSON/HTML 多格式报告
- **CLI 工具**: 完整的命令行交互界面

## 快速开始

### 环境要求

- Python 3.12+ (推荐使用 asdf 管理)
- PostgreSQL 17+
- 富途牛牛客户端 (用于 API 连接)

### 安装

```bash
# 克隆项目
git clone <repository-url>
cd investment-analyzer

# 设置 Python 版本 (使用 asdf)
asdf install python 3.12.7
asdf local python 3.12.7

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库连接信息和富途密码
```

### 数据库初始化

```bash
# 创建数据库
python scripts/init_db.py create-db

# 初始化表结构
python scripts/init_db.py init

# 填充测试数据 (可选)
python scripts/init_db.py seed
```

### 配置用户

编辑 `config/users.yaml`:

```yaml
users:
  - username: your_name
    futu:
      host: 127.0.0.1
      port: 11111
      trade_env: REAL  # 或 SIMULATE
      security_firm: FUTUINC
      markets: [HK, US]
    settings:
      default_kline_days: 120
```

## 使用指南

### CLI 命令

```bash
# 查看帮助
python main.py --help

# 数据同步
python main.py sync all --user your_name        # 同步所有数据
python main.py sync positions --user your_name  # 仅同步持仓
python main.py sync klines --user your_name --codes "HK.00700,US.NVDA"

# 图表生成
python main.py chart single --code HK.00700 --days 120 --style dark
python main.py chart watchlist --user your_name
python main.py chart positions --user your_name

# 报告生成
python main.py report portfolio --user your_name
python main.py report technical --user your_name --codes "HK.00700"

# 数据导入 (CSV)
python main.py import watchlist --file watchlist.csv --user your_name
python main.py import positions --file positions.csv --user your_name

# 账户信息
python main.py account list --user your_name
python main.py account info --user your_name

# 配置查看
python main.py config show
python main.py config users
```

### Python API

```python
# 技术分析
from analysis import RSI, MACD, detect_vcp
from fetchers import KlineFetcher

fetcher = KlineFetcher()
df = fetcher.fetch("HK.00700", days=120).df

rsi = RSI(14).calculate(df)
vcp_result = detect_vcp(df)

if vcp_result.is_vcp:
    print(f"VCP 得分: {vcp_result.score}")

# 组合分析
from analysis import PortfolioAnalyzer, PositionData

positions = [
    PositionData(market="HK", code="00700", qty=100, cost_price=350, market_price=380),
]
result = PortfolioAnalyzer().analyze(positions)
print(f"总盈亏: {result.summary.total_pl_value}")

# 报告生成
from reports import ReportGenerator, ReportType

generator = ReportGenerator()
report = generator.generate_portfolio_report(result.to_dict())
report.save("reports/output/portfolio.md")
```

## 项目结构

```
investment-analyzer/
├── analysis/           # 分析模块
│   ├── indicators/     # 技术指标 (MA, RSI, MACD, BB, OBV, VCP)
│   ├── portfolio.py    # 组合分析
│   └── technical.py    # 技术分析器
├── charts/             # 图表生成
│   ├── generator.py    # K线图生成器
│   └── styles.py       # 图表样式
├── config/             # 配置管理
│   ├── settings.py     # 全局设置
│   └── users.py        # 用户配置
├── db/                 # 数据库
│   ├── models.py       # SQLAlchemy 模型
│   ├── database.py     # 连接管理
│   └── migrations/     # SQL 迁移脚本
├── fetchers/           # 数据采集
│   ├── futu_fetcher.py # 富途 API
│   └── kline_fetcher.py# K线数据 (akshare)
├── reports/            # 报告生成
│   ├── generator.py    # 报告生成器
│   └── templates/      # Jinja2 模板
├── services/           # 业务服务
│   ├── sync_service.py # 数据同步
│   └── chart_service.py# 图表服务
├── skills/             # Claude Code Skills
│   ├── portfolio_analyzer/
│   ├── technical_analyzer/
│   └── report_generator/
├── scripts/            # 脚本工具
│   ├── init_db.py      # 数据库初始化
│   └── import_csv.py   # CSV 导入
├── tests/              # 测试用例
├── docs/               # 文档
├── main.py             # CLI 入口
└── CLAUDE.md           # Claude Code 指令
```

## 技术栈

| 组件 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| 数据库 | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 |
| 数据采集 | futu-api, akshare |
| 图表 | mplfinance, matplotlib |
| 报告 | Jinja2 |
| CLI | Click |
| 测试 | pytest |

## 技术指标

### 支持的指标

| 指标 | 类 | 说明 |
|------|-----|------|
| SMA/EMA/WMA | `MA`, `SMA`, `EMA`, `WMA` | 移动平均线 |
| RSI | `RSI`, `StochasticRSI` | 相对强弱指数 |
| MACD | `MACD`, `MACDCrossover` | 指数平滑异同移动平均 |
| 布林带 | `BollingerBands`, `BollingerBandsSqueeze` | 波动率指标 |
| OBV | `OBV`, `OBVDivergence` | 能量潮 |
| VCP | `VCP`, `VCPScanner` | 波动收缩形态 |

### VCP 形态

VCP (Volatility Contraction Pattern) 是 Mark Minervini 提出的技术形态:

- 价格收缩至少 2-3 次
- 每次收缩深度递减
- 成交量逐渐萎缩
- 接近枢轴价位

```python
from analysis import detect_vcp, VCPConfig

config = VCPConfig(
    min_contractions=2,
    max_first_depth_pct=35.0,
    depth_decrease_ratio=0.7,
)
result = detect_vcp(df, config)
# result.score: 0-100 评分
```

## 报告类型

| 类型 | 说明 |
|------|------|
| Portfolio | 投资组合分析报告 |
| Technical | 技术分析报告 |
| Daily | 每日投资简报 |
| Weekly | 周度投资回顾 |

支持输出格式: Markdown, JSON, HTML

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行覆盖率测试
python -m pytest tests/ -v --cov=.

# 运行特定模块测试
python -m pytest tests/test_portfolio.py -v
```

当前测试覆盖: **526 tests passed**

## 开发

### 代码规范

```bash
# 格式化代码
python -m black .
python -m isort .

# 代码检查
python -m flake8 .
```

### Claude Code 集成

本项目使用 "自动化工厂" 开发模式，集成 Claude Code 进行 AI 辅助开发:

- `CLAUDE.md`: Claude Code 核心指令
- `PLANNING.md`: 项目规划总览
- `TASKS.md`: 任务追踪 (JSON 格式)
- `.claude/`: 子代理和命令定义

详见 [开发文档](docs/development/claude-code.md)

## 文档

- [需求设计](docs/design/requirements.md)
- [架构设计](docs/design/architecture.md)
- [数据库设计](docs/database/schema.md)
- [API 文档](docs/api/README.md)
- [开发指南](docs/development/README.md)

## 许可证

MIT License

## 致谢

- [futu-api](https://github.com/FutunnOpen/py-futu-api) - 富途 OpenAPI
- [akshare](https://github.com/akfamily/akshare) - 股票数据接口
- [mplfinance](https://github.com/matplotlib/mplfinance) - 金融图表
- [Claude Code](https://claude.com/claude-code) - AI 辅助开发
