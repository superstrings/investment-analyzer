"""
K-line data fetcher using akshare.

Fetches daily K-line (OHLCV) data from free sources:
- Hong Kong stocks via akshare
- US stocks via akshare
- A-shares (China) via akshare

Note: akshare provides free market data without API key requirements.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

import akshare as ak
import pandas as pd

from .base import FetchResult, Market

logger = logging.getLogger(__name__)


@dataclass
class KlineData:
    """K-line (candlestick) data for a single day."""

    market: Market
    code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    amount: Decimal = Decimal("0")
    turnover_rate: Decimal = Decimal("0")
    change_pct: Decimal = Decimal("0")

    @property
    def full_code(self) -> str:
        """Get full stock code with market prefix."""
        return f"{self.market.value}.{self.code}"


@dataclass
class KlineFetchResult(FetchResult):
    """Extended FetchResult for K-line data with DataFrame support."""

    df: Optional[pd.DataFrame] = None

    @classmethod
    def ok_with_df(cls, data: list, df: pd.DataFrame) -> "KlineFetchResult":
        """Create successful result with DataFrame."""
        return cls(success=True, data=data, records_count=len(data), df=df)


class KlineFetcher:
    """
    K-line data fetcher using akshare.

    Fetches daily OHLCV data for HK, US, and A-share stocks.

    Usage:
        fetcher = KlineFetcher()

        # Fetch single stock
        result = fetcher.fetch("HK.00700", days=120)
        if result.success:
            for kline in result.data:
                print(kline.trade_date, kline.close)

        # Fetch with auto-detected market
        result = fetcher.fetch("00700", days=60)  # Auto-detects as HK

        # Fetch multiple stocks
        results = fetcher.fetch_batch(["HK.00700", "US.NVDA"], days=60)
    """

    # Code patterns for market detection
    HK_PATTERN = re.compile(r"^(\d{5})$")  # 5 digits: 00700
    US_PATTERN = re.compile(r"^([A-Z]{1,5})$")  # 1-5 uppercase letters: NVDA
    A_SH_PATTERN = re.compile(r"^(6\d{5})$")  # Starts with 6: 600519 (Shanghai)
    A_SZ_PATTERN = re.compile(r"^(0\d{5}|3\d{5})$")  # Starts with 0 or 3 (Shenzhen)

    def __init__(self, default_days: int = 250):
        """
        Initialize K-line fetcher.

        Args:
            default_days: Default number of days to fetch
        """
        self.default_days = default_days

    def fetch(
        self,
        code: str,
        days: Optional[int] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        adjust: str = "qfq",
    ) -> KlineFetchResult:
        """
        Fetch K-line data for a single stock.

        Args:
            code: Stock code (e.g., "HK.00700", "US.NVDA", "00700")
            days: Number of days to fetch (from end_date backwards)
            start_date: Start date (optional, overrides days)
            end_date: End date (default: today)
            adjust: Price adjustment type ("qfq"=forward, "hfq"=backward, ""=none)

        Returns:
            KlineFetchResult containing list of KlineData
        """
        # Parse market and code
        market, pure_code = self._parse_code(code)

        # Calculate date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            fetch_days = days or self.default_days
            start_date = end_date - timedelta(
                days=fetch_days * 2
            )  # Fetch extra for holidays

        try:
            if market == Market.HK:
                return self._fetch_hk(pure_code, start_date, end_date, adjust)
            elif market == Market.US:
                return self._fetch_us(pure_code, start_date, end_date, adjust)
            elif market == Market.A:
                return self._fetch_a_share(pure_code, start_date, end_date, adjust)
            else:
                return KlineFetchResult.error(f"Unsupported market: {market}")
        except Exception as e:
            logger.error(f"Failed to fetch K-line for {code}: {e}")
            return KlineFetchResult.error(str(e))

    def fetch_batch(
        self,
        codes: list[str],
        days: Optional[int] = None,
        adjust: str = "qfq",
    ) -> dict[str, KlineFetchResult]:
        """
        Fetch K-line data for multiple stocks.

        Args:
            codes: List of stock codes
            days: Number of days to fetch
            adjust: Price adjustment type

        Returns:
            Dict mapping code to KlineFetchResult
        """
        results = {}
        for code in codes:
            results[code] = self.fetch(code, days=days, adjust=adjust)
        return results

    def _fetch_hk(
        self, code: str, start_date: date, end_date: date, adjust: str
    ) -> KlineFetchResult:
        """Fetch Hong Kong stock K-line data."""
        try:
            # akshare HK stock daily data
            # Note: akshare uses different API depending on version
            df = ak.stock_hk_daily(symbol=code, adjust=adjust)

            if df is None or df.empty:
                return KlineFetchResult.error(f"No data returned for HK.{code}")

            # Standardize column names
            df = self._standardize_hk_columns(df)

            # Filter by date range
            df = self._filter_by_date(df, start_date, end_date)

            # Convert to KlineData list
            klines = self._df_to_klines(df, Market.HK, code)

            return KlineFetchResult.ok_with_df(klines, df)

        except Exception as e:
            logger.error(f"Error fetching HK.{code}: {e}")
            return KlineFetchResult.error(f"HK fetch error: {e}")

    def _fetch_us(
        self, code: str, start_date: date, end_date: date, adjust: str
    ) -> KlineFetchResult:
        """Fetch US stock K-line data."""
        try:
            # akshare US stock daily data
            df = ak.stock_us_daily(symbol=code, adjust=adjust)

            if df is None or df.empty:
                return KlineFetchResult.error(f"No data returned for US.{code}")

            # Standardize column names
            df = self._standardize_us_columns(df)

            # Filter by date range
            df = self._filter_by_date(df, start_date, end_date)

            # Convert to KlineData list
            klines = self._df_to_klines(df, Market.US, code)

            return KlineFetchResult.ok_with_df(klines, df)

        except Exception as e:
            logger.error(f"Error fetching US.{code}: {e}")
            return KlineFetchResult.error(f"US fetch error: {e}")

    def _fetch_a_share(
        self, code: str, start_date: date, end_date: date, adjust: str
    ) -> KlineFetchResult:
        """Fetch A-share (China) stock K-line data."""
        try:
            # akshare A-share daily data
            # Convert adjust type: qfq -> qfq, hfq -> hfq, "" -> ""
            ak_adjust = adjust if adjust in ("qfq", "hfq") else ""

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime("%Y%m%d"),
                end_date=end_date.strftime("%Y%m%d"),
                adjust=ak_adjust,
            )

            if df is None or df.empty:
                return KlineFetchResult.error(f"No data returned for A.{code}")

            # Standardize column names
            df = self._standardize_a_share_columns(df)

            # Convert to KlineData list
            klines = self._df_to_klines(df, Market.A, code)

            return KlineFetchResult.ok_with_df(klines, df)

        except Exception as e:
            logger.error(f"Error fetching A.{code}: {e}")
            return KlineFetchResult.error(f"A-share fetch error: {e}")

    def _standardize_hk_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize HK stock DataFrame columns."""
        # Expected columns from akshare: date, open, high, low, close, volume
        column_map = {
            "date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }

        # Rename columns that exist
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        # Ensure trade_date is datetime
        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])

        # Add missing columns with defaults
        for col in ["amount", "turnover_rate", "change_pct"]:
            if col not in df.columns:
                df[col] = 0

        return df

    def _standardize_us_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize US stock DataFrame columns."""
        column_map = {
            "date": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
        }

        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])

        for col in ["amount", "turnover_rate", "change_pct"]:
            if col not in df.columns:
                df[col] = 0

        return df

    def _standardize_a_share_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize A-share DataFrame columns."""
        # A-share columns from akshare: 日期, 开盘, 最高, 最低, 收盘, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
        column_map = {
            "日期": "trade_date",
            "开盘": "open",
            "最高": "high",
            "最低": "low",
            "收盘": "close",
            "成交量": "volume",
            "成交额": "amount",
            "换手率": "turnover_rate",
            "涨跌幅": "change_pct",
        }

        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])

        return df

    def _filter_by_date(
        self, df: pd.DataFrame, start_date: date, end_date: date
    ) -> pd.DataFrame:
        """Filter DataFrame by date range."""
        if "trade_date" not in df.columns:
            return df

        df = df[
            (df["trade_date"] >= pd.Timestamp(start_date))
            & (df["trade_date"] <= pd.Timestamp(end_date))
        ]
        return df.sort_values("trade_date").reset_index(drop=True)

    def _df_to_klines(
        self, df: pd.DataFrame, market: Market, code: str
    ) -> list[KlineData]:
        """Convert DataFrame to list of KlineData."""
        klines = []
        for _, row in df.iterrows():
            try:
                trade_date = row.get("trade_date")
                if pd.isna(trade_date):
                    continue

                # Convert to date if datetime
                if isinstance(trade_date, pd.Timestamp):
                    trade_date = trade_date.date()

                kline = KlineData(
                    market=market,
                    code=code,
                    trade_date=trade_date,
                    open=Decimal(str(row.get("open", 0))),
                    high=Decimal(str(row.get("high", 0))),
                    low=Decimal(str(row.get("low", 0))),
                    close=Decimal(str(row.get("close", 0))),
                    volume=int(row.get("volume", 0) or 0),
                    amount=Decimal(str(row.get("amount", 0) or 0)),
                    turnover_rate=Decimal(str(row.get("turnover_rate", 0) or 0)),
                    change_pct=Decimal(str(row.get("change_pct", 0) or 0)),
                )
                klines.append(kline)
            except Exception as e:
                logger.warning(f"Failed to parse row: {e}")
                continue

        return klines

    def _parse_code(self, code: str) -> tuple[Market, str]:
        """
        Parse stock code and detect market.

        Args:
            code: Stock code (e.g., "HK.00700", "US.NVDA", "00700", "NVDA")

        Returns:
            Tuple of (Market, pure_code)
        """
        # Check for explicit market prefix
        if "." in code:
            parts = code.split(".", 1)
            market_str = parts[0].upper()
            pure_code = parts[1]

            if market_str == "HK":
                return Market.HK, pure_code
            elif market_str == "US":
                return Market.US, pure_code
            elif market_str in ("A", "SH", "SZ", "CN"):
                return Market.A, pure_code

        # Auto-detect market from code pattern
        pure_code = code.upper()

        if self.HK_PATTERN.match(pure_code):
            return Market.HK, pure_code
        elif self.US_PATTERN.match(pure_code):
            return Market.US, pure_code
        elif self.A_SH_PATTERN.match(pure_code) or self.A_SZ_PATTERN.match(pure_code):
            return Market.A, pure_code

        # Default to HK for numeric codes
        if pure_code.isdigit():
            return Market.HK, pure_code.zfill(5)

        # Default to US for alphabetic codes
        return Market.US, pure_code

    def detect_market(self, code: str) -> Market:
        """
        Detect market from stock code.

        Args:
            code: Stock code

        Returns:
            Detected Market enum
        """
        market, _ = self._parse_code(code)
        return market


def create_kline_fetcher(default_days: int = 250) -> KlineFetcher:
    """
    Factory function to create a KlineFetcher.

    Args:
        default_days: Default number of days to fetch

    Returns:
        KlineFetcher instance
    """
    return KlineFetcher(default_days=default_days)
