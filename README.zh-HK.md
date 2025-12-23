# Investment Analyzer

> 本地化投資分析自動化系統 - 整合富途數據、技術分析、圖表生成和報告輸出

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**語言: [简体中文](README.md) | [English](README.en.md) | [繁體中文 (台灣)](README.zh-TW.md) | 繁體中文 (香港) | [日本語](README.ja.md)**

## 功能特性

- **數據採集**: 富途 OpenAPI 持倉/交易/K線 + akshare A股數據
- **深度分析**: 技術面 + 基本面 + 行業 + 消息綜合評分
- **技術分析**: MA/MACD/RSI/保力加通道/OBV/VCP 指標計算
- **形態識別**: VCP (波動收縮形態) 自動檢測與評分
- **組合分析**: 倉位權重、風險評估、HHI 集中度指數
- **圖表生成**: K線圖 + 均線 + 成交量 (mplfinance)
- **報告輸出**: Markdown/JSON/HTML 多格式報告
- **Skills 系統**: 分析師/風控/交易指導/市場觀察多角色
- **Claude 命令**: 便捷嘅 Slash 命令快速操作
- **CLI 工具**: 完整嘅命令行交互界面

## 快速開始

### 環境要求

- Python 3.12+ (建議使用 asdf 管理)
- PostgreSQL 17+
- 富途牛牛客戶端 (用於 API 連接)

### 安裝

```bash
# Clone 專案
git clone <repository-url>
cd investment-analyzer

# 設定 Python 版本 (使用 asdf)
asdf install python 3.12.7
asdf local python 3.12.7

# 建立虛擬環境
python -m venv .venv
source .venv/bin/activate

# 安裝依賴
pip install -r requirements.txt

# 配置環境變量
cp .env.example .env
# 編輯 .env 填入數據庫連接信息同富途密碼
```

### 數據庫初始化

```bash
# 建立數據庫
python scripts/init_db.py create-db

# 初始化表結構
python scripts/init_db.py init

# 填充測試數據 (可選)
python scripts/init_db.py seed
```

### 配置用戶

複製 `config/users.yaml.example` 至 `config/users.yaml` 並編輯:

```yaml
users:
  your_name:
    display_name: "Your Name"
    opend:
      host: 127.0.0.1
      port: 11111
    default_markets:
      - HK
      - US
    kline_days: 250
    is_active: true
```

## 使用指南

> 詳細指南請參閱 [docs/guide/README.md](docs/guide/README.md)

### 日常分析 (推薦)

```bash
# 同步所有數據
python main.py sync all -u your_name

# 深度分析 (單隻股票)
python main.py deep-analyze -u your_name -c HK.00700

# 深度分析 (批量 - 按市場)
python main.py deep-analyze -u your_name --market HK --batch
python main.py deep-analyze -u your_name --market US --batch
python main.py deep-analyze -u your_name --market A --batch

# 查看持倉
python main.py account info -u your_name
```

### Claude 快捷命令

喺 Claude Code 入面可以使用以下命令：

| 命令 | 說明 |
|------|------|
| `/daily-analysis` | 每日分析 (開市前/收市後) |
| `/deep-analyze HK` | 深度分析指定市場 |
| `/market-summary` | 三市場匯總報告 |
| `/sync-all` | 同步所有數據 |

### CLI 命令

```bash
# 查看幫助
python main.py --help

# 數據同步
python main.py sync all -u your_name           # 同步所有數據
python main.py sync positions -u your_name     # 只同步持倉
python main.py sync klines -u your_name --codes "HK.00700,US.NVDA"

# 圖表生成
python main.py chart single --code HK.00700 --days 120
python main.py chart positions -u your_name

# 報告生成
python main.py report portfolio -u your_name
python main.py report technical -u your_name --codes "HK.00700"

# 賬戶資訊
python main.py account list -u your_name
python main.py account info -u your_name
```

### Python API

```python
# 技術分析
from analysis import RSI, MACD, detect_vcp
from fetchers import KlineFetcher

fetcher = KlineFetcher()
df = fetcher.fetch("HK.00700", days=120).df

rsi = RSI(14).calculate(df)
vcp_result = detect_vcp(df)

if vcp_result.is_vcp:
    print(f"VCP 得分: {vcp_result.score}")

# 組合分析
from analysis import PortfolioAnalyzer, PositionData

positions = [
    PositionData(market="HK", code="00700", qty=100, cost_price=350, market_price=380),
]
result = PortfolioAnalyzer().analyze(positions)
print(f"總盈虧: {result.summary.total_pl_value}")

# 報告生成
from reports import ReportGenerator, ReportType

generator = ReportGenerator()
report = generator.generate_portfolio_report(result.to_dict())
report.save("reports/output/portfolio.md")
```

## 專案結構

