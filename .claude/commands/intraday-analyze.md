# 盘中5分钟K线分析命令

基于量价OBV三要素，分析5分钟K线并检测交易信号。

支持两种模式：
1. **数据模式**：提供股票代码，自动从 Futu 获取5分钟K线数据进行分析
2. **截图模式**：用户附带5分钟K线截图，人工识别并分析

## 参数

$ARGUMENTS - 股票代码（如 US.MRVL、HK.00175），可逗号分隔多个

## 核心哲学

> 量在价先。价格可以骗人，量不会。
> 只在高确定性的时刻才做判断。

## 分析三要素

| 要素 | 观察点 | 权重 |
|------|--------|------|
| **量能(VOL)** | 量柱大小、vs MAVOL5/10、放量/缩量 | 最高 |
| **OBV** | 趋势方向、是否创新高/新低、与价格背离 | 高 |
| **价格(MA)** | MA5/MA20/MA60 位置、支撑阻力、K线形态 | 辅助 |

## 五种核心信号

| 信号 | 条件 | 预测 | 可靠性 |
|------|------|------|--------|
| **放量突破** | 量 > MAVOL5×2 + 价格突破横盘区间 | 🟢强烈看涨 | ⭐⭐⭐ |
| **缩量整理** | 量缩 + 价不跌 + OBV 不降 | 🟢偏涨(强势整理) | ⭐⭐⭐ |
| **冲高量不足** | 创新高但量 < 前次放量柱 | 🟠警惕回调(假突破) | ⭐⭐ |
| **放量冲高回落** | 长上影线 + 放量 | 🔴短期见顶 | ⭐⭐ |
| **无量横盘** | 极小量 + 窄幅 | 🟡不预测，等催化 | ⭐(不可判) |

## 决策流程

```
1. 量能是否放大？
   ├─ 是 → 价格方向？
   │   ├─ 向上突破区间 → 做多信号
   │   ├─ 冲高回落(长上影) → 短期顶部
   │   └─ 向下破位 → 做空/止损信号
   └─ 否 → OBV 方向？
       ├─ 维持高位/上升 → 强势整理，偏多
       ├─ 下降 → 资金出逃，偏空
       └─ 走平 → 无方向，继续等待
```

## 执行步骤

### 模式一：数据模式（提供代码，无截图）

#### 1. 获取5分钟K线数据

对每个股票代码，运行以下 Python 代码获取数据：

```python
source .venv/bin/activate && python << 'PYEOF'
from fetchers.kline_fetcher import KlineFetcher
from services.intraday_service import create_intraday_analyzer
import pandas as pd
import numpy as np

code = "$CODE"  # e.g., "US.MRVL"
fetcher = KlineFetcher()
df = fetcher.fetch_intraday(code, ktype='K_5M', bars=60)

if df.empty:
    print(f"无法获取 {code} 的5分钟K线数据（可能无行情权限或非交易时段）")
else:
    # 计算指标
    df['mavol5'] = df['volume'].rolling(5).mean()
    df['mavol10'] = df['volume'].rolling(10).mean()
    df['vol_ratio'] = df['volume'] / df['mavol5']
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean() if len(df) >= 60 else None

    # OBV
    obv = [0.0]
    for i in range(1, len(df)):
        if float(df['close'].iloc[i]) > float(df['close'].iloc[i-1]):
            obv.append(obv[-1] + float(df['volume'].iloc[i]))
        elif float(df['close'].iloc[i]) < float(df['close'].iloc[i-1]):
            obv.append(obv[-1] - float(df['volume'].iloc[i]))
        else:
            obv.append(obv[-1])
    df['obv'] = obv

    # 输出最近20根K线
    print(f"\n=== {code} 5分钟K线 (最近20根) ===\n")
    cols = ['trade_date', 'open', 'high', 'low', 'close', 'volume', 'vol_ratio', 'obv']
    for _, r in df.tail(20).iterrows():
        body = "阳" if float(r['close']) > float(r['open']) else "阴"
        vr = f"{float(r.get('vol_ratio') or 0):.2f}x"
        upper = float(r['high']) - max(float(r['close']), float(r['open']))
        total = float(r['high']) - float(r['low'])
        shadow_pct = f"{upper/total*100:.0f}%" if total > 0 else "0%"
        print(f"  {r['trade_date']}  O:{float(r['open']):>8.2f}  H:{float(r['high']):>8.2f}  L:{float(r['low']):>8.2f}  C:{float(r['close']):>8.2f}  {body}  Vol:{int(r['volume']):>10,}  量比:{vr}  上影:{shadow_pct}  OBV:{float(r['obv']):>12,.0f}")

    # 当前状态摘要
    latest = df.iloc[-1]
    print(f"\n--- 当前状态 ---")
    print(f"最新价: {float(latest['close']):.2f}  MA5: {float(latest.get('ma5') or 0):.2f}  MA20: {float(latest.get('ma20') or 0):.2f}")
    print(f"量比: {float(latest.get('vol_ratio') or 0):.2f}x MAVOL5")
    print(f"OBV: {float(latest['obv']):,.0f}  (5根前: {float(df['obv'].iloc[-6]):,.0f})")
    print(f"OBV趋势: {'UP' if float(latest['obv']) > float(df['obv'].iloc[-6]) else 'DOWN'}")

    # 运行信号检测
    analyzer = create_intraday_analyzer()
    market = code.split('.')[0]
    if market in ('SH', 'SZ'): market = 'A'
    signals = analyzer.analyze(df, code, market)
    print(f"\n--- 信号检测 ---")
    if signals:
        for s in signals:
            print(f"  {s.signal_type.value}: {s.reason} (置信度:{s.confidence:.0f}%)")
    else:
        print("  无明确信号")

fetcher._close_futu_ctx()
PYEOF
```

