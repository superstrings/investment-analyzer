# 盘中5分钟K线分析

> 量在价先。价格可以骗人，量不会。只在高确定性的时刻才做判断。

## 参数

$ARGUMENTS - 股票代码（如 US.MRVL），逗号分隔多个。无代码时使用截图模式。

---

## 核心策略：趋势拐点 + 极端偏离

本策略寻找两类高盈亏比机会，用 Call/Put 捕捉趋势性行情：

### 机会类型A：趋势反转拐点

V2估值通过的股票，在技术面出现趋势逆转信号时入场。

**做多（买Call）拐点信号：**
- 长期下跌后，OBV底背离（价格新低但OBV不新低）+ 放量突破MA20
- 跌破20周线后缩量企稳 → 放量收回20周线
- 连续阴跌后出现放量长下影线（锤子线）+ OBV止跌

**做空（买Put）拐点信号：**
- 长期上涨后，OBV顶背离（价格新高但OBV不新高）+ 放量跌破MA20
- 站上20周线后冲高回落 → 放量跌破20周线
- 连续暴涨后出现放量长上影线（射击之星）+ OBV下台阶

### 机会类型B：极端偏离修复

股价出现不合理的大涨或大跌（偏离均值2σ+），预期均值回归。

**不合理暴跌（买Call）：**
- 单日跌幅>8% 且无基本面利空（非财报暴雷、非退市风险）
- 偏离20周线>-20% 且V2估值仍通过
- 盘中OBV在暴跌中企稳或出现底背离

**不合理暴涨（买Put）：**
- 单日涨幅>10% 且无基本面支撑（非业绩超预期、非并购）
- 偏离20周线>+40%，短期超买严重
- 盘中OBV在暴涨中出现顶背离或量能衰减

---

## 分析清单（每只股票必须逐项检查）

### 第一步：V2估值前置（一票否决）

- [ ] **V2估值是否通过？** 未通过不做Call（可考虑Put）
- [ ] **当前价 vs 20周线位置？** 偏离幅度决定方向和策略

### 第二步：OBV判断（权重最高）

- [ ] **盘中OBV趋势**：持续新高 ✅ / 持平 ⚠️ / 回落 ❌ / 深度负值 ❌❌
- [ ] **OBV-价格背离**：底背离(价跌OBV升) 🟢Call / 顶背离(价涨OBV跌) 🔴Put / 无背离
- [ ] **V12日线OBV子分(/50)**：≥35 ✅ / 25-35 ⚠️ / <25 ❌
- [ ] **日线+盘中OBV共振**：双强 ✅ / 一强一弱 ⚠️ / 双弱 ❌
- [ ] **VOL单调性**：VOL递减+OBV不跌(最佳) ✅ / VOL红绿交替放量(散户乱炒) ❌

> OBV = 能量/方向（主力意图）；VOL = 参与人数（含散户噪音）。
> **最佳组合：OBV强 + 缩量 = 主力吸筹散户不关注。**
> **理想形态：VOL单调递减 + OBV单调递增 = 散户退场+主力不走，最安全的入场窗口。**
> OBV弱 + 任何VOL = 不碰。

### 第三步：趋势拐点 or 极端偏离识别

- [ ] **属于哪种机会？**
  - A1: 趋势反转做多（OBV底背离 + 突破关键均线）→ 买Call
  - A2: 趋势反转做空（OBV顶背离 + 跌破关键均线）→ 买Put
  - B1: 不合理暴跌修复（单日>-8% + 无利空 + OBV企稳）→ 买Call
  - B2: 不合理暴涨修复（单日>+10% + 无利好 + OBV背离）→ 买Put
  - ❌ 无拐点/无偏离 → 不做

### 20周线规则（重要）

20周线（约100日均线）是中期趋势的核心锚点，优先级高于日线MA20。

| 信号 | 条件 | 操作 | 可靠性 |
|------|------|------|--------|
| **放量突破20周线** | 价格从下方突破+放量+OBV配合 | 🟢 趋势拐点，买Call | ⭐⭐⭐ |
| **缩量回踩20周线** | 上升趋势中回调到20周线+缩量+OBV不跌 | 🟢 最佳安全边际买Call | ⭐⭐⭐ |
| **放量跌破20周线** | 价格跌破+放量+OBV下台阶 | 🔴 趋势转空，买Put或离场 | ⭐⭐⭐ |

