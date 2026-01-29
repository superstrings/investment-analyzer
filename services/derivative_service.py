"""
Derivative Contract Service - 衍生品合约信息服务

获取并管理期权/窝轮的合约信息（换股比率、合约乘数等）。
支持从 Futu API 和网络获取数据。
"""

import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy.orm import Session

from db import DerivativeContract, get_session

logger = logging.getLogger(__name__)


# 默认合约乘数
DEFAULT_US_OPTION_MULTIPLIER = Decimal("100")  # 美股期权标准合约乘数
DEFAULT_HK_WARRANT_RATIO = Decimal("1")  # 港股窝轮默认换股比率（保守值）


def parse_option_code(market: str, code: str) -> Optional[dict]:
    """
    解析期权/窝轮代码，提取信息。

    港股窝轮格式: {正股代码}{YYMMDD}{C/P}{行权价}
    例如: KST260226C75000 -> 快手科技 2026-02-26 Call 75.00

    美股期权格式: {正股代码}{YYMMDD}{C/P}{行权价}
    例如: NVDA260220C195000 -> NVDA 2026-02-20 Call 195.00

    Returns:
        dict with keys: underlying, expiry_date, option_type, strike_price
        or None if not parseable
    """
    if market == "HK":
        # 港股窝轮: 代码前缀是正股简称（2-3个字母），后面是日期+类型+行权价
        match = re.match(r"^([A-Z]{2,4})(\d{6})([CP])(\d+)$", code)
        if match:
            underlying_abbr = match.group(1)
            date_str = match.group(2)
            opt_type = "CALL" if match.group(3) == "C" else "PUT"
            strike = Decimal(match.group(4)) / 1000  # 行权价除以1000

            # 解析到期日 (YYMMDD)
            try:
                expiry = datetime.strptime(date_str, "%y%m%d").date()
            except ValueError:
                expiry = None

            return {
                "underlying": underlying_abbr,
                "expiry_date": expiry,
                "option_type": opt_type,
                "strike_price": strike,
            }

    elif market == "US":
        # 美股期权: 正股代码(1-5字母) + YYMMDD + C/P + 行权价
        match = re.match(r"^([A-Z]{1,5})(\d{6})([CP])(\d+)$", code)
        if match:
            underlying = match.group(1)
            date_str = match.group(2)
            opt_type = "CALL" if match.group(3) == "C" else "PUT"
            strike = Decimal(match.group(4)) / 1000

            try:
                expiry = datetime.strptime(date_str, "%y%m%d").date()
            except ValueError:
                expiry = None

            return {
                "underlying": underlying,
                "expiry_date": expiry,
                "option_type": opt_type,
                "strike_price": strike,
            }

    return None


def is_derivative_code(market: str, code: str) -> bool:
    """判断是否为衍生品代码（期权/窝轮）"""
    if market == "HK":
        # 港股期权/窝轮代码中包含字母
        return any(c.isalpha() for c in code)

    if market == "US":
        # 美股期权格式: SYMBOL + YYMMDD + C/P + STRIKE
        return bool(re.match(r"^[A-Z]+\d{6}[CP]\d+$", code))

    return False


def get_derivative_type(market: str, code: str) -> Optional[str]:
    """获取衍生品类型"""
    if not is_derivative_code(market, code):
        return None

    if market == "HK":
        return "WARRANT"  # 港股窝轮
    elif market == "US":
        return "OPTION"  # 美股期权

    return None


