"""Intraday signal detection engine based on Volume-Price-OBV analysis."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

import numpy as np
import pandas as pd


class IntradaySignalType(Enum):
    VOLUME_BREAKOUT = "放量突破"
    LOW_VOL_CONSOLIDATION = "缩量整理"
    WEAK_VOL_HIGH = "冲高量不足"
    VOL_REVERSAL = "放量冲高回落"
    NO_VOL_RANGE = "无量横盘"


@dataclass
class IntradaySignal:
    code: str
    stock_name: str
    market: str
    signal_type: IntradaySignalType
    signal_time: datetime
    price: Decimal
    volume_ratio: float
    obv_trend: str  # "up" / "down" / "flat"
    confidence: float  # 0-100
    reason: str
    target_price: Optional[Decimal] = None
    stop_loss_price: Optional[Decimal] = None


class IntradayAnalyzer:
    """Analyzes 5-min K-line data for intraday trading signals."""

    def __init__(
        self,
        vol_breakout_mult: float = 2.0,
        vol_shrink_ratio: float = 0.6,
        vol_dead_ratio: float = 0.3,
        consolidation_bars: int = 12,
        upper_shadow_ratio: float = 0.6,
        range_narrow_pct: float = 0.003,
        min_bars: int = 30,
    ):
        self.vol_breakout_mult = vol_breakout_mult
        self.vol_shrink_ratio = vol_shrink_ratio
        self.vol_dead_ratio = vol_dead_ratio
        self.consolidation_bars = consolidation_bars
        self.upper_shadow_ratio = upper_shadow_ratio
        self.range_narrow_pct = range_narrow_pct
        self.min_bars = min_bars

    def analyze(
        self,
        df: pd.DataFrame,
        code: str,
        market: str,
        stock_name: str = "",
    ) -> list[IntradaySignal]:
        """
        Run signal detection on 5-min K-line DataFrame.

        Args:
            df: DataFrame with columns: open, high, low, close, volume, trade_date
            code: Stock code (e.g., "HK.00175")
            market: Market string ("HK", "US", "A")
            stock_name: Display name

        Returns:
            List of detected signals (usually 0 or 1 per bar).
        """
        if df is None or df.empty or len(df) < self.min_bars:
            return []

        df = self._prepare(df)
        if df.empty:
            return []

        signals = []

        # Try each signal detector; return the first match (priority order)
        detectors = [
            self._detect_volume_breakout,
            self._detect_vol_reversal,
            self._detect_weak_vol_high,
            self._detect_low_vol_consolidation,
            self._detect_no_vol_range,
        ]

        for detector in detectors:
            signal = detector(df, code, market, stock_name)
            if signal:
                signals.append(signal)
                break  # One signal per analysis cycle

        return signals

    def _prepare(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare DataFrame with derived columns."""
        df = df.copy()

        # Ensure numeric types
        for col in ["open", "high", "low", "close", "volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        required = {"close", "volume"}
        if not required.issubset(df.columns):
            return pd.DataFrame()

        df = df.dropna(subset=["close", "volume"])
        if df.empty:
            return df

        # Moving average volumes
        df["mavol5"] = df["volume"].rolling(5).mean()
        df["mavol10"] = df["volume"].rolling(10).mean()

        # Volume ratio
        df["vol_ratio"] = df["volume"] / df["mavol5"].replace(0, np.nan)

        # OBV
        df["obv"] = self._calc_obv(df)

        # Price MAs
        df["ma5"] = df["close"].rolling(5).mean()
        df["ma20"] = df["close"].rolling(20).mean()

        return df

    @staticmethod
    def _calc_obv(df: pd.DataFrame) -> pd.Series:
        """Calculate On-Balance Volume."""
        obv = [0.0]
        for i in range(1, len(df)):
            if df["close"].iloc[i] > df["close"].iloc[i - 1]:
                obv.append(obv[-1] + float(df["volume"].iloc[i]))
            elif df["close"].iloc[i] < df["close"].iloc[i - 1]:
                obv.append(obv[-1] - float(df["volume"].iloc[i]))
            else:
                obv.append(obv[-1])
        return pd.Series(obv, index=df.index)

    def _obv_trend(self, df: pd.DataFrame, lookback: int = 12) -> str:
        """Determine OBV trend over last N bars."""
        if len(df) < lookback + 1:
            return "flat"
        obv_now = float(df["obv"].iloc[-1])
        obv_past = float(df["obv"].iloc[-lookback])
        diff_pct = (obv_now - obv_past) / max(abs(obv_past), 1) * 100
        if diff_pct > 5:
            return "up"
        elif diff_pct < -5:
            return "down"
        return "flat"

    def _obv_new_high(self, df: pd.DataFrame) -> bool:
        """Check if OBV is at session high."""
        if len(df) < 5:
            return False
        return float(df["obv"].iloc[-1]) >= float(df["obv"].iloc[:-1].max())

    def _consolidation_range(self, df: pd.DataFrame) -> tuple[float, float]:
        """Get high/low of consolidation range (last N bars excluding latest)."""
        n = min(self.consolidation_bars, len(df) - 1)
        subset = df.iloc[-(n + 1) : -1]
        return float(subset["high"].max()), float(subset["low"].min())

    def _max_volume_bar(self, df: pd.DataFrame) -> float:
        """Get the maximum volume in the session (excluding latest bar)."""
        if len(df) < 2:
            return 0.0
        return float(df["volume"].iloc[:-1].max())

    def _make_signal(
        self,
        df: pd.DataFrame,
        code: str,
        market: str,
        stock_name: str,
        signal_type: IntradaySignalType,
        confidence: float,
        reason: str,
        target_price: Optional[float] = None,
        stop_loss_price: Optional[float] = None,
    ) -> IntradaySignal:
        latest = df.iloc[-1]
        price = float(latest["close"])
        vol_ratio = float(latest.get("vol_ratio", 0) or 0)
        obv_trend = self._obv_trend(df)

        trade_date = latest.get("trade_date")
        if isinstance(trade_date, pd.Timestamp):
            signal_time = trade_date.to_pydatetime()
        else:
            signal_time = datetime.now()

        return IntradaySignal(
            code=code,
            stock_name=stock_name,
            market=market,
            signal_type=signal_type,
            signal_time=signal_time,
            price=Decimal(str(round(price, 3))),
            volume_ratio=round(vol_ratio, 2),
            obv_trend=obv_trend,
            confidence=round(confidence, 1),
            reason=reason,
            target_price=Decimal(str(round(target_price, 3))) if target_price else None,
            stop_loss_price=Decimal(str(round(stop_loss_price, 3))) if stop_loss_price else None,
        )

    # ---- Signal Detectors ----

    def _detect_volume_breakout(
        self, df: pd.DataFrame, code: str, market: str, name: str
    ) -> Optional[IntradaySignal]:
        """VOL > MAVOL5 * 2 + price breaks above consolidation range."""
        latest = df.iloc[-1]
        mavol5 = latest.get("mavol5")
        if pd.isna(mavol5) or mavol5 == 0:
            return None

        vol_ratio = float(latest["volume"]) / float(mavol5)
        if vol_ratio < self.vol_breakout_mult:
            return None

        range_high, range_low = self._consolidation_range(df)
        price = float(latest["close"])
        if price <= range_high:
            return None

        # Confidence boost if OBV also at session high
        confidence = 70.0
        if self._obv_new_high(df):
            confidence += 15.0
        if vol_ratio > 3.0:
            confidence += 10.0

        target = round(price * 1.03, 3)  # +3% target
        stop_loss = round(range_low, 3)

        return self._make_signal(
            df, code, market, name,
            IntradaySignalType.VOLUME_BREAKOUT,
            min(confidence, 95),
            f"放量{vol_ratio:.1f}x突破整理区间{range_high:.2f}, OBV趋势{self._obv_trend(df)}",
            target_price=target,
            stop_loss_price=stop_loss,
        )

    def _detect_vol_reversal(
        self, df: pd.DataFrame, code: str, market: str, name: str
    ) -> Optional[IntradaySignal]:
        """Long upper shadow + high volume = short-term top."""
        latest = df.iloc[-1]
        high = float(latest["high"])
        low = float(latest["low"])
        close = float(latest["close"])
        open_ = float(latest["open"])

        total_range = high - low
        if total_range == 0:
            return None

        upper_shadow = high - max(close, open_)
        shadow_ratio = upper_shadow / total_range

        if shadow_ratio < self.upper_shadow_ratio:
            return None

        mavol5 = latest.get("mavol5")
        if pd.isna(mavol5) or mavol5 == 0:
            return None

        vol_ratio = float(latest["volume"]) / float(mavol5)
        if vol_ratio < 1.5:
            return None

        confidence = 65.0 + min(shadow_ratio * 20, 15) + min((vol_ratio - 1.5) * 10, 10)

        return self._make_signal(
            df, code, market, name,
            IntradaySignalType.VOL_REVERSAL,
            min(confidence, 90),
            f"放量冲高回落, 上影线占比{shadow_ratio:.0%}, 量比{vol_ratio:.1f}x",
        )

    def _detect_weak_vol_high(
        self, df: pd.DataFrame, code: str, market: str, name: str
    ) -> Optional[IntradaySignal]:
        """New session high but volume less than previous breakout volume."""
        if len(df) < 10:
            return None

        latest = df.iloc[-1]
        prev_high = float(df["high"].iloc[:-1].max())

        if float(latest["high"]) <= prev_high:
            return None

        max_vol = self._max_volume_bar(df)
        if max_vol == 0:
            return None

        current_vol = float(latest["volume"])
        if current_vol >= max_vol * 0.7:
            return None  # Volume sufficient, not a weak high

        vol_deficit = 1 - (current_vol / max_vol)
        confidence = 55.0 + min(vol_deficit * 30, 25)

        return self._make_signal(
            df, code, market, name,
            IntradaySignalType.WEAK_VOL_HIGH,
            min(confidence, 85),
            f"创新高{float(latest['high']):.2f}但量仅为前高量的{current_vol/max_vol:.0%}",
        )

    def _detect_low_vol_consolidation(
        self, df: pd.DataFrame, code: str, market: str, name: str
    ) -> Optional[IntradaySignal]:
        """Volume shrinks + price holds + OBV doesn't drop."""
        latest = df.iloc[-1]
        mavol5 = latest.get("mavol5")
        if pd.isna(mavol5) or mavol5 == 0:
            return None

        vol_ratio = float(latest["volume"]) / float(mavol5)
        if vol_ratio > self.vol_shrink_ratio:
            return None

        # OBV should not be declining
        obv_trend = self._obv_trend(df)
        if obv_trend == "down":
            return None

        # Price should be near consolidation midpoint (not collapsing)
        range_high, range_low = self._consolidation_range(df)
        price = float(latest["close"])
        if range_high == range_low:
            return None
        position = (price - range_low) / (range_high - range_low)
        if position < 0.3:
            return None  # Price near bottom of range, not holding

        confidence = 60.0
        if obv_trend == "up":
            confidence += 10
        if position > 0.7:
            confidence += 5

        return self._make_signal(
            df, code, market, name,
            IntradaySignalType.LOW_VOL_CONSOLIDATION,
            min(confidence, 80),
            f"缩量整理, 量比{vol_ratio:.2f}x, OBV{obv_trend}, 价格位于区间{position:.0%}位置",
        )

    def _detect_no_vol_range(
        self, df: pd.DataFrame, code: str, market: str, name: str
    ) -> Optional[IntradaySignal]:
        """Very low volume + narrow price range = no signal."""
        latest = df.iloc[-1]
        mavol5 = latest.get("mavol5")
        if pd.isna(mavol5) or mavol5 == 0:
            return None

        vol_ratio = float(latest["volume"]) / float(mavol5)
        if vol_ratio > self.vol_dead_ratio:
            return None

        # Check last 6 bars for narrow range
        recent = df.tail(6)
        high = float(recent["high"].max())
        low = float(recent["low"].min())
        if low == 0:
            return None
        range_pct = (high - low) / low
        if range_pct > self.range_narrow_pct:
            return None

        return self._make_signal(
            df, code, market, name,
            IntradaySignalType.NO_VOL_RANGE,
            30.0,
            f"无量横盘, 量比{vol_ratio:.2f}x, 6根K线振幅仅{range_pct:.2%}",
        )


def create_intraday_analyzer(**kwargs) -> IntradayAnalyzer:
    """Factory function for IntradayAnalyzer."""
    return IntradayAnalyzer(**kwargs)
