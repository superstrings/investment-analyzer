"""
K-line data fetcher with Futu API priority and akshare fallback.

Data source priority:
- HK/A-shares: Futu OpenD API (primary) → akshare (fallback)
- US stocks: akshare only (Futu has no US quote permission)

Futu OpenD must be running locally for HK/A-share primary path.
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
    K-line data fetcher with Futu API priority and akshare fallback.

    For HK and A-share stocks, tries Futu OpenD first, then falls back to
    akshare on failure. US stocks always use akshare (no Futu permission).

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

    def __init__(
        self,
        default_days: int = 250,
        futu_host: str = "127.0.0.1",
        futu_port: int = 11111,
    ):
        """
        Initialize K-line fetcher.

        Args:
            default_days: Default number of days to fetch
            futu_host: Futu OpenD host address
            futu_port: Futu OpenD port number
        """
        self.default_days = default_days
        self.futu_host = futu_host
        self.futu_port = futu_port
        self._futu_ctx = None

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

    def _get_futu_ctx(self):
        """Get or create Futu OpenQuoteContext (lazy initialization)."""
        if self._futu_ctx is None:
            from futu import OpenQuoteContext

            self._futu_ctx = OpenQuoteContext(host=self.futu_host, port=self.futu_port)
        return self._futu_ctx

    def _close_futu_ctx(self):
        """Close Futu context if open."""
        if self._futu_ctx is not None:
            try:
                self._futu_ctx.close()
            except Exception:
                pass
            self._futu_ctx = None

    def __del__(self):
        """Ensure Futu context is released."""
        self._close_futu_ctx()

    def _to_futu_code(self, market: Market, code: str) -> str:
        """
        Convert internal code to Futu format.

        Args:
            market: Market enum
            code: Pure stock code (e.g., "00700", "600519")

        Returns:
            Futu-format code (e.g., "HK.00700", "SH.600519", "SZ.000975")
        """
        if market == Market.HK:
            return f"HK.{code}"
        elif market == Market.A:
            if self.A_SH_PATTERN.match(code):
                return f"SH.{code}"
            else:
                return f"SZ.{code}"
        elif market == Market.US:
            return f"US.{code}"
        return f"HK.{code}"

    def _fetch_via_futu(
        self,
        futu_code: str,
        start_date: date,
        end_date: date,
        market: Market,
        pure_code: str,
    ) -> KlineFetchResult:
        """
        Fetch K-line data via Futu OpenD API.

        Args:
            futu_code: Futu-format code (e.g., "HK.00700")
            start_date: Start date
            end_date: End date
            market: Market enum for KlineData
            pure_code: Pure code for KlineData

        Returns:
            KlineFetchResult with data

        Raises:
            Exception: If Futu API call fails
        """
        from futu import RET_OK, AuType, KLType

        ctx = self._get_futu_ctx()
        all_data = []
        page_req_key = None

        while True:
            ret, data, page_req_key = ctx.request_history_kline(
                futu_code,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                ktype=KLType.K_DAY,
                autype=AuType.QFQ,
                max_count=500,
                page_req_key=page_req_key,
            )
            if ret != RET_OK:
                raise Exception(f"Futu API error: {data}")
            all_data.append(data)
            if page_req_key is None:
                break

        df = pd.concat(all_data, ignore_index=True)

        if df.empty:
            raise Exception(f"No data returned from Futu for {futu_code}")

        # Standardize Futu columns to our format
        # Futu returns: code, name, time_key, open, close, high, low,
        #   pe_ratio, turnover_rate, volume, turnover, change_rate, last_close
        df = self._standardize_futu_columns(df)

        klines = self._df_to_klines(df, market, pure_code)
        logger.info(f"Fetched {len(klines)} bars for {futu_code} via Futu API")
        return KlineFetchResult.ok_with_df(klines, df)

    def _standardize_futu_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Standardize Futu DataFrame columns to our format."""
        column_map = {
            "time_key": "trade_date",
            "open": "open",
            "high": "high",
            "low": "low",
            "close": "close",
            "volume": "volume",
            "turnover": "amount",
            "turnover_rate": "turnover_rate",
            "change_rate": "change_pct",
        }
        rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
        df = df.rename(columns=rename_dict)

        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"])

        for col in ["amount", "turnover_rate", "change_pct"]:
            if col not in df.columns:
                df[col] = 0

        return df

    def _fetch_hk(
        self, code: str, start_date: date, end_date: date, adjust: str
    ) -> KlineFetchResult:
        """Fetch Hong Kong stock K-line data. Tries Futu first, then akshare."""
        # 1. Try Futu API first
        try:
            futu_code = self._to_futu_code(Market.HK, code)
            return self._fetch_via_futu(
                futu_code, start_date, end_date, Market.HK, code
            )
        except Exception as e:
            logger.info(
                f"Futu fetch failed for HK.{code}, falling back to akshare: {e}"
            )

        # 2. Fallback to akshare
        try:
            df = ak.stock_hk_daily(symbol=code, adjust=adjust)

            if df is None or df.empty:
                return KlineFetchResult.error(f"No data returned for HK.{code}")

            df = self._standardize_hk_columns(df)
            df = self._filter_by_date(df, start_date, end_date)
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
        """Fetch A-share (China) stock K-line data. Tries Futu first, then akshare."""
        # 1. Try Futu API first
        try:
            futu_code = self._to_futu_code(Market.A, code)
            return self._fetch_via_futu(futu_code, start_date, end_date, Market.A, code)
        except Exception as e:
            logger.info(f"Futu fetch failed for A.{code}, falling back to akshare: {e}")

        # 2. Fallback to akshare
        try:
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

            df = self._standardize_a_share_columns(df)
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


def create_kline_fetcher(
    default_days: int = 250,
    futu_host: Optional[str] = None,
    futu_port: Optional[int] = None,
) -> KlineFetcher:
    """
    Factory function to create a KlineFetcher.

    If futu_host/futu_port are not provided, reads from settings.

    Args:
        default_days: Default number of days to fetch
        futu_host: Futu OpenD host (default: from settings)
        futu_port: Futu OpenD port (default: from settings)

    Returns:
        KlineFetcher instance
    """
    from config.settings import settings

    return KlineFetcher(
        default_days=default_days,
        futu_host=futu_host or settings.futu.default_host,
        futu_port=futu_port or settings.futu.default_port,
    )
