# Deep Analyzer Skill

## Overview

Deep Analyzer provides comprehensive stock analysis for trend traders seeking compound growth opportunities in major industry cycles. It combines multiple analysis dimensions to generate actionable investment recommendations.

## Features

### Technical Analysis (Enhanced)

- **Trend Analysis**: Short/medium/long term trend detection with strength scoring
- **Moving Averages**: MA5/10/20/60 with alignment analysis
- **RSI Analysis**: Overbought/oversold detection with divergence signals
- **MACD Analysis**: Trend, crossover, and divergence detection
- **OBV Analysis**: Volume trend and price-volume divergence
- **VCP Pattern**: Volatility Contraction Pattern detection
- **Bollinger Bands**: Position and volatility analysis
- **Support/Resistance**: Pivot point based level calculation
- **Volume Analysis**: Volume trend and ratio vs average

### Fundamental Analysis (Web-based)

- **Valuation Metrics**: PE, PB, PS, PEG ratios
- **Financial Metrics**: ROE, ROA, margins, growth rates
- **Market Data**: Market cap, shares outstanding
- **Dividend Data**: Yield and payout ratio

### Industry Analysis

- **Industry Classification**: Sector and industry identification
- **Industry Trends**: Key trends and outlook
- **Competitive Landscape**: Major competitors

### News Analysis

- **Recent News**: Latest news and announcements
- **Sentiment Analysis**: Positive/negative/neutral classification
- **Event Detection**: Earnings, announcements, etc.

## Usage

### CLI Command

```bash
# Basic analysis
python main.py deep-analyze --code HK.00700 --user dyson

# Analysis with output file
python main.py deep-analyze --code HK.00700 --user dyson --output report.md

# Analysis without web data (faster)
python main.py deep-analyze --code HK.00700 --user dyson --no-web

# Multiple stocks
python main.py deep-analyze --codes "HK.00700,HK.00981" --user dyson
```

### Programmatic Usage

```python
from skills.deep_analyzer import DeepAnalyzer, generate_deep_analysis_report
from skills.shared import DataProvider

# Initialize
data_provider = DataProvider()
analyzer = DeepAnalyzer(data_provider)

# Analyze
result = analyzer.analyze(
    market="HK",
    code="00700",
    stock_name="腾讯控股",
    user_id=1,
    include_web_data=True,
)

# Generate report
report = generate_deep_analysis_report(result)
print(report)
```

## Output Format

The report includes:

1. **Header**: Stock info, price, overall rating
2. **Executive Summary**: Key points and signals
3. **Technical Analysis**: Comprehensive technical indicators
4. **Fundamental Analysis**: Valuation and financial metrics
5. **Industry Analysis**: Industry trends and outlook
6. **News & Events**: Recent news with sentiment
7. **Investment Recommendation**:
   - Short/medium/long term actions
   - Entry/stop-loss/target prices
   - Risk-reward ratio
8. **Risk Assessment**: Risk factors and warnings

## Scoring System

- **Technical Score**: 0-100 based on indicators
- **Overall Score**: Weighted combination of technical, fundamental, news, and industry
- **Rating**: strong_buy (75+), buy (60-74), hold (40-59), sell (25-39), strong_sell (<25)

## Investment Philosophy

This analyzer is designed for:

- **Trend Trading**: Following medium to long-term trends
- **Compound Growth**: Focus on high-quality growth opportunities
- **Industry Cycles**: Identifying stocks in favorable industry cycles
- **Risk Management**: Clear stop-loss and target recommendations

## Dependencies

- `analysis.indicators`: Technical indicator calculations
- `skills.shared`: Data provider for market data
- Web search capabilities for fundamental/news data

## Limitations

- Fundamental data quality depends on web search results
- News sentiment is based on simple keyword matching
- Not suitable for high-frequency trading decisions
- Web data may be delayed or incomplete
