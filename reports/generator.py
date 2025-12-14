"""
Report generation module for Investment Analyzer.

Provides report generation capabilities including:
- Portfolio reports (position analysis, P&L, risk assessment)
- Technical analysis reports (indicators, VCP patterns)
- Daily briefs (summary of daily activity)
- Weekly reviews (performance over the week)

Usage:
    from reports import ReportGenerator, ReportConfig, ReportType

    generator = ReportGenerator()
    config = ReportConfig(
        report_type=ReportType.PORTFOLIO,
        user_id=1,
        include_charts=True,
    )
    result = generator.generate(config)
    result.save("reports/output/portfolio_report.md")
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

logger = logging.getLogger(__name__)

# Get the templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportType(Enum):
    """Report type enumeration."""

    PORTFOLIO = "portfolio"
    TECHNICAL = "technical"
    DAILY = "daily"
    WEEKLY = "weekly"


class OutputFormat(Enum):
    """Output format enumeration."""

    MARKDOWN = "markdown"
    JSON = "json"
    HTML = "html"


@dataclass
class ReportConfig:
    """Configuration for report generation."""

    report_type: ReportType
    user_id: Optional[int] = None
    codes: Optional[list[str]] = None  # Stock codes for technical report
    include_charts: bool = True
    output_format: OutputFormat = OutputFormat.MARKDOWN
    title: Optional[str] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    extra_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportResult:
    """Result of report generation."""

    report_type: ReportType
    content: str
    output_format: OutputFormat
    generated_at: datetime
    title: str
    metadata: dict[str, Any] = field(default_factory=dict)
    chart_paths: list[str] = field(default_factory=list)

    def save(self, file_path: str | Path) -> Path:
        """
        Save report to file.

        Args:
            file_path: Path to save the report

        Returns:
            Path to saved file
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.content, encoding="utf-8")
        logger.info(f"Report saved to {path}")
        return path

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_type": self.report_type.value,
            "content": self.content,
            "output_format": self.output_format.value,
            "generated_at": self.generated_at.isoformat(),
            "title": self.title,
            "metadata": self.metadata,
            "chart_paths": self.chart_paths,
        }


