#!/usr/bin/env python3
"""
Intraday monitoring script.

Polls 5-minute K-line data from Futu OpenAPI, detects trading signals
using Volume-Price-OBV analysis, and sends DingTalk alerts.

Usage:
    python scripts/intraday_monitor.py --codes HK.00175,US.MRVL --user dyson
    python scripts/intraday_monitor.py --positions --user dyson
    python scripts/intraday_monitor.py --codes HK.00175 --interval 5 --dry-run
"""

import argparse
import json
import logging
import os
import sys
import time as time_mod
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.intraday_service import (
    IntradayAnalyzer,
    IntradaySignal,
    IntradaySignalType,
    create_intraday_analyzer,
)
from services.market_hours import get_active_markets, is_market_open, seconds_until_market_open

# Logging setup
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "intraday.log")),
    ],
)
logger = logging.getLogger("intraday_monitor")


class IntradayMonitor:
    """
    Main intraday monitoring loop.

    Fetches 5-min K-lines, runs signal detection, and alerts via DingTalk.
    """

    def __init__(
        self,
        user: str,
        codes: list[str],
        interval_minutes: int = 5,
        cooldown_minutes: int = 30,
        dry_run: bool = False,
    ):
        self.user = user
        self.codes = codes
        self.interval = interval_minutes
        self.cooldown = cooldown_minutes
        self.dry_run = dry_run

        # In-memory 5-min bar storage: {"HK.00175": pd.DataFrame}
        self._bars: dict[str, pd.DataFrame] = {}

        # Signal cooldown: {"HK.00175:放量突破": datetime}
        self._cooldowns: dict[str, datetime] = {}

        # Last trading date per code (for clearing bars on new day)
        self._last_dates: dict[str, str] = {}

        # Services (lazy init)
        self._analyzer = create_intraday_analyzer()
        self._kline_fetcher = None
        self._dingtalk = None
        self._signal_svc = None

    def run(self):
        """Main monitoring loop."""
        logger.info(f"Starting intraday monitor: {len(self.codes)} stocks, interval={self.interval}m, dry_run={self.dry_run}")
        logger.info(f"Monitoring: {', '.join(self.codes)}")

        while True:
            try:
                active_markets = get_active_markets()
                active_codes = [
                    c for c in self.codes
                    if self._code_market(c) in active_markets
                ]

                if not active_codes:
                    all_markets = list(set(self._code_market(c) for c in self.codes))
                    wait_times = []
                    for m in all_markets:
                        w = seconds_until_market_open(m)
                        if w > 0:
                            wait_times.append(w)

                    if wait_times:
                        wait = min(wait_times)
                        wait_capped = min(wait, 300)  # Check every 5 min max
                        logger.info(f"No markets open. Next open in {wait/60:.0f}min. Sleeping {wait_capped:.0f}s")
                        time_mod.sleep(wait_capped)
                    else:
                        time_mod.sleep(60)
                    continue

                logger.info(f"Poll cycle: {len(active_codes)} active stocks in markets {active_markets}")
                self._poll_cycle(active_codes)
                time_mod.sleep(self.interval * 60)

            except (KeyboardInterrupt, SystemExit):
                logger.info("Monitor stopped")
                break
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                time_mod.sleep(30)

        self._cleanup()

    def _poll_cycle(self, codes: list[str]):
        """One polling cycle: fetch bars → analyze → alert."""
        fetcher = self._get_kline_fetcher()

        for code in codes:
            try:
                df = fetcher.fetch_intraday(code, ktype="K_5M", bars=60)
                if df is None or df.empty:
                    continue

                # Clear bars if new trading day
                self._check_new_day(code, df)

                # Merge with existing bars
                self._bars[code] = self._merge_bars(self._bars.get(code), df)

                # Analyze
                market = self._code_market(code)
                stock_name = ""
                if "name" in self._bars[code].columns and not self._bars[code]["name"].empty:
                    stock_name = str(self._bars[code]["name"].iloc[0] or "")
                signals = self._analyzer.analyze(
                    self._bars[code], code, market, stock_name=stock_name,
                )

                for signal in signals:
                    if self._is_cooled_down(signal):
                        self._handle_signal(signal)

                # Rate limit: 0.6s between requests
                time_mod.sleep(0.6)

            except Exception as e:
                logger.error(f"Error processing {code}: {e}")

    def _handle_signal(self, signal: IntradaySignal):
        """Persist signal to DB and send DingTalk alert."""
        logger.info(
            f"SIGNAL: {signal.signal_type.value} | {signal.code} | "
            f"${signal.price} | vol_ratio={signal.volume_ratio}x | "
            f"OBV={signal.obv_trend} | confidence={signal.confidence}%"
        )

        # Persist to DB
        if not self.dry_run:
            try:
                self._save_signal(signal)
            except Exception as e:
                logger.error(f"Failed to save signal to DB: {e}")

        # Send DingTalk alert (skip NO_VOL_RANGE - not actionable)
        if signal.signal_type != IntradaySignalType.NO_VOL_RANGE:
            self._send_alert(signal)

        # Update cooldown
        key = f"{signal.code}:{signal.signal_type.value}"
        self._cooldowns[key] = datetime.now()

    def _save_signal(self, signal: IntradaySignal):
        """Save signal to database via SignalService."""
        svc = self._get_signal_service()
        if svc is None:
            return

        signal_type_map = {
            IntradaySignalType.VOLUME_BREAKOUT: "BUY",
            IntradaySignalType.LOW_VOL_CONSOLIDATION: "HOLD",
            IntradaySignalType.WEAK_VOL_HIGH: "WATCH",
            IntradaySignalType.VOL_REVERSAL: "SELL",
            IntradaySignalType.NO_VOL_RANGE: "WATCH",
        }

        market = self._code_market(signal.code)
        pure_code = signal.code.split(".")[-1] if "." in signal.code else signal.code

        svc.create_signal(
            user_id=self._get_user_id(),
            market=market,
            code=pure_code,
            signal_type=signal_type_map.get(signal.signal_type, "WATCH"),
            signal_source="intraday_monitor",
            signal_category="intraday",
            stock_name=signal.stock_name,
            score=signal.confidence,
            confidence=signal.confidence,
            strength="strong" if signal.confidence >= 70 else "moderate",
            trigger_price=signal.price,
            target_price=signal.target_price,
            stop_loss_price=signal.stop_loss_price,
            reason=signal.reason,
            metadata_json=json.dumps({
                "signal_name": signal.signal_type.value,
                "volume_ratio": signal.volume_ratio,
                "obv_trend": signal.obv_trend,
            }),
        )

    def _send_alert(self, signal: IntradaySignal):
        """Format and send DingTalk alert."""
        emoji_map = {
            IntradaySignalType.VOLUME_BREAKOUT: "🟢",
            IntradaySignalType.LOW_VOL_CONSOLIDATION: "🟢",
            IntradaySignalType.WEAK_VOL_HIGH: "🟠",
            IntradaySignalType.VOL_REVERSAL: "🔴",
        }
        emoji = emoji_map.get(signal.signal_type, "🟡")

        title = f"{emoji} {signal.signal_type.value} | {signal.code}"
        text = f"""## {emoji} {signal.signal_type.value}

**{signal.code}** {signal.stock_name}

- 价格: ${signal.price}
- 量比: {signal.volume_ratio:.1f}x MAVOL5
- OBV趋势: {signal.obv_trend}
- 置信度: {signal.confidence:.0f}%

**分析**: {signal.reason}
"""
        if signal.signal_type == IntradaySignalType.VOLUME_BREAKOUT:
            text += f"""
### Call 参考
- 入场: ${signal.price}
- 目标: ${signal.target_price or 'N/A'}
- 止损: ${signal.stop_loss_price or 'N/A'}
- OCO: 止盈+50% / 止损-30%
"""

        if self.dry_run:
            logger.info(f"[DRY-RUN] Would send DingTalk: {title}")
        else:
            try:
                dingtalk = self._get_dingtalk()
                if dingtalk:
                    dingtalk.send_markdown(title, text)
            except Exception as e:
                logger.error(f"Failed to send DingTalk alert: {e}")

    def _is_cooled_down(self, signal: IntradaySignal) -> bool:
        """Check if signal has passed cooldown period."""
        key = f"{signal.code}:{signal.signal_type.value}"
        last_sent = self._cooldowns.get(key)
        if last_sent is None:
            return True
        elapsed = (datetime.now() - last_sent).total_seconds()
        return elapsed >= self.cooldown * 60

    def _check_new_day(self, code: str, df: pd.DataFrame):
        """Clear cached bars if a new trading day started."""
        if df.empty or "trade_date" not in df.columns:
            return
        latest_date = str(df["trade_date"].iloc[-1].date()) if hasattr(df["trade_date"].iloc[-1], "date") else str(df["trade_date"].iloc[-1])[:10]
        if code in self._last_dates and self._last_dates[code] != latest_date:
            logger.info(f"New trading day for {code}: {self._last_dates[code]} -> {latest_date}, clearing bars")
            self._bars.pop(code, None)
            # Clear cooldowns for this code
            self._cooldowns = {k: v for k, v in self._cooldowns.items() if not k.startswith(f"{code}:")}
        self._last_dates[code] = latest_date

    @staticmethod
    def _merge_bars(existing: pd.DataFrame | None, new: pd.DataFrame) -> pd.DataFrame:
        """Merge new bars with existing, dedup by trade_date."""
        if existing is None or existing.empty:
            return new
        combined = pd.concat([existing, new], ignore_index=True)
        if "trade_date" in combined.columns:
            combined = combined.drop_duplicates(subset=["trade_date"], keep="last")
            combined = combined.sort_values("trade_date").reset_index(drop=True)
        # Keep rolling 2-day window (max ~200 bars of 5-min)
        if len(combined) > 200:
            combined = combined.tail(200).reset_index(drop=True)
        return combined

    @staticmethod
    def _code_market(code: str) -> str:
        """Extract market from code like 'HK.00175' -> 'HK'."""
        if "." in code:
            prefix = code.split(".")[0]
            if prefix in ("SH", "SZ"):
                return "A"
            return prefix
        return "HK"

    # ---- Lazy service initialization ----

    def _get_kline_fetcher(self):
        if self._kline_fetcher is None:
            from fetchers.kline_fetcher import KlineFetcher
            self._kline_fetcher = KlineFetcher()
        return self._kline_fetcher

    def _get_dingtalk(self):
        if self._dingtalk is None:
            try:
                from services.dingtalk_service import create_dingtalk_service
                self._dingtalk = create_dingtalk_service()
            except Exception as e:
                logger.warning(f"DingTalk service not available: {e}")
        return self._dingtalk

    def _get_signal_service(self):
        if self._signal_svc is None:
            try:
                from services.signal_service import create_signal_service
                self._signal_svc = create_signal_service()
            except Exception as e:
                logger.warning(f"Signal service not available: {e}")
        return self._signal_svc

    def _get_user_id(self) -> int:
        """Resolve username to user ID. Cached after first lookup."""
        if not hasattr(self, "_cached_user_id"):
            from db.database import get_session
            from db.models import User
            from sqlalchemy import select
            with get_session() as s:
                user = s.execute(select(User).where(User.username == self.user)).scalar()
                if not user:
                    raise ValueError(f"User '{self.user}' not found in database")
                self._cached_user_id = user.id
        return self._cached_user_id

    def _cleanup(self):
        """Clean up resources."""
        if self._kline_fetcher:
            try:
                self._kline_fetcher._close_futu_ctx()
            except Exception:
                pass
        logger.info("Monitor cleaned up")


