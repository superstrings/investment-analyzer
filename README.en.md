# Investment Analyzer

> Local investment analysis automation system - integrating Futu data, technical analysis, chart generation, and report output

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

**Language: [简体中文](README.md) | English | [繁體中文 (台灣)](README.zh-TW.md) | [繁體中文 (香港)](README.zh-HK.md) | [日本語](README.ja.md)**

## Features

- **Data Collection**: Futu OpenAPI positions/trades/K-lines + akshare A-share data
- **Deep Analysis**: Technical + fundamental + industry + news comprehensive scoring
- **Technical Analysis**: MA/MACD/RSI/Bollinger Bands/OBV/VCP indicator calculation
- **Pattern Recognition**: VCP (Volatility Contraction Pattern) auto-detection and scoring
- **Portfolio Analysis**: Position weighting, risk assessment, HHI concentration index
- **Chart Generation**: Candlestick charts + moving averages + volume (mplfinance)
- **Report Output**: Markdown/JSON/HTML multi-format reports
- **Skills System**: Analyst/Risk Control/Trading Coach/Market Observer multi-role
- **Claude Commands**: Convenient slash commands for quick operations
- **CLI Tools**: Complete command-line interface

## Quick Start

### Requirements

- Python 3.12+ (asdf recommended for version management)
- PostgreSQL 17+
- Futu OpenD client (for API connection)

### Installation

```bash
# Clone the project
git clone <repository-url>
cd investment-analyzer

# Set Python version (using asdf)
asdf install python 3.12.7
asdf local python 3.12.7

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env with database connection info and Futu password
```

### Database Initialization

```bash
# Create database
python scripts/init_db.py create-db

# Initialize schema
python scripts/init_db.py init

# Seed test data (optional)
python scripts/init_db.py seed
```

### User Configuration

Copy and edit `config/users.yaml.example` to `config/users.yaml`:

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

## Usage Guide

> For detailed guide, see [docs/guide/README.md](docs/guide/README.md)

### Daily Analysis (Recommended)

```bash
# Sync all data
python main.py sync all -u your_name

# Deep analysis (single stock)
python main.py deep-analyze -u your_name -c HK.00700

# Deep analysis (batch - by market)
python main.py deep-analyze -u your_name --market HK --batch
python main.py deep-analyze -u your_name --market US --batch
python main.py deep-analyze -u your_name --market A --batch

# View positions
python main.py account info -u your_name
```

### Claude Quick Commands

Use these commands in Claude Code:

| Command | Description |
|---------|-------------|
| `/daily-analysis` | Daily analysis (pre/post market) |
| `/deep-analyze HK` | Deep analyze specified market |
| `/market-summary` | Three-market summary report |
| `/sync-all` | Sync all data |

### CLI Commands

```bash
# View help
python main.py --help

# Data sync
python main.py sync all -u your_name           # Sync all data
python main.py sync positions -u your_name     # Sync positions only
python main.py sync klines -u your_name --codes "HK.00700,US.NVDA"

# Chart generation
python main.py chart single --code HK.00700 --days 120
python main.py chart positions -u your_name

# Report generation
python main.py report portfolio -u your_name
python main.py report technical -u your_name --codes "HK.00700"

# Account info
python main.py account list -u your_name
python main.py account info -u your_name
```

### Python API

```python
# Technical analysis
from analysis import RSI, MACD, detect_vcp
from fetchers import KlineFetcher

fetcher = KlineFetcher()
df = fetcher.fetch("HK.00700", days=120).df

rsi = RSI(14).calculate(df)
vcp_result = detect_vcp(df)

if vcp_result.is_vcp:
    print(f"VCP Score: {vcp_result.score}")

# Portfolio analysis
from analysis import PortfolioAnalyzer, PositionData

positions = [
    PositionData(market="HK", code="00700", qty=100, cost_price=350, market_price=380),
]
result = PortfolioAnalyzer().analyze(positions)
print(f"Total P&L: {result.summary.total_pl_value}")

# Report generation
from reports import ReportGenerator, ReportType

generator = ReportGenerator()
report = generator.generate_portfolio_report(result.to_dict())
report.save("reports/output/portfolio.md")
```

## Project Structure