class ReportGenerator:
    """
    Report generator for investment analysis.

    Generates various types of reports including:
    - Portfolio reports with position analysis and risk metrics
    - Technical analysis reports with indicators and patterns
    - Daily briefs summarizing daily activity
    - Weekly reviews with performance metrics

    Usage:
        generator = ReportGenerator()

        # Generate portfolio report
        from analysis import PortfolioAnalysisResult
        result = generator.generate_portfolio_report(portfolio_data)
        result.save("reports/output/portfolio.md")

        # Generate technical report
        from analysis import AnalysisResult
        result = generator.generate_technical_report("HK.00700", analysis_data)
        result.save("reports/output/technical.md")
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize report generator.

        Args:
            templates_dir: Directory containing Jinja2 templates
        """
        self.templates_dir = templates_dir or TEMPLATES_DIR

        # Initialize Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters
        self.env.filters["format_number"] = self._format_number
        self.env.filters["format_percent"] = self._format_percent
        self.env.filters["format_currency"] = self._format_currency
        self.env.filters["format_date"] = self._format_date

    @staticmethod
    def _format_number(value: Optional[float], decimals: int = 2) -> str:
        """Format number with thousands separator."""
        if value is None:
            return "-"
        return f"{value:,.{decimals}f}"

    @staticmethod
    def _format_percent(value: Optional[float], decimals: int = 1) -> str:
        """Format percentage value."""
        if value is None:
            return "-"
        sign = "+" if value > 0 else ""
        return f"{sign}{value:.{decimals}f}%"

    @staticmethod
    def _format_currency(value: Optional[float], currency: str = "$") -> str:
        """Format currency value."""
        if value is None:
            return "-"
        return f"{currency}{value:,.2f}"

    @staticmethod
    def _format_date(value: Optional[date], fmt: str = "%Y-%m-%d") -> str:
        """Format date value."""
        if value is None:
            return "-"
        if isinstance(value, datetime):
            return value.strftime(fmt)
        return value.strftime(fmt)

    def generate(self, config: ReportConfig, data: Any = None) -> ReportResult:
        """
        Generate a report based on configuration.

        Args:
            config: Report configuration
            data: Data to use for report generation

        Returns:
            ReportResult with generated report content

        Raises:
            ValueError: If report type is not supported
        """
        if config.report_type == ReportType.PORTFOLIO:
            return self.generate_portfolio_report(data, config)
        elif config.report_type == ReportType.TECHNICAL:
            return self.generate_technical_report(data, config)
        elif config.report_type == ReportType.DAILY:
            return self.generate_daily_brief(data, config)
        elif config.report_type == ReportType.WEEKLY:
            return self.generate_weekly_review(data, config)
        else:
            raise ValueError(f"Unsupported report type: {config.report_type}")

    def generate_portfolio_report(
        self,
        portfolio_data: Any,
        config: Optional[ReportConfig] = None,
    ) -> ReportResult:
        """
        Generate portfolio analysis report.

        Args:
            portfolio_data: PortfolioAnalysisResult object or dict
            config: Optional report configuration

        Returns:
            ReportResult with portfolio report
        """
        config = config or ReportConfig(report_type=ReportType.PORTFOLIO)
        now = datetime.now()

        # Convert to dict if needed
        if hasattr(portfolio_data, "to_dict"):
            data = portfolio_data.to_dict()
        elif isinstance(portfolio_data, dict):
            data = portfolio_data
        else:
            data = {}

        title = config.title or f"投资组合报告 - {now.strftime('%Y-%m-%d')}"

        # Prepare template context
        context = {
            "title": title,
            "generated_at": now,
            "data": data,
            "config": config,
        }

        # Generate content based on format
        if config.output_format == OutputFormat.JSON:
            content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        elif config.output_format == OutputFormat.HTML:
            template = self._get_template("portfolio.html.j2")
            content = template.render(**context)
        else:  # MARKDOWN
            template = self._get_template("portfolio.md.j2")
            content = template.render(**context)

        return ReportResult(
            report_type=ReportType.PORTFOLIO,
            content=content,
            output_format=config.output_format,
            generated_at=now,
            title=title,
            metadata={
                "user_id": config.user_id,
                "position_count": data.get("summary", {}).get("position_count", 0),
            },
        )

    def generate_technical_report(
        self,
        technical_data: Any,
        config: Optional[ReportConfig] = None,
    ) -> ReportResult:
        """
        Generate technical analysis report.

        Args:
            technical_data: Technical analysis data (dict or object with to_dict)
            config: Optional report configuration

        Returns:
            ReportResult with technical report
        """
        config = config or ReportConfig(report_type=ReportType.TECHNICAL)
        now = datetime.now()

        # Convert to dict if needed
        if hasattr(technical_data, "to_dict"):
            data = technical_data.to_dict()
        elif isinstance(technical_data, dict):
            data = technical_data
        else:
            data = {}

        # Get code from data or config
        code = data.get("code", "")
        if config.codes:
            code = config.codes[0] if isinstance(config.codes, list) else config.codes

        title = config.title or f"{code} 技术分析报告 - {now.strftime('%Y-%m-%d')}"

        # Prepare template context
        context = {
            "title": title,
            "generated_at": now,
            "code": code,
            "data": data,
            "config": config,
        }

        # Generate content based on format
        if config.output_format == OutputFormat.JSON:
            content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        elif config.output_format == OutputFormat.HTML:
            template = self._get_template("technical.html.j2")
            content = template.render(**context)
        else:  # MARKDOWN
            template = self._get_template("technical.md.j2")
            content = template.render(**context)

        chart_paths = []
        if config.include_charts:
            chart_path = data.get("chart_path")
            if chart_path:
                chart_paths.append(chart_path)

        return ReportResult(
            report_type=ReportType.TECHNICAL,
            content=content,
            output_format=config.output_format,
            generated_at=now,
            title=title,
            metadata={
                "code": code,
                "indicators": data.get("indicators", []),
            },
            chart_paths=chart_paths,
        )

    def generate_daily_brief(
        self,
        daily_data: Any,
        config: Optional[ReportConfig] = None,
    ) -> ReportResult:
        """
        Generate daily investment brief.

        Args:
            daily_data: Daily summary data
            config: Optional report configuration

        Returns:
            ReportResult with daily brief
        """
        config = config or ReportConfig(report_type=ReportType.DAILY)
        now = datetime.now()

        # Convert to dict if needed
        if hasattr(daily_data, "to_dict"):
            data = daily_data.to_dict()
        elif isinstance(daily_data, dict):
            data = daily_data
        else:
            data = {}

        report_date = config.date_range_start or date.today()
        title = config.title or f"每日投资简报 - {report_date.strftime('%Y-%m-%d')}"

        # Prepare template context
        context = {
            "title": title,
            "generated_at": now,
            "report_date": report_date,
            "data": data,
            "config": config,
        }

        # Generate content based on format
        if config.output_format == OutputFormat.JSON:
            content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        elif config.output_format == OutputFormat.HTML:
            template = self._get_template("daily.html.j2")
            content = template.render(**context)
        else:  # MARKDOWN
            template = self._get_template("daily.md.j2")
            content = template.render(**context)

        return ReportResult(
            report_type=ReportType.DAILY,
            content=content,
            output_format=config.output_format,
            generated_at=now,
            title=title,
            metadata={
                "report_date": report_date.isoformat(),
            },
        )

    def generate_weekly_review(
        self,
        weekly_data: Any,
        config: Optional[ReportConfig] = None,
    ) -> ReportResult:
        """
        Generate weekly investment review.

        Args:
            weekly_data: Weekly summary data
            config: Optional report configuration

        Returns:
            ReportResult with weekly review
        """
        config = config or ReportConfig(report_type=ReportType.WEEKLY)
        now = datetime.now()

        # Convert to dict if needed
        if hasattr(weekly_data, "to_dict"):
            data = weekly_data.to_dict()
        elif isinstance(weekly_data, dict):
            data = weekly_data
        else:
            data = {}

        week_start = config.date_range_start or date.today()
        week_end = config.date_range_end or date.today()
        title = (
            config.title
            or f"周度投资回顾 - {week_start.strftime('%m/%d')} ~ {week_end.strftime('%m/%d')}"
        )

        # Prepare template context
        context = {
            "title": title,
            "generated_at": now,
            "week_start": week_start,
            "week_end": week_end,
            "data": data,
            "config": config,
        }

        # Generate content based on format
        if config.output_format == OutputFormat.JSON:
            content = json.dumps(data, indent=2, ensure_ascii=False, default=str)
        elif config.output_format == OutputFormat.HTML:
            template = self._get_template("weekly.html.j2")
            content = template.render(**context)
        else:  # MARKDOWN
            template = self._get_template("weekly.md.j2")
            content = template.render(**context)

        return ReportResult(
            report_type=ReportType.WEEKLY,
            content=content,
            output_format=config.output_format,
            generated_at=now,
            title=title,
            metadata={
                "week_start": week_start.isoformat(),
                "week_end": week_end.isoformat(),
            },
        )

    def _get_template(self, template_name: str):
        """
        Get Jinja2 template.

        Args:
            template_name: Name of the template file

        Returns:
            Jinja2 Template object
        """
        try:
            return self.env.get_template(template_name)
        except Exception as e:
            logger.warning(f"Template {template_name} not found: {e}")
            # Return a fallback template
            return self.env.from_string(self._get_fallback_template(template_name))

    def _get_fallback_template(self, template_name: str) -> str:
        """
        Get fallback template string when template file is not found.

        Args:
            template_name: Name of the template file

        Returns:
            Fallback template string
        """
        if "portfolio" in template_name:
            return PORTFOLIO_FALLBACK_TEMPLATE
        elif "technical" in template_name:
            return TECHNICAL_FALLBACK_TEMPLATE
        elif "daily" in template_name:
            return DAILY_FALLBACK_TEMPLATE
        elif "weekly" in template_name:
            return WEEKLY_FALLBACK_TEMPLATE
        else:
            return "{{ title }}\n\nGenerated at: {{ generated_at }}\n\n{{ data }}"


