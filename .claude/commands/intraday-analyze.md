# 盘中5分钟K线分析

> 量在价先。价格可以骗人，量不会。只在高确定性的时刻才做判断。

## 参数

$ARGUMENTS - 股票代码（如 US.MRVL），逗号分隔多个。无代码时使用截图模式。

---

## 分析清单（每只股票必须逐项检查）

对每只股票，按顺序完成以下检查，输出时标注 ✅/⚠️/❌：

### 第一步：OBV判断（权重最高，一票否决）

- [ ] **盘中OBV趋势**：持续新高 ✅ / 持平 ⚠️ / 回落 ❌ / 深度负值 ❌❌
- [ ] **OBV-价格背离**：底背离(价跌OBV升) 🟢买点 / 顶背离(价涨OBV跌) 🔴卖点 / 无背离
- [ ] **V12日线OBV子分(/50)**：≥35 ✅ / 25-35 ⚠️ / <25 ❌
- [ ] **日线+盘中OBV共振**：双强 ✅ / 一强一弱 ⚠️ / 双弱 ❌（一票否决）

> OBV = 能量/方向（主力意图）；VOL = 参与人数（含散户噪音）。
> **最佳组合：OBV强 + 缩量 = 主力吸筹散户不关注。**
> OBV弱 + 任何VOL = 不碰。

### 第二步：回调质量（安全边际）

- [ ] **回调时量能**：缩量(<暴涨量30%) ✅ / 放量(>暴涨量50%) ❌
- [ ] **回调时OBV**：持平或微跌 ✅ / 下台阶 ❌
- [ ] **回调幅度**：38%-50%回撤 ✅ / >61.8%回撤 ❌
- [ ] **K线形态**：小实体+下影线(有买盘托) ✅ / 大阴线无下影(恐慌) ❌
- [ ] **均线支撑**：回踩MA5/MA20 ✅ / 跌破MA20 ❌

> **核心原则：做上升趋势中的小回调，不追涨。安全边际最重要。**
> 不看价格回调了多少，看OBV回调了多少。

### 第三步：信号确认

- [ ] **当前属于哪种信号？**
  - 🟢 放量突破（量>MAVOL5×2 + 价格突破区间）⭐⭐⭐
  - 🟢 缩量整理（量缩 + 价不跌 + OBV不降）⭐⭐⭐
  - 🟠 冲高量不足（新高但量<前次放量柱）⭐⭐
  - 🔴 放量冲高回落（长上影 + 放量）⭐⭐
  - 🟡 无量横盘（极小量 + 窄幅 → 不预测）⭐

### 第四步：超短Call决策（如适用）

- [ ] **选股排序**：盘中OBV > V12日线OBV > Delta > Call流动性
- [ ] **行权价**：略虚值，距当前价3%-5%
- [ ] **挂单价**：钟摆过头 — 挂bid下方整数位，不市价追入
- [ ] **OCO**：成交后立即设止盈+50% / 止损-30%
- [ ] **仓位**：同时≤3个标的，总风险敞口可控

---

## 决策流程

```
1. OBV方向？（一票否决）
   ├─ OBV持续新高/底背离 → 继续
   └─ OBV下台阶/深度负值 → 不碰，结束

2. 回调质量？（安全边际）
   ├─ 缩量回调 + OBV不跌 → 继续
   └─ 放量回调 + OBV下台阶 → 不入场，结束

3. 信号类型？
   ├─ 放量突破 / 缩量整理 → 入场
   ├─ 冲高量不足 → 观望
   └─ 冲高回落 / 无量横盘 → 不做

4. 挂单（钟摆过头）
   └─ 观察Call报价区间 → 挂区间低端下方整数位 → 等成交 → 设OCO
```

---

## 执行步骤

### 数据模式（提供代码）

运行以下代码获取5分钟K线数据：

