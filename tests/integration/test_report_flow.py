"""Integration tests for report generation flow."""

import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from analysis import PositionData, TechnicalAnalyzer, analyze_portfolio
from charts import ChartGenerator
from db.models import Kline, Position
from reports import (
    OutputFormat,
    ReportConfig,
    ReportGenerator,
    ReportResult,
    ReportType,
    generate_report,
)


class TestPortfolioReportFlow:
    """Test portfolio report generation flow."""

    def test_positions_to_portfolio_report(
        self, integration_session, sample_positions, temp_report_dir
    ):
        """Test generating portfolio report from positions."""
        # Step 1: Convert DB positions to analysis format
        position_data = [
            PositionData(
                market=p.market,
                code=p.code,
                stock_name=p.stock_name,
                qty=float(p.qty),
                cost_price=float(p.cost_price),
                market_price=float(p.market_price),
                market_val=float(p.market_val),
                pl_val=float(p.pl_val),
                pl_ratio=float(p.pl_ratio),
            )
            for p in sample_positions
        ]

        # Step 2: Run portfolio analysis
        analysis_result = analyze_portfolio(position_data)

        # Step 3: Convert to report data format
        report_data = {
            "title": "测试持仓分析报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "position_count": analysis_result.summary.position_count,
                "total_market_value": analysis_result.summary.total_market_value,
                "total_cost_value": analysis_result.summary.total_cost_value,
                "total_pl_value": analysis_result.summary.total_pl_value,
                "total_pl_ratio": analysis_result.summary.total_pl_ratio,
                "profitable_count": analysis_result.summary.profitable_count,
                "losing_count": analysis_result.summary.losing_count,
                "win_rate": analysis_result.summary.win_rate,
            },
            "positions": [
                {
                    "code": p.code,
                    "name": p.name,
                    "market": p.market,
                    "qty": p.qty,
                    "cost_price": p.cost_price,
                    "market_price": p.market_price,
                    "market_value": p.market_value,
                    "pl_value": p.pl_value,
                    "pl_ratio": p.pl_ratio,
                    "weight": p.weight,
                }
                for p in analysis_result.positions
            ],
            "market_allocation": [
                {
                    "market": m.market,
                    "position_count": m.position_count,
                    "market_value": m.market_value,
                    "weight": m.weight,
                    "pl_value": m.pl_value,
                    "pl_ratio": m.pl_ratio,
                }
                for m in analysis_result.market_allocation
            ],
            "signals": analysis_result.signals,
        }

        # Step 4: Generate report
        generator = ReportGenerator()
        result = generator.generate_portfolio_report(report_data)

        assert result is not None
        assert result.report_type == ReportType.PORTFOLIO
        assert len(result.content) > 0

        # Step 5: Save report
        output_path = os.path.join(temp_report_dir, "portfolio_report.md")
        result.save(output_path)
        assert os.path.exists(output_path)

    def test_portfolio_report_with_risk_metrics(
        self, integration_session, sample_positions, temp_report_dir
    ):
        """Test portfolio report includes risk metrics."""
        position_data = [
            PositionData(
                market=p.market,
                code=p.code,
                stock_name=p.stock_name,
                qty=float(p.qty),
                cost_price=float(p.cost_price),
                market_price=float(p.market_price),
            )
            for p in sample_positions
        ]

        analysis_result = analyze_portfolio(position_data)

        report_data = {
            "title": "风险分析报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "position_count": analysis_result.summary.position_count,
                "total_market_value": analysis_result.summary.total_market_value,
                "total_cost_value": analysis_result.summary.total_cost_value,
                "total_pl_value": analysis_result.summary.total_pl_value,
                "total_pl_ratio": analysis_result.summary.total_pl_ratio,
                "profitable_count": analysis_result.summary.profitable_count,
                "losing_count": analysis_result.summary.losing_count,
                "win_rate": analysis_result.summary.win_rate,
            },
            "risk_metrics": {
                "hhi_index": analysis_result.risk_metrics.hhi_index,
                "concentration_risk": analysis_result.risk_metrics.concentration_risk.value,
                "diversification_score": analysis_result.risk_metrics.diversification_score,
                "total_unrealized_loss": analysis_result.risk_metrics.total_unrealized_loss,
                "positions_at_loss_ratio": analysis_result.risk_metrics.positions_at_loss_ratio,
            },
            "positions": [
                {
                    "code": p.code,
                    "name": p.name,
                    "qty": p.qty,
                    "cost_price": p.cost_price,
                    "market_price": p.market_price,
                    "market_value": p.market_value,
                    "pl_value": p.pl_value,
                    "pl_ratio": p.pl_ratio,
                    "weight": p.weight,
                }
                for p in analysis_result.positions
            ],
            "signals": analysis_result.signals,
        }

        generator = ReportGenerator()
        result = generator.generate_portfolio_report(report_data)

        assert result.content is not None
        assert len(result.content) > 0