# Fallback templates (used when template files are not found)
PORTFOLIO_FALLBACK_TEMPLATE = """# {{ title }}

生成时间: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}

## 组合概览

{% if data.summary %}
| 指标 | 值 |
|------|-----|
| 持仓数量 | {{ data.summary.position_count }} |
| 总市值 | {{ data.summary.total_market_value|format_currency }} |
| 总盈亏 | {{ data.summary.total_pl_value|format_currency }} |
| 盈亏比例 | {{ data.summary.total_pl_ratio|format_percent }} |
| 胜率 | {{ data.summary.win_rate|format_percent(0) }} |
{% if data.summary.cash_balance is not none %}
| 现金余额 | {{ data.summary.cash_balance|format_currency }} |
{% endif %}
{% endif %}

## 市场配比

{% if data.market_allocation %}
| 市场 | 持仓数 | 市值 | 权重 | 盈亏 |
|------|--------|------|------|------|
{% for alloc in data.market_allocation %}
| {{ alloc.market }} | {{ alloc.position_count }} | {{ alloc.market_value|format_currency }} | {{ alloc.weight|format_percent }} | {{ alloc.pl_value|format_currency }} |
{% endfor %}
{% endif %}

## 持仓明细

{% if data.positions %}
| 股票代码 | 名称 | 数量 | 成本价 | 现价 | 市值 | 盈亏 | 盈亏% | 权重 |
|----------|------|------|--------|------|------|------|-------|------|
{% for pos in data.positions %}
| {{ pos.code }} | {{ pos.name or '-' }} | {{ pos.qty|format_number(0) }} | {{ pos.cost_price|format_currency }} | {{ pos.market_price|format_currency }} | {{ pos.market_value|format_currency }} | {{ pos.pl_value|format_currency }} | {{ pos.pl_ratio|format_percent }} | {{ pos.weight|format_percent }} |
{% endfor %}
{% endif %}

## 风险评估

{% if data.risk_metrics %}
| 风险指标 | 值 | 状态 |
|----------|-----|------|
| 集中度风险 | {{ data.risk_metrics.concentration_risk|upper }} | {% if data.risk_metrics.concentration_risk in ['high', 'very_high'] %}⚠️{% else %}✅{% endif %} |
| HHI指数 | {{ data.risk_metrics.hhi_index|format_number(0) }} | {% if data.risk_metrics.hhi_index > 2500 %}⚠️ 高度集中{% elif data.risk_metrics.hhi_index > 1500 %}⚡ 中等集中{% else %}✅ 分散{% endif %} |
| 分散化得分 | {{ data.risk_metrics.diversification_score|format_number(0) }}/100 | - |
{% if data.risk_metrics.largest_loss_position %}
| 最大亏损持仓 | {{ data.risk_metrics.largest_loss_position }} | {{ data.risk_metrics.largest_loss_ratio|format_percent }} |
{% endif %}
{% endif %}

## 信号提醒

{% if data.signals %}
{% for signal in data.signals %}
- {{ signal }}
{% endfor %}
{% else %}
无特别信号
{% endif %}

---
*本报告由 Investment Analyzer 自动生成*
"""