def resolve_codes(args) -> list[str]:
    """Resolve stock codes from CLI arguments."""
    if args.codes:
        return [c.strip() for c in args.codes.split(",")]

    if args.positions:
        from db.database import get_session
        from db.models import Position, Account, User
        from sqlalchemy import select, func, and_
        with get_session() as s:
            latest = s.execute(
                select(func.max(Position.snapshot_date))
                .select_from(Position).join(Account).join(User)
                .where(User.username == args.user)
            ).scalar()
            if not latest:
                return []
            positions = s.execute(
                select(Position).join(Account).join(User)
                .where(and_(
                    User.username == args.user,
                    Position.snapshot_date == latest,
                    Position.qty > 0,
                ))
            ).scalars().all()
            codes = []
            for p in positions:
                market = p.market or "HK"
                if market == "A":
                    prefix = "SH" if p.code.startswith("6") else "SZ"
                    codes.append(f"{prefix}.{p.code}")
                else:
                    codes.append(f"{market}.{p.code}")
            return codes

    if args.watchlist:
        from db.database import get_session
        from db.models import WatchlistItem, User
        from sqlalchemy import select
        skip_prefixes = (".", "800", "GAH", "ZJM", "CNC", "MET", "AMD2", "MRVL2")
        skip_codes = {"USDCNH", "XAUUSD"}
        with get_session() as s:
            items = s.execute(
                select(WatchlistItem).join(User)
                .where(User.username == args.user, WatchlistItem.is_active == True)
            ).scalars().all()
            codes = []
            for item in items:
                if item.code in skip_codes:
                    continue
                if any(item.code.startswith(p) for p in skip_prefixes):
                    continue
                market = item.market
                if market == "A":
                    prefix = "SH" if item.code.startswith("6") else "SZ"
                    codes.append(f"{prefix}.{item.code}")
                else:
                    codes.append(f"{market}.{item.code}")
            return codes

    return []


def main():
    import signal
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    parser = argparse.ArgumentParser(description="Intraday Monitor - Volume/Price/OBV Signal Detection")
    parser.add_argument("--codes", help="Comma-separated stock codes (e.g., HK.00175,US.MRVL)")
    parser.add_argument("--positions", action="store_true", help="Monitor current positions")
    parser.add_argument("--watchlist", action="store_true", help="Monitor watchlist stocks")
    parser.add_argument("--user", default="dyson", help="Username")
    parser.add_argument("--interval", type=int, default=5, help="Poll interval in minutes (default: 5)")
    parser.add_argument("--cooldown", type=int, default=30, help="Signal cooldown in minutes (default: 30)")
    parser.add_argument("--dry-run", action="store_true", help="Log signals but don't send alerts")
    args = parser.parse_args()

    codes = resolve_codes(args)
    if not codes:
        print("No stocks to monitor. Use --codes, --positions, or --watchlist")
        sys.exit(1)

    monitor = IntradayMonitor(
        user=args.user,
        codes=codes,
        interval_minutes=args.interval,
        cooldown_minutes=args.cooldown,
        dry_run=args.dry_run,
    )
    monitor.run()


if __name__ == "__main__":
    main()
