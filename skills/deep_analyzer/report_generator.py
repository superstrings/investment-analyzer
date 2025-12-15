"""
Report Generator for Deep Analysis.

Generates comprehensive markdown reports similar to professional
stock analysis reports.
"""

from datetime import date
from typing import Optional

from .deep_analyzer import DeepAnalysisResult, InvestmentRecommendation
from .technical_analyzer import EnhancedTechnicalResult
from .web_data_fetcher import FundamentalData, IndustryData, NewsItem


def generate_deep_analysis_report(result: DeepAnalysisResult) -> str:
    """
    Generate a comprehensive deep analysis report.

    Args:
        result: DeepAnalysisResult from DeepAnalyzer

    Returns:
        Markdown formatted report string
    """
    sections = []

    # Header
    sections.append(_generate_header(result))

    # Executive Summary
    sections.append(_generate_executive_summary(result))

    # Technical Analysis
    if result.technical:
        sections.append(_generate_technical_section(result.technical))

    # Fundamental Analysis
    if result.fundamental:
        sections.append(_generate_fundamental_section(result.fundamental))

    # Industry Analysis
    if result.industry:
        sections.append(_generate_industry_section(result.industry))

    # News and Events
    if result.news_items:
        sections.append(_generate_news_section(result.news_items))

    # Investment Recommendation
    if result.recommendation:
        sections.append(_generate_recommendation_section(result))

    # Risk Assessment
    sections.append(_generate_risk_section(result))

    # Footer
    sections.append(_generate_footer(result))

    return "\n\n".join(sections)


def _generate_header(result: DeepAnalysisResult) -> str:
    """Generate report header."""
    name = result.stock_name or f"{result.market}.{result.code}"
    full_code = f"{result.market}.{result.code}"

    lines = [
        f"# {name} ({full_code}) 深度分析报告",
        "",
        f"**分析日期**: {result.analysis_date}",
        f"**当前价格**: {result.current_price:.2f}",
        f"**综合评分**: {result.overall_score}/100",
        f"**投资评级**: {_rating_to_chinese(result.overall_rating)}",
    ]

    if result.position_held:
        pl = result.position_pl_ratio or 0
        pl_str = f"+{float(pl):.1f}%" if pl >= 0 else f"{float(pl):.1f}%"
        lines.append(f"**持仓状态**: 持有中 ({pl_str})")

    return "\n".join(lines)


def _generate_executive_summary(result: DeepAnalysisResult) -> str:
    """Generate executive summary section."""
    lines = [
        "## 摘要",
        "",
    ]

    # Overall assessment
    lines.append(result.summary)

    # Key points
    if result.technical or result.fundamental:
        lines.append("")
        lines.append("### 关键要点")
        lines.append("")

        if result.technical:
            tech = result.technical
            lines.append(f"- 技术评分: {tech.technical_score}/100 ({tech.technical_rating})")
            lines.append(f"- 趋势状态: {tech.trend.description}")
            if tech.signals:
                lines.append(f"- 买入信号: {', '.join(tech.signals[:3])}")
            if tech.warnings:
                lines.append(f"- 风险信号: {', '.join(tech.warnings[:3])}")

        if result.fundamental:
            fund = result.fundamental
            if fund.pe_ratio:
                lines.append(f"- 市盈率 (PE): {fund.pe_ratio:.1f}")
            if fund.market_cap:
                lines.append(f"- 市值: {fund.market_cap:.1f}B {fund.market_cap_currency}")

    return "\n".join(lines)


