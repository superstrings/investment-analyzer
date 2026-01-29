"""
Futu OpenAPI data fetcher.

Fetches trading data from Futu OpenD server including:
- Account list
- Positions
- Account info (balance)
- Today's deals
- Historical deals

Requires FutuOpenD to be running locally.
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional

from futu import (
    RET_ERROR,
    RET_OK,
    OpenQuoteContext,
    OpenSecTradeContext,
    SecurityFirm,
    TrdEnv,
    TrdMarket,
    TrdSide,
)

from .base import (
    AccountInfo,
    AccountType,
    BaseFetcher,
    FetchResult,
    Market,
    PositionInfo,
    PositionSide,
    TradeInfo,
    TradeSide,
    WatchlistInfo,
)

logger = logging.getLogger(__name__)


# Mapping from Futu market to our Market enum
FUTU_MARKET_MAP = {
    TrdMarket.HK: Market.HK,
    TrdMarket.US: Market.US,
    TrdMarket.CN: Market.A,
    TrdMarket.HKCC: Market.A,  # HK connect to A-shares
}

# Mapping from Futu trade side to our TradeSide enum
FUTU_SIDE_MAP = {
    TrdSide.BUY: TradeSide.BUY,
    TrdSide.SELL: TradeSide.SELL,
    TrdSide.BUY_BACK: TradeSide.BUY,
    TrdSide.SELL_SHORT: TradeSide.SELL,
}

# Currency mapping by market
MARKET_CURRENCY_MAP = {
    Market.HK: "HKD",
    Market.US: "USD",
    Market.A: "CNY",
}


def _parse_market(market_str: str) -> Market:
    """Parse market string to Market enum."""
    market_str = market_str.upper()
    if market_str in ("HK", "HKEX"):
        return Market.HK
    elif market_str in ("US", "NYSE", "NASDAQ", "AMEX"):
        return Market.US
    elif market_str in ("SH", "SZ", "A", "CN"):
        return Market.A
    else:
        return Market.HK  # Default to HK


def _parse_code(full_code: str) -> tuple[Market, str]:
    """
    Parse full stock code into market and code.

    Args:
        full_code: Full code like "HK.00700" or "US.NVDA"

    Returns:
        Tuple of (Market, code)
    """
    if "." in full_code:
        market_str, code = full_code.split(".", 1)
        return _parse_market(market_str), code
    return Market.HK, full_code


class FutuFetcher(BaseFetcher):
    """
    Futu OpenAPI data fetcher.

    Connects to FutuOpenD server to fetch trading data.

    Usage:
        with FutuFetcher(host="127.0.0.1", port=11111) as fetcher:
            # Unlock trade (required for real accounts)
            fetcher.unlock_trade("your_password")

            # Get account list
            result = fetcher.get_account_list()
            if result.success:
                for acc in result.data:
                    print(acc.acc_id, acc.market)

            # Get positions
            result = fetcher.get_positions(acc_id=123456)
            if result.success:
                for pos in result.data:
                    print(pos.code, pos.qty, pos.pl_ratio)
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 11111,
        security_firm: SecurityFirm = SecurityFirm.FUTUSECURITIES,
        trd_env: TrdEnv = TrdEnv.REAL,
    ):
        """
        Initialize Futu fetcher.

        Args:
            host: FutuOpenD host address
            port: FutuOpenD port number
            security_firm: Security firm (default: Futu Securities)
            trd_env: Trading environment (REAL or SIMULATE)
        """
        super().__init__(host, port)
        self.security_firm = security_firm
        self.trd_env = trd_env
        self._ctx: Optional[OpenSecTradeContext] = None
        self._unlocked = False

    def connect(self) -> bool:
        """
        Connect to FutuOpenD server.

        Returns:
            True if connection successful
        """
        if self._connected and self._ctx:
            return True

        try:
            self._ctx = OpenSecTradeContext(
                host=self.host,
                port=self.port,
                security_firm=self.security_firm,
            )
            self._connected = True
            logger.info(f"Connected to FutuOpenD at {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to FutuOpenD: {e}")
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Disconnect from FutuOpenD server."""
        if self._ctx:
            self._ctx.close()
            self._ctx = None
        self._connected = False
        self._unlocked = False
        logger.info("Disconnected from FutuOpenD")

    def unlock_trade(self, password: str, is_unlock: bool = True) -> FetchResult:
        """
        Unlock trade operations.

        Required before accessing real account data.

        Args:
            password: Trading password
            is_unlock: True to unlock, False to lock

        Returns:
            FetchResult indicating success/failure
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        ret, data = self._ctx.unlock_trade(password, is_unlock=is_unlock)
        if ret == RET_OK:
            self._unlocked = is_unlock
            logger.info(f"Trade {'unlocked' if is_unlock else 'locked'}")
            return FetchResult.ok([])
        else:
            logger.error(f"Failed to unlock trade: {data}")
            return FetchResult.error(str(data))

    def get_account_list(self) -> FetchResult:
        """
        Get list of trading accounts.

        Returns:
            FetchResult containing list of AccountInfo
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        ret, data = self._ctx.get_acc_list()
        if ret != RET_OK:
            return FetchResult.error(str(data))

        accounts = []
        for _, row in data.iterrows():
            acc_type = (
                AccountType.SIMULATE
                if row.get("trd_env") == "SIMULATE"
                else AccountType.REAL
            )

            # Determine market from trd_market_auth
            trd_market = row.get("trd_market_auth", [])
            if isinstance(trd_market, list) and trd_market:
                market = FUTU_MARKET_MAP.get(trd_market[0], Market.HK)
            else:
                market = Market.HK

            acc = AccountInfo(
                acc_id=int(row["acc_id"]),
                account_type=acc_type,
                market=market,
                currency=row.get("currency", "HKD"),
            )
            accounts.append(acc)

        return FetchResult.ok(accounts)

    def get_positions(
        self, acc_id: int, trd_env: Optional[TrdEnv] = None
    ) -> FetchResult:
        """
        Get positions for an account.

        Args:
            acc_id: Account ID
            trd_env: Trading environment (default: use instance setting)

        Returns:
            FetchResult containing list of PositionInfo
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        env = trd_env or self.trd_env
        ret, data = self._ctx.position_list_query(acc_id=acc_id, trd_env=env)

        if ret != RET_OK:
            return FetchResult.error(str(data))

        positions = []
        for _, row in data.iterrows():
            market, code = _parse_code(row.get("code", ""))

            pos = PositionInfo(
                market=market,
                code=code,
                stock_name=row.get("stock_name", ""),
                qty=Decimal(str(row.get("qty", 0))),
                can_sell_qty=Decimal(str(row.get("can_sell_qty", 0))),
                cost_price=Decimal(str(row.get("cost_price", 0))),
                market_price=Decimal(str(row.get("nominal_price", 0))),
                market_val=Decimal(str(row.get("market_val", 0))),
                pl_val=Decimal(str(row.get("pl_val", 0))),
                pl_ratio=Decimal(str(row.get("pl_ratio", 0))),
                position_side=(
                    PositionSide.SHORT
                    if row.get("position_side") == "SHORT"
                    else PositionSide.LONG
                ),
            )
            positions.append(pos)

        return FetchResult.ok(positions)

    def get_account_info(
        self, acc_id: int, trd_env: Optional[TrdEnv] = None
    ) -> FetchResult:
        """
        Get account balance and asset information.

        Args:
            acc_id: Account ID
            trd_env: Trading environment (default: use instance setting)

        Returns:
            FetchResult containing AccountInfo with balance details
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        env = trd_env or self.trd_env
        ret, data = self._ctx.accinfo_query(acc_id=acc_id, trd_env=env)

        if ret != RET_OK:
            return FetchResult.error(str(data))

        if data.empty:
            return FetchResult.error("No account info returned")

        row = data.iloc[0]

        # Determine market from trd_market
        market = Market.HK
        trd_market = row.get("trd_market")
        if trd_market in FUTU_MARKET_MAP:
            market = FUTU_MARKET_MAP[trd_market]

        acc_info = AccountInfo(
            acc_id=acc_id,
            account_type=(
                AccountType.SIMULATE if env == TrdEnv.SIMULATE else AccountType.REAL
            ),
            market=market,
            currency=row.get("currency", "HKD"),
            total_assets=Decimal(str(row.get("total_assets", 0))),
            cash=Decimal(str(row.get("cash", 0))),
            market_val=Decimal(str(row.get("market_val", 0))),
            frozen_cash=Decimal(str(row.get("frozen_cash", 0))),
            buying_power=Decimal(str(row.get("avl_withdrawal_cash", 0))),
            max_power_short=Decimal(str(row.get("max_power_short", 0))),
        )

        return FetchResult.ok([acc_info])

    def get_today_deals(
        self,
        acc_id: int,
        trd_env: Optional[TrdEnv] = None,
        query_fees: bool = True,
    ) -> FetchResult:
        """
        Get today's executed trades/deals.

        Args:
            acc_id: Account ID
            trd_env: Trading environment (default: use instance setting)
            query_fees: Whether to query fees (may be slow due to API limits)

        Returns:
            FetchResult containing list of TradeInfo
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        env = trd_env or self.trd_env
        ret, data = self._ctx.deal_list_query(acc_id=acc_id, trd_env=env)

        if ret != RET_OK:
            return FetchResult.error(str(data))

        # Query fees if requested
        fee_map = {}
        if query_fees and len(data) > 0:
            order_ids = data["order_id"].astype(str).tolist()
            fee_map = self._query_order_fees(order_ids, acc_id, env)

        return self._parse_deals(data, fee_map)

    def _query_order_fees(
        self,
        order_ids: list[str],
        acc_id: int,
        trd_env: TrdEnv,
    ) -> dict[str, Decimal]:
        """
        Query fees for orders using order_fee_query API.

        Args:
            order_ids: List of order IDs
            acc_id: Account ID
            trd_env: Trading environment

        Returns:
            Dict mapping order_id to fee amount
        """
        fees = {}
        if not order_ids:
            return fees

        # Remove duplicates and batch in groups of 400 (API limit)
        unique_order_ids = list(set(order_ids))
        batch_size = 400

        for i in range(0, len(unique_order_ids), batch_size):
            batch = unique_order_ids[i : i + batch_size]
            try:
                ret, data = self._ctx.order_fee_query(
                    order_id_list=batch,
                    acc_id=acc_id,
                    trd_env=trd_env,
                )
                if ret == RET_OK and data is not None and len(data) > 0:
                    for _, row in data.iterrows():
                        order_id = str(row.get("order_id", ""))
                        fee_amount = row.get("fee_amount", 0)
                        if order_id:
                            fees[order_id] = Decimal(str(fee_amount))
            except Exception as e:
                logger.warning(f"Failed to query fees for batch: {e}")

        return fees

    def get_history_deals(
        self,
        acc_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        trd_env: Optional[TrdEnv] = None,
        query_fees: bool = True,
    ) -> FetchResult:
        """
        Get historical executed trades/deals.

        Args:
            acc_id: Account ID
            start_date: Start date (default: 90 days ago)
            end_date: End date (default: today)
            trd_env: Trading environment (default: use instance setting)
            query_fees: Whether to query fees (may be slow due to API limits)

        Returns:
            FetchResult containing list of TradeInfo
        """
        if not self._ensure_connected():
            return FetchResult.error("Not connected to FutuOpenD")

        env = trd_env or self.trd_env

        # Default date range
        if end_date is None:
            end_date = date.today()
        if start_date is None:
            start_date = end_date - timedelta(days=90)

        # Format dates for Futu API
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")

        ret, data = self._ctx.history_deal_list_query(
            acc_id=acc_id,
            trd_env=env,
            start=start_str,
            end=end_str,
        )

        if ret != RET_OK:
            return FetchResult.error(str(data))

        # Query fees if requested
        fee_map = {}
        if query_fees and len(data) > 0:
            order_ids = data["order_id"].astype(str).tolist()
            fee_map = self._query_order_fees(order_ids, acc_id, env)
            logger.info(f"Queried fees for {len(fee_map)} orders")

        return self._parse_deals(data, fee_map)

    def _parse_deals(
        self, data, fee_map: Optional[dict[str, Decimal]] = None
    ) -> FetchResult:
        """
        Parse deals DataFrame into list of TradeInfo.

        Args:
            data: DataFrame from Futu API
            fee_map: Optional dict mapping order_id to fee amount
        """
        if fee_map is None:
            fee_map = {}

        trades = []
        for _, row in data.iterrows():
            market, code = _parse_code(row.get("code", ""))

            # Parse trade time (format: 2025-12-11 11:26:45.279)
            trade_time_str = row.get("create_time", "")
            try:
                # Try with milliseconds first
                trade_time = datetime.strptime(trade_time_str, "%Y-%m-%d %H:%M:%S.%f")
            except (ValueError, TypeError):
                try:
                    # Fallback to without milliseconds
                    trade_time = datetime.strptime(trade_time_str, "%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError):
                    trade_time = datetime.now()

            # Parse trade side
            trd_side = row.get("trd_side")
            side = FUTU_SIDE_MAP.get(trd_side, TradeSide.BUY)

            # Get currency based on market (API doesn't return it)
            currency = MARKET_CURRENCY_MAP.get(market, "HKD")

            # Get fee from fee_map if available
            order_id = str(row.get("order_id", ""))
            fee = fee_map.get(order_id, Decimal("0"))

            trade = TradeInfo(
                deal_id=str(row.get("deal_id", "")),
                market=market,
                code=code,
                stock_name=row.get("stock_name", ""),
                trd_side=side,
                qty=Decimal(str(row.get("qty", 0))),
                price=Decimal(str(row.get("price", 0))),
                trade_time=trade_time,
                order_id=order_id,
                amount=Decimal(str(row.get("qty", 0)))
                * Decimal(str(row.get("price", 0))),
                fee=fee,
                currency=currency,
            )
            trades.append(trade)

        return FetchResult.ok(trades)

    def get_watchlist(
        self,
        groups: Optional[list[str]] = None,
    ) -> FetchResult:
        """
        Get watchlist (user securities) from Futu.

        Uses OpenQuoteContext to fetch user's watchlist.

        Args:
            groups: List of group names to fetch. If None, fetches from common groups.

        Returns:
            FetchResult containing list of WatchlistInfo
        """
        # Default groups to fetch (most common ones)
        if groups is None:
            groups = ["全部", "港股", "美股", "沪深"]

        watchlist = []
        seen_codes = set()  # Avoid duplicates

        try:
            # Use quote context for watchlist
            quote_ctx = OpenQuoteContext(host=self.host, port=self.port)

            try:
                for group_name in groups:
                    ret, data = quote_ctx.get_user_security(group_name)
                    if ret != RET_OK:
                        logger.warning(f"Failed to get watchlist for group '{group_name}': {data}")
                        continue

                    for _, row in data.iterrows():
                        full_code = row.get("code", "")
                        if full_code in seen_codes:
                            continue
                        seen_codes.add(full_code)

                        market, code = _parse_code(full_code)
                        item = WatchlistInfo(
                            market=market,
                            code=code,
                            stock_name=row.get("name", ""),
                            group_name=group_name,
                        )
                        watchlist.append(item)

                return FetchResult.ok(watchlist)

            finally:
                quote_ctx.close()

        except Exception as e:
            logger.error(f"Error fetching watchlist: {e}")
            return FetchResult.error(str(e))

    def _ensure_connected(self) -> bool:
        """Ensure connection is established."""
        if not self._connected or not self._ctx:
            return self.connect()
        return True

    @property
    def is_unlocked(self) -> bool:
        """Check if trade is unlocked."""
        return self._unlocked


def create_futu_fetcher(
    username: str,
    host: str = "127.0.0.1",
    port: int = 11111,
    password: Optional[str] = None,
) -> FutuFetcher:
    """
    Factory function to create a FutuFetcher with optional auto-unlock.

    Args:
        username: Username for logging
        host: FutuOpenD host
        port: FutuOpenD port
        password: Optional trade password for auto-unlock

    Returns:
        Connected FutuFetcher instance
    """
    from config import get_futu_password

    fetcher = FutuFetcher(host=host, port=port)
    fetcher.connect()

    # Try to unlock if password provided or available from env
    pwd = password or get_futu_password(username)
    if pwd:
        fetcher.unlock_trade(pwd)

    return fetcher
