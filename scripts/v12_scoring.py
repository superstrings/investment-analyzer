"""
V12 Technical Scoring for watchlist stocks.

Uses skills/analyst/ OBV + VCP analysis framework.
OBV score (0-50) + VCP score (0-50) -> Total V12 score (0-12)

Weekly K correction applied on top.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import date, timedelta
from skills.shared import DataProvider
from skills.analyst.stock_analyzer import StockAnalyzer


def get_weekly_kline(df: pd.DataFrame) -> pd.DataFrame:
    """Resample daily OHLCV to weekly."""
    if df.empty or len(df) < 10:
        return pd.DataFrame()
    weekly = df.resample("W").agg({
        "Open": "first",
        "High": "max",
        "Low": "min",
        "Close": "last",
        "Volume": "sum",
    }).dropna()
    return weekly


def calc_weekly_correction(df: pd.DataFrame) -> float:
    """
    Calculate weekly K-line correction (-1.0 to +1.0).
    Based on:
    - Weekly MA5/MA10/MA20 alignment
    - Weekly trend direction
    - Weekly volume trend
    """
    weekly = get_weekly_kline(df)
    if weekly.empty or len(weekly) < 20:
        return 0.0

    close = weekly["Close"]
    ma5 = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    correction = 0.0

    # MA alignment check (max +/- 0.5)
    latest_close = close.iloc[-1]
    latest_ma5 = ma5.iloc[-1]
    latest_ma10 = ma10.iloc[-1]
    latest_ma20 = ma20.iloc[-1]

    if pd.isna(latest_ma20):
        return 0.0

    # Bullish alignment: price > ma5 > ma10 > ma20
    if latest_close > latest_ma5 > latest_ma10 > latest_ma20:
        correction += 0.5
    # Bearish alignment: price < ma5 < ma10 < ma20
    elif latest_close < latest_ma5 < latest_ma10 < latest_ma20:
        correction -= 0.5
    # Partial alignment
    elif latest_close > latest_ma20:
        correction += 0.2
    elif latest_close < latest_ma20:
        correction -= 0.2

    # Weekly trend (last 4 weeks slope) (max +/- 0.3)
    recent_close = close.iloc[-4:]
    if len(recent_close) >= 4:
        x = np.arange(len(recent_close))
        slope = np.polyfit(x, recent_close.values.astype(float), 1)[0]
        avg_price = float(recent_close.mean())
        if avg_price > 0:
            norm_slope = slope / avg_price * 100
            if norm_slope > 2:
                correction += 0.3
            elif norm_slope > 0.5:
                correction += 0.15
            elif norm_slope < -2:
                correction -= 0.3
            elif norm_slope < -0.5:
                correction -= 0.15

    # Weekly volume trend (max +/- 0.2)
    vol = weekly["Volume"].iloc[-8:]
    if len(vol) >= 8:
        vol_first_half = float(vol.iloc[:4].mean())
        vol_second_half = float(vol.iloc[4:].mean())
        if vol_first_half > 0:
            vol_change = (vol_second_half - vol_first_half) / vol_first_half
            # Rising volume with rising price = bullish
            price_rising = float(close.iloc[-1]) > float(close.iloc[-4])
            if price_rising and vol_change > 0.1:
                correction += 0.2
            elif not price_rising and vol_change > 0.2:
                correction -= 0.2

    return max(-1.0, min(1.0, correction))


def get_ma20_trend(df: pd.DataFrame) -> str:
    """Determine MA20 trend direction."""
    if df.empty or len(df) < 25:
        return "N/A"
    close = df["Close"]
    ma20 = close.rolling(20).mean()
    if pd.isna(ma20.iloc[-1]) or pd.isna(ma20.iloc[-5]):
        return "N/A"
    slope = float(ma20.iloc[-1]) - float(ma20.iloc[-5])
    latest_price = float(close.iloc[-1])
    latest_ma20 = float(ma20.iloc[-1])

    if latest_price > latest_ma20 and slope > 0:
        return "UP"
    elif latest_price < latest_ma20 and slope < 0:
        return "DOWN"
    elif slope > 0:
        return "UP(below)"
    elif slope < 0:
        return "DOWN(above)"
    else:
        return "FLAT"


def get_signal_label(total_score: float) -> str:
    """Map V12 score to signal label."""
    if total_score >= 10:
        return "极强"
    elif total_score >= 8:
        return "强势"
    elif total_score >= 5:
        return "中性"
    elif total_score >= 3:
        return "转弱"
    else:
        return "弱势"


def calc_recent_change(df: pd.DataFrame, days: int = 20) -> float:
    """Calculate recent N-day price change %."""
    if df.empty or len(df) < days + 1:
        return 0.0
    close = df["Close"]
    start = float(close.iloc[-days - 1]) if len(close) > days else float(close.iloc[0])
    end = float(close.iloc[-1])
    if start == 0:
        return 0.0
    return (end - start) / start * 100


def load_watchlist_from_db():
    """Load active watchlist stocks from database."""
    from db.database import get_session
    from db.models import WatchlistItem, User
    from sqlalchemy import select

    # Skip non-stock items (indices, forex, options)
    skip_prefixes = (".", "800", "GAH", "ZJM", "CNC", "MET", "AMD2", "MRVL2")
    skip_codes = {"USDCNH", "XAUUSD"}

    stocks = []
    with get_session() as s:
        items = s.execute(
            select(WatchlistItem).join(User)
            .where(User.username == "dyson", WatchlistItem.is_active == True)
            .order_by(WatchlistItem.market, WatchlistItem.code)
        ).scalars().all()

        for item in items:
            code = item.code
            # Skip indices, forex, options
            if code in skip_codes:
                continue
            if any(code.startswith(p) for p in skip_prefixes):
                continue
            stocks.append((item.market, code, item.stock_name or code))

    return stocks


def main():
    stocks = load_watchlist_from_db()
    if not stocks:
        print("[ERROR] No watchlist stocks found in database")
        return

    analyzer = StockAnalyzer()
    data_provider = DataProvider()

    results = []

    for market, code, name in stocks:
        try:
            # Fetch 200 days to have enough for weekly resampling
            df = data_provider.get_klines_df(market, code, days=200)
            if df.empty or len(df) < 30:
                print(f"[WARN] {market}.{code} ({name}): insufficient data ({len(df)} rows), skipping")
                results.append({
                    "market": market, "code": code, "name": name,
                    "obv_score": 0, "vcp_score": 0, "weekly_corr": 0,
                    "total": 0, "signal": "N/A", "ma20": "N/A",
                    "price": 0, "change_20d": 0,
                })
                continue

            # Run analysis
            analysis = analyzer.analyze(df, market=market, code=code, name=name)

            # Raw scores from analyzer (0-100 scale)
            obv_raw = analysis.obv_analysis.score       # 0-100
            vcp_raw = analysis.vcp_analysis.overall_score  # 0-100

            # Convert to V12 sub-scores (each max 50)
            obv_v12 = obv_raw / 100 * 50   # 0-50
            vcp_v12 = vcp_raw / 100 * 50   # 0-50

            # Weekly K correction
            weekly_corr = calc_weekly_correction(df)

            # Total V12 score
            total = (obv_v12 + vcp_v12) / 100 * 12 + weekly_corr

            # Clamp to 0-12
            total = max(0, min(12, total))

            signal = get_signal_label(total)
            ma20_trend = get_ma20_trend(df)
            latest_price = float(df["Close"].iloc[-1])
            change_20d = calc_recent_change(df, 20)

            results.append({
                "market": market, "code": code, "name": name,
                "obv_score": obv_v12, "vcp_score": vcp_v12,
                "weekly_corr": weekly_corr, "total": total,
                "signal": signal, "ma20": ma20_trend,
                "price": latest_price, "change_20d": change_20d,
            })

        except Exception as e:
            print(f"[ERROR] {market}.{code} ({name}): {e}")
            results.append({
                "market": market, "code": code, "name": name,
                "obv_score": 0, "vcp_score": 0, "weekly_corr": 0,
                "total": 0, "signal": "ERROR", "ma20": "N/A",
                "price": 0, "change_20d": 0,
            })

    # Sort by total score descending
    results.sort(key=lambda x: x["total"], reverse=True)

    # Print table
    print()
    print(f"{'='*120}")
    print(f"V12 Technical Scoring Report - {date.today()}")
    print(f"{'='*120}")
    print(f"{'代码':<12} {'名称':<14} {'OBV/50':>8} {'VCP/50':>8} {'周K修正':>8} {'总分/12':>8} {'信号':<6} {'MA20趋势':<12} {'最新价':>10} {'近20日涨幅%':>12}")
    print(f"{'-'*120}")

    for r in results:
        full_code = f"{r['market']}.{r['code']}"
        print(
            f"{full_code:<12} {r['name']:<14} {r['obv_score']:>8.1f} {r['vcp_score']:>8.1f} "
            f"{r['weekly_corr']:>+8.2f} {r['total']:>8.2f} {r['signal']:<6} {r['ma20']:<12} "
            f"{r['price']:>10.2f} {r['change_20d']:>+12.2f}"
        )

    print(f"{'-'*120}")
    print(f"Total stocks: {len(results)}")
    print()

    # Summary by signal
    from collections import Counter
    signal_counts = Counter(r["signal"] for r in results)
    print("Signal distribution:")
    for sig in ["极强", "强势", "中性", "转弱", "弱势", "N/A", "ERROR"]:
        if sig in signal_counts:
            print(f"  {sig}: {signal_counts[sig]}")
    print()


if __name__ == "__main__":
    main()
