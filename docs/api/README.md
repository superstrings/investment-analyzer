# API 文档

> Investment Analyzer - Python API 参考

## 1. 分析模块 (analysis)

### 1.1 技术指标

#### RSI - 相对强弱指数

```python
from analysis import RSI, calculate_rsi

# 使用类
rsi = RSI(period=14)
result = rsi.calculate(df)
print(result.values.iloc[-1])  # 最新 RSI 值

# 使用便捷函数
rsi_series = calculate_rsi(df['close'], period=14)
```

#### MACD

```python
from analysis import MACD, MACDCrossover

macd = MACD(fast=12, slow=26, signal=9)
result = macd.calculate(df)

macd_df = result.values
# macd_df['macd'] - MACD 线
# macd_df['signal'] - 信号线
# macd_df['histogram'] - 柱状图

# 金叉/死叉检测
crossover = MACDCrossover()
cross_result = crossover.calculate(df)
# cross_result.values['crossover']: 1=金叉, -1=死叉, 0=无
```

#### 移动平均线

```python
from analysis import SMA, EMA, WMA, calculate_sma, calculate_ema

# 类方式
sma = SMA(period=20)
result = sma.calculate(df)

# 便捷函数
ma5 = calculate_sma(df['close'], 5)
ema20 = calculate_ema(df['close'], 20)
```

#### 布林带

```python
from analysis import BollingerBands, BollingerBandsSqueeze

bb = BollingerBands(period=20, std_dev=2)
result = bb.calculate(df)

bb_df = result.values
# bb_df['upper'] - 上轨
# bb_df['middle'] - 中轨
# bb_df['lower'] - 下轨

# 挤压检测
squeeze = BollingerBandsSqueeze(period=20, squeeze_threshold=0.05)
squeeze_result = squeeze.calculate(df)
```

#### OBV - 能量潮

```python
from analysis import OBV, OBVDivergence, calculate_obv

obv = calculate_obv(df['close'], df['volume'])

# 背离检测
divergence = OBVDivergence(lookback=20)
result = divergence.calculate(df)
```

### 1.2 VCP 形态识别

```python
from analysis import detect_vcp, VCPConfig, VCPScanner

# 快速检测
result = detect_vcp(df)
if result.is_vcp:
    print(f"VCP 得分: {result.score}")
    print(f"收缩次数: {result.contraction_count}")
    print(f"枢轴价: {result.pivot_price}")

# 自定义配置
config = VCPConfig(
    min_contractions=2,
    max_first_depth_pct=35.0,
    depth_decrease_ratio=0.7,
    pivot_distance_threshold=5.0,
)
result = detect_vcp(df, config)

# 使用扫描器 (带最低得分阈值)
scanner = VCPScanner(config=config, min_score=70)
scan_result = scanner.scan(df)
if scan_result.passed:
    print(f"VCP 检测通过: {scan_result.score}")
```

**VCPResult 属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| is_vcp | bool | 是否检测到 VCP |
| score | float | 得分 (0-100) |
| contraction_count | int | 收缩次数 |
| depth_sequence | list[float] | 深度序列 |
| pivot_price | float | 枢轴价格 |
| pivot_distance_pct | float | 距枢轴百分比 |
| volume_trend | float | 成交量趋势 |
| signals | list[str] | 信号列表 |

### 1.3 组合分析

```python
from analysis import (
    PortfolioAnalyzer,
    PositionData,
    AccountData,
    analyze_portfolio,
    analyze_positions_from_db,
)

# 准备数据
positions = [
    PositionData(
        market="HK",
        code="00700",
        stock_name="腾讯控股",
        qty=100,
        cost_price=350.0,
        market_price=380.0,
    ),
    PositionData(
        market="US",
        code="NVDA",
        stock_name="NVIDIA",
        qty=50,
        cost_price=500.0,
        market_price=600.0,
    ),
]

account = AccountData(
    total_assets=100000.0,
    cash=15000.0,
)

# 分析
result = analyze_portfolio(positions, account)

# 查看结果
print(f"持仓数量: {result.summary.position_count}")
print(f"总市值: {result.summary.total_market_value}")
print(f"总盈亏: {result.summary.total_pl_value}")
print(f"胜率: {result.summary.win_rate}%")

# 市场配比
for alloc in result.market_allocation:
    print(f"{alloc.market}: {alloc.weight:.1f}%")

# 风险指标
print(f"集中度风险: {result.risk_metrics.concentration_risk.value}")
print(f"HHI指数: {result.risk_metrics.hhi_index}")

# 信号
for signal in result.signals:
    print(f"- {signal}")
```

**PortfolioAnalysisResult 结构**:

```python
@dataclass
class PortfolioAnalysisResult:
    analysis_date: date
    summary: PortfolioSummary
    positions: list[PositionMetrics]
    market_allocation: list[MarketAllocation]
    risk_metrics: RiskMetrics
    top_performers: list[PositionMetrics]
    bottom_performers: list[PositionMetrics]
    signals: list[str]
```

### 1.4 技术分析器

```python
from analysis import TechnicalAnalyzer, AnalysisConfig

analyzer = TechnicalAnalyzer()
config = AnalysisConfig(
    ma_periods=[5, 10, 20, 60],
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
)

result = analyzer.analyze(df, config)
summary = result.summary()
```

