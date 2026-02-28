"""
Exchange rate service for multi-currency portfolio valuation.

Reads rates from DB (exchange_rates table). Supports manual refresh via BOC API.
"""

import logging
from datetime import datetime
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

# Fallback rates (used only when DB has no data)
FALLBACK_RATES = {
    "USD": Decimal("7.25"),
    "HKD": Decimal("0.93"),
    "JPY": Decimal("0.048"),
    "CNY": Decimal("1"),
}


class ExchangeRateService:
    """Service for currency exchange rate conversion. Reads from DB."""

    def get_rate_to_cny(self, currency: str) -> Decimal:
        """
        Get exchange rate from currency to CNY.
        Reads from DB; falls back to hardcoded rate if DB has no record.
        """
        currency = currency.upper()
        if currency == "CNY":
            return Decimal("1")

        from db.database import get_session
        from db.models import ExchangeRate

        with get_session() as session:
            row = (
                session.query(ExchangeRate)
                .filter_by(currency=currency)
                .first()
            )
            if row:
                return row.rate_to_cny

        fallback = FALLBACK_RATES.get(currency, Decimal("1"))
        logger.warning(f"No DB rate for {currency}, using fallback: {fallback}")
        return fallback

    def get_all_rates(self) -> dict[str, Decimal]:
        """Get all exchange rates to CNY."""
        rates = {"CNY": Decimal("1")}
        for currency in ["USD", "HKD", "JPY"]:
            rates[currency] = self.get_rate_to_cny(currency)
        return rates

    def get_all_rates_with_time(self) -> list[dict]:
        """
        Return all rates with their updated_at timestamps.

        Returns list of dicts: [{currency, rate_to_cny, updated_at}, ...]
        """
        from db.database import get_session
        from db.models import ExchangeRate

        with get_session() as session:
            rows = session.query(ExchangeRate).all()
            return [
                {
                    "currency": r.currency,
                    "rate_to_cny": float(r.rate_to_cny),
                    "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                }
                for r in rows
            ]

    def refresh_rates(self) -> dict:
        """
        Fetch latest rates from BOC API and write to DB.

        Returns dict with success status and rate data.
        """
        results = {}
        errors = []

        for currency in ["USD", "HKD", "JPY"]:
            rate = self._fetch_rate(currency)
            if rate:
                self._upsert_rate(currency, rate)
                results[currency] = float(rate)
            else:
                errors.append(currency)

        if errors:
            return {
                "success": len(results) > 0,
                "rates": results,
                "errors": errors,
                "message": f"Failed to refresh: {', '.join(errors)}",
            }

        return {
            "success": True,
            "rates": results,
            "errors": [],
            "message": "All rates refreshed successfully",
        }

    def set_rate(self, currency: str, rate: Decimal) -> None:
        """Manually set a single exchange rate in DB."""
        currency = currency.upper()
        self._upsert_rate(currency, rate)
        logger.info(f"Manually set {currency}/CNY = {rate}")

    def _upsert_rate(self, currency: str, rate: Decimal) -> None:
        """Insert or update a rate in DB."""
        from db.database import get_session
        from db.models import ExchangeRate

        with get_session() as session:
            row = (
                session.query(ExchangeRate)
                .filter_by(currency=currency)
                .first()
            )
            if row:
                row.rate_to_cny = rate
                row.updated_at = datetime.now()
            else:
                session.add(
                    ExchangeRate(
                        currency=currency,
                        rate_to_cny=rate,
                        updated_at=datetime.now(),
                    )
                )

    def _fetch_rate(self, currency: str) -> Optional[Decimal]:
        """Fetch exchange rate from akshare BOC API."""
        try:
            import akshare as ak

            df = ak.currency_boc_safe()
            if df is None or df.empty:
                return None

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

            logger.info(f"Fetched {currency}/CNY rate from BOC: {rate}")
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


def create_exchange_rate_service() -> ExchangeRateService:
    """Factory function for ExchangeRateService."""
    return ExchangeRateService()