> **20周线是"牛熊分界线"——站上做多Call，跌破做空Put。**

### 第四步：Call/Put决策

- [ ] **方向**：Call（做多拐点/暴跌修复） or Put（做空拐点/暴涨修复）
- [ ] **行权价**：深度虚值，距当前价10%-15%（追求高盈亏比）
- [ ] **到期日**：至少30天以上（给趋势展开留时间）
- [ ] **挂单价**：钟摆过头 — 挂bid下方整数位，不市价追入
- [ ] **止损**：正股跌破/涨破关键技术位即止损（非固定百分比）
- [ ] **止盈**：不设固定止盈，跟踪趋势走，正股趋势结束再平仓
- [ ] **仓位**：单笔不超总资金2%，同时≤3个标的

---

## 盈亏比管理（核心）

**不用固定百分比OCO**，改用趋势跟踪：

### 止损规则（小亏）
- Call止损：正股跌破入场时的关键支撑位（如MA20/20周线/前低）
- Put止损：正股突破入场时的关键阻力位（如MA20/20周线/前高）
- 最大亏损：单笔不超过期权成本的100%（即最多亏完本金，但提前止损控制在30-50%）

### 止盈规则（大赚）
- **不设固定止盈**，让利润奔跑
- 正股到达目标位（如下一阻力位/支撑位）后，移动止盈至成本价
- 趋势加速阶段持有，趋势放缓（OBV背离/量能衰减）时分批止盈
- 目标盈亏比：1:3 起步，理想 1:5 ~ 1:10

### 仓位规则
- 期权仓位 = 愿意亏损的金额（假设全部归零）
- 单笔最大亏损 ≤ 总资金2%
- 看对了加仓（正股确认趋势后追加同方向期权），看错了认赔

---

## 决策流程

```
1. V2估值通过？
   ├─ 通过 → 可做Call，继续
   ├─ 不通过 → 只能做Put或不做
   └─ 未盈利 → 不做期权

2. 当前属于哪种机会？
   ├─ 趋势拐点（A1/A2）→ 确认OBV背离 + 关键位突破/跌破
   ├─ 极端偏离（B1/B2）→ 确认无基本面变化 + OBV信号
   └─ 都不是 → 不做，结束

3. OBV确认？
   ├─ 背离/企稳/共振 → 入场
   └─ OBV方向与预期矛盾 → 不做

4. 挂单
   └─ 深度虚值期权 → 钟摆挂单 → 成交后设关键位止损 → 跟踪趋势
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

V2估值: ✅/❌
20周线: 上方/下方 [偏离X%]

清单:
- 盘中OBV: ✅/❌ [具体值和方向]
- OBV背离: 🟢底背离/🔴顶背离/无
- 日线OBV: ✅/❌ [X/50]
- 机会类型: A1/A2/B1/B2/无
- 信号强度: ⭐⭐⭐/⭐⭐/⭐

当前: $XX | OBV: XX (UP/DOWN) | 量比: X.Xx
关键位: 支撑 $XX | 阻力 $XX

期权参考（如有拐点/偏离信号）:
- 方向: Call/Put
- 行权价: $XX（虚值10-15%）
- 到期日: MMDD（≥30天）
- 止损: 正股跌破/涨破 $XX 时平仓
- 止盈: 跟踪趋势，不设固定目标
- 盈亏比预期: 1:X
```

---

## 实战经验参考

### 趋势拐点案例
- 底背离做多：正股连跌3天但OBV持平 → 第4天放量反弹 → Call获利3-5倍
- 顶背离做空：正股创新高但OBV走平 → 随后破MA20 → Put获利2-3倍

### 极端偏离案例
- 暴跌修复：NVDA单日-8%无利空 → OBV企稳 → 买深虚Call → 3天反弹5% → Call获利4倍
- 暴涨修复：某股单日+15% → OBV顶背离 → 买深虚Put → 回调8% → Put获利3倍

### 钟摆挂单案例
- LITE 960C: 报价$76-84 → 挂$71 → 成交$70（超调30%）
- GEV 965C: 报价$36-40 → 挂$36 → 流动性差耐心等

### 注意事项
- 无量时不预测，等催化
- OBV下台阶是最强空头信号
- 深虚值期权流动性差，挂单要有耐心
- 非交易时段获取的是上一个交易日数据
- 美股可能无Futu行情权限，需截图模式
- **绝不追涨杀跌买期权** — 只在拐点和极端偏离时出手
