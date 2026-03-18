"""
Generate daily analysis reports for positions and watchlist by market.

Usage:
    python scripts/gen_daily_analysis.py --user dyson --date 2026-03-17 \
        --markets HK,A --type post-market --output output/2026-03-17/
    python scripts/gen_daily_analysis.py --user dyson --date 2026-03-17 \
        --markets US --type pre-market --output output/2026-03-17/
"""

import argparse
import logging
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from analysis.technical import AnalysisConfig, TechnicalAnalyzer
from db.database import get_session
from db.models import Account, Kline, Position, User, WatchlistItem
from skills.analyst.batch_analyzer import BatchAnalyzer
from skills.analyst.stock_analyzer import StockAnalyzer
from skills.shared.data_provider import DataProvider

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def get_user_id(username: str) -> int:
    with get_session() as s:
        user = s.query(User).filter_by(username=username).first()
        if not user:
            raise ValueError(f"User '{username}' not found")
        return user.id


def get_positions_by_market(user_id: int, market: str) -> list[dict]:
    """Get deduplicated positions for a market."""
    with get_session() as s:
        account_ids = [a.id for a in s.query(Account).filter_by(user_id=user_id).all()]
        if not account_ids:
            return []

        positions = (
            s.query(Position)
            .filter(Position.account_id.in_(account_ids), Position.market == market)
            .all()
        )

        # Deduplicate by code, keeping the one with highest market_val
        seen = {}
        for p in positions:
            key = p.code
            val = float(p.market_val or 0)
            if key not in seen or val > seen[key]["market_val"]:
                seen[key] = {
                    "code": p.code,
                    "stock_name": p.stock_name,
                    "qty": float(p.qty),
                    "cost_price": float(p.cost_price),
                    "market_val": val,
                    "market": p.market,
                }
        return list(seen.values())


def get_watchlist_by_market(user_id: int, market: str) -> list[dict]:
    with get_session() as s:
        items = (
            s.query(WatchlistItem)
            .filter_by(user_id=user_id, market=market)
            .all()
        )
        return [
            {"code": w.code, "stock_name": w.stock_name, "market": w.market}
            for w in items
        ]


def get_klines_df(market: str, code: str, days: int = 250) -> pd.DataFrame:
    """Get K-line data as DataFrame."""
    with get_session() as s:
        klines = (
            s.query(Kline)
            .filter_by(market=market, code=code)
            .order_by(Kline.trade_date.desc())
            .limit(days)
            .all()
        )
        if not klines:
            return pd.DataFrame()

        data = []
        for k in reversed(klines):
            data.append({
                "trade_date": k.trade_date,
                "open": float(k.open),
                "high": float(k.high),
                "low": float(k.low),
                "close": float(k.close),
                "volume": float(k.volume),
            })
        df = pd.DataFrame(data)
        df.set_index("trade_date", inplace=True)
        return df


def is_option_code(code: str) -> bool:
    """Check if code is an option/warrant."""
    import re
    # HK option: contains letters mixed with digits like MET260629P60000
    if re.match(r"^[A-Z]+\d{6}[CP]\d+$", code):
        return True
    # US option format
    if re.match(r"^[A-Z]+\d{6}[CP]\d+$", code):
        return True
    return False


def is_index_code(code: str) -> bool:
    """Check if code is an index."""
    return code.startswith(".") or code in ("800000", "800125", "000001")


def is_futures_code(code: str) -> bool:
    """Check if code is futures."""
    return code.endswith("main")


def is_forex_code(code: str) -> bool:
    return code in ("USDCNH", "XAUUSD")