def _generate_technical_section(tech: EnhancedTechnicalResult) -> str:
    """Generate technical analysis section."""
    lines = [
        "## 技术面分析",
        "",
    ]

    # Price Summary
    lines.append("### 价格表现")
    lines.append("")
    lines.append("| 周期 | 涨跌幅 |")
    lines.append("|------|--------|")
    lines.append(f"| 1日 | {tech.change_1d:+.2f}% |")
    lines.append(f"| 5日 | {tech.change_5d:+.2f}% |")
    lines.append(f"| 20日 | {tech.change_20d:+.2f}% |")
    lines.append(f"| 60日 | {tech.change_60d:+.2f}% |")

    # Trend Analysis
    lines.append("")
    lines.append("### 趋势分析")
    lines.append("")
    lines.append(f"**当前趋势**: {tech.trend.description}")
    lines.append(f"**趋势强度**: {tech.trend.strength}/100")
    lines.append("")
    lines.append("| 周期 | 方向 |")
    lines.append("|------|------|")
    lines.append(f"| 短期 | {_trend_to_chinese(tech.trend.short_term)} |")
    lines.append(f"| 中期 | {_trend_to_chinese(tech.trend.medium_term)} |")
    lines.append(f"| 长期 | {_trend_to_chinese(tech.trend.long_term)} |")

    # Moving Averages
    lines.append("")
    lines.append("### 均线分析")
    lines.append("")
    lines.append(f"**均线排列**: {_ma_alignment_to_chinese(tech.ma_alignment)}")
    lines.append("")
    lines.append("| 均线 | 价格 | 相对现价 |")
    lines.append("|------|------|----------|")

    current = tech.current_price
    for name, value in [("MA5", tech.ma5), ("MA10", tech.ma10), ("MA20", tech.ma20), ("MA60", tech.ma60)]:
        diff = ((current - value) / value) * 100 if value else 0
        status = "上方" if diff > 0 else "下方"
        lines.append(f"| {name} | {value:.2f} | {status} {abs(diff):.1f}% |")

    # RSI Analysis
    lines.append("")
    lines.append("### RSI 分析")
    lines.append("")
    lines.append(f"- **RSI值**: {tech.rsi.value:.1f}")
    lines.append(f"- **状态**: {_rsi_zone_to_chinese(tech.rsi.zone)}")
    lines.append(f"- **趋势**: {_rsi_trend_to_chinese(tech.rsi.trend)}")
    if tech.rsi.divergence:
        lines.append(f"- **背离**: {_divergence_to_chinese(tech.rsi.divergence)}")

    # MACD Analysis
    lines.append("")
    lines.append("### MACD 分析")
    lines.append("")
    lines.append(f"- **MACD**: {tech.macd.macd_value:.4f}")
    lines.append(f"- **Signal**: {tech.macd.signal_value:.4f}")
    lines.append(f"- **Histogram**: {tech.macd.histogram:.4f}")
    lines.append(f"- **趋势**: {_macd_trend_to_chinese(tech.macd.trend)}")
    if tech.macd.crossover:
        lines.append(f"- **信号**: {_crossover_to_chinese(tech.macd.crossover)}")
    if tech.macd.divergence:
        lines.append(f"- **背离**: {_divergence_to_chinese(tech.macd.divergence)}")

    # OBV Analysis
    lines.append("")
    lines.append("### OBV 成交量分析")
    lines.append("")
    lines.append(f"- **OBV趋势**: {_trend_to_chinese(tech.obv_trend)}")
    lines.append(f"- **OBV评分**: {tech.obv_score:.0f}/100")
    if tech.obv_divergence:
        lines.append(f"- **背离信号**: {_divergence_to_chinese(tech.obv_divergence)}")
    lines.append(f"- **成交量趋势**: {_volume_trend_to_chinese(tech.volume_trend)}")
    lines.append(f"- **成交量比**: {tech.volume_ratio:.2f}x (相对20日均量)")

    # VCP Pattern
    if tech.vcp_detected:
        lines.append("")
        lines.append("### VCP 形态分析")
        lines.append("")
        lines.append(f"- **VCP形态**: 已确认")
        lines.append(f"- **形态阶段**: {tech.vcp_stage or '形成中'}")
        lines.append(f"- **收缩次数**: {tech.vcp_contractions}")
        lines.append(f"- **VCP评分**: {tech.vcp_score:.0f}/100")

    # Bollinger Bands
    lines.append("")
    lines.append("### 布林带分析")
    lines.append("")
    lines.append(f"- **价格位置**: {_bb_position_to_chinese(tech.bb_position)}")
    lines.append(f"- **带宽**: {tech.bb_width:.2f}% (波动性指标)")

    # Support/Resistance
    lines.append("")
    lines.append("### 支撑与阻力")
    lines.append("")
    lines.append("| 级别 | 价格 | 距现价 |")
    lines.append("|------|------|--------|")

    levels = tech.levels
    for name, value in [
        ("阻力2", levels.resistance_2),
        ("阻力1", levels.resistance_1),
        ("轴心", levels.pivot),
        ("支撑1", levels.support_1),
        ("支撑2", levels.support_2),
    ]:
        diff = ((value - current) / current) * 100
        lines.append(f"| {name} | {value:.2f} | {diff:+.1f}% |")

    return "\n".join(lines)


