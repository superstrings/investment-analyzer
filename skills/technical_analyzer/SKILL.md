# 技术分析师 (Technical Analyzer)

## 能力描述
对个股进行技术分析，计算技术指标，识别VCP形态，评估趋势强度，生成买卖信号。

## 数据来源
- 数据库表: `klines`
- K线数据: `fetchers.KlineFetcher`
- 图表输出: `charts/output/`
- Python 模块: `analysis.indicators`, `analysis.technical`

## 使用方法

### 方法 1: Python API (推荐)

```python
import pandas as pd
from fetchers import KlineFetcher
from analysis import (
    TechnicalAnalyzer,
    AnalysisConfig,
    analyze_stock,
)
from analysis.indicators import (
    RSI, MACD, BollingerBands, OBV,
    VCP, VCPScanner, detect_vcp, scan_vcp,
    calculate_sma, calculate_ema, calculate_rsi,
)

# 获取K线数据
fetcher = KlineFetcher()
result = fetcher.fetch("HK.00700", days=120)
df = result.df

# === 单独使用指标 ===

# RSI
rsi = RSI(period=14)
rsi_result = rsi.calculate(df)
print(f"RSI(14): {rsi_result.values.iloc[-1]:.2f}")

# MACD
macd = MACD()
macd_result = macd.calculate(df)
macd_df = macd_result.values
print(f"MACD: {macd_df['macd'].iloc[-1]:.2f}")
print(f"Signal: {macd_df['signal'].iloc[-1]:.2f}")

# Bollinger Bands
bb = BollingerBands(period=20, std_dev=2)
bb_result = bb.calculate(df)
bb_df = bb_result.values
print(f"Upper: {bb_df['upper'].iloc[-1]:.2f}")
print(f"Middle: {bb_df['middle'].iloc[-1]:.2f}")
print(f"Lower: {bb_df['lower'].iloc[-1]:.2f}")

# VCP 形态检测
vcp_result = detect_vcp(df)
if vcp_result.is_vcp:
    print(f"VCP 检测到! 得分: {vcp_result.score:.1f}")
    print(f"收缩次数: {vcp_result.contraction_count}")
    print(f"枢轴价: {vcp_result.pivot_price:.2f}")
    for signal in vcp_result.signals:
        print(f"  - {signal}")

# === 使用统一分析器 ===

analyzer = TechnicalAnalyzer()
config = AnalysisConfig(
    ma_periods=[5, 10, 20, 60],
    rsi_period=14,
    macd_fast=12,
    macd_slow=26,
    macd_signal=9,
)
analysis_result = analyzer.analyze(df, config)

# 查看分析摘要
summary = analysis_result.summary()
print(summary)
```

### 方法 2: CLI 命令

```bash
# 生成带技术指标的K线图
python main.py chart single --code HK.00700 --days 120 --style dark

# 生成关注列表的图表
python main.py chart watchlist --user dyson --days 60

# 生成持仓股票图表
python main.py chart positions --user dyson
```

## 技术指标

### 1. 均线系统 (MA)
```python
from analysis.indicators import SMA, EMA, WMA, calculate_sma

# 计算多条均线
ma5 = calculate_sma(df['close'], 5)
ma10 = calculate_sma(df['close'], 10)
ma20 = calculate_sma(df['close'], 20)
ma60 = calculate_sma(df['close'], 60)

# 多头排列判断: MA5 > MA10 > MA20 > MA60
bullish_alignment = ma5.iloc[-1] > ma10.iloc[-1] > ma20.iloc[-1] > ma60.iloc[-1]
```

### 2. RSI (相对强弱指数)
```python
from analysis.indicators import RSI, calculate_rsi

rsi_values = calculate_rsi(df['close'], period=14)
current_rsi = rsi_values.iloc[-1]

# 判断超买超卖
if current_rsi > 70:
    signal = "超买"
elif current_rsi < 30:
    signal = "超卖"
else:
    signal = "中性"
```

