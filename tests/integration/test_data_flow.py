"""Integration tests for data flow: fetch → store → analyze → chart."""

import os
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from analysis import (
    PortfolioAnalyzer,
    PositionData,
    TechnicalAnalyzer,
    analyze_portfolio,
)
from analysis.indicators import MACD, OBV, RSI, SMA, BollingerBands, detect_vcp
from charts import ChartConfig, ChartGenerator, ChartStyle
from db.models import Kline, Position


class TestDataFetchToStorage:
    """Test data fetching and storage flow."""

    def test_kline_data_stored_correctly(self, integration_session, sample_klines_db):
        """Test that K-line data is correctly stored in database."""
        # Query stored klines
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

        assert len(klines) == 120
        assert klines[0].market == "HK"

        # Verify OHLCV data integrity
        for kline in klines:
            assert kline.low <= kline.open <= kline.high
            assert kline.low <= kline.close <= kline.high
            assert kline.volume > 0

    def test_position_data_relationships(
        self, integration_session, sample_user, sample_account, sample_positions
    ):
        """Test position data with proper relationships."""
        # Query positions through relationships
        positions = (
            integration_session.query(Position)
            .filter(Position.account_id == sample_account.id)
            .all()
        )

        assert len(positions) == 3

        # Verify account relationship
        for pos in positions:
            assert pos.account.user_id == sample_user.id

        # Verify position calculations
        for pos in positions:
            expected_market_val = pos.qty * pos.market_price
            assert abs(pos.market_val - expected_market_val) < Decimal("0.01")

    def test_trade_data_chronological(self, integration_session, sample_trades):
        """Test trade data is stored chronologically."""
        from db.models import Trade

        trades = integration_session.query(Trade).order_by(Trade.trade_time).all()

        assert len(trades) == 3

        # Verify chronological order
        for i in range(1, len(trades)):
            assert trades[i].trade_time >= trades[i - 1].trade_time


class TestStorageToAnalysis:
    """Test analysis from stored data."""

    def test_technical_analysis_from_klines(
        self, integration_session, sample_klines_db
    ):
        """Test technical analysis on stored K-line data."""
        # Query klines from DB
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

        # Convert to DataFrame
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

        # Run technical analysis
        analyzer = TechnicalAnalyzer()
        result = analyzer.analyze(df)

        assert result is not None
        assert "SMA20" in result.results
        assert "RSI14" in result.results

    def test_individual_indicators_from_db_data(
        self, integration_session, sample_klines_db
    ):
        """Test individual indicators calculation."""
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

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

        # Test RSI
        rsi = RSI(period=14)
        rsi_result = rsi.calculate(df)
        assert rsi_result is not None
        assert len(rsi_result.values) == len(df)

        # Test MACD
        macd = MACD()
        macd_result = macd.calculate(df)
        assert macd_result is not None
        assert "MACD" in macd_result.values.columns

        # Test Bollinger Bands
        bb = BollingerBands(period=20)
        bb_result = bb.calculate(df)
        assert bb_result is not None
        assert "upper" in bb_result.values.columns

    def test_portfolio_analysis_from_positions(
        self, integration_session, sample_positions
    ):
        """Test portfolio analysis from stored positions."""
        positions = integration_session.query(Position).all()

        # Convert to PositionData
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
            for p in positions
        ]

        # Analyze portfolio
        result = analyze_portfolio(position_data)

        assert result is not None
        assert result.summary.position_count == 3
        assert result.summary.total_market_value > 0
        assert len(result.positions) == 3

    def test_vcp_detection_on_db_data(self, integration_session, sample_klines_db):
        """Test VCP pattern detection on stored data."""
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )

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

        # Run VCP detection (may or may not find VCP depending on data)
        result = detect_vcp(df)

        # Just verify it runs without error and returns valid result
        assert result is not None
        assert hasattr(result, "is_vcp")
        assert hasattr(result, "score")


class TestAnalysisToChart:
    """Test chart generation from analysis results."""

    def test_chart_generation_from_df(self, sample_klines, temp_chart_dir):
        """Test chart generation from DataFrame."""
        generator = ChartGenerator()

        output_path = os.path.join(temp_chart_dir, "test_chart.png")
        config = ChartConfig(
            ma_periods=[5, 10, 20],
            show_volume=True,
            figsize=(12, 8),
        )

        result = generator.generate(
            sample_klines,
            title="HK.00700 Test",
            output_path=output_path,
            config=config,
        )

        assert result is not None
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_chart_with_indicators(self, sample_klines, temp_chart_dir):
        """Test chart generation with technical indicators overlaid."""
        generator = ChartGenerator()

        output_path = os.path.join(temp_chart_dir, "chart_with_indicators.png")
        config = ChartConfig(
            ma_periods=[5, 10, 20, 60],
            show_volume=True,
            figsize=(14, 10),
        )

        result = generator.generate(
            sample_klines,
            title="HK.00700 Technical Analysis",
            output_path=output_path,
            config=config,
        )

        assert os.path.exists(output_path)

    def test_batch_chart_generation(self, sample_klines, temp_chart_dir):
        """Test batch chart generation."""
        generator = ChartGenerator()

        # Generate multiple charts
        codes = ["00700", "09988", "03690"]
        for code in codes:
            output_path = os.path.join(temp_chart_dir, f"{code}.png")
            generator.generate(
                sample_klines,
                title=f"HK.{code}",
                output_path=output_path,
            )

        # Verify all charts exist
        for code in codes:
            chart_path = os.path.join(temp_chart_dir, f"{code}.png")
            assert os.path.exists(chart_path)