def _generate_fundamental_section(fund: FundamentalData) -> str:
    """Generate fundamental analysis section."""
    lines = [
        "## 基本面分析",
        "",
    ]

    # Valuation
    lines.append("### 估值指标")
    lines.append("")
    lines.append("| 指标 | 数值 | 评价 |")
    lines.append("|------|------|------|")

    if fund.pe_ratio:
        eval_pe = "低估" if fund.pe_ratio < 15 else "合理" if fund.pe_ratio < 30 else "偏高"
        lines.append(f"| 市盈率 (PE) | {fund.pe_ratio:.1f} | {eval_pe} |")
    if fund.pb_ratio:
        eval_pb = "低估" if fund.pb_ratio < 1.5 else "合理" if fund.pb_ratio < 3 else "偏高"
        lines.append(f"| 市净率 (PB) | {fund.pb_ratio:.1f} | {eval_pb} |")
    if fund.ps_ratio:
        lines.append(f"| 市销率 (PS) | {fund.ps_ratio:.1f} | - |")
    if fund.market_cap:
        lines.append(f"| 市值 | {fund.market_cap:.1f}B {fund.market_cap_currency} | - |")

    # Financial Metrics
    if any([fund.roe, fund.revenue_growth, fund.net_margin]):
        lines.append("")
        lines.append("### 财务指标")
        lines.append("")
        lines.append("| 指标 | 数值 | 评价 |")
        lines.append("|------|------|------|")

        if fund.roe:
            eval_roe = "优秀" if fund.roe > 20 else "良好" if fund.roe > 10 else "一般"
            lines.append(f"| ROE | {fund.roe:.1f}% | {eval_roe} |")
        if fund.roa:
            lines.append(f"| ROA | {fund.roa:.1f}% | - |")
        if fund.revenue_growth:
            eval_growth = "高速" if fund.revenue_growth > 30 else "稳健" if fund.revenue_growth > 10 else "低迷"
            lines.append(f"| 营收增长 | {fund.revenue_growth:.1f}% | {eval_growth} |")
        if fund.net_margin:
            lines.append(f"| 净利率 | {fund.net_margin:.1f}% | - |")
        if fund.gross_margin:
            lines.append(f"| 毛利率 | {fund.gross_margin:.1f}% | - |")

    # Dividend
    if fund.dividend_yield:
        lines.append("")
        lines.append("### 股息")
        lines.append("")
        lines.append(f"- **股息率**: {fund.dividend_yield:.2f}%")
        if fund.dividend_payout_ratio:
            lines.append(f"- **派息率**: {fund.dividend_payout_ratio:.1f}%")

    return "\n".join(lines)