class TestTechnicalReportFlow:
    """Test technical analysis report generation flow."""

    def test_klines_to_technical_report(
        self, integration_session, sample_klines_db, temp_report_dir
    ):
        """Test generating technical report from K-lines."""
        # Step 1: Get klines from DB
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

        # Step 2: Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "open": float(k.open),
                    "high": float(k.high),
                    "low": float(k.low),
                    "close": float(k.close),
                    "volume": k.volume,
                }
                for k in klines
            ]
        )

        # Step 3: Run technical analysis
        analyzer = TechnicalAnalyzer()
        analysis_result = analyzer.analyze(df)

        # Step 4: Prepare report data
        latest_close = df["close"].iloc[-1]
        report_data = {
            "title": "技术分析报告 - HK.00700",
            "code": "00700",
            "market": "HK",
            "stock_name": "腾讯控股",
            "generated_at": datetime.now().isoformat(),
            "price_info": {
                "latest_close": latest_close,
                "change_pct": ((latest_close / df["close"].iloc[-2]) - 1) * 100,
                "high_52w": df["high"].max(),
                "low_52w": df["low"].min(),
            },
            "indicators": {},
            "signals": [],
        }

        # Add indicator values
        for name, indicator_result in analysis_result.results.items():
            if hasattr(indicator_result, "values"):
                if isinstance(indicator_result.values, pd.Series):
                    value = indicator_result.values.iloc[-1]
                    if pd.notna(value):
                        report_data["indicators"][name] = round(float(value), 2)

        # Step 5: Generate report
        generator = ReportGenerator()
        result = generator.generate_technical_report(report_data)

        assert result is not None
        assert result.report_type == ReportType.TECHNICAL

        # Step 6: Save report
        output_path = os.path.join(temp_report_dir, "technical_report.md")
        result.save(output_path)
        assert os.path.exists(output_path)

    def test_technical_report_with_chart(
        self, sample_klines, temp_report_dir, temp_chart_dir
    ):
        """Test technical report with chart generation."""
        # Generate chart first
        generator = ChartGenerator()
        chart_path = os.path.join(temp_chart_dir, "tech_chart.png")
        generator.generate(
            sample_klines,
            title="HK.00700",
            output_path=chart_path,
        )

        # Run analysis
        analyzer = TechnicalAnalyzer()
        analysis_result = analyzer.analyze(sample_klines)

        # Prepare report with chart reference
        report_data = {
            "title": "技术分析报告",
            "code": "00700",
            "market": "HK",
            "stock_name": "腾讯控股",
            "generated_at": datetime.now().isoformat(),
            "chart_path": chart_path,
            "price_info": {
                "close": 380.0,
                "open": 375.0,
                "high": 385.0,
                "low": 370.0,
                "volume": 1000000,
                "change_pct": 1.5,
            },
            "indicators": {
                "ma": {"MA5": 378.0, "MA10": 375.0, "MA20": 370.0},
                "rsi": {"RSI14": 55.5},
                "macd": {"macd": 2.3, "signal": 1.8, "histogram": 0.5},
                "bollinger": {"upper": 400.0, "middle": 380.0, "lower": 360.0},
            },
            "signals": ["RSI 中性区间", "MACD 金叉"],
        }

        report_generator = ReportGenerator()
        result = report_generator.generate_technical_report(report_data)

        assert result is not None
        assert os.path.exists(chart_path)