```python
source .venv/bin/activate && python << 'PYEOF'
from fetchers.kline_fetcher import KlineFetcher
from services.intraday_service import create_intraday_analyzer
import pandas as pd
import numpy as np

code = "$CODE"
fetcher = KlineFetcher()
df = fetcher.fetch_intraday(code, ktype='K_5M', bars=60)

if df.empty:
    print(f"无法获取 {code} 的5分钟K线数据")
else:
    df['mavol5'] = df['volume'].rolling(5).mean()
    df['vol_ratio'] = df['volume'] / df['mavol5']
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma20'] = df['close'].rolling(20).mean()

    obv = [0.0]
    for i in range(1, len(df)):
        if float(df['close'].iloc[i]) > float(df['close'].iloc[i-1]):
            obv.append(obv[-1] + float(df['volume'].iloc[i]))
        elif float(df['close'].iloc[i]) < float(df['close'].iloc[i-1]):
            obv.append(obv[-1] - float(df['volume'].iloc[i]))
        else:
            obv.append(obv[-1])
    df['obv'] = obv

    for _, r in df.tail(20).iterrows():
        body = "阳" if float(r['close']) > float(r['open']) else "阴"
        vr = f"{float(r.get('vol_ratio') or 0):.2f}x"
        print(f"  {r['trade_date']}  O:{float(r['open']):>8.2f}  H:{float(r['high']):>8.2f}  L:{float(r['low']):>8.2f}  C:{float(r['close']):>8.2f}  {body}  Vol:{int(r['volume']):>10,}  量比:{vr}  OBV:{float(r['obv']):>12,.0f}")

    latest = df.iloc[-1]
    print(f"\n最新价: {float(latest['close']):.2f}  MA5: {float(latest.get('ma5') or 0):.2f}  MA20: {float(latest.get('ma20') or 0):.2f}")
    print(f"量比: {float(latest.get('vol_ratio') or 0):.2f}x  OBV: {float(latest['obv']):,.0f}  (5根前: {float(df['obv'].iloc[-6]):,.0f})")
    print(f"OBV趋势: {'UP' if float(latest['obv']) > float(df['obv'].iloc[-6]) else 'DOWN'}")

    analyzer = create_intraday_analyzer()
    market = code.split('.')[0]
    if market in ('SH', 'SZ'): market = 'A'
    signals = analyzer.analyze(df, code, market)
    if signals:
        for s in signals:
            print(f"  {s.signal_type.value}: {s.reason} (置信度:{s.confidence:.0f}%)")
    else:
        print("  无明确信号")

fetcher._close_futu_ctx()
PYEOF
```

然后按分析清单逐项检查，输出结论。

### 截图模式（用户提供截图）

从截图中识别：价格/涨跌幅、MA数值、OBV值和趋势、VOL/MAVOL、K线形态。
找出关键拐点，按分析清单逐项检查，给出逐点分析表：

| # | 时间 | 价格 | 信号 | 预测 | 依据 | 实际 | 对错 |
|---|------|------|------|------|------|------|------|

---

## 输出格式

```
## [代码] 盘中分析

清单:
- OBV趋势: ✅/❌ [具体值和方向]
- OBV背离: 🟢/🔴/无
- V12日线OBV: ✅/❌ [X/50]
- 回调质量: ✅/❌ [缩量/放量, OBV变化]
- 信号: 🟢/🟠/🔴/🟡 [类型]

当前: $XX | OBV: XX (UP/DOWN) | 量比: X.Xx
关键位: 支撑 $XX | 阻力 $XX
操作: [具体建议]

Call参考（如适用）:
- 标的: XX 0424 XXC
- 挂单: $XX（钟摆）
- OCO: TP +50% / SL -30%
```

---

## 实战经验参考

### 钟摆挂单案例
- LITE 960C: 报价$76-84 → 挂$71 → 成交$70（超调30%）
- GEV 965C: 报价$36-40 → 挂$36 → 流动性差耐心等

### 回调质量案例（2026-04-09）
- GEV ✅: 涨至$962→回调$952, OBV 50→55持续新高 → 强势回调, 全天最优
- MRVL ✅: 开盘砸至$117.8, OBV从-750回升至-534(底背离) → 随后突破$122
- LITE ❌: 涨至$960→回调$918, OBV 532→475持续下滑 → 弱势回调, 放量出货
- COHR ❌: 涨至$301→回调$287, OBV 300→236持续下滑 → 弱势回调, 放量出货

### 注意事项
- 无量时不预测，等催化
- OBV下台阶是最强空头信号
- 超短做回调不追涨
- 非交易时段获取的是上一个交易日数据
- 美股可能无Futu行情权限，需截图模式