def analyze_stock(market: str, code: str, name: str, ta: TechnicalAnalyzer) -> dict | None:
    """Run technical analysis on a single stock."""
    df = get_klines_df(market, code)
    if df.empty or len(df) < 20:
        return None

    config = AnalysisConfig(
        ma_periods=[5, 10, 20, 60],
        rsi_period=14,
        include_signals=False,
    )
    analysis = ta.analyze(df, config)
    summary = analysis.summary()

    current = df["close"].iloc[-1]
    prev = df["close"].iloc[-2] if len(df) > 1 else current
    chg = (current - prev) / prev * 100

    # Extract MA values from summary
    ma5 = summary.get("SMA5")
    ma10 = summary.get("SMA10")
    ma20 = summary.get("SMA20")
    ma60 = summary.get("SMA60")

    # Convert numpy to float
    if ma5 is not None: ma5 = float(ma5)
    if ma10 is not None: ma10 = float(ma10)
    if ma20 is not None: ma20 = float(ma20)
    if ma60 is not None: ma60 = float(ma60)

    # RSI
    rsi_val = None
    rsi_data = summary.get(f"RSI{config.rsi_period}")
    if rsi_data is not None:
        rsi_val = float(rsi_data)

    # MACD - keys are lowercase: MACD, signal, histogram
    macd_val = macd_signal_val = macd_hist = None
    macd_data = summary.get("MACD")
    if isinstance(macd_data, dict):
        macd_val = macd_data.get("MACD")
        macd_signal_val = macd_data.get("signal")
        macd_hist = macd_data.get("histogram")
        if macd_val is not None: macd_val = float(macd_val)
        if macd_signal_val is not None: macd_signal_val = float(macd_signal_val)
        if macd_hist is not None: macd_hist = float(macd_hist)

    # Bollinger Bands - keys are lowercase
    bb_upper = bb_lower = bb_mid = None
    bb_data = summary.get("BollingerBands")
    if isinstance(bb_data, dict):
        bb_upper = bb_data.get("upper")
        bb_lower = bb_data.get("lower")
        bb_mid = bb_data.get("middle")
        if bb_upper is not None: bb_upper = float(bb_upper)
        if bb_lower is not None: bb_lower = float(bb_lower)
        if bb_mid is not None: bb_mid = float(bb_mid)

    # Trend detection
    ma_trend = "—"
    if ma5 and ma10 and ma20:
        if ma5 > ma10 > ma20:
            ma_trend = "多头排列"
        elif ma5 < ma10 < ma20:
            ma_trend = "空头排列"
        else:
            ma_trend = "交叉整理"

    # 20-day change
    d20 = min(20, len(df) - 1)
    chg20 = (current - df["close"].iloc[-d20 - 1]) / df["close"].iloc[-d20 - 1] * 100

    # Volume analysis
    vol_5avg = df["volume"].iloc[-5:].mean() if len(df) >= 5 else df["volume"].mean()
    vol_20avg = df["volume"].iloc[-20:].mean() if len(df) >= 20 else df["volume"].mean()
    vol_ratio = vol_5avg / vol_20avg if vol_20avg > 0 else 1.0

    return {
        "market": market,
        "code": code,
        "name": name,
        "price": current,
        "chg_pct": chg,
        "chg20_pct": chg20,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "ma_trend": ma_trend,
        "rsi": rsi_val,
        "macd": macd_val,
        "macd_signal": macd_signal_val,
        "macd_hist": macd_hist,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "bb_mid": bb_mid,
        "vol_ratio": vol_ratio,
        "last_date": str(df.index[-1]),
    }


def format_price(val, market=""):
    if val is None:
        return "—"
    if market in ("US",):
        return f"${val:.2f}"
    return f"{val:.3f}" if val < 1 else f"{val:.2f}"


def format_pct(val):
    if val is None:
        return "—"
    sign = "+" if val > 0 else ""
    return f"{sign}{val:.2f}%"


def rsi_status(rsi):
    if rsi is None:
        return "—"
    if rsi >= 70:
        return f"**{rsi:.1f}** (超买)"
    elif rsi <= 30:
        return f"**{rsi:.1f}** (超卖)"
    elif rsi >= 60:
        return f"{rsi:.1f} (偏强)"
    elif rsi <= 40:
        return f"{rsi:.1f} (偏弱)"
    return f"{rsi:.1f} (中性)"


def macd_status(hist):
    if hist is None:
        return "—"
    if hist > 0:
        return "红柱 (多头)"
    else:
        return "绿柱 (空头)"


MARKET_NAMES = {
    "HK": "港股",
    "US": "美股",
    "A": "A股",
    "JP": "日股",
}


