"""
Web Data Fetcher for Deep Analysis.

Fetches fundamental data, news, and industry information using akshare.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FundamentalData:
    """Fundamental financial data."""

    market: str
    code: str
    stock_name: str
    fetch_date: date

    # Valuation
    pe_ratio: Optional[float] = None
    pe_ttm: Optional[float] = None
    pb_ratio: Optional[float] = None
    ps_ratio: Optional[float] = None
    peg_ratio: Optional[float] = None

    # Market data
    market_cap: Optional[float] = None  # in billions
    market_cap_currency: str = "HKD"
    shares_outstanding: Optional[float] = None
    float_shares: Optional[float] = None

    # Financial metrics
    revenue: Optional[float] = None  # TTM in millions
    revenue_growth: Optional[float] = None  # YoY %
    net_income: Optional[float] = None
    net_income_growth: Optional[float] = None
    gross_margin: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None

    # Dividend
    dividend_yield: Optional[float] = None
    dividend_payout_ratio: Optional[float] = None

    # Balance sheet
    total_assets: Optional[float] = None
    total_debt: Optional[float] = None
    cash_and_equivalents: Optional[float] = None
    debt_to_equity: Optional[float] = None

    # Per share data
    eps: Optional[float] = None
    eps_growth: Optional[float] = None
    book_value_per_share: Optional[float] = None

    # 52-week range
    high_52week: Optional[float] = None
    low_52week: Optional[float] = None

    # Source info
    data_source: str = ""
    raw_text: str = ""


@dataclass
class NewsItem:
    """A news item about a stock."""

    title: str
    source: str
    date: Optional[date] = None
    summary: str = ""
    url: str = ""
    sentiment: str = "neutral"  # positive, negative, neutral


@dataclass
class IndustryData:
    """Industry and competitive analysis data."""

    industry: str
    sector: str
    description: str = ""
    market_size: str = ""
    growth_rate: str = ""
    key_trends: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    competitive_position: str = ""
    industry_outlook: str = ""


@dataclass
class WebDataResult:
    """Complete web data fetch result."""

    market: str
    code: str
    stock_name: str
    fetch_time: datetime

    # Data components
    fundamental: Optional[FundamentalData] = None
    news_items: list[NewsItem] = field(default_factory=list)
    industry: Optional[IndustryData] = None

    # Status
    success: bool = True
    errors: list[str] = field(default_factory=list)


class WebDataFetcher:
    """
    Fetches fundamental data, news, and industry information.

    Uses akshare for HK/A-share data.
    """

    # Industry classification based on stock characteristics
    INDUSTRY_MAP = {
        # HK Tech/Internet
        "00700": ("互联网科技", "Internet/Gaming", "Technology", ["阿里巴巴", "美团", "京东"]),
        "09988": ("电子商务", "E-commerce", "Technology", ["京东", "拼多多", "唯品会"]),
        "03690": ("本地生活", "Local Services", "Consumer", ["饿了么", "京东到家"]),
        "09618": ("电子商务", "E-commerce", "Technology", ["阿里巴巴", "拼多多"]),
        "01024": ("短视频/社交", "Short Video", "Technology", ["抖音", "微博", "B站"]),
        # HK Semiconductor
        "00981": ("半导体", "Semiconductor", "Technology", ["华虹半导体", "台积电", "联华电子"]),
        "01347": ("半导体", "Semiconductor", "Technology", ["中芯国际", "台积电", "联华电子"]),
        # HK Finance
        "02318": ("保险", "Insurance", "Financials", ["中国人寿", "中国太保", "新华保险"]),
        "00388": ("交易所", "Exchange", "Financials", ["上交所", "深交所", "纳斯达克"]),
        # HK Others
        "00020": ("人工智能", "AI", "Technology", ["旷视科技", "云从科技", "依图科技"]),
        "09992": ("潮玩", "Collectibles", "Consumer", ["名创优品", "泡泡玛特"]),
        # US Tech
        "NVDA": ("半导体/AI", "Semiconductor/AI", "Technology", ["AMD", "Intel", "台积电"]),
        "AAPL": ("消费电子", "Consumer Electronics", "Technology", ["三星", "华为", "小米"]),
        "TSLA": ("电动汽车", "Electric Vehicles", "Consumer", ["比亚迪", "蔚来", "小鹏"]),
        "META": ("社交媒体", "Social Media", "Technology", ["Snap", "Twitter", "Pinterest"]),
        "GOOG": ("互联网/广告", "Internet/Advertising", "Technology", ["Meta", "Microsoft", "Amazon"]),
        "GOOGL": ("互联网/广告", "Internet/Advertising", "Technology", ["Meta", "Microsoft", "Amazon"]),
        "MSFT": ("软件/云计算", "Software/Cloud", "Technology", ["Amazon", "Google", "Oracle"]),
        "AMZN": ("电商/云计算", "E-commerce/Cloud", "Technology", ["阿里巴巴", "Microsoft", "Google"]),
    }

    # Stock name mappings
    STOCK_NAME_MAP = {
        "HK.00700": ("腾讯控股", "Tencent"),
        "HK.09988": ("阿里巴巴", "Alibaba"),
        "HK.00981": ("中芯国际", "SMIC"),
        "HK.01347": ("华虹半导体", "Hua Hong Semiconductor"),
        "HK.01024": ("快手", "Kuaishou"),
        "HK.03690": ("美团", "Meituan"),
        "HK.09618": ("京东", "JD.com"),
        "HK.02318": ("中国平安", "Ping An"),
        "HK.00020": ("商汤科技", "SenseTime"),
        "HK.09992": ("泡泡玛特", "Pop Mart"),
        "US.NVDA": ("英伟达", "NVIDIA"),
        "US.AAPL": ("苹果", "Apple"),
        "US.TSLA": ("特斯拉", "Tesla"),
        "US.META": ("Meta", "Meta"),
        "US.GOOG": ("谷歌", "Google"),
        "US.MSFT": ("微软", "Microsoft"),
        "US.AMZN": ("亚马逊", "Amazon"),
    }

    def __init__(self, web_search_func=None, web_fetch_func=None):
        """
        Initialize fetcher.

        Args:
            web_search_func: Optional web search function (for future extension)
            web_fetch_func: Optional web fetch function (for future extension)
        """
        self._web_search = web_search_func
        self._web_fetch = web_fetch_func

    def fetch_sync(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        include_news: bool = True,
        include_industry: bool = True,
    ) -> WebDataResult:
        """
        Fetch comprehensive data for a stock.

        Args:
            market: Market code (HK, US, A)
            code: Stock code
            stock_name: Stock name (optional)
            include_news: Whether to fetch news
            include_industry: Whether to fetch industry data

        Returns:
            WebDataResult with all fetched data
        """
        full_code = f"{market}.{code}"
        result = WebDataResult(
            market=market,
            code=code,
            stock_name=stock_name,
            fetch_time=datetime.now(),
        )

        try:
            # Fetch fundamental data using akshare
            fundamental = self._fetch_fundamental_akshare(market, code, stock_name)
            if fundamental:
                result.fundamental = fundamental

            # Fetch industry data
            if include_industry:
                industry = self._get_industry_data(market, code, stock_name)
                if industry:
                    result.industry = industry

            # News fetching would require additional API integration
            # For now, we provide industry-based context
            if include_news:
                news = self._get_industry_news_context(market, code, stock_name)
                result.news_items = news

        except Exception as e:
            logger.exception(f"Error fetching data for {full_code}: {e}")
            result.errors.append(str(e))

        return result

    async def fetch(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        include_news: bool = True,
        include_industry: bool = True,
    ) -> WebDataResult:
        """Async version - delegates to sync for now."""
        return self.fetch_sync(market, code, stock_name, include_news, include_industry)

    def _fetch_fundamental_akshare(
        self, market: str, code: str, stock_name: str
    ) -> Optional[FundamentalData]:
        """Fetch fundamental data using Futu API or akshare as fallback."""
        fundamental = FundamentalData(
            market=market,
            code=code,
            stock_name=stock_name or code,
            fetch_date=date.today(),
        )

        # Try Futu API first (more reliable for HK/US markets)
        if market in ("HK", "US"):
            futu_result = self._fetch_fundamental_futu(market, code, fundamental)
            if futu_result and (futu_result.pe_ratio or futu_result.pb_ratio):
                return futu_result

        # Fallback to akshare for A-shares or if Futu failed
        try:
            import akshare as ak
        except ImportError:
            logger.debug("akshare not installed")
            return fundamental

        try:
            if market == "HK":
                fundamental = self._fetch_hk_fundamental(ak, code, fundamental)
            elif market == "A":
                fundamental = self._fetch_a_share_fundamental(ak, code, fundamental)
            elif market == "US":
                fundamental = self._fetch_us_fundamental(ak, code, fundamental)

            return fundamental

        except Exception as e:
            logger.warning(f"Failed to fetch fundamental data for {market}.{code}: {e}")
            return fundamental

    def _fetch_fundamental_futu(
        self, market: str, code: str, fundamental: FundamentalData
    ) -> Optional[FundamentalData]:
        """Fetch fundamental data using Futu OpenD API."""
        try:
            from futu import OpenQuoteContext, RET_OK
        except ImportError:
            logger.debug("futu-api not installed")
            return None

        full_code = f"{market}.{code}"
        quote_ctx = None

        try:
            quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
            ret, data = quote_ctx.get_market_snapshot([full_code])

            if ret != RET_OK or data is None or data.empty:
                logger.debug(f"Futu snapshot failed for {full_code}: {data}")
                return None

            row = data.iloc[0]

            # Stock name
            if "name" in row.index and pd.notna(row["name"]):
                fundamental.stock_name = str(row["name"])

            # Valuation metrics
            if "pe_ratio" in row.index and pd.notna(row["pe_ratio"]):
                fundamental.pe_ratio = float(row["pe_ratio"])

            if "pe_ttm_ratio" in row.index and pd.notna(row["pe_ttm_ratio"]):
                fundamental.pe_ttm = float(row["pe_ttm_ratio"])

            if "pb_ratio" in row.index and pd.notna(row["pb_ratio"]):
                fundamental.pb_ratio = float(row["pb_ratio"])

            # Market cap (convert to billions)
            if "total_market_val" in row.index and pd.notna(row["total_market_val"]):
                market_val = float(row["total_market_val"])
                fundamental.market_cap = market_val / 1e8  # 转换为亿
                fundamental.market_cap_currency = "HKD" if market == "HK" else "USD"

            # 52-week range
            if "highest52weeks_price" in row.index and pd.notna(row["highest52weeks_price"]):
                fundamental.high_52week = float(row["highest52weeks_price"])

            if "lowest52weeks_price" in row.index and pd.notna(row["lowest52weeks_price"]):
                fundamental.low_52week = float(row["lowest52weeks_price"])

            # Shares
            if "issued_shares" in row.index and pd.notna(row["issued_shares"]):
                fundamental.shares_outstanding = float(row["issued_shares"])

            if "outstanding_shares" in row.index and pd.notna(row["outstanding_shares"]):
                fundamental.float_shares = float(row["outstanding_shares"])

            # EPS and book value
            if "earning_per_share" in row.index and pd.notna(row["earning_per_share"]):
                fundamental.eps = float(row["earning_per_share"])

            if "net_asset_per_share" in row.index and pd.notna(row["net_asset_per_share"]):
                fundamental.book_value_per_share = float(row["net_asset_per_share"])

            # Dividend
            if "dividend_ratio_ttm" in row.index and pd.notna(row["dividend_ratio_ttm"]):
                fundamental.dividend_yield = float(row["dividend_ratio_ttm"])

            # Net asset and profit
            if "net_asset" in row.index and pd.notna(row["net_asset"]):
                fundamental.total_assets = float(row["net_asset"]) / 1e8  # 亿

            if "net_profit" in row.index and pd.notna(row["net_profit"]):
                fundamental.net_income = float(row["net_profit"]) / 1e8  # 亿

            fundamental.data_source = "futu"
            return fundamental

        except Exception as e:
            logger.debug(f"Futu fundamental fetch error for {full_code}: {e}")
            return None

        finally:
            if quote_ctx:
                try:
                    quote_ctx.close()
                except Exception:
                    pass

    def _fetch_hk_fundamental(
        self, ak, code: str, fundamental: FundamentalData
    ) -> FundamentalData:
        """Fetch HK stock fundamental data."""
        fundamental.market_cap_currency = "HKD"
        fundamental.data_source = "akshare"

        try:
            # Get HK stock spot data with fundamentals
            df = ak.stock_hk_spot_em()

            if df is not None and not df.empty:
                # Find the stock by code (remove leading zeros for matching)
                code_int = code.lstrip("0")
                mask = df["代码"].astype(str).str.contains(code_int)
                stock_row = df[mask]

                if not stock_row.empty:
                    row = stock_row.iloc[0]

                    # Extract available data
                    if "市盈率" in row.index and pd.notna(row["市盈率"]):
                        fundamental.pe_ratio = float(row["市盈率"])

                    if "市净率" in row.index and pd.notna(row["市净率"]):
                        fundamental.pb_ratio = float(row["市净率"])

                    if "总市值" in row.index and pd.notna(row["总市值"]):
                        # Convert to billions
                        market_cap = float(row["总市值"])
                        fundamental.market_cap = market_cap / 1e8  # 亿

                    if "52周最高" in row.index and pd.notna(row["52周最高"]):
                        fundamental.high_52week = float(row["52周最高"])

                    if "52周最低" in row.index and pd.notna(row["52周最低"]):
                        fundamental.low_52week = float(row["52周最低"])

                    if "名称" in row.index and pd.notna(row["名称"]):
                        if not fundamental.stock_name:
                            fundamental.stock_name = str(row["名称"])

        except Exception as e:
            logger.debug(f"HK fundamental fetch error: {e}")

        return fundamental

    def _fetch_a_share_fundamental(
        self, ak, code: str, fundamental: FundamentalData
    ) -> FundamentalData:
        """Fetch A-share fundamental data."""
        fundamental.market_cap_currency = "CNY"
        fundamental.data_source = "akshare"

        try:
            # Get A-share indicators
            df = ak.stock_a_indicator_lg(symbol=code)

            if df is not None and not df.empty:
                latest = df.iloc[-1]

                if "pe" in latest.index and pd.notna(latest["pe"]):
                    fundamental.pe_ratio = float(latest["pe"])

                if "pe_ttm" in latest.index and pd.notna(latest["pe_ttm"]):
                    fundamental.pe_ttm = float(latest["pe_ttm"])

                if "pb" in latest.index and pd.notna(latest["pb"]):
                    fundamental.pb_ratio = float(latest["pb"])

                if "ps" in latest.index and pd.notna(latest["ps"]):
                    fundamental.ps_ratio = float(latest["ps"])

                if "dv_ratio" in latest.index and pd.notna(latest["dv_ratio"]):
                    fundamental.dividend_yield = float(latest["dv_ratio"])

                if "total_mv" in latest.index and pd.notna(latest["total_mv"]):
                    fundamental.market_cap = float(latest["total_mv"]) / 1e8

        except Exception as e:
            logger.debug(f"A-share fundamental fetch error: {e}")

        return fundamental

    def _fetch_us_fundamental(
        self, ak, code: str, fundamental: FundamentalData
    ) -> FundamentalData:
        """Fetch US stock fundamental data."""
        fundamental.market_cap_currency = "USD"
        fundamental.data_source = "akshare"

        # US stock data is more limited in akshare
        # For now, return with basic data
        return fundamental

    def _get_industry_data(
        self, market: str, code: str, stock_name: str
    ) -> Optional[IndustryData]:
        """Get industry classification and data."""
        # Check predefined industry map
        if code in self.INDUSTRY_MAP:
            ind_cn, ind_en, sector, competitors = self.INDUSTRY_MAP[code]
            return IndustryData(
                industry=ind_cn,
                sector=sector,
                description=f"{ind_cn}行业",
                competitors=competitors,
                key_trends=self._get_industry_trends(ind_cn),
            )

        # Try to infer from stock name
        industry = self._infer_industry_from_name(stock_name)
        if industry:
            return industry

        return None

    def _infer_industry_from_name(self, stock_name: str) -> Optional[IndustryData]:
        """Infer industry from stock name."""
        if not stock_name:
            return None

        industry_keywords = {
            "半导体": ("半导体", "Semiconductor", "Technology"),
            "芯片": ("半导体", "Semiconductor", "Technology"),
            "集成电路": ("半导体", "Semiconductor", "Technology"),
            "互联网": ("互联网", "Internet", "Technology"),
            "科技": ("科技", "Technology", "Technology"),
            "银行": ("银行", "Banking", "Financials"),
            "保险": ("保险", "Insurance", "Financials"),
            "证券": ("证券", "Securities", "Financials"),
            "地产": ("房地产", "Real Estate", "Real Estate"),
            "医药": ("医药", "Pharmaceuticals", "Healthcare"),
            "新能源": ("新能源", "New Energy", "Energy"),
            "汽车": ("汽车", "Automotive", "Consumer"),
            "消费": ("消费", "Consumer", "Consumer"),
            "零售": ("零售", "Retail", "Consumer"),
        }

        for keyword, (ind_cn, ind_en, sector) in industry_keywords.items():
            if keyword in stock_name:
                return IndustryData(
                    industry=ind_cn,
                    sector=sector,
                    key_trends=self._get_industry_trends(ind_cn),
                )

        return None

    def _get_industry_trends(self, industry: str) -> list[str]:
        """Get key trends for an industry."""
        trends_map = {
            "半导体": [
                "AI芯片需求持续增长",
                "国产替代进程加速",
                "先进制程技术突破",
                "汽车芯片需求旺盛",
                "存储芯片周期复苏",
            ],
            "互联网科技": [
                "AI大模型应用落地",
                "云计算持续增长",
                "数字化转型加速",
                "游戏出海成效显著",
                "短视频电商崛起",
            ],
            "电子商务": [
                "直播电商快速增长",
                "跨境电商机遇",
                "下沉市场拓展",
                "即时零售发展",
                "AI提升运营效率",
            ],
            "新能源": [
                "电动车渗透率提升",
                "储能需求爆发",
                "光伏装机增长",
                "氢能产业起步",
                "碳中和政策支持",
            ],
            "保险": [
                "养老保险需求增长",
                "健康险快速发展",
                "数字化转型",
                "利率环境影响投资收益",
                "监管政策持续优化",
            ],
        }

        return trends_map.get(industry, ["行业发展中", "关注政策变化"])

    def _get_industry_news_context(
        self, market: str, code: str, stock_name: str
    ) -> list[NewsItem]:
        """Generate contextual news based on industry."""
        news_items = []

        # Get industry info
        industry = None
        if code in self.INDUSTRY_MAP:
            ind_cn, _, _, _ = self.INDUSTRY_MAP[code]
            industry = ind_cn
        else:
            ind_data = self._infer_industry_from_name(stock_name)
            if ind_data:
                industry = ind_data.industry

        if not industry:
            return news_items

        # Generate contextual news based on industry
        context_news = {
            "半导体": [
                NewsItem(
                    title="半导体行业: AI芯片需求持续拉动行业增长",
                    source="行业分析",
                    sentiment="positive",
                ),
                NewsItem(
                    title="国产替代持续推进，国内晶圆厂扩产积极",
                    source="行业分析",
                    sentiment="positive",
                ),
                NewsItem(
                    title="消费电子需求疲软，手机芯片承压",
                    source="行业分析",
                    sentiment="negative",
                ),
            ],
            "互联网科技": [
                NewsItem(
                    title="互联网平台: AI应用加速落地，提升运营效率",
                    source="行业分析",
                    sentiment="positive",
                ),
                NewsItem(
                    title="监管政策趋于稳定，行业估值修复",
                    source="行业分析",
                    sentiment="positive",
                ),
            ],
            "电子商务": [
                NewsItem(
                    title="电商行业: 直播电商增速放缓但仍保持增长",
                    source="行业分析",
                    sentiment="neutral",
                ),
                NewsItem(
                    title="跨境电商: 海外市场拓展带来新增量",
                    source="行业分析",
                    sentiment="positive",
                ),
            ],
        }

        return context_news.get(industry, [])

    def _get_search_names(
        self, full_code: str, stock_name: str
    ) -> tuple[str, str]:
        """Get Chinese and English names for searching."""
        if full_code in self.STOCK_NAME_MAP:
            return self.STOCK_NAME_MAP[full_code]

        if stock_name:
            return stock_name, stock_name
        return full_code, full_code


def create_fundamental_summary(fundamental: FundamentalData) -> str:
    """Create a text summary of fundamental data."""
    lines = []
    lines.append(f"## 基本面数据 - {fundamental.stock_name}")
    lines.append(f"数据日期: {fundamental.fetch_date}")
    lines.append("")

    lines.append("### 估值指标")
    if fundamental.pe_ratio:
        lines.append(f"- 市盈率 (PE): {fundamental.pe_ratio:.2f}")
    if fundamental.pe_ttm:
        lines.append(f"- 市盈率TTM: {fundamental.pe_ttm:.2f}")
    if fundamental.pb_ratio:
        lines.append(f"- 市净率 (PB): {fundamental.pb_ratio:.2f}")
    if fundamental.ps_ratio:
        lines.append(f"- 市销率 (PS): {fundamental.ps_ratio:.2f}")
    if fundamental.market_cap:
        lines.append(
            f"- 市值: {fundamental.market_cap:.2f}亿 {fundamental.market_cap_currency}"
        )

    if fundamental.roe or fundamental.revenue_growth:
        lines.append("")
        lines.append("### 财务指标")
        if fundamental.roe:
            lines.append(f"- ROE: {fundamental.roe:.2f}%")
        if fundamental.revenue_growth:
            lines.append(f"- 营收增长: {fundamental.revenue_growth:.2f}%")
        if fundamental.net_margin:
            lines.append(f"- 净利率: {fundamental.net_margin:.2f}%")

    if fundamental.dividend_yield:
        lines.append("")
        lines.append("### 股息")
        lines.append(f"- 股息率: {fundamental.dividend_yield:.2f}%")

    if fundamental.high_52week or fundamental.low_52week:
        lines.append("")
        lines.append("### 52周价格区间")
        if fundamental.high_52week:
            lines.append(f"- 52周最高: {fundamental.high_52week:.2f}")
        if fundamental.low_52week:
            lines.append(f"- 52周最低: {fundamental.low_52week:.2f}")

    return "\n".join(lines)


def create_news_summary(news_items: list[NewsItem]) -> str:
    """Create a text summary of news items."""
    if not news_items:
        return "## 最新消息\n\n暂无相关新闻"

    lines = []
    lines.append("## 最新消息")
    lines.append("")

    positive = [n for n in news_items if n.sentiment == "positive"]
    negative = [n for n in news_items if n.sentiment == "negative"]
    neutral = [n for n in news_items if n.sentiment == "neutral"]

    if positive:
        lines.append("### 利好消息")
        for item in positive[:3]:
            lines.append(f"- {item.title}")
        lines.append("")

    if negative:
        lines.append("### 利空消息")
        for item in negative[:3]:
            lines.append(f"- {item.title}")
        lines.append("")

    if neutral:
        lines.append("### 其他消息")
        for item in neutral[:3]:
            lines.append(f"- {item.title}")

    return "\n".join(lines)


def create_industry_summary(industry: IndustryData) -> str:
    """Create a text summary of industry data."""
    if not industry:
        return "## 行业分析\n\n暂无行业数据"

    lines = []
    lines.append("## 行业分析")
    lines.append("")
    lines.append(f"- 行业: {industry.industry}")
    lines.append(f"- 板块: {industry.sector}")

    if industry.description:
        lines.append("")
        lines.append("### 行业概述")
        lines.append(industry.description[:300])

    if industry.key_trends:
        lines.append("")
        lines.append("### 行业趋势")
        for trend in industry.key_trends[:5]:
            lines.append(f"- {trend}")

    if industry.competitors:
        lines.append("")
        lines.append("### 主要竞争对手")
        lines.append(", ".join(industry.competitors))

    return "\n".join(lines)
