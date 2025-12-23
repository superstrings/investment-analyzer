# Investment Analyzer

> ローカル投資分析自動化システム - Futuデータ、テクニカル分析、チャート生成、レポート出力の統合

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**言語: [简体中文](README.md) | [English](README.en.md) | [繁體中文 (台灣)](README.zh-TW.md) | [繁體中文 (香港)](README.zh-HK.md) | 日本語**

## 機能

- **データ収集**: Futu OpenAPI ポジション/取引/ローソク足 + akshare A株データ
- **深度分析**: テクニカル + ファンダメンタル + 業種 + ニュース総合スコアリング
- **テクニカル分析**: MA/MACD/RSI/ボリンジャーバンド/OBV/VCP 指標計算
- **パターン認識**: VCP（ボラティリティ収縮パターン）自動検出とスコアリング
- **ポートフォリオ分析**: ポジション配分、リスク評価、HHI集中度指数
- **チャート生成**: ローソク足チャート + 移動平均線 + 出来高 (mplfinance)
- **レポート出力**: Markdown/JSON/HTML マルチフォーマットレポート
- **Skills システム**: アナリスト/リスク管理/トレーディングコーチ/マーケットオブザーバー
- **Claude コマンド**: 便利なスラッシュコマンドでクイック操作
- **CLI ツール**: 完全なコマンドラインインターフェース

## クイックスタート

### 必要要件

- Python 3.12+ (asdfでのバージョン管理を推奨)
- PostgreSQL 17+
- Futu OpenD クライアント (API接続用)

### インストール

```bash
# プロジェクトをクローン
git clone <repository-url>
cd investment-analyzer

# Python バージョンを設定 (asdf使用)
asdf install python 3.12.7
asdf local python 3.12.7

# 仮想環境を作成
python -m venv .venv
source .venv/bin/activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境変数を設定
cp .env.example .env
# .env を編集してデータベース接続情報とFutuパスワードを入力
```

### データベース初期化

```bash
# データベースを作成
python scripts/init_db.py create-db

# スキーマを初期化
python scripts/init_db.py init

# テストデータを投入 (オプション)
python scripts/init_db.py seed
```

### ユーザー設定

`config/users.yaml.example` を `config/users.yaml` にコピーして編集:

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

## 使用ガイド

> 詳細なガイドは [docs/guide/README.md](docs/guide/README.md) を参照

### 日常分析 (推奨)

```bash
# すべてのデータを同期
python main.py sync all -u your_name

# 深度分析 (単一銘柄)
python main.py deep-analyze -u your_name -c HK.00700

# 深度分析 (バッチ - 市場別)
python main.py deep-analyze -u your_name --market HK --batch
python main.py deep-analyze -u your_name --market US --batch
python main.py deep-analyze -u your_name --market A --batch

# ポジション表示
python main.py account info -u your_name
```

### Claude クイックコマンド

Claude Code で以下のコマンドを使用可能:

| コマンド | 説明 |
|----------|------|
| `/daily-analysis` | 日次分析 (寄り付き前/引け後) |
| `/deep-analyze HK` | 指定市場の深度分析 |
| `/market-summary` | 3市場サマリーレポート |
| `/sync-all` | すべてのデータを同期 |

### CLI コマンド

```bash
# ヘルプ表示
python main.py --help

# データ同期
python main.py sync all -u your_name           # すべてのデータを同期
python main.py sync positions -u your_name     # ポジションのみ同期
python main.py sync klines -u your_name --codes "HK.00700,US.NVDA"

# チャート生成
python main.py chart single --code HK.00700 --days 120
python main.py chart positions -u your_name

# レポート生成
python main.py report portfolio -u your_name
python main.py report technical -u your_name --codes "HK.00700"

# アカウント情報
python main.py account list -u your_name
python main.py account info -u your_name
```

### Python API

```python
# テクニカル分析
from analysis import RSI, MACD, detect_vcp
from fetchers import KlineFetcher

fetcher = KlineFetcher()
df = fetcher.fetch("HK.00700", days=120).df

rsi = RSI(14).calculate(df)
vcp_result = detect_vcp(df)

if vcp_result.is_vcp:
    print(f"VCP スコア: {vcp_result.score}")

# ポートフォリオ分析
from analysis import PortfolioAnalyzer, PositionData

positions = [
    PositionData(market="HK", code="00700", qty=100, cost_price=350, market_price=380),
]
result = PortfolioAnalyzer().analyze(positions)
print(f"総損益: {result.summary.total_pl_value}")

# レポート生成
from reports import ReportGenerator, ReportType

generator = ReportGenerator()
report = generator.generate_portfolio_report(result.to_dict())
report.save("reports/output/portfolio.md")
```

## プロジェクト構造

