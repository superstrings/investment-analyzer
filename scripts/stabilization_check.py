"""
企稳信号每日检查脚本

监控市场是否从下跌中企稳，给出可量化的企稳得分。
满足 ≥3 项信号即可开始考虑分批建仓 / Call 期权。

使用：
  python scripts/stabilization_check.py

输出：
  - 8 项信号检查（每项 0/1 分）
  - 综合得分 + 建议（0-2 等待 / 3-5 部分企稳 / 6-8 全面企稳）
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from sqlalchemy import select, desc

from db import get_session
from db.models import Kline


def get_kline(code: str, days: int = 60) -> pd.DataFrame:
    with get_session() as s:
        rows = s.execute(
            select(Kline).where(Kline.code == code).order_by(desc(Kline.trade_date)).limit(days)
        ).scalars().all()
    rows = list(reversed(rows))
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame([{
        'date': r.trade_date,
        'open': float(r.open), 'high': float(r.high), 'low': float(r.low), 'close': float(r.close),
        'vol': int(r.volume or 0),
        'pct': float(r.change_pct or 0),
    } for r in rows])
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    diff = df['close'].diff()
    direction = (diff > 0).astype(int) - (diff < 0).astype(int)
    df['obv'] = (direction * df['vol']).cumsum()
    return df


def signal_avgo_recover() -> tuple[int, str]:
    """信号1: AVGO 收复 400 + 站上 MA20"""
    df = get_kline('AVGO')
    if df.empty:
        return 0, 'AVGO 无数据'
    last = df.iloc[-1]
    cond1 = last.close > 400
    cond2 = last.close > last.ma20
    score = 1 if cond1 and cond2 else 0
    return score, f'AVGO ${last.close:.2f} | >400={cond1} | >MA20({last.ma20:.2f})={cond2}'


def signal_nvda_hold_ma10() -> tuple[int, str]:
    """信号2: NVDA 不破 MA10"""
    df = get_kline('NVDA')
    if df.empty:
        return 0, 'NVDA 无数据'
    last = df.iloc[-1]
    cond = last.close > last.ma10
    return (1 if cond else 0), f'NVDA ${last.close:.2f} > MA10(${last.ma10:.2f})? {cond}'


def signal_mrvl_obv_hold() -> tuple[int, str]:
    """信号3: MRVL 日线 OBV 不再创新低"""
    df = get_kline('MRVL', days=20)
    if df.empty or len(df) < 10:
        return 0, 'MRVL 数据不足'
    obv_now = df['obv'].iloc[-1]
    obv_min10 = df['obv'].tail(10).min()
    cond = obv_now > obv_min10
    return (1 if cond else 0), f'MRVL OBV={obv_now:.0f} | 10日最低={obv_min10:.0f} | 未创新低?{cond}'


def signal_us_3day_pos() -> tuple[int, str]:
    """信号4: 美股核心标的近3日累计涨跌 (NVDA+AVGO+MRVL+TER+GLW 平均)"""
    codes = ['NVDA', 'AVGO', 'MRVL', 'TER', 'GLW']
    pcts = []
    for c in codes:
        df = get_kline(c, days=10)
        if not df.empty and len(df) >= 3:
            recent = df.tail(3)
            cum = (recent['close'].iloc[-1] / recent['close'].iloc[0] - 1) * 100
            pcts.append(cum)
    if not pcts:
        return 0, '无数据'
    avg = sum(pcts) / len(pcts)
    cond = avg > -2  # 3日累计跌幅<2%即视为企稳
    return (1 if cond else 0), f'美股核心3日均涨跌={avg:+.2f}% (>-2%即企稳)'


def signal_hk_index_recover() -> tuple[int, str]:
    """信号5: 恒指缩量收阳"""
    df = get_kline('800000', days=10)
    if df.empty or len(df) < 5:
        return 0, '恒指无数据'
    last = df.iloc[-1]
    prev_5_vol = df['vol'].iloc[-6:-1].mean()
    cond1 = last.close > last.open
    cond2 = last.vol < prev_5_vol * 0.9 if prev_5_vol > 0 else False
    score = 1 if cond1 and cond2 else 0
    return score, f'恒指 收阳={cond1} | 缩量={cond2}'


def signal_a_leader_rise() -> tuple[int, str]:
    """信号6: A股领涨股(工业富联 601138)能否续涨"""
    df = get_kline('601138', days=5)
    if df.empty or len(df) < 2:
        return 0, '工业富联无数据'
    last = df.iloc[-1]
    cond = last.pct > 0
    return (1 if cond else 0), f'601138 工业富联 今日={last.pct:+.2f}% (>0即领涨)'


def signal_avgo_volume_capitulation() -> tuple[int, str]:
    """信号7: AVGO 成交量峰值（恐慌见底信号）"""
    df = get_kline('AVGO', days=30)
    if df.empty or len(df) < 20:
        return 0, 'AVGO 数据不足'
    last_vol = df['vol'].iloc[-1]
    avg_20vol = df['vol'].iloc[-20:].mean()
    cond = last_vol > avg_20vol * 1.5
    return (1 if cond else 0), f'AVGO 量={last_vol/1e6:.1f}M | 20日均量={avg_20vol/1e6:.1f}M | 放量>1.5x?{cond}'


def signal_no_new_low() -> tuple[int, str]:
    """信号8: 三大美股核心(NVDA/AVGO/MRVL)无一创 5 日新低"""
    codes = ['NVDA', 'AVGO', 'MRVL']
    new_lows = 0
    msgs = []
    for c in codes:
        df = get_kline(c, days=10)
        if df.empty or len(df) < 5:
            continue
        last_low = df['low'].iloc[-1]
        prev_5_low = df['low'].iloc[-6:-1].min()
        is_new_low = last_low < prev_5_low
        if is_new_low:
            new_lows += 1
        msgs.append(f'{c}={"⚠️新低" if is_new_low else "✓"}')
    cond = new_lows == 0
    return (1 if cond else 0), f'{" ".join(msgs)} | 无新低?{cond}'


SIGNALS = [
    ('1. AVGO 收复 400 + 站上 MA20', signal_avgo_recover),
    ('2. NVDA 不破 MA10', signal_nvda_hold_ma10),
    ('3. MRVL OBV 不创新低', signal_mrvl_obv_hold),
    ('4. 美股核心 3日累计 >-2%', signal_us_3day_pos),
    ('5. 恒指缩量收阳', signal_hk_index_recover),
    ('6. 工业富联续涨 (A股领涨)', signal_a_leader_rise),
    ('7. AVGO 放量 >1.5x (恐慌见底)', signal_avgo_volume_capitulation),
    ('8. 美股核心无一创5日新低', signal_no_new_low),
]


def main():
    print('═' * 70)
    print(f'  企稳信号检查 - {date.today().isoformat()}')
    print('═' * 70)
    total = 0
    for name, fn in SIGNALS:
        try:
            score, detail = fn()
            mark = '✅' if score else '❌'
            print(f'{mark} {name}')
            print(f'    └─ {detail}')
            total += score
        except Exception as e:
            print(f'❌ {name}')
            print(f'    └─ ERROR: {e}')

    print()
    print('═' * 70)
    print(f'  综合得分: {total}/8')
    print('═' * 70)

    if total >= 6:
        print('🟢 全面企稳 — 可启动 Call 期权 + 分批建仓')
    elif total >= 3:
        print('🟡 部分企稳 — 可小仓位试水核心标的（≤2%）')
    else:
        print('🔴 仍在下跌 — 继续观望，不主动交易')

    print()
    if total >= 3:
        print('📋 接下来执行：/企稳了-交易策略')
    else:
        print('📋 明天再检查 / 等待至少 3 项满足')

    print()
    print('⚠️  数据滞后提醒：本脚本基于数据库收盘数据（美股=昨日，A股/港股=今日）')
    print('    若需实时盘前/盘中信号，请先 `python main.py sync all -u dyson` 后再跑')


if __name__ == '__main__':
    main()