TECHNICAL_FALLBACK_TEMPLATE = """# {{ title }}

生成时间: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}

{% if data.chart_path %}
## K线图

![K线图]({{ data.chart_path }})
{% endif %}

## 基本信息

{% if data.price_info %}
| 指标 | 值 |
|------|-----|
| 最新价 | {{ data.price_info.close|format_currency if data.price_info.close else '-' }} |
| 开盘价 | {{ data.price_info.open|format_currency if data.price_info.open else '-' }} |
| 最高价 | {{ data.price_info.high|format_currency if data.price_info.high else '-' }} |
| 最低价 | {{ data.price_info.low|format_currency if data.price_info.low else '-' }} |
| 成交量 | {{ data.price_info.volume|format_number(0) if data.price_info.volume else '-' }} |
{% endif %}

## 技术指标

{% if data.indicators %}
### 均线系统
{% if data.indicators.ma %}
| 均线 | 值 | 趋势 |
|------|-----|------|
{% for name, value in data.indicators.ma.items() %}
| {{ name }} | {{ value|format_currency }} | - |
{% endfor %}
{% endif %}

### RSI
{% if data.indicators.rsi %}
| RSI周期 | 值 | 信号 |
|---------|-----|------|
{% for name, value in data.indicators.rsi.items() %}
| {{ name }} | {{ value|format_number }} | {% if value > 70 %}超买{% elif value < 30 %}超卖{% else %}中性{% endif %} |
{% endfor %}
{% endif %}

### MACD
{% if data.indicators.macd %}
| 指标 | 值 |
|------|-----|
| MACD | {{ data.indicators.macd.macd|format_number if data.indicators.macd.macd else '-' }} |
| Signal | {{ data.indicators.macd.signal|format_number if data.indicators.macd.signal else '-' }} |
| Histogram | {{ data.indicators.macd.histogram|format_number if data.indicators.macd.histogram else '-' }} |
{% endif %}

### 布林带
{% if data.indicators.bollinger %}
| 指标 | 值 |
|------|-----|
| 上轨 | {{ data.indicators.bollinger.upper|format_currency if data.indicators.bollinger.upper else '-' }} |
| 中轨 | {{ data.indicators.bollinger.middle|format_currency if data.indicators.bollinger.middle else '-' }} |
| 下轨 | {{ data.indicators.bollinger.lower|format_currency if data.indicators.bollinger.lower else '-' }} |
{% endif %}
{% endif %}

## VCP 形态分析

{% if data.vcp %}
| 指标 | 值 |
|------|-----|
| 状态 | {% if data.vcp.is_vcp %}✅ 检测到VCP{% else %}❌ 未检测到VCP{% endif %} |
| 得分 | {{ data.vcp.score|format_number }}/100 |
| 收缩次数 | {{ data.vcp.contraction_count }} |
{% if data.vcp.pivot_price %}
| 枢轴价 | {{ data.vcp.pivot_price|format_currency }} |
| 距枢轴 | {{ data.vcp.pivot_distance_pct|format_percent }} |
{% endif %}

{% if data.vcp.signals %}
### VCP 信号
{% for signal in data.vcp.signals %}
- {{ signal }}
{% endfor %}
{% endif %}
{% endif %}

## 综合评估

{% if data.summary %}
| 维度 | 评分 | 信号 |
|------|------|------|
{% if data.summary.trend_score is defined %}
| 趋势 | {{ data.summary.trend_score }}/100 | {{ data.summary.trend_signal or '-' }} |
{% endif %}
{% if data.summary.momentum_score is defined %}
| 动量 | {{ data.summary.momentum_score }}/100 | {{ data.summary.momentum_signal or '-' }} |
{% endif %}
{% if data.summary.overall_score is defined %}
| **综合** | **{{ data.summary.overall_score }}/100** | **{{ data.summary.overall_signal or '-' }}** |
{% endif %}
{% endif %}

---
*本报告由 Investment Analyzer 自动生成*
"""

