"""
Exchange rate service for multi-currency portfolio valuation.

Reads rates from DB (exchange_rates table). Supports manual refresh via open.er-api.com.
"""

import logging
import time
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

# Module-level rate cache (5-minute TTL)
_rate_cache: dict[str, Decimal] = {}
_rate_cache_time: float = 0
_CACHE_TTL = 300  # seconds


def _invalidate_cache():
    global _rate_cache, _rate_cache_time
    _rate_cache = {}
    _rate_cache_time = 0


class ExchangeRateService:
    """Service for currency exchange rate conversion. Reads from DB."""

    def get_rate_to_cny(self, currency: str) -> Decimal:
        """
        Get exchange rate from currency to CNY.
        Uses in-memory cache (5-min TTL), falls back to DB then hardcoded rate.
        """
        currency = currency.upper()
        if currency == "CNY":
            return Decimal("1")

        global _rate_cache, _rate_cache_time

        # Check cache
        if _rate_cache and (time.monotonic() - _rate_cache_time) < _CACHE_TTL:
            if currency in _rate_cache:
                return _rate_cache[currency]

        # Cache miss — load all rates from DB
        self._load_rates_to_cache()

        if currency in _rate_cache:
            return _rate_cache[currency]

        fallback = FALLBACK_RATES.get(currency, Decimal("1"))
        logger.warning(f"No DB rate for {currency}, using fallback: {fallback}")
        return fallback

    def _load_rates_to_cache(self):
        """Load all rates from DB into cache in a single query."""
        global _rate_cache, _rate_cache_time

        from db.database import get_session
        from db.models import ExchangeRate

        with get_session() as session:
            rows = (
                session.query(ExchangeRate)
                .filter(ExchangeRate.currency.in_(["USD", "HKD", "JPY"]))
                .all()
            )
            _rate_cache = {r.currency: r.rate_to_cny for r in rows}
            _rate_cache_time = time.monotonic()

    def get_all_rates(self) -> dict[str, Decimal]:
        """Get all exchange rates to CNY (single query, cached)."""
        global _rate_cache, _rate_cache_time

        # If cache is fresh, use it directly
        if not _rate_cache or (time.monotonic() - _rate_cache_time) >= _CACHE_TTL:
            self._load_rates_to_cache()

        rates = {"CNY": Decimal("1")}
        for currency in ["USD", "HKD", "JPY"]:
            rates[currency] = _rate_cache.get(
                currency, FALLBACK_RATES.get(currency, Decimal("1"))
            )
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
        Fetch latest rates from open.er-api.com and write to DB.

        Returns dict with success status and rate data.
        """
        rates = self._fetch_all_rates()
        if rates is None:
            return {
                "success": False,
                "rates": {},
                "errors": ["USD", "HKD", "JPY"],
                "message": "Failed to fetch rates from API",
            }

        results = {}
        errors = []
        for currency in ["USD", "HKD", "JPY"]:
            rate = rates.get(currency)
            if rate:
                self._upsert_rate(currency, rate)
                results[currency] = float(rate)
            else:
                errors.append(currency)

        _invalidate_cache()

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
        _invalidate_cache()
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

    def _fetch_all_rates(self) -> Optional[dict[str, Decimal]]:
        """
        Fetch all exchange rates from open.er-api.com in a single request.

        Returns dict like {"USD": Decimal("7.25"), "HKD": Decimal("0.93"), "JPY": Decimal("0.048")}
        or None on failure.
        """
        try:
            import requests

            resp = requests.get(
                "https://open.er-api.com/v6/latest/CNY", timeout=10
            )
            resp.raise_for_status()
            data = resp.json()

            if data.get("result") != "success":
                logger.warning(f"er-api returned non-success: {data}")
                return None

            api_rates = data.get("rates", {})
            result = {}
            for currency in ["USD", "HKD", "JPY"]:
                foreign_per_cny = api_rates.get(currency)
                if foreign_per_cny and float(foreign_per_cny) > 0:
                    # API gives CNY→X rate; we need X→CNY = 1 / (CNY→X)
                    result[currency] = Decimal("1") / Decimal(
                        str(foreign_per_cny)
                    )
                else:
                    logger.warning(f"No rate for {currency} in API response")

            logger.info(f"Fetched rates from er-api: {result}")
            return result

        except Exception as e:
            logger.warning(f"Failed to fetch rates from er-api: {e}")
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