## 2. 数据采集 (fetchers)

### 2.1 K线数据

```python
from fetchers import KlineFetcher, create_kline_fetcher

fetcher = KlineFetcher()

# 获取单只股票
result = fetcher.fetch("HK.00700", days=120)
df = result.df  # DataFrame

# 获取多只股票
results = fetcher.fetch_batch(["HK.00700", "US.NVDA"], days=60)
for code, result in results.items():
    print(f"{code}: {len(result.df)} 条记录")
```

### 2.2 富途数据

```python
from fetchers import FutuFetcher, create_futu_fetcher

# 使用工厂函数
fetcher = create_futu_fetcher(
    host="127.0.0.1",
    port=11111,
    trade_password="your_pwd",
)

# 上下文管理器
with fetcher:
    # 获取账户列表
    accounts = fetcher.get_account_list()

    # 获取持仓
    positions = fetcher.get_positions(account_id)

    # 获取交易记录
    deals = fetcher.get_today_deals(account_id)
```

## 3. 图表生成 (charts)

### 3.1 单图生成

```python
from charts import ChartGenerator, ChartConfig

generator = ChartGenerator(style="dark")

config = ChartConfig(
    ma_periods=[5, 10, 20, 60],
    show_volume=True,
    figsize=(16, 10),
)

# 生成图表
output_path = generator.generate(
    df,
    title="HK.00700",
    output_path="charts/output/00700.png",
    config=config,
)
```

### 3.2 批量生成

```python
from services import ChartService, create_chart_service

service = create_chart_service()

# 生成关注列表图表
result = service.generate_watchlist_charts(user_id=1, days=120)
print(f"生成 {result.charts_generated} 张图表")

# 生成持仓图表
result = service.generate_position_charts(user_id=1)
for path in result.generated_files:
    print(f"生成: {path}")
```

## 4. 报告生成 (reports)

### 4.1 报告类型

```python
from reports import ReportType, OutputFormat

# 报告类型
ReportType.PORTFOLIO   # 组合报告
ReportType.TECHNICAL   # 技术报告
ReportType.DAILY       # 每日简报
ReportType.WEEKLY      # 周度回顾

# 输出格式
OutputFormat.MARKDOWN  # Markdown
OutputFormat.JSON      # JSON
OutputFormat.HTML      # HTML
```

### 4.2 生成报告

```python
from reports import ReportGenerator, ReportConfig, generate_report

generator = ReportGenerator()

# 组合报告
portfolio_data = {...}  # PortfolioAnalysisResult.to_dict()
result = generator.generate_portfolio_report(portfolio_data)
result.save("reports/output/portfolio.md")

# 技术报告
technical_data = {...}
config = ReportConfig(
    report_type=ReportType.TECHNICAL,
    codes=["HK.00700"],
    include_charts=True,
)
result = generator.generate_technical_report(technical_data, config)

# 便捷函数
result = generate_report(ReportType.PORTFOLIO, data)
```

### 4.3 ReportResult

```python
@dataclass
class ReportResult:
    report_type: ReportType
    content: str              # 报告内容
    output_format: OutputFormat
    generated_at: datetime
    title: str
    metadata: dict
    chart_paths: list[str]

    def save(self, file_path: str) -> Path:
        """保存报告到文件"""

    def to_dict(self) -> dict:
        """转换为字典"""
```

## 5. 服务层 (services)

### 5.1 同步服务

```python
from services import SyncService, create_sync_service

service = create_sync_service(user_config)

# 同步持仓
result = service.sync_positions()
print(f"同步 {result.records_synced} 条持仓")

# 同步交易
result = service.sync_trades(days=30)

# 同步 K 线
result = service.sync_klines(codes=["HK.00700"])

# 全量同步
result = service.sync_all()
```

### 5.2 图表服务

```python
from services import ChartService

service = ChartService()

# 关注列表图表
result = service.generate_watchlist_charts(user_id, days=120)

# 持仓图表
result = service.generate_position_charts(user_id)

# 自定义代码
result = service.generate_charts_for_codes(
    codes=["HK.00700", "US.NVDA"],
    days=60,
    style="dark",
)
```

## 6. 数据库 (db)

### 6.1 会话管理

```python
from db import get_session, engine

# 会话上下文
with get_session() as session:
    user = session.query(User).filter_by(username="dyson").first()
    positions = session.query(Position).filter_by(account_id=1).all()
```

### 6.2 模型

```python
from db import User, Account, Position, Trade, Kline, Watchlist

# 查询示例
with get_session() as session:
    # 获取用户所有持仓
    positions = (
        session.query(Position)
        .join(Account)
        .filter(Account.user_id == user_id)
        .all()
    )
```

## 7. 配置 (config)

### 7.1 全局设置

```python
from config import get_settings

settings = get_settings()
print(settings.database_url)
print(settings.futu_host)
```

### 7.2 用户配置

```python
from config import get_user_config, list_users

# 获取用户配置
user_config = get_user_config("dyson")
print(user_config.futu.host)
print(user_config.futu.port)

# 列出所有用户
users = list_users()
```

---

*文档版本: 1.0*
*最后更新: 2025-12-14*