```
investment-analyzer/
├── analysis/           # Analysis module
│   ├── indicators/     # Technical indicators (MA, RSI, MACD, BB, OBV, VCP)
│   ├── portfolio.py    # Portfolio analysis
│   └── technical.py    # Technical analyzer
├── charts/             # Chart generation
│   ├── generator.py    # Candlestick chart generator
│   └── styles.py       # Chart styles
├── config/             # Configuration management
│   ├── settings.py     # Global settings
│   └── users.py        # User configuration
├── db/                 # Database
│   ├── models.py       # SQLAlchemy models
│   ├── database.py     # Connection management
│   └── migrations/     # SQL migration scripts
├── fetchers/           # Data fetching
│   ├── futu_fetcher.py # Futu API
│   └── kline_fetcher.py# K-line data (akshare)
├── reports/            # Report generation
│   ├── generator.py    # Report generator
│   └── templates/      # Jinja2 templates
├── services/           # Business services
│   ├── sync_service.py # Data sync
│   └── chart_service.py# Chart service
├── skills/             # Claude Code Skills
│   ├── analyst/        # Analyst (OBV + VCP)
│   ├── risk_controller/# Risk controller
│   ├── trading_coach/  # Trading coach
│   ├── market_observer/# Market observer
│   ├── deep_analyzer/  # Deep analyzer
│   └── shared/         # Shared components
├── scripts/            # Utility scripts
│   ├── init_db.py      # Database initialization
│   └── import_csv.py   # CSV import
├── tests/              # Test cases
├── docs/               # Documentation
├── main.py             # CLI entry point
└── CLAUDE.md           # Claude Code instructions
```

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.12+ |
| Database | PostgreSQL 17 |
| ORM | SQLAlchemy 2.0 |
| Data Fetching | futu-api, akshare |
| Charts | mplfinance, matplotlib |
| Reports | Jinja2 |
| CLI | Click |
| Testing | pytest |

## Technical Indicators

### Supported Indicators

| Indicator | Class | Description |
|-----------|-------|-------------|
| SMA/EMA/WMA | `MA`, `SMA`, `EMA`, `WMA` | Moving Averages |
| RSI | `RSI`, `StochasticRSI` | Relative Strength Index |
| MACD | `MACD`, `MACDCrossover` | Moving Average Convergence Divergence |
| Bollinger Bands | `BollingerBands`, `BollingerBandsSqueeze` | Volatility Indicator |
| OBV | `OBV`, `OBVDivergence` | On-Balance Volume |
| VCP | `VCP`, `VCPScanner` | Volatility Contraction Pattern |

### VCP Pattern

VCP (Volatility Contraction Pattern) is a technical pattern proposed by Mark Minervini:

- Price contracts at least 2-3 times
- Each contraction depth decreases
- Volume gradually dries up
- Approaches pivot price

```python
from analysis import detect_vcp, VCPConfig

config = VCPConfig(
    min_contractions=2,
    max_first_depth_pct=35.0,
    depth_decrease_ratio=0.7,
)
result = detect_vcp(df, config)
# result.score: 0-100 score
```

## Report Types

| Type | Description |
|------|-------------|
| Portfolio | Investment portfolio analysis report |
| Technical | Technical analysis report |
| Daily | Daily investment brief |
| Weekly | Weekly investment review |

Supported output formats: Markdown, JSON, HTML

## Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=.

# Run specific module tests
python -m pytest tests/test_portfolio.py -v
```

Current test coverage: **1097 tests passed**

## Development

### Code Style

```bash
# Format code
python -m black .
python -m isort .

# Lint code
python -m flake8 .
```

### Claude Code Integration

This project uses the "Automation Factory" development model, integrating Claude Code for AI-assisted development:

- `CLAUDE.md`: Claude Code core instructions
- `PLANNING.md`: Project planning overview
- `TASKS.md`: Task tracking (JSON format)
- `.claude/`: Sub-agent and command definitions

See [Development Documentation](docs/development/claude-code.md)

## Documentation

- [User Guide](docs/guide/README.md) - Complete user manual
- [Requirements](docs/design/requirements.md)
- [Architecture](docs/design/architecture.md)
- [Database Schema](docs/database/schema.md)
- [API Documentation](docs/api/README.md)
- [Development Guide](docs/development/README.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

Please follow our [Code of Conduct](CODE_OF_CONDUCT.md) when participating.

## License

MIT License - See [LICENSE](LICENSE)

## Acknowledgments

- [futu-api](https://github.com/FutunnOpen/py-futu-api) - Futu OpenAPI
- [akshare](https://github.com/akfamily/akshare) - Stock data interface
- [mplfinance](https://github.com/matplotlib/mplfinance) - Financial charts
- [Claude Code](https://claude.com/claude-code) - AI-assisted development