DAILY_FALLBACK_TEMPLATE = """# {{ title }}

生成时间: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}

## 持仓变动

{% if data.trades %}
| 类型 | 数量 | 金额 |
|------|------|------|
| 买入 | {{ data.trades.buy_count or 0 }} 笔 | {{ data.trades.buy_amount|format_currency if data.trades.buy_amount else '-' }} |
| 卖出 | {{ data.trades.sell_count or 0 }} 笔 | {{ data.trades.sell_amount|format_currency if data.trades.sell_amount else '-' }} |
| 净买入 | - | {{ data.trades.net_buy|format_currency if data.trades.net_buy else '-' }} |
{% else %}
今日无交易记录
{% endif %}

## 持仓盈亏

{% if data.pl %}
| 指标 | 值 |
|------|-----|
| 今日盈亏 | {{ data.pl.today_pl|format_currency if data.pl.today_pl else '-' }} |
| 累计盈亏 | {{ data.pl.total_pl|format_currency if data.pl.total_pl else '-' }} |
{% else %}
无盈亏数据
{% endif %}

## 重点关注

{% if data.watchlist_alerts %}
{% for alert in data.watchlist_alerts %}
- {{ alert }}
{% endfor %}
{% else %}
无特别关注事项
{% endif %}

## 技术信号

{% if data.technical_signals %}
{% for signal in data.technical_signals %}
- {{ signal }}
{% endfor %}
{% else %}
无技术信号
{% endif %}

---
*本报告由 Investment Analyzer 自动生成*
"""

