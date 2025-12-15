"""
Web Data Fetcher for Deep Analysis.

Fetches fundamental data, news, and industry information from web sources.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

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
    Fetches fundamental data, news, and industry information from web.

    Uses WebSearch tool to gather information from reliable sources.
    """

    # Stock name mappings for search
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
            web_search_func: Function for web search (for testing/mocking)
            web_fetch_func: Function for web fetch (for testing/mocking)
        """
        self._web_search = web_search_func
        self._web_fetch = web_fetch_func

    async def fetch(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        include_news: bool = True,
        include_industry: bool = True,
    ) -> WebDataResult:
        """
        Fetch comprehensive web data for a stock.

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

        # Get search names
        cn_name, en_name = self._get_search_names(full_code, stock_name)

        try:
            # Fetch fundamental data
            fundamental = await self._fetch_fundamental(market, code, cn_name, en_name)
            if fundamental:
                result.fundamental = fundamental

            # Fetch news
            if include_news:
                news = await self._fetch_news(market, code, cn_name, en_name)
                result.news_items = news

            # Fetch industry data
            if include_industry:
                industry = await self._fetch_industry(market, code, cn_name, en_name)
                if industry:
                    result.industry = industry

        except Exception as e:
            logger.exception(f"Error fetching web data for {full_code}: {e}")
            result.success = False
            result.errors.append(str(e))

        return result

    def fetch_sync(
        self,
        market: str,
        code: str,
        stock_name: str = "",
        include_news: bool = True,
        include_industry: bool = True,
    ) -> WebDataResult:
        """
        Synchronous version of fetch.

        For environments without async support.
        """
        import asyncio

        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.fetch(market, code, stock_name, include_news, include_industry)
        )

    def _get_search_names(
        self, full_code: str, stock_name: str
    ) -> tuple[str, str]:
        """Get Chinese and English names for searching."""
        if full_code in self.STOCK_NAME_MAP:
            return self.STOCK_NAME_MAP[full_code]

        # Use provided name or code
        if stock_name:
            return stock_name, stock_name
        return full_code, full_code

    async def _fetch_fundamental(
        self, market: str, code: str, cn_name: str, en_name: str
    ) -> Optional[FundamentalData]:
        """Fetch fundamental data from web sources."""
        fundamental = FundamentalData(
            market=market,
            code=code,
            stock_name=cn_name,
            fetch_date=date.today(),
        )

        # Build search queries based on market
        if market == "HK":
            queries = [
                f"{cn_name} PE 市盈率 市值",
                f"{en_name} Hong Kong stock fundamentals PE ratio",
            ]
            fundamental.market_cap_currency = "HKD"
        elif market == "US":
            queries = [
                f"{en_name} stock PE ratio market cap",
                f"{en_name} financial metrics EPS revenue",
            ]
            fundamental.market_cap_currency = "USD"
        else:  # A-shares
            queries = [
                f"{cn_name} A股 市盈率 市值 财务数据",
            ]
            fundamental.market_cap_currency = "CNY"

        # Simulate search and extract data
        # In real implementation, this would use WebSearch tool
        if self._web_search:
            for query in queries:
                try:
                    search_result = await self._web_search(query)
                    self._parse_fundamental_data(fundamental, search_result)
                except Exception as e:
                    logger.warning(f"Search failed for '{query}': {e}")

        return fundamental

    def _parse_fundamental_data(self, fundamental: FundamentalData, text: str) -> None:
        """Parse fundamental data from search result text."""
        if not text:
            return

        fundamental.raw_text += text + "\n"

        # Extract PE ratio
        pe_match = re.search(r"P/?E[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if pe_match:
            fundamental.pe_ratio = float(pe_match.group(1))

        # Extract market cap
        cap_match = re.search(
            r"[市值|Market Cap][:\s]+(\d+\.?\d*)\s*(亿|B|billion)?",
            text,
            re.IGNORECASE,
        )
        if cap_match:
            value = float(cap_match.group(1))
            unit = cap_match.group(2) or ""
            if "亿" in unit or "B" in unit.upper() or "billion" in unit.lower():
                fundamental.market_cap = value
            else:
                fundamental.market_cap = value / 1000  # Assume millions

        # Extract PB ratio
        pb_match = re.search(r"P/?B[:\s]+(\d+\.?\d*)", text, re.IGNORECASE)
        if pb_match:
            fundamental.pb_ratio = float(pb_match.group(1))

        # Extract dividend yield
        div_match = re.search(
            r"[股息率|Dividend Yield][:\s]+(\d+\.?\d*)%?",
            text,
            re.IGNORECASE,
        )
        if div_match:
            fundamental.dividend_yield = float(div_match.group(1))

        # Extract ROE
        roe_match = re.search(r"ROE[:\s]+(\d+\.?\d*)%?", text, re.IGNORECASE)
        if roe_match:
            fundamental.roe = float(roe_match.group(1))

    async def _fetch_news(
        self, market: str, code: str, cn_name: str, en_name: str
    ) -> list[NewsItem]:
        """Fetch recent news about the stock."""
        news_items = []

        # Build news search queries
        if market in ["HK", "A"]:
            queries = [
                f"{cn_name} 最新消息 新闻",
                f"{cn_name} 公告 业绩",
            ]
        else:
            queries = [
                f"{en_name} stock news latest",
                f"{en_name} earnings announcement",
            ]

        if self._web_search:
            for query in queries:
                try:
                    search_result = await self._web_search(query)
                    items = self._parse_news(search_result)
                    news_items.extend(items)
                except Exception as e:
                    logger.warning(f"News search failed for '{query}': {e}")

        # Deduplicate and limit
        seen_titles = set()
        unique_news = []
        for item in news_items:
            if item.title not in seen_titles:
                seen_titles.add(item.title)
                unique_news.append(item)

        return unique_news[:10]  # Limit to 10 news items

    def _parse_news(self, text: str) -> list[NewsItem]:
        """Parse news items from search result."""
        items = []

        if not text:
            return items

        # Simple parsing - in real implementation would be more sophisticated
        # Look for patterns like titles and sources
        lines = text.split("\n")
        for line in lines:
            line = line.strip()
            if len(line) > 20 and len(line) < 200:
                # Determine sentiment from keywords
                sentiment = "neutral"
                positive_words = ["涨", "增长", "盈利", "突破", "利好", "上涨", "gains", "up", "growth"]
                negative_words = ["跌", "下降", "亏损", "下跌", "利空", "drop", "down", "loss"]

                if any(word in line.lower() for word in positive_words):
                    sentiment = "positive"
                elif any(word in line.lower() for word in negative_words):
                    sentiment = "negative"

                items.append(
                    NewsItem(
                        title=line[:100],
                        source="Web Search",
                        summary=line,
                        sentiment=sentiment,
                    )
                )

        return items

    async def _fetch_industry(
        self, market: str, code: str, cn_name: str, en_name: str
    ) -> Optional[IndustryData]:
        """Fetch industry analysis data."""
        industry = IndustryData(
            industry="",
            sector="",
        )

        # Determine industry from stock name
        industry_keywords = {
            "半导体": ("半导体", "Semiconductor", "Technology"),
            "芯片": ("半导体", "Semiconductor", "Technology"),
            "SMIC": ("半导体", "Semiconductor", "Technology"),
            "华虹": ("半导体", "Semiconductor", "Technology"),
            "互联网": ("互联网", "Internet", "Technology"),
            "腾讯": ("互联网科技", "Internet/Gaming", "Technology"),
            "阿里": ("电子商务", "E-commerce", "Consumer"),
            "快手": ("短视频", "Short Video", "Technology"),
            "美团": ("本地生活", "Local Services", "Consumer"),
            "平安": ("保险", "Insurance", "Financials"),
            "NVIDIA": ("半导体/AI", "Semiconductor/AI", "Technology"),
            "Apple": ("消费电子", "Consumer Electronics", "Technology"),
            "Tesla": ("电动汽车", "Electric Vehicles", "Consumer"),
        }

        for keyword, (ind_cn, ind_en, sector) in industry_keywords.items():
            if keyword.lower() in cn_name.lower() or keyword.lower() in en_name.lower():
                industry.industry = ind_cn
                industry.sector = sector
                break

        # Search for industry trends
        if industry.industry and self._web_search:
            query = f"{industry.industry} 行业 趋势 分析 2024 2025"
            try:
                search_result = await self._web_search(query)
                self._parse_industry_data(industry, search_result)
            except Exception as e:
                logger.warning(f"Industry search failed: {e}")

        return industry if industry.industry else None

    def _parse_industry_data(self, industry: IndustryData, text: str) -> None:
        """Parse industry data from search result."""
        if not text:
            return

        industry.description = text[:500] if len(text) > 500 else text

        # Extract key trends
        trend_keywords = ["趋势", "发展", "增长", "trend", "growth"]
        lines = text.split("\n")
        for line in lines:
            if any(kw in line.lower() for kw in trend_keywords):
                if len(line) > 10 and len(line) < 200:
                    industry.key_trends.append(line.strip())
                    if len(industry.key_trends) >= 5:
                        break


def create_fundamental_summary(fundamental: FundamentalData) -> str:
    """Create a text summary of fundamental data."""
    lines = []
    lines.append(f"## 基本面数据 - {fundamental.stock_name}")
    lines.append(f"数据日期: {fundamental.fetch_date}")
    lines.append("")

    lines.append("### 估值指标")
    if fundamental.pe_ratio:
        lines.append(f"- 市盈率 (PE): {fundamental.pe_ratio:.2f}")
    if fundamental.pb_ratio:
        lines.append(f"- 市净率 (PB): {fundamental.pb_ratio:.2f}")
    if fundamental.ps_ratio:
        lines.append(f"- 市销率 (PS): {fundamental.ps_ratio:.2f}")
    if fundamental.market_cap:
        lines.append(
            f"- 市值: {fundamental.market_cap:.2f}B {fundamental.market_cap_currency}"
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