class TestDailyReportFlow:
    """Test daily brief report generation flow."""

    def test_generate_daily_brief(self, temp_report_dir):
        """Test daily brief generation."""
        # Prepare daily data with complete market info
        daily_data = {
            "title": "每日投资简报",
            "date": date.today().isoformat(),
            "generated_at": datetime.now().isoformat(),
            "market_summary": [
                {"name": "恒生指数", "close": 17000.0, "change_pct": 0.5},
                {"name": "标普500", "close": 5000.0, "change_pct": -0.3},
            ],
            "portfolio_summary": {
                "total_value": 60350.0,
                "daily_change": 350.0,
                "daily_change_pct": 0.58,
            },
            "top_movers": [
                {"code": "00700", "name": "腾讯控股", "change_pct": 2.5},
                {"code": "03690", "name": "美团-W", "change_pct": 1.8},
            ],
            "alerts": [
                "HK.00700 接近年内高点",
                "整体仓位集中度偏高",
            ],
        }

        generator = ReportGenerator()
        result = generator.generate_daily_brief(daily_data)

        assert result is not None
        assert result.report_type == ReportType.DAILY

        # Save report
        output_path = os.path.join(temp_report_dir, "daily_brief.md")
        result.save(output_path)
        assert os.path.exists(output_path)

    def test_daily_brief_empty_alerts(self, temp_report_dir):
        """Test daily brief with no alerts."""
        daily_data = {
            "title": "每日投资简报",
            "date": date.today().isoformat(),
            "generated_at": datetime.now().isoformat(),
            "portfolio_summary": {
                "total_value": 60350.0,
                "daily_change": 0,
            },
            "alerts": [],
        }

        generator = ReportGenerator()
        result = generator.generate_daily_brief(daily_data)

        assert result is not None


class TestWeeklyReportFlow:
    """Test weekly review report generation flow."""

    def test_generate_weekly_review(self, temp_report_dir):
        """Test weekly review generation."""
        weekly_data = {
            "title": "周度投资回顾",
            "week_start": "2024-12-09",
            "week_end": "2024-12-13",
            "generated_at": datetime.now().isoformat(),
            "portfolio_performance": {
                "start_value": 58000.0,
                "end_value": 60350.0,
                "change": 2350.0,
                "change_pct": 4.05,
            },
            "trades_summary": {
                "total_trades": 3,
                "buy_trades": 2,
                "sell_trades": 1,
                "total_volume": 58000.0,
            },
            "top_gainers": [
                {"code": "00700", "name": "腾讯控股", "gain_pct": 5.2},
            ],
            "top_losers": [
                {"code": "09988", "name": "阿里巴巴-SW", "loss_pct": -2.1},
            ],
            "notes": "本周市场整体表现良好，科技股领涨。",
        }

        generator = ReportGenerator()
        result = generator.generate_weekly_review(weekly_data)

        assert result is not None
        assert result.report_type == ReportType.WEEKLY

        # Save report
        output_path = os.path.join(temp_report_dir, "weekly_review.md")
        result.save(output_path)
        assert os.path.exists(output_path)


class TestReportOutputFormats:
    """Test different report output formats."""

    def test_markdown_output(self, temp_report_dir):
        """Test Markdown output format."""
        report_data = {
            "title": "Markdown 测试报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "position_count": 3,
                "total_market_value": 60350.0,
                "total_cost_value": 58000.0,
                "total_pl_value": 2350.0,
                "total_pl_ratio": 4.05,
                "win_rate": 66.7,
            },
            "positions": [],
            "signals": [],
        }

        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            output_format=OutputFormat.MARKDOWN,
        )
        result = generator.generate_portfolio_report(report_data, config)

        assert result.output_format == OutputFormat.MARKDOWN
        assert "#" in result.content  # Markdown headers

    def test_json_output(self, temp_report_dir):
        """Test JSON output format."""
        report_data = {
            "title": "JSON 测试报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {"position_count": 3, "total_value": 60350.0},
        }

        generator = ReportGenerator()
        config = ReportConfig(
            report_type=ReportType.PORTFOLIO,
            output_format=OutputFormat.JSON,
        )
        result = generator.generate_portfolio_report(report_data, config)

        assert result.output_format == OutputFormat.JSON

        # Should be valid JSON
        import json

        parsed = json.loads(result.content)
        assert "title" in parsed