class DerivativeService:
    """衍生品合约信息服务"""

    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._owns_session = session is None

    def _get_session(self) -> Session:
        if self._session is None:
            self._session = get_session().__enter__()
        return self._session

    def close(self):
        if self._owns_session and self._session:
            self._session.close()
            self._session = None

    def get_contract(self, market: str, code: str) -> Optional[DerivativeContract]:
        """从数据库获取合约信息"""
        session = self._get_session()
        return (
            session.query(DerivativeContract)
            .filter_by(market=market, code=code)
            .first()
        )

    def get_multiplier(self, market: str, code: str) -> Decimal:
        """
        获取衍生品的乘数。

        1. 先从数据库查询
        2. 如果没有，返回默认值

        Returns:
            乘数值（港股窝轮为换股比率，美股期权为合约乘数）
        """
        contract = self.get_contract(market, code)
        if contract:
            return contract.multiplier

        # 返回默认值
        if market == "US":
            return DEFAULT_US_OPTION_MULTIPLIER
        else:
            return DEFAULT_HK_WARRANT_RATIO

    def save_contract(
        self,
        market: str,
        code: str,
        stock_name: Optional[str] = None,
        contract_type: Optional[str] = None,
        underlying_code: Optional[str] = None,
        contract_multiplier: Optional[Decimal] = None,
        conversion_ratio: Optional[Decimal] = None,
        option_type: Optional[str] = None,
        strike_price: Optional[Decimal] = None,
        expiry_date: Optional[date] = None,
        lot_size: Optional[int] = None,
        data_source: str = "MANUAL",
    ) -> DerivativeContract:
        """保存或更新合约信息"""
        session = self._get_session()

        contract = self.get_contract(market, code)
        if contract is None:
            contract = DerivativeContract(market=market, code=code)
            session.add(contract)

        # 更新字段
        if stock_name is not None:
            contract.stock_name = stock_name
        if contract_type is not None:
            contract.contract_type = contract_type
        if underlying_code is not None:
            contract.underlying_code = underlying_code
        if contract_multiplier is not None:
            contract.contract_multiplier = contract_multiplier
        if conversion_ratio is not None:
            contract.conversion_ratio = conversion_ratio
        if option_type is not None:
            contract.option_type = option_type
        if strike_price is not None:
            contract.strike_price = strike_price
        if expiry_date is not None:
            contract.expiry_date = expiry_date
        if lot_size is not None:
            contract.lot_size = lot_size
        contract.data_source = data_source
        contract.updated_at = datetime.now()

        session.commit()
        return contract

    def fetch_from_futu(
        self, market: str, code: str, futu_ctx=None
    ) -> Optional[DerivativeContract]:
        """
        从 Futu API 获取合约信息。

        Args:
            market: 市场 (HK/US)
            code: 期权/窝轮代码
            futu_ctx: OpenQuoteContext 实例

        Returns:
            DerivativeContract or None
        """
        if futu_ctx is None:
            logger.warning("No Futu context provided, cannot fetch from API")
            return None

        try:
            from futu import RET_OK

            full_code = f"{market}.{code}"
            ret, data = futu_ctx.get_market_snapshot([full_code])

            if ret != RET_OK or data is None or len(data) == 0:
                logger.warning(f"Failed to get snapshot for {full_code}: {data}")
                return None

            row = data.iloc[0]

            # 解析代码信息
            parsed = parse_option_code(market, code)

            # 根据市场类型提取信息
            if market == "HK":
                # 港股窝轮
                wrt_valid = row.get("wrt_valid", False)
                if not wrt_valid:
                    logger.info(f"{full_code} is not a valid warrant")
                    return None

                conversion_ratio = row.get("wrt_conversion_ratio")
                if conversion_ratio and conversion_ratio > 0:
                    conversion_ratio = Decimal(str(conversion_ratio))
                else:
                    conversion_ratio = None

                contract = self.save_contract(
                    market=market,
                    code=code,
                    stock_name=row.get("name"),
                    contract_type="WARRANT",
                    underlying_code=row.get("stock_owner"),
                    conversion_ratio=conversion_ratio,
                    option_type=parsed.get("option_type") if parsed else None,
                    strike_price=row.get("wrt_strike_price"),
                    expiry_date=parsed.get("expiry_date") if parsed else None,
                    lot_size=row.get("lot_size"),
                    data_source="FUTU",
                )
                logger.info(
                    f"Fetched HK warrant {full_code}: ratio={conversion_ratio}"
                )
                return contract

            elif market == "US":
                # 美股期权
                option_valid = row.get("option_valid", False)
                if not option_valid:
                    logger.info(f"{full_code} is not a valid option")
                    return None

                contract_size = row.get("option_contract_size")
                if contract_size and contract_size > 0:
                    contract_multiplier = Decimal(str(contract_size))
                else:
                    contract_multiplier = DEFAULT_US_OPTION_MULTIPLIER

                contract = self.save_contract(
                    market=market,
                    code=code,
                    stock_name=row.get("name"),
                    contract_type="OPTION",
                    underlying_code=row.get("stock_owner"),
                    contract_multiplier=contract_multiplier,
                    option_type=parsed.get("option_type") if parsed else None,
                    strike_price=row.get("option_strike_price"),
                    expiry_date=parsed.get("expiry_date") if parsed else None,
                    lot_size=row.get("lot_size"),
                    data_source="FUTU",
                )
                logger.info(
                    f"Fetched US option {full_code}: multiplier={contract_multiplier}"
                )
                return contract

        except Exception as e:
            logger.error(f"Error fetching from Futu API: {e}")
            return None

        return None

    def auto_populate_from_code(
        self, market: str, code: str, stock_name: Optional[str] = None
    ) -> Optional[DerivativeContract]:
        """
        从代码自动解析并创建合约记录。

        用于无法从 API 获取数据时的备选方案。
        美股期权使用默认乘数 100，港股窝轮使用默认比率 1。
        """
        if not is_derivative_code(market, code):
            return None

        parsed = parse_option_code(market, code)
        contract_type = get_derivative_type(market, code)

        if contract_type == "OPTION":
            # 美股期权
            return self.save_contract(
                market=market,
                code=code,
                stock_name=stock_name,
                contract_type="OPTION",
                underlying_code=parsed.get("underlying") if parsed else None,
                contract_multiplier=DEFAULT_US_OPTION_MULTIPLIER,
                option_type=parsed.get("option_type") if parsed else None,
                strike_price=parsed.get("strike_price") if parsed else None,
                expiry_date=parsed.get("expiry_date") if parsed else None,
                data_source="AUTO",
            )
        elif contract_type == "WARRANT":
            # 港股窝轮 - 使用默认值
            return self.save_contract(
                market=market,
                code=code,
                stock_name=stock_name,
                contract_type="WARRANT",
                underlying_code=parsed.get("underlying") if parsed else None,
                conversion_ratio=DEFAULT_HK_WARRANT_RATIO,
                option_type=parsed.get("option_type") if parsed else None,
                strike_price=parsed.get("strike_price") if parsed else None,
                expiry_date=parsed.get("expiry_date") if parsed else None,
                data_source="AUTO",
            )

        return None

    def batch_fetch_contracts(
        self, codes: list[tuple[str, str]], futu_ctx=None
    ) -> dict[str, DerivativeContract]:
        """
        批量获取合约信息。

        Args:
            codes: List of (market, code) tuples
            futu_ctx: OpenQuoteContext 实例

        Returns:
            Dict mapping "market.code" to DerivativeContract
        """
        results = {}

        for market, code in codes:
            full_code = f"{market}.{code}"

            # 先查数据库
            contract = self.get_contract(market, code)
            if contract:
                results[full_code] = contract
                continue

            # 尝试从 API 获取
            if futu_ctx:
                contract = self.fetch_from_futu(market, code, futu_ctx)
                if contract:
                    results[full_code] = contract
                    continue

            # 自动解析创建
            contract = self.auto_populate_from_code(market, code)
            if contract:
                results[full_code] = contract

        return results

    def list_contracts(
        self,
        market: Optional[str] = None,
        contract_type: Optional[str] = None,
        expired: Optional[bool] = None,
    ) -> list[DerivativeContract]:
        """列出合约"""
        session = self._get_session()
        query = session.query(DerivativeContract)

        if market:
            query = query.filter_by(market=market)
        if contract_type:
            query = query.filter_by(contract_type=contract_type)
        if expired is not None:
            today = date.today()
            if expired:
                query = query.filter(DerivativeContract.expiry_date < today)
            else:
                query = query.filter(
                    (DerivativeContract.expiry_date >= today)
                    | (DerivativeContract.expiry_date.is_(None))
                )

        return query.order_by(DerivativeContract.market, DerivativeContract.code).all()


def sync_derivative_contracts_for_trades(
    trades_codes: list[tuple[str, str, str]],
    futu_ctx=None,
) -> int:
    """
    为交易记录中的衍生品同步合约信息。

    Args:
        trades_codes: List of (market, code, stock_name) from trades
        futu_ctx: OpenQuoteContext 实例

    Returns:
        Number of contracts synced
    """
    # 筛选出衍生品
    derivative_codes = [
        (m, c, n) for m, c, n in trades_codes if is_derivative_code(m, c)
    ]

    if not derivative_codes:
        logger.info("No derivative codes found in trades")
        return 0

    logger.info(f"Found {len(derivative_codes)} derivative codes to sync")

    with get_session() as session:
        service = DerivativeService(session)
        synced = 0

        for market, code, stock_name in derivative_codes:
            # 检查是否已存在
            existing = service.get_contract(market, code)
            if existing:
                continue

            # 尝试从 API 获取
            contract = None
            if futu_ctx:
                contract = service.fetch_from_futu(market, code, futu_ctx)

            # 备选：自动解析
            if not contract:
                contract = service.auto_populate_from_code(market, code, stock_name)

            if contract:
                synced += 1
                logger.info(f"Synced contract: {market}.{code}")

        return synced