WEEKLY_FALLBACK_TEMPLATE = """# {{ title }}

生成时间: {{ generated_at.strftime('%Y-%m-%d %H:%M:%S') }}
统计周期: {{ week_start.strftime('%Y-%m-%d') }} ~ {{ week_end.strftime('%Y-%m-%d') }}

## 本周交易汇总

{% if data.trades %}
| 指标 | 值 |
|------|-----|
| 总交易笔数 | {{ data.trades.total_count or 0 }} |
| 买入金额 | {{ data.trades.buy_amount|format_currency if data.trades.buy_amount else '-' }} |
| 卖出金额 | {{ data.trades.sell_amount|format_currency if data.trades.sell_amount else '-' }} |
{% else %}
本周无交易记录
{% endif %}

## 本周盈亏

{% if data.pl %}
| 指标 | 值 |
|------|-----|
| 实现盈亏 | {{ data.pl.realized_pl|format_currency if data.pl.realized_pl else '-' }} |
| 浮动盈亏变化 | {{ data.pl.unrealized_change|format_currency if data.pl.unrealized_change else '-' }} |
| 总盈亏变化 | {{ data.pl.total_change|format_currency if data.pl.total_change else '-' }} |
{% else %}
无盈亏数据
{% endif %}

## 持仓变化

{% if data.position_changes %}
| 股票 | 变化类型 | 数量变化 | 备注 |
|------|----------|----------|------|
{% for change in data.position_changes %}
| {{ change.code }} | {{ change.type }} | {{ change.qty_change|format_number(0) if change.qty_change else '-' }} | {{ change.note or '-' }} |
{% endfor %}
{% else %}
无持仓变化
{% endif %}

## 下周计划

{% if data.next_week %}
### 关注突破
{% if data.next_week.breakout_candidates %}
{% for candidate in data.next_week.breakout_candidates %}
- {{ candidate }}
{% endfor %}
{% else %}
无
{% endif %}

### 止盈目标
{% if data.next_week.profit_targets %}
{% for target in data.next_week.profit_targets %}
- {{ target }}
{% endfor %}
{% else %}
无
{% endif %}

### 止损预警
{% if data.next_week.stop_loss_alerts %}
{% for alert in data.next_week.stop_loss_alerts %}
- {{ alert }}
{% endfor %}
{% else %}
无
{% endif %}
{% else %}
暂无下周计划
{% endif %}

---
*本报告由 Investment Analyzer 自动生成*
"""


def create_report_generator(templates_dir: Optional[Path] = None) -> ReportGenerator:
    """
    Factory function to create a ReportGenerator.

    Args:
        templates_dir: Optional directory containing Jinja2 templates

    Returns:
        ReportGenerator instance
    """
    return ReportGenerator(templates_dir=templates_dir)


def generate_report(
    report_type: ReportType,
    data: Any,
    config: Optional[ReportConfig] = None,
) -> ReportResult:
    """
    Convenience function to generate a report.

    Args:
        report_type: Type of report to generate
        data: Data for the report
        config: Optional report configuration

    Returns:
        ReportResult with generated report
    """
    config = config or ReportConfig(report_type=report_type)
    if config.report_type != report_type:
        config = ReportConfig(
            report_type=report_type,
            user_id=config.user_id,
            codes=config.codes,
            include_charts=config.include_charts,
            output_format=config.output_format,
            title=config.title,
            date_range_start=config.date_range_start,
            date_range_end=config.date_range_end,
            extra_data=config.extra_data,
        )

    generator = ReportGenerator()
    return generator.generate(config, data)
