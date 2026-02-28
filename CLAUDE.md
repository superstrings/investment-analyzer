# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Investment Analyzer - a local investment analysis system for HK/US/A/JP markets. Data comes from Futu OpenAPI (positions, trades) and akshare (K-line data), stored in PostgreSQL, analyzed with technical indicators, and output as charts/reports.

Interaction is via CLI (`python main.py ...`), Web Dashboard (FastAPI, `python main.py web`), MCP Server (Claude Desktop), and Claude Code slash commands.

## Commands

```bash
# Activate environment
source .venv/bin/activate

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_indicators.py -v

# Run a specific test
python -m pytest tests/test_indicators.py::test_rsi_basic -v

# Run integration tests only
python -m pytest tests/integration/ -v

# Lint and format
python -m black .
python -m isort .
python -m black --check .
python -m isort --check .

# Database
python scripts/init_db.py init    # Create tables
python main.py db-migrate         # Run migrations

# Data sync (requires Futu OpenD running)
python main.py sync all -u dyson

# Deep analysis
python main.py deep-analyze -u dyson -c HK.00700
python main.py deep-analyze -u dyson --market HK --batch
```

## Architecture

### Data Flow Pipeline

```
Futu OpenD / akshare  →  Fetchers  →  SyncService  →  PostgreSQL
                                                          ↓
                    CLI / Web / MCP  ←  Services / Skills
                                              ↓
                                    Analysis / Charts / Reports / DingTalk
```

### Layer Responsibilities

- **`config/`**: Settings loaded from `.env` + `config/users.yaml`. The `settings` singleton (dataclass-based) provides `settings.database.url`, `settings.futu.*`, etc. User config defines per-user Futu OpenD connections and market preferences.

- **`fetchers/`**: Two fetcher implementations, both following `BaseFetcher` → `FetchResult` pattern:
  - `FutuFetcher`: Connects to Futu OpenD for positions/trades/account info. Uses context manager for connection lifecycle.
  - `KlineFetcher`: Uses akshare (A/HK/US) and Futu API (JP) for candlestick data. Auto-detects market (HK/US/A/JP) from stock code prefix and routes to the correct API.

- **`db/`**: SQLAlchemy 2.0 ORM with `Mapped[]` type annotations. Session management via `get_session()` context manager that auto-commits/rollbacks. Models: User → Account → Position/Trade, WatchlistItem, Kline, PriceAlert, SyncLog, DerivativeContract.

- **`services/`**: Business logic orchestration layer. Each service has a `create_*_service()` factory function:
  - `SyncService`: Coordinates fetcher → database storage with incremental sync (dedup by deal_id/date)
  - `ChartService`: Generates mplfinance candlestick charts (single/batch)
  - `AlertService`: Price alert CRUD and triggering
  - `ExportService`: Multi-format data export (CSV/XLSX/JSON)
  - `ExchangeRateService`: Real-time BOC exchange rates with 1hr cache for multi-currency CNY conversion
  - `DingtalkService`: DingTalk bot message push (Webhook + HMAC signature)

- **`analysis/`**: Technical analysis with `BaseIndicator.calculate(df)` pattern returning `IndicatorResult`. Indicators: MA/EMA/WMA, MACD, RSI, Bollinger Bands, OBV. Pattern detection: VCP, Cup-and-Handle, Head-and-Shoulders, Double Top/Bottom, Triangles. Also includes portfolio analysis (`PortfolioAnalyzer`) and support/resistance detection.

- **`skills/`**: Higher-level analysis "roles" built on top of services and analysis modules. Each skill has a main controller class and specialized sub-modules:
  - `analyst/`: OBV + VCP focused scoring (40%/60% weighting)
  - `risk_controller/`: Position monitoring, HHI concentration, risk alerts
  - `trading_coach/`: Trading plans, compound interest education, psychology
  - `market_observer/`: Market sentiment, pre/post-market analysis, sector rotation
  - `deep_analyzer/`: Comprehensive single-stock analysis with web data
  - `trade_analyzer/`: Trade matching, statistics, Excel/DOCX export
  - `workflow/`: Automated daily/monthly workflow orchestration
  - `shared/`: `BaseSkill`, `SkillContext`, `DataProvider`, `ReportBuilder` base classes

- **`backtest/`**: Strategy backtesting engine. `Strategy` base class with `MACrossStrategy` and `VCPBreakoutStrategy` implementations. `BacktestEngine` runs simulations and computes metrics (Sharpe, Sortino, max drawdown).

- **`charts/`**: mplfinance wrapper. `ChartGenerator` with configurable styles (dark/light/chinese/western) and MA overlay support.

- **`reports/`**: Jinja2 template-based report generation. Templates in `reports/templates/*.md.j2` for portfolio, technical, daily, and weekly reports.

- **`cli/`**: Rich-based CLI utilities (colored output, tables, progress bars). Used by `main.py` Click commands.

- **`api/`**: FastAPI web application with Jinja2 templates (Tailwind CSS dark theme). Token-based auth via cookie/Bearer/query param. Routes: dashboard, portfolio, manual positions CRUD, analysis, charts, signals, DingTalk webhook, plans. Auth middleware redirects unauthenticated users to `/login`.

- **`mcp_server.py`**: MCP Server for Claude Desktop integration. Exposes analysis capabilities via MCP protocol.

### Key Patterns

- **Factory functions**: Most components expose `create_*()` functions (e.g., `create_sync_service()`, `create_chart_service()`) that wire up dependencies.
- **Dataclass results**: Operations return typed dataclass results (`FetchResult`, `SyncResult`, `ChartResult`, etc.) with `success` flag and `data`/`error` fields.
- **Stock code format**: Always includes market prefix: `HK.00700`, `US.AAPL`, `SH.600519`, `SZ.000858`, `JP.7203`. The `KlineFetcher._parse_code()` method splits these. Auto-detection: 6-digit→A, 5-digit→HK, 4-digit→JP, letters→US.
- **Option detection**: `_is_option_code()` in `main.py` identifies options by code pattern (HK: letters in code; US: `SYMBOL+YYMMDD+C/P+STRIKE`).
- **User resolution**: CLI commands take `-u dyson` flag → validated against `config/users.yaml` → looked up in DB as `User` record.

### Database Schema (key relationships)

```
User (1) → (*) Account (1) → (*) Position
                             → (*) Trade
User (1) → (*) WatchlistItem
User (1) → (*) PriceAlert
Kline: standalone (indexed by code + trade_date)
```

DB sessions use `with get_session() as session:` which auto-commits on success and rollbacks on exception.

## Project State Files

| File | Purpose |
|------|---------|
| `PLANNING.md` | Project structure, milestones, agent workflow |
| `TASKS.md` | Current task list (JSON format) |
| `TASKS_DONE.md` | Completed task archive |
| `claude-progress.txt` | Session progress log |

When starting a session: read `TASKS.md` and `claude-progress.txt` tail to understand current state.

## Tech Stack

- Python 3.12 (asdf), venv in `.venv/`
- PostgreSQL 17 (Homebrew, localhost:5432, DB: `investment_db`)
- SQLAlchemy 2.0+ with `Mapped[]` annotations
- FastAPI + Jinja2 + Tailwind CSS for Web UI
- Click for CLI, Rich for output formatting
- Futu OpenD must be running locally for data sync (HK/US/JP markets)
- Black + isort for formatting (configured in `pyproject.toml`)
- Deployment: launchd (macOS) + frpc → nginx → Cloudflare Tunnel for external access