### 3. MACD
```python
from analysis.indicators import MACD, MACDCrossover

macd = MACD(fast=12, slow=26, signal=9)
result = macd.calculate(df)

# 金叉/死叉检测
crossover = MACDCrossover()
cross_result = crossover.calculate(df)
# cross_result.values 包含 'crossover' 列: 1=金叉, -1=死叉, 0=无
```

### 4. 布林带 (Bollinger Bands)
```python
from analysis.indicators import BollingerBands, BollingerBandsSqueeze

bb = BollingerBands(period=20, std_dev=2)
bb_result = bb.calculate(df)

# 挤压检测 (波动收窄)
squeeze = BollingerBandsSqueeze(period=20, squeeze_threshold=0.05)
squeeze_result = squeeze.calculate(df)
# squeeze_result.values['squeeze'] = True 表示挤压状态
```

### 5. OBV (能量潮)
```python
from analysis.indicators import OBV, OBVDivergence, calculate_obv

obv = calculate_obv(df['close'], df['volume'])

# 背离检测
divergence = OBVDivergence(lookback=20)
div_result = divergence.calculate(df)
# 'bullish_divergence' 和 'bearish_divergence' 列
```

### 6. VCP (波动收缩形态)
```python
from analysis.indicators import VCP, VCPScanner, VCPConfig, detect_vcp, scan_vcp

# 快速检测
vcp_result = detect_vcp(df)

# 带自定义参数
config = VCPConfig(
    min_contractions=2,        # 最少收缩次数
    max_first_depth_pct=35.0,  # 首次收缩最大深度
    depth_decrease_ratio=0.7,  # 收缩深度递减比例
    pivot_distance_threshold=5.0,  # 距枢轴最大距离
)
scanner = VCPScanner(config=config, min_score=70)
scan_result = scanner.scan(df)

# VCP 得分解读
# 0-50: 弱VCP
# 50-70: 一般VCP
# 70-85: 良好VCP
# 85-100: 优秀VCP
```

## 评分标准

### 趋势得分 (0-100)
- MA排列: 多头排列+30, 空头排列-30
- 价格位置: 高于MA20+20, 低于MA20-20
- 斜率: MA20上升+15, 下降-15

### RSI得分 (0-100)
- 30-50: 40分 (超卖回升区)
- 50-60: 70分 (健康区)
- 60-70: 50分 (强势区)
- >70或<30: 30分 (极端区)

### MACD得分 (0-100)
- 金叉: +30
- MACD>0: +20
- 柱状图放大: +20
- 零轴以上金叉: +30 (额外)

### VCP得分 (0-100)
- 直接使用 `vcp_result.score`

### 综合评分
```
综合得分 = 趋势得分 × 0.3 + RSI得分 × 0.2 + MACD得分 × 0.2 + VCP得分 × 0.3
```

## 输出格式

### 技术分析报告
```
股票: HK.00700 腾讯控股
日期: 2024-12-14

=== 趋势分析 ===
均线排列: 多头 (MA5 > MA10 > MA20 > MA60)
价格位置: 高于MA20 3.5%
MA20斜率: 上升 (+2.1%/周)

=== 动量指标 ===
RSI(14): 58.3 (中性)
MACD: 2.35 (零轴上方)
MACD信号: 金叉 (3天前)

=== 波动分析 ===
布林带位置: 中轨上方 (62%)
布林带宽度: 5.2% (正常)
ATR(14): 8.5

=== VCP形态 ===
状态: 检测到VCP
得分: 78.5
收缩次数: 3
深度序列: 18% → 11% → 5%
枢轴价: 385.00
距枢轴: 1.3%

=== 综合评估 ===
技术评分: 75/100
信号: 看多
建议: 等待突破枢轴385.00后买入

=== 支撑/阻力 ===
支撑1: 365.00 (MA20)
支撑2: 350.00 (MA60)
阻力1: 385.00 (枢轴)
阻力2: 400.00 (前高)
```