```
investment-analyzer/
├── analysis/           # 分析模塊
│   ├── indicators/     # 技術指標 (MA, RSI, MACD, BB, OBV, VCP)
│   ├── portfolio.py    # 組合分析
│   └── technical.py    # 技術分析器
├── charts/             # 圖表生成
│   ├── generator.py    # K線圖生成器
│   └── styles.py       # 圖表樣式
├── config/             # 配置管理
│   ├── settings.py     # 全局設定
│   └── users.py        # 用戶配置
├── db/                 # 數據庫
│   ├── models.py       # SQLAlchemy 模型
│   ├── database.py     # 連接管理
│   └── migrations/     # SQL 遷移腳本
├── fetchers/           # 數據採集
│   ├── futu_fetcher.py # 富途 API
│   └── kline_fetcher.py# K線數據 (akshare)
├── reports/            # 報告生成
│   ├── generator.py    # 報告生成器
│   └── templates/      # Jinja2 模板
├── services/           # 業務服務
│   ├── sync_service.py # 數據同步
│   └── chart_service.py# 圖表服務
├── skills/             # Claude Code Skills
│   ├── analyst/        # 分析師 (OBV + VCP)
│   ├── risk_controller/# 風控師
│   ├── trading_coach/  # 交易導師
│   ├── market_observer/# 市場觀察員
│   ├── deep_analyzer/  # 深度分析
│   └── shared/         # 共享組件
├── scripts/            # 腳本工具
│   ├── init_db.py      # 數據庫初始化
│   └── import_csv.py   # CSV 導入
├── tests/              # 測試用例
├── docs/               # 文檔
├── main.py             # CLI 入口
└── CLAUDE.md           # Claude Code 指令
```

## 技術棧

| 組件 | 技術 |
|------|------|
| 語言 | Python 3.12+ |
| 數據庫 | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 |
| 數據採集 | futu-api, akshare |
| 圖表 | mplfinance, matplotlib |
| 報告 | Jinja2 |
| CLI | Click |
| 測試 | pytest |

## 技術指標

### 支持嘅指標

| 指標 | 類 | 說明 |
|------|-----|------|
| SMA/EMA/WMA | `MA`, `SMA`, `EMA`, `WMA` | 移動平均線 |
| RSI | `RSI`, `StochasticRSI` | 相對強弱指數 |
| MACD | `MACD`, `MACDCrossover` | 指數平滑異同移動平均 |
| 保力加通道 | `BollingerBands`, `BollingerBandsSqueeze` | 波動率指標 |
| OBV | `OBV`, `OBVDivergence` | 能量潮 |
| VCP | `VCP`, `VCPScanner` | 波動收縮形態 |

### VCP 形態

VCP (Volatility Contraction Pattern) 係 Mark Minervini 提出嘅技術形態:

- 價格收縮至少 2-3 次
- 每次收縮深度遞減
- 成交量逐漸萎縮
- 接近樞軸價位

```python
from analysis import detect_vcp, VCPConfig

config = VCPConfig(
    min_contractions=2,
    max_first_depth_pct=35.0,
    depth_decrease_ratio=0.7,
)
result = detect_vcp(df, config)
# result.score: 0-100 評分
```

## 報告類型

| 類型 | 說明 |
|------|------|
| Portfolio | 投資組合分析報告 |
| Technical | 技術分析報告 |
| Daily | 每日投資簡報 |
| Weekly | 周度投資回顧 |

支持輸出格式: Markdown, JSON, HTML

## 測試

```bash
# 運行所有測試
python -m pytest tests/ -v

# 運行覆蓋率測試
python -m pytest tests/ -v --cov=.

# 運行特定模塊測試
python -m pytest tests/test_portfolio.py -v
```

目前測試覆蓋: **1097 tests passed**

## 開發

### 代碼規範

```bash
# 格式化代碼
python -m black .
python -m isort .

# 代碼檢查
python -m flake8 .
```

### Claude Code 集成

本專案使用「自動化工廠」開發模式，集成 Claude Code 進行 AI 輔助開發:

- `CLAUDE.md`: Claude Code 核心指令
- `PLANNING.md`: 專案規劃總覽
- `TASKS.md`: 任務追蹤 (JSON 格式)
- `.claude/`: 子代理同命令定義

詳見 [開發文檔](docs/development/claude-code.md)

## 文檔

- [使用指南](docs/guide/README.md) - 完整使用手冊
- [需求設計](docs/design/requirements.md)
- [架構設計](docs/design/architecture.md)
- [數據庫設計](docs/database/schema.md)
- [API 文檔](docs/api/README.md)
- [開發指南](docs/development/README.md)

## 貢獻

歡迎貢獻代碼！請查閱 [CONTRIBUTING.md](CONTRIBUTING.md) 了解貢獻指南。

參與專案請遵守我哋嘅 [行為準則](CODE_OF_CONDUCT.md)。

## 許可證

MIT License - 詳見 [LICENSE](LICENSE)

## 致謝

- [futu-api](https://github.com/FutunnOpen/py-futu-api) - 富途 OpenAPI
- [akshare](https://github.com/akfamily/akshare) - 股票數據接口
- [mplfinance](https://github.com/matplotlib/mplfinance) - 金融圖表
- [Claude Code](https://claude.com/claude-code) - AI 輔助開發
