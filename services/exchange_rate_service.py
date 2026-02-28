"""
Exchange rate service for multi-currency portfolio valuation.

Uses akshare to fetch real-time exchange rates from Bank of China.
Converts foreign currency amounts to CNY.
"""

import logging
import time
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# Market → Currency mapping
MARKET_CURRENCY_MAP = {
    "HK": "HKD",
    "US": "USD",
    "A": "CNY",
    "JP": "JPY",
}

# Fallback rates (approximate) if API fails
FALLBACK_RATES = {
    "USD": Decimal("7.25"),
    "HKD": Decimal("0.93"),
    "JPY": Decimal("0.048"),
    "CNY": Decimal("1"),
}

# Cache: {currency: (timestamp, rate)}
_rate_cache: dict[str, tuple[float, Decimal]] = {}
_CACHE_TTL = 3600  # 1 hour


class ExchangeRateService:
    """Service for currency exchange rate conversion."""

    def __init__(self, cache_ttl: int = 3600):
        self.cache_ttl = cache_ttl

    def get_rate_to_cny(self, currency: str) -> Decimal:
        """
        Get exchange rate from currency to CNY.

        Args:
            currency: Currency code (USD, HKD, JPY, CNY)

        Returns:
            Exchange rate (1 unit of currency = X CNY)
        """
        currency = currency.upper()
        if currency == "CNY":
            return Decimal("1")

        # Check cache
        cached = _rate_cache.get(currency)
        if cached and (time.time() - cached[0]) < self.cache_ttl:
            return cached[1]

        # Fetch from akshare
        rate = self._fetch_rate(currency)
        if rate:
            _rate_cache[currency] = (time.time(), rate)
            return rate

        # Fallback
        fallback = FALLBACK_RATES.get(currency, Decimal("1"))
        logger.warning(f"Using fallback rate for {currency}: {fallback}")
        return fallback

    def _fetch_rate(self, currency: str) -> Optional[Decimal]:
        """Fetch exchange rate from akshare."""
        try:
            import akshare as ak

            df = ak.currency_boc_safe()
            if df is None or df.empty:
                return None

            # BOC safe rates have columns like: 货币名称, 现汇买入价, 现钞买入价, 现汇卖出价, 现钞卖出价, 中行折算价
            # Map currency code to Chinese name
            currency_names = {
                "USD": "美元",
                "HKD": "港币",
                "JPY": "日元",
                "GBP": "英镑",
                "EUR": "欧元",
            }

            name = currency_names.get(currency)
            if not name:
                return None

            # Find the row for our currency
            name_col = None
            for col in df.columns:
                if "货币" in str(col) or "名称" in str(col):
                    name_col = col
                    break

            if name_col is None:
                name_col = df.columns[0]

            row = df[df[name_col].astype(str).str.contains(name)]
            if row.empty:
                return None

            # Use 中行折算价 (BOC conversion rate) or 现汇卖出价
            rate_col = None
            for col in df.columns:
                if "折算" in str(col):
                    rate_col = col
                    break
            if rate_col is None:
                for col in df.columns:
                    if "卖出" in str(col) and "现汇" in str(col):
                        rate_col = col
                        break
            if rate_col is None:
                rate_col = df.columns[-2]

            rate_val = row.iloc[0][rate_col]
            rate = Decimal(str(rate_val))

            # BOC rates are per 100 units for JPY
            if currency == "JPY":
                rate = rate / Decimal("100")

            logger.info(f"Fetched {currency}/CNY rate: {rate}")
            return rate

        except Exception as e:
            logger.warning(f"Failed to fetch rate for {currency}: {e}")
            return None

    def convert_to_cny(self, amount: Decimal, currency: str) -> Decimal:
        """Convert an amount from given currency to CNY."""
        rate = self.get_rate_to_cny(currency)
        return amount * rate

    def get_market_currency(self, market: str) -> str:
        """Get currency code for a market."""
        return MARKET_CURRENCY_MAP.get(market, "CNY")

    def get_all_rates(self) -> dict[str, Decimal]:
        """Get all exchange rates to CNY."""
        rates = {"CNY": Decimal("1")}
        for currency in ["USD", "HKD", "JPY"]:
            rates[currency] = self.get_rate_to_cny(currency)
        return rates


def create_exchange_rate_service() -> ExchangeRateService:
    """Factory function for ExchangeRateService."""
    return ExchangeRateService()
