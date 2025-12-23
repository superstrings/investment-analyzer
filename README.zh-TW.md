# Investment Analyzer

> 本地化投資分析自動化系統 - 整合富途資料、技術分析、圖表生成和報告輸出

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**語言: [简体中文](README.md) | [English](README.en.md) | 繁體中文 (台灣) | [繁體中文 (香港)](README.zh-HK.md) | [日本語](README.ja.md)**

## 功能特性

- **資料採集**: 富途 OpenAPI 持倉/交易/K線 + akshare A股資料
- **深度分析**: 技術面 + 基本面 + 產業 + 消息綜合評分
- **技術分析**: MA/MACD/RSI/布林通道/OBV/VCP 指標計算
- **型態識別**: VCP (波動收縮型態) 自動檢測與評分
- **組合分析**: 倉位權重、風險評估、HHI 集中度指數
- **圖表生成**: K線圖 + 均線 + 成交量 (mplfinance)
- **報告輸出**: Markdown/JSON/HTML 多格式報告
- **Skills 系統**: 分析師/風控/交易指導/市場觀察多角色
- **Claude 命令**: 便捷的 Slash 命令快速操作
- **CLI 工具**: 完整的命令列交互介面

## 快速開始

### 環境要求

- Python 3.12+ (建議使用 asdf 管理)
- PostgreSQL 17+
- 富途牛牛用戶端 (用於 API 連接)

### 安裝

```bash
# 複製專案
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

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入資料庫連接資訊和富途密碼
```

### 資料庫初始化

```bash
# 建立資料庫
python scripts/init_db.py create-db

# 初始化資料表結構
python scripts/init_db.py init

# 填充測試資料 (選用)
python scripts/init_db.py seed
```

### 設定使用者

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

### 日常分析 (建議)

```bash
# 同步所有資料
python main.py sync all -u your_name

# 深度分析 (單檔股票)
python main.py deep-analyze -u your_name -c HK.00700

# 深度分析 (批量 - 按市場)
python main.py deep-analyze -u your_name --market HK --batch
python main.py deep-analyze -u your_name --market US --batch
python main.py deep-analyze -u your_name --market A --batch

# 查看持倉
python main.py account info -u your_name
```

### Claude 快捷命令

在 Claude Code 中可使用以下命令：

| 命令 | 說明 |
|------|------|
| `/daily-analysis` | 每日分析 (盤前/盤後) |
| `/deep-analyze HK` | 深度分析指定市場 |
| `/market-summary` | 三市場彙總報告 |
| `/sync-all` | 同步所有資料 |

### CLI 命令

```bash
# 查看幫助
python main.py --help

# 資料同步
python main.py sync all -u your_name           # 同步所有資料
python main.py sync positions -u your_name     # 僅同步持倉
python main.py sync klines -u your_name --codes "HK.00700,US.NVDA"

# 圖表生成
python main.py chart single --code HK.00700 --days 120
python main.py chart positions -u your_name

# 報告生成
python main.py report portfolio -u your_name
python main.py report technical -u your_name --codes "HK.00700"

# 帳戶資訊
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
├── analysis/           # 分析模組
│   ├── indicators/     # 技術指標 (MA, RSI, MACD, BB, OBV, VCP)
│   ├── portfolio.py    # 組合分析
│   └── technical.py    # 技術分析器
├── charts/             # 圖表生成
│   ├── generator.py    # K線圖生成器
│   └── styles.py       # 圖表樣式
├── config/             # 設定管理
│   ├── settings.py     # 全域設定
│   └── users.py        # 使用者設定
├── db/                 # 資料庫
│   ├── models.py       # SQLAlchemy 模型
│   ├── database.py     # 連接管理
│   └── migrations/     # SQL 遷移腳本
├── fetchers/           # 資料採集
│   ├── futu_fetcher.py # 富途 API
│   └── kline_fetcher.py# K線資料 (akshare)
├── reports/            # 報告生成
│   ├── generator.py    # 報告生成器
│   └── templates/      # Jinja2 模板
├── services/           # 業務服務
│   ├── sync_service.py # 資料同步
│   └── chart_service.py# 圖表服務
├── skills/             # Claude Code Skills
│   ├── analyst/        # 分析師 (OBV + VCP)
│   ├── risk_controller/# 風控師
│   ├── trading_coach/  # 交易導師
│   ├── market_observer/# 市場觀察員
│   ├── deep_analyzer/  # 深度分析
│   └── shared/         # 共享元件
├── scripts/            # 腳本工具
│   ├── init_db.py      # 資料庫初始化
│   └── import_csv.py   # CSV 匯入
├── tests/              # 測試案例
├── docs/               # 文件
├── main.py             # CLI 入口
└── CLAUDE.md           # Claude Code 指令
```

