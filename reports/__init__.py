"""
Report generation module for Investment Analyzer.

Provides report generation capabilities including:
- Portfolio reports (position analysis, P&L, risk assessment)
- Technical analysis reports (indicators, VCP patterns)
- Daily briefs (summary of daily activity)
- Weekly reviews (performance over the week)

Usage:
    from reports import ReportGenerator, ReportConfig, ReportType

    # Generate portfolio report
    generator = ReportGenerator()
    result = generator.generate_portfolio_report(portfolio_data)
    result.save("reports/output/portfolio.md")

    # Using convenience function
    from reports import generate_report, ReportType
    result = generate_report(ReportType.PORTFOLIO, data)
"""

from .generator import (
    ReportType,
    OutputFormat,
    ReportConfig,
    ReportResult,
    ReportGenerator,
    create_report_generator,
    generate_report,
)

__all__ = [
    "ReportType",
    "OutputFormat",
    "ReportConfig",
    "ReportResult",
    "ReportGenerator",
    "create_report_generator",
    "generate_report",
]