def _generate_industry_section(industry: IndustryData) -> str:
    """Generate industry analysis section."""
    lines = [
        "## 行业分析",
        "",
        f"**行业**: {industry.industry}",
        f"**板块**: {industry.sector}",
    ]

    if industry.description:
        lines.append("")
        lines.append("### 行业概述")
        lines.append("")
        lines.append(industry.description[:500])

    if industry.key_trends:
        lines.append("")
        lines.append("### 行业趋势")
        lines.append("")
        for trend in industry.key_trends[:5]:
            lines.append(f"- {trend}")

    if industry.competitors:
        lines.append("")
        lines.append("### 主要竞争对手")
        lines.append("")
        lines.append(", ".join(industry.competitors))

    if industry.industry_outlook:
        lines.append("")
        lines.append("### 行业展望")
        lines.append("")
        lines.append(industry.industry_outlook)

    return "\n".join(lines)


def _generate_news_section(news_items: list[NewsItem]) -> str:
    """Generate news and events section."""
    lines = [
        "## 最新消息与事件",
        "",
    ]

    positive = [n for n in news_items if n.sentiment == "positive"]
    negative = [n for n in news_items if n.sentiment == "negative"]
    neutral = [n for n in news_items if n.sentiment == "neutral"]

    if positive:
        lines.append("### 利好消息")
        lines.append("")
        for item in positive[:5]:
            lines.append(f"- {item.title}")
        lines.append("")

    if negative:
        lines.append("### 利空消息")
        lines.append("")
        for item in negative[:5]:
            lines.append(f"- {item.title}")
        lines.append("")

    if neutral:
        lines.append("### 其他动态")
        lines.append("")
        for item in neutral[:5]:
            lines.append(f"- {item.title}")

    return "\n".join(lines)


def _generate_recommendation_section(result: DeepAnalysisResult) -> str:
    """Generate investment recommendation section."""
    rec = result.recommendation
    if not rec:
        return ""

    lines = [
        "## 投资建议",
        "",
    ]

    # Action recommendations by time horizon
    lines.append("### 操作建议")
    lines.append("")
    lines.append("| 周期 | 建议 | 理由 | 信心度 |")
    lines.append("|------|------|------|--------|")
    lines.append(f"| 短期 (1-2周) | **{_action_to_chinese(rec.short_term_action)}** | {rec.short_term_reason} | {rec.short_term_confidence}% |")
    lines.append(f"| 中期 (1-3月) | **{_action_to_chinese(rec.medium_term_action)}** | {rec.medium_term_reason} | {rec.medium_term_confidence}% |")
    lines.append(f"| 长期 (6-12月) | **{_action_to_chinese(rec.long_term_action)}** | {rec.long_term_reason} | {rec.long_term_confidence}% |")

    # Price targets
    if rec.suggested_entry:
        lines.append("")
        lines.append("### 价格目标")
        lines.append("")

        current = result.current_price
        lines.append("| 类型 | 价格 | 距现价 |")
        lines.append("|------|------|--------|")

        entry_diff = ((rec.suggested_entry - current) / current) * 100
        lines.append(f"| 建议入场 | {rec.suggested_entry:.2f} | {entry_diff:+.1f}% |")

        stop_diff = ((rec.stop_loss - current) / current) * 100
        lines.append(f"| 止损位 | {rec.stop_loss:.2f} | {stop_diff:+.1f}% |")

        target1_diff = ((rec.target_price_1 - current) / current) * 100
        lines.append(f"| 目标价1 | {rec.target_price_1:.2f} | {target1_diff:+.1f}% |")

        target2_diff = ((rec.target_price_2 - current) / current) * 100
        lines.append(f"| 目标价2 | {rec.target_price_2:.2f} | {target2_diff:+.1f}% |")

        # Risk-reward ratio
        if rec.stop_loss and rec.target_price_1:
            risk = current - rec.stop_loss
            reward = rec.target_price_1 - current
            if risk > 0:
                rr_ratio = reward / risk
                lines.append("")
                lines.append(f"**风险收益比**: 1:{rr_ratio:.1f} (目标1)")

    return "\n".join(lines)