#### 2. 分析数据

基于获取到的K线数据：
- 识别最近的关键拐点（放量/缩量/冲高回落等）
- 判断当前属于哪种信号类型
- 给出短期预测和操作建议

#### 3. 输出结论

```
## [代码] 5分钟盘中分析

当前: $XX.XX | 量比: X.Xx | OBV趋势: UP/DOWN
信号: 🟢/🟠/🔴/🟡 [信号类型]

分析: [关键发现]
操作: [具体建议]
关键位: 支撑 $XX | 阻力 $XX

Call 参考 (如有放量突破信号):
- 建议行权价: $XX
- OCO: 止盈+50% / 止损-30%
```

### 模式二：截图模式（用户提供截图）

#### 1. 读取截图

从用户提供的5分钟K线截图中识别：
- 当前价格、涨跌幅
- MA5/MA10/MA20/MA60/MA250 数值
- OBV 当前值和趋势
- VOL 当前值、MAVOL5/MAVOL10
- 关键K线形态（阳线/阴线/十字星/长上影/长下影）

#### 2. 识别关键时间点

在图表中找出所有关键拐点/信号点：
- 放量突破的K线
- 冲高回落的K线
- 缩量整理区间
- OBV 方向变化点
- 均线金叉/死叉

#### 3. 逐点预测

对每个关键时间点，基于"当时可见信息"（假设后续未发生）：
- 识别属于哪种信号类型
- 给出预测方向（看涨/看跌/观望）
- 说明依据

#### 4. 对比实际

将预测与实际走势对比，标记对错。

## 输出格式

### 逐点分析表（截图模式）

| # | 时间 | 价格 | 可见信号 | 预测 | 依据 | 实际 | 对错 |
|---|------|------|---------|------|------|------|------|

### 当前状态判断

基于最新K线给出：
- 当前信号类型
- 短期预测（下一个5分钟/30分钟/收盘）
- 关键价位（支撑/阻力）
- 操作建议（含 Call 交易参考）

### 统计（如有多个预测点）

| 指标 | 数值 |
|------|------|
| 总预测点 | X |
| 正确 | X |
| 错误 | X |
| 成功率 | X% |

## 注意事项

- **无量时不预测** — 没有量就没有信息，观望比猜测更有价值
- **OBV 是真相** — 价格回调但 OBV 不跌 = 主力没走
- **量价背离是最强预警** — 新高无量比任何指标都先发出警告
- 不要在每根K线都做预测，只在**信号明确的关键拐点**预测
- 每次分析截图都是独立的，不要假设之前的预测结果
- 数据模式下如果 Futu 无行情权限（如美股），提示用户提供截图
- 非交易时段获取到的是上一个交易日的数据，注意标注