class TestCompleteReportPipeline:
    """Test complete report generation pipeline."""

    def test_full_report_pipeline(
        self,
        integration_session,
        sample_user,
        sample_account,
        sample_positions,
        sample_klines_db,
        temp_report_dir,
        temp_chart_dir,
    ):
        """Test complete pipeline: data → analysis → charts → report."""
        # Step 1: Gather all data
        positions = integration_session.query(Position).all()
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

        # Step 2: Analyze portfolio
        position_data = [
            PositionData(
                market=p.market,
                code=p.code,
                stock_name=p.stock_name,
                qty=float(p.qty),
                cost_price=float(p.cost_price),
                market_price=float(p.market_price),
            )
            for p in positions
        ]
        portfolio_result = analyze_portfolio(position_data)

        # Step 3: Analyze technicals
        kline_df = pd.DataFrame(
            [
                {
                    "open": float(k.open),
                    "high": float(k.high),
                    "low": float(k.low),
                    "close": float(k.close),
                    "volume": k.volume,
                }
                for k in klines
            ]
        )
        kline_df.index = pd.to_datetime([k.trade_date for k in klines])

        analyzer = TechnicalAnalyzer()
        tech_result = analyzer.analyze(kline_df)

        # Step 4: Generate charts
        chart_generator = ChartGenerator()
        chart_path = os.path.join(temp_chart_dir, "pipeline_chart.png")
        chart_generator.generate(
            kline_df,
            title="HK.00700 Pipeline Test",
            output_path=chart_path,
        )

        # Step 5: Generate comprehensive report
        report_data = {
            "title": "综合投资分析报告",
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "position_count": portfolio_result.summary.position_count,
                "total_market_value": portfolio_result.summary.total_market_value,
                "total_cost_value": portfolio_result.summary.total_cost_value,
                "total_pl_value": portfolio_result.summary.total_pl_value,
                "total_pl_ratio": portfolio_result.summary.total_pl_ratio,
                "profitable_count": portfolio_result.summary.profitable_count,
                "losing_count": portfolio_result.summary.losing_count,
                "win_rate": portfolio_result.summary.win_rate,
            },
            "positions": [
                {
                    "code": p.code,
                    "name": p.name,
                    "qty": p.qty,
                    "cost_price": p.cost_price,
                    "market_price": p.market_price,
                    "market_value": p.market_value,
                    "pl_value": p.pl_value,
                    "pl_ratio": p.pl_ratio,
                    "weight": p.weight,
                }
                for p in portfolio_result.positions
            ],
            "signals": portfolio_result.signals,
            "chart_path": chart_path,
        }

        generator = ReportGenerator()
        result = generator.generate_portfolio_report(report_data)

        # Save final report
        output_path = os.path.join(temp_report_dir, "comprehensive_report.md")
        result.save(output_path)

        # Verify all outputs
        assert os.path.exists(chart_path)
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_multi_stock_report_pipeline(
        self, sample_klines, temp_report_dir, temp_chart_dir
    ):
        """Test report pipeline for multiple stocks."""
        codes = ["00700", "09988", "03690"]
        stock_reports = []

        for code in codes:
            # Generate chart
            chart_path = os.path.join(temp_chart_dir, f"{code}_report.png")
            generator = ChartGenerator()
            generator.generate(
                sample_klines,
                title=f"HK.{code}",
                output_path=chart_path,
            )

            # Analyze
            analyzer = TechnicalAnalyzer()
            result = analyzer.analyze(sample_klines)

            stock_reports.append(
                {
                    "code": code,
                    "chart_path": chart_path,
                    "analysis_completed": result is not None,
                }
            )

        # Generate combined report data
        combined_data = {
            "title": "多股票技术分析",
            "generated_at": datetime.now().isoformat(),
            "stocks": stock_reports,
        }

        generator = ReportGenerator()
        result = generator.generate_technical_report(combined_data)

        output_path = os.path.join(temp_report_dir, "multi_stock_report.md")
        result.save(output_path)

        assert os.path.exists(output_path)