def _generate_risk_section(result: DeepAnalysisResult) -> str:
    """Generate risk assessment section."""
    lines = [
        "## 风险评估",
        "",
    ]

    if result.recommendation:
        rec = result.recommendation
        lines.append(f"**风险等级**: {_risk_to_chinese(rec.risk_level)}")
        lines.append("")

        if rec.risk_factors:
            lines.append("### 风险因素")
            lines.append("")
            for factor in rec.risk_factors:
                lines.append(f"- {factor}")

    if result.warnings:
        lines.append("")
        lines.append("### 警示信号")
        lines.append("")
        for warning in result.warnings:
            lines.append(f"- {warning}")

    # General risk disclaimer
    lines.append("")
    lines.append("### 投资提示")
    lines.append("")
    lines.append("- 本报告仅供参考，不构成投资建议")
    lines.append("- 股市有风险，投资需谨慎")
    lines.append("- 请根据自身风险承受能力做出决策")
    lines.append("- 建议设置止损，控制单笔交易风险")

    return "\n".join(lines)


def _generate_footer(result: DeepAnalysisResult) -> str:
    """Generate report footer."""
    lines = [
        "---",
        "",
        f"*报告生成时间: {result.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}*",
        "",
        "*本报告由 Investment Analyzer 自动生成*",
    ]

    if result.errors:
        lines.append("")
        lines.append("**注意**: 部分数据获取失败:")
        for err in result.errors:
            lines.append(f"- {err}")

    return "\n".join(lines)


# Helper functions for Chinese translations
def _rating_to_chinese(rating: str) -> str:
    mapping = {
        "strong_buy": "强烈推荐",
        "buy": "推荐买入",
        "hold": "持有观望",
        "sell": "建议卖出",
        "strong_sell": "强烈卖出",
    }
    return mapping.get(rating, rating)


def _action_to_chinese(action: str) -> str:
    mapping = {
        "buy": "买入",
        "sell": "卖出",
        "hold": "持有",
    }
    return mapping.get(action, action)


def _trend_to_chinese(trend: str) -> str:
    mapping = {
        "up": "上升",
        "down": "下降",
        "sideways": "横盘",
        "strong_up": "强势上升",
        "strong_down": "强势下降",
        "unknown": "未知",
    }
    return mapping.get(trend, trend)


def _ma_alignment_to_chinese(alignment: str) -> str:
    mapping = {
        "bullish": "多头排列",
        "bearish": "空头排列",
        "mixed": "交叉排列",
    }
    return mapping.get(alignment, alignment)


def _rsi_zone_to_chinese(zone: str) -> str:
    mapping = {
        "overbought": "超买区",
        "oversold": "超卖区",
        "neutral": "中性区",
    }
    return mapping.get(zone, zone)


def _rsi_trend_to_chinese(trend: str) -> str:
    mapping = {
        "rising": "上升中",
        "falling": "下降中",
        "flat": "平稳",
    }
    return mapping.get(trend, trend)


def _macd_trend_to_chinese(trend: str) -> str:
    mapping = {
        "bullish": "多头",
        "bearish": "空头",
        "neutral": "中性",
    }
    return mapping.get(trend, trend)


def _crossover_to_chinese(crossover: str) -> str:
    mapping = {
        "golden_cross": "金叉",
        "death_cross": "死叉",
    }
    return mapping.get(crossover, crossover)


def _divergence_to_chinese(divergence: str) -> str:
    mapping = {
        "bullish": "看涨背离",
        "bearish": "看跌背离",
    }
    return mapping.get(divergence, divergence)


def _volume_trend_to_chinese(trend: str) -> str:
    mapping = {
        "increasing": "放量",
        "decreasing": "缩量",
        "stable": "平稳",
    }
    return mapping.get(trend, trend)


def _bb_position_to_chinese(position: str) -> str:
    mapping = {
        "above_upper": "突破上轨",
        "below_lower": "跌破下轨",
        "middle": "轨道内",
    }
    return mapping.get(position, position)


def _risk_to_chinese(risk: str) -> str:
    mapping = {
        "low": "低风险",
        "medium": "中等风险",
        "high": "高风险",
    }
    return mapping.get(risk, risk)