def generate_report(
    analysis_date: str,
    report_type: str,
    markets: list[str],
    user_id: int,
    username: str,
) -> str:
    """Generate the analysis report markdown."""
    ta = TechnicalAnalyzer()

    market_labels = " / ".join(MARKET_NAMES.get(m, m) for m in markets)
    type_label = "盘后分析" if report_type == "post-market" else "盘前分析"

    lines = []
    lines.append(f"# {market_labels} {type_label} | {analysis_date}")
    lines.append("")
    lines.append(f"> 用户: {username} | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for market in markets:
        market_name = MARKET_NAMES.get(market, market)
        lines.append(f"## {market_name}市场")
        lines.append("")

        # Get positions (filter out options, zero qty)
        positions = get_positions_by_market(user_id, market)
        stock_positions = [
            p for p in positions
            if not is_option_code(p["code"]) and p["qty"] > 0
        ]
        option_positions = [
            p for p in positions
            if is_option_code(p["code"]) and p["qty"] > 0
        ]

        # Get watchlist (filter out indices, forex, futures, options already in positions)
        watchlist = get_watchlist_by_market(user_id, market)
        position_codes = {p["code"] for p in positions}
        watchlist_stocks = [
            w for w in watchlist
            if w["code"] not in position_codes
            and not is_index_code(w["code"])
            and not is_futures_code(w["code"])
            and not is_forex_code(w["code"])
            and not is_option_code(w["code"])
        ]

        # === POSITIONS ===
        if stock_positions:
            lines.append(f"### 持仓分析 ({len(stock_positions)} 只)")
            lines.append("")

            for pos in stock_positions:
                full_code = f"{market}.{pos['code']}"
                result = analyze_stock(market, pos["code"], pos["stock_name"], ta)
                if not result:
                    lines.append(f"#### {full_code} {pos['stock_name']} — 数据不足")
                    lines.append("")
                    continue

                cost = pos["cost_price"]
                mval = pos["market_val"]
                pl_pct = (result["price"] - cost) / cost * 100 if cost > 0 else 0

                lines.append(f"#### {full_code} {pos['stock_name']}")
                lines.append("")
                lines.append(f"| 指标 | 数值 |")
                lines.append(f"|------|------|")
                lines.append(f"| 现价 | {format_price(result['price'], market)} |")
                lines.append(f"| 成本 | {format_price(cost, market)} |")
                lines.append(f"| 持仓市值 | {format_price(mval, market)} |")
                lines.append(f"| 盈亏 | {format_pct(pl_pct)} |")
                lines.append(f"| 日涨跌 | {format_pct(result['chg_pct'])} |")
                lines.append(f"| 20日涨跌 | {format_pct(result['chg20_pct'])} |")
                lines.append(f"| MA趋势 | {result['ma_trend']} |")
                lines.append(f"| RSI(14) | {rsi_status(result['rsi'])} |")
                lines.append(f"| MACD | {macd_status(result['macd_hist'])} |")
                lines.append(f"| 量比(5/20) | {result['vol_ratio']:.2f} |")
                lines.append(f"| 数据截至 | {result['last_date']} |")
                lines.append("")

                # Key levels
                lines.append("**关键价位:**")
                if result["ma20"]:
                    lines.append(f"- MA20: {format_price(result['ma20'], market)}")
                if result["ma60"]:
                    lines.append(f"- MA60: {format_price(result['ma60'], market)}")
                if result["bb_upper"] and result["bb_lower"]:
                    lines.append(f"- 布林上轨: {format_price(result['bb_upper'], market)}")
                    lines.append(f"- 布林下轨: {format_price(result['bb_lower'], market)}")
                lines.append("")

        # === OPTIONS ===
        if option_positions:
            lines.append(f"### 期权/窝轮持仓 ({len(option_positions)} 只)")
            lines.append("")
            lines.append(f"| 代码 | 名称 | 数量 | 市值 |")
            lines.append(f"|------|------|------|------|")
            for pos in option_positions:
                lines.append(
                    f"| {market}.{pos['code']} | {pos['stock_name']} | "
                    f"{pos['qty']:.0f} | {format_price(pos['market_val'], market)} |"
                )
            lines.append("")

        # === WATCHLIST ===
        if watchlist_stocks:
            lines.append(f"### 关注列表 ({len(watchlist_stocks)} 只)")
            lines.append("")
            lines.append(
                f"| 代码 | 名称 | 现价 | 日涨跌 | 20日涨跌 | MA趋势 | RSI | MACD | 量比 |"
            )
            lines.append(
                f"|------|------|------|--------|---------|--------|-----|------|------|"
            )

            for w in watchlist_stocks:
                result = analyze_stock(market, w["code"], w["stock_name"], ta)
                if not result:
                    lines.append(
                        f"| {market}.{w['code']} | {w['stock_name']} | — | — | — | — | — | — | — |"
                    )
                    continue
                lines.append(
                    f"| {market}.{w['code']} | {w['stock_name']} | "
                    f"{format_price(result['price'], market)} | "
                    f"{format_pct(result['chg_pct'])} | "
                    f"{format_pct(result['chg20_pct'])} | "
                    f"{result['ma_trend']} | "
                    f"{rsi_status(result['rsi'])} | "
                    f"{macd_status(result['macd_hist'])} | "
                    f"{result['vol_ratio']:.2f} |"
                )
            lines.append("")

        if not stock_positions and not option_positions and not watchlist_stocks:
            lines.append("*无持仓或关注数据*")
            lines.append("")

        lines.append("---")
        lines.append("")

    # Footer
    lines.append("> 技术指标仅供参考，不构成投资建议。")
    lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate daily analysis reports")
    parser.add_argument("--user", "-u", required=True, help="Username")
    parser.add_argument("--date", "-d", default=date.today().isoformat(), help="Analysis date")
    parser.add_argument("--markets", "-m", required=True, help="Comma-separated markets (HK,US,A,JP)")
    parser.add_argument("--type", "-t", choices=["pre-market", "post-market"], required=True)
    parser.add_argument("--output", "-o", required=True, help="Output directory")

    args = parser.parse_args()
    markets = [m.strip() for m in args.markets.split(",")]

    user_id = get_user_id(args.user)

    report = generate_report(
        analysis_date=args.date,
        report_type=args.type,
        markets=markets,
        user_id=user_id,
        username=args.user,
    )

    # Write report
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    market_label = "-".join(m.lower() for m in markets)
    type_label = args.type
    filename = f"{args.date}-{market_label}-{type_label}.md"
    filepath = output_dir / filename

    filepath.write_text(report, encoding="utf-8")
    print(f"Report saved: {filepath}")
    print(f"  Markets: {', '.join(markets)}")
    print(f"  Type: {args.type}")


if __name__ == "__main__":
    main()