## 技術堆疊

| 元件 | 技術 |
|------|------|
| 語言 | Python 3.12+ |
| 資料庫 | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 |
| 資料採集 | futu-api, akshare |
| 圖表 | mplfinance, matplotlib |
| 報告 | Jinja2 |
| CLI | Click |
| 測試 | pytest |

## 技術指標

### 支援的指標

| 指標 | 類別 | 說明 |
|------|-----|------|
| SMA/EMA/WMA | `MA`, `SMA`, `EMA`, `WMA` | 移動平均線 |
| RSI | `RSI`, `StochasticRSI` | 相對強弱指數 |
| MACD | `MACD`, `MACDCrossover` | 指數平滑異同移動平均 |
| 布林通道 | `BollingerBands`, `BollingerBandsSqueeze` | 波動率指標 |
| OBV | `OBV`, `OBVDivergence` | 能量潮 |
| VCP | `VCP`, `VCPScanner` | 波動收縮型態 |

### VCP 型態

VCP (Volatility Contraction Pattern) 是 Mark Minervini 提出的技術型態:

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
| Weekly | 週度投資回顧 |

支援輸出格式: Markdown, JSON, HTML

## 測試

```bash
# 執行所有測試
python -m pytest tests/ -v

# 執行覆蓋率測試
python -m pytest tests/ -v --cov=.

# 執行特定模組測試
python -m pytest tests/test_portfolio.py -v
```

目前測試覆蓋: **1097 tests passed**

## 開發

### 程式碼規範

```bash
# 格式化程式碼
python -m black .
python -m isort .

# 程式碼檢查
python -m flake8 .
```

### Claude Code 整合

本專案使用「自動化工廠」開發模式，整合 Claude Code 進行 AI 輔助開發:

- `CLAUDE.md`: Claude Code 核心指令
- `PLANNING.md`: 專案規劃總覽
- `TASKS.md`: 任務追蹤 (JSON 格式)
- `.claude/`: 子代理和命令定義

詳見 [開發文件](docs/development/claude-code.md)

## 文件

- [使用指南](docs/guide/README.md) - 完整使用手冊
- [需求設計](docs/design/requirements.md)
- [架構設計](docs/design/architecture.md)
- [資料庫設計](docs/database/schema.md)
- [API 文件](docs/api/README.md)
- [開發指南](docs/development/README.md)

## 貢獻

歡迎貢獻程式碼！請查閱 [CONTRIBUTING.md](CONTRIBUTING.md) 了解貢獻指南。

參與專案請遵守我們的 [行為準則](CODE_OF_CONDUCT.md)。

## 授權條款

MIT License - 詳見 [LICENSE](LICENSE)

## 致謝

- [futu-api](https://github.com/FutunnOpen/py-futu-api) - 富途 OpenAPI
- [akshare](https://github.com/akfamily/akshare) - 股票資料介面
- [mplfinance](https://github.com/matplotlib/mplfinance) - 金融圖表
- [Claude Code](https://claude.com/claude-code) - AI 輔助開發