```
investment-analyzer/
├── analysis/           # 分析モジュール
│   ├── indicators/     # テクニカル指標 (MA, RSI, MACD, BB, OBV, VCP)
│   ├── portfolio.py    # ポートフォリオ分析
│   └── technical.py    # テクニカルアナライザー
├── charts/             # チャート生成
│   ├── generator.py    # ローソク足チャートジェネレーター
│   └── styles.py       # チャートスタイル
├── config/             # 設定管理
│   ├── settings.py     # グローバル設定
│   └── users.py        # ユーザー設定
├── db/                 # データベース
│   ├── models.py       # SQLAlchemy モデル
│   ├── database.py     # 接続管理
│   └── migrations/     # SQL マイグレーションスクリプト
├── fetchers/           # データ取得
│   ├── futu_fetcher.py # Futu API
│   └── kline_fetcher.py# ローソク足データ (akshare)
├── reports/            # レポート生成
│   ├── generator.py    # レポートジェネレーター
│   └── templates/      # Jinja2 テンプレート
├── services/           # ビジネスサービス
│   ├── sync_service.py # データ同期
│   └── chart_service.py# チャートサービス
├── skills/             # Claude Code Skills
│   ├── analyst/        # アナリスト (OBV + VCP)
│   ├── risk_controller/# リスクコントローラー
│   ├── trading_coach/  # トレーディングコーチ
│   ├── market_observer/# マーケットオブザーバー
│   ├── deep_analyzer/  # ディープアナライザー
│   └── shared/         # 共有コンポーネント
├── scripts/            # ユーティリティスクリプト
│   ├── init_db.py      # データベース初期化
│   └── import_csv.py   # CSV インポート
├── tests/              # テストケース
├── docs/               # ドキュメント
├── main.py             # CLI エントリーポイント
└── CLAUDE.md           # Claude Code 指示
```

## 技術スタック

| コンポーネント | 技術 |
|---------------|------|
| 言語 | Python 3.12+ |
| データベース | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 |
| データ取得 | futu-api, akshare |
| チャート | mplfinance, matplotlib |
| レポート | Jinja2 |
| CLI | Click |
| テスト | pytest |

## テクニカル指標

### サポートされる指標

| 指標 | クラス | 説明 |
|------|--------|------|
| SMA/EMA/WMA | `MA`, `SMA`, `EMA`, `WMA` | 移動平均線 |
| RSI | `RSI`, `StochasticRSI` | 相対力指数 |
| MACD | `MACD`, `MACDCrossover` | 移動平均収束拡散法 |
| ボリンジャーバンド | `BollingerBands`, `BollingerBandsSqueeze` | ボラティリティ指標 |
| OBV | `OBV`, `OBVDivergence` | オンバランスボリューム |
| VCP | `VCP`, `VCPScanner` | ボラティリティ収縮パターン |

### VCP パターン

VCP (Volatility Contraction Pattern) は Mark Minervini が提唱したテクニカルパターン:

- 価格が少なくとも2-3回収縮
- 各収縮の深さが減少
- 出来高が徐々に減少
- ピボット価格に接近

```python
from analysis import detect_vcp, VCPConfig

config = VCPConfig(
    min_contractions=2,
    max_first_depth_pct=35.0,
    depth_decrease_ratio=0.7,
)
result = detect_vcp(df, config)
# result.score: 0-100 スコア
```

## レポートタイプ

| タイプ | 説明 |
|--------|------|
| Portfolio | 投資ポートフォリオ分析レポート |
| Technical | テクニカル分析レポート |
| Daily | 日次投資ブリーフ |
| Weekly | 週次投資レビュー |

サポート出力フォーマット: Markdown, JSON, HTML

## テスト

```bash
# すべてのテストを実行
python -m pytest tests/ -v

# カバレッジ付きで実行
python -m pytest tests/ -v --cov=.

# 特定モジュールのテストを実行
python -m pytest tests/test_portfolio.py -v
```

現在のテストカバレッジ: **1097 tests passed**

## 開発

### コードスタイル

```bash
# コードをフォーマット
python -m black .
python -m isort .

# コードをリント
python -m flake8 .
```

### Claude Code 統合

このプロジェクトは「自動化ファクトリー」開発モデルを使用し、Claude Code を AI アシスト開発に統合:

- `CLAUDE.md`: Claude Code コア指示
- `PLANNING.md`: プロジェクト計画概要
- `TASKS.md`: タスクトラッキング (JSON 形式)
- `.claude/`: サブエージェントとコマンド定義

詳細は [開発ドキュメント](docs/development/claude-code.md) を参照

## ドキュメント

- [使用ガイド](docs/guide/README.md) - 完全な使用マニュアル
- [要件](docs/design/requirements.md)
- [アーキテクチャ](docs/design/architecture.md)
- [データベーススキーマ](docs/database/schema.md)
- [API ドキュメント](docs/api/README.md)
- [開発ガイド](docs/development/README.md)

## コントリビュート

コントリビュートを歓迎します！[CONTRIBUTING.md](CONTRIBUTING.md) でコントリビューションガイドラインを確認してください。

参加する際は [行動規範](CODE_OF_CONDUCT.md) を遵守してください。

## ライセンス

MIT License - [LICENSE](LICENSE) を参照

## 謝辞

- [futu-api](https://github.com/FutunnOpen/py-futu-api) - Futu OpenAPI
- [akshare](https://github.com/akfamily/akshare) - 株式データインターフェース
- [mplfinance](https://github.com/matplotlib/mplfinance) - 金融チャート
- [Claude Code](https://claude.com/claude-code) - AI アシスト開発