class TestEndToEndFlow:
    """Test complete end-to-end data flow."""

    def test_complete_analysis_pipeline(
        self,
        integration_session,
        sample_user,
        sample_account,
        sample_positions,
        sample_klines_db,
        temp_chart_dir,
    ):
        """Test complete pipeline: positions + klines → analysis → chart."""
        # Step 1: Get positions from DB
        positions = integration_session.query(Position).all()
        assert len(positions) == 3

        # Step 2: Get klines from DB
        klines = (
            integration_session.query(Kline)
            .filter(Kline.code == "00700")
            .order_by(Kline.trade_date)
            .all()
        )
        assert len(klines) == 120

        # Step 3: Convert to DataFrames
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

        # Step 4: Run technical analysis
        analyzer = TechnicalAnalyzer()
        tech_result = analyzer.analyze(kline_df)
        assert tech_result is not None

        # Step 5: Run portfolio analysis
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
        assert portfolio_result.summary.position_count == 3

        # Step 6: Generate chart
        generator = ChartGenerator()
        output_path = os.path.join(temp_chart_dir, "pipeline_test.png")
        chart_result = generator.generate(
            kline_df,
            title="Pipeline Test - HK.00700",
            output_path=output_path,
        )
        assert os.path.exists(output_path)

    def test_multi_stock_analysis_flow(self, sample_klines, temp_chart_dir):
        """Test analysis flow for multiple stocks."""
        codes = ["00700", "09988", "03690"]
        results = {}

        for code in codes:
            # Generate slight variations of sample data
            df = sample_klines.copy()
            df = df * (1 + (hash(code) % 10) / 100)  # Add variation

            # Run analysis
            analyzer = TechnicalAnalyzer()
            result = analyzer.analyze(df)
            results[code] = result

            # Generate chart
            generator = ChartGenerator()
            output_path = os.path.join(temp_chart_dir, f"multi_{code}.png")
            generator.generate(df, title=f"HK.{code}", output_path=output_path)

        # Verify all analyses completed
        assert len(results) == 3
        for code, result in results.items():
            assert result is not None

        # Verify all charts exist
        for code in codes:
            chart_path = os.path.join(temp_chart_dir, f"multi_{code}.png")
            assert os.path.exists(chart_path)


class TestDataConsistency:
    """Test data consistency across operations."""

    def test_position_pnl_consistency(self, integration_session, sample_positions):
        """Test P&L calculations are consistent."""
        for pos in sample_positions:
            # Recalculate P&L
            expected_pl = (pos.market_price - pos.cost_price) * pos.qty
            expected_ratio = (pos.market_price - pos.cost_price) / pos.cost_price

            # Allow small floating point differences
            assert abs(float(pos.pl_val) - float(expected_pl)) < 1.0
            assert abs(float(pos.pl_ratio) - float(expected_ratio)) < 0.001

    def test_kline_ohlc_validity(self, integration_session, sample_klines_db):
        """Test OHLC data validity constraints."""
        klines = integration_session.query(Kline).all()

        for k in klines:
            # High should be highest
            assert k.high >= k.open
            assert k.high >= k.close
            assert k.high >= k.low

            # Low should be lowest
            assert k.low <= k.open
            assert k.low <= k.close
            assert k.low <= k.high

            # Volume should be positive
            assert k.volume > 0

    def test_trade_account_consistency(
        self, integration_session, sample_account, sample_trades
    ):
        """Test trade-account relationship consistency."""
        from db.models import Trade

        trades = integration_session.query(Trade).all()

        for trade in trades:
            assert trade.account_id == sample_account.id
            assert trade.qty > 0
            assert trade.price > 0
            assert trade.amount > 0

            # Verify amount calculation
            expected_amt = trade.qty * trade.price
            assert abs(float(trade.amount) - float(expected_amt)) < 1.0


class TestErrorHandling:
    """Test error handling in data flow."""

    def test_empty_dataframe_handling(self, temp_chart_dir):
        """Test handling of empty DataFrame."""
        generator = ChartGenerator()
        empty_df = pd.DataFrame()

        output_path = os.path.join(temp_chart_dir, "empty.png")

        with pytest.raises(Exception):
            generator.generate(empty_df, title="Empty", output_path=output_path)

    def test_insufficient_data_handling(self):
        """Test handling of insufficient data for indicators."""
        # DataFrame with only 5 rows (insufficient for RSI-14)
        df = pd.DataFrame(
            {
                "open": [100, 101, 102, 103, 104],
                "high": [102, 103, 104, 105, 106],
                "low": [99, 100, 101, 102, 103],
                "close": [101, 102, 103, 104, 105],
                "volume": [1000, 1100, 1200, 1300, 1400],
            }
        )

        rsi = RSI(period=14)
        result = rsi.calculate(df)

        # Should handle gracefully - result may have NaN values
        assert result is not None

    def test_zero_position_handling(self):
        """Test handling of positions with zero values."""
        position_data = [
            PositionData(
                market="HK",
                code="00700",
                stock_name="Test",
                qty=0,  # Zero quantity
                cost_price=100.0,
                market_price=100.0,
            )
        ]

        result = analyze_portfolio(position_data)
        # Should handle zero positions gracefully
        assert result is not None
