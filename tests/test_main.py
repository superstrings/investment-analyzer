"""Tests for main CLI module."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from main import cli, parse_codes


@pytest.fixture
def runner():
    """Create CLI runner."""
    return CliRunner()


class TestCLIBasic:
    """Basic CLI tests."""

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Investment Analyzer" in result.output
        assert "sync" in result.output
        assert "chart" in result.output
        assert "report" in result.output
        assert "account" in result.output
        assert "db" in result.output
        assert "config" in result.output

    def test_cli_version(self, runner):
        """Test CLI version command."""
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_cli_verbose(self, runner):
        """Test verbose flag doesn't break CLI."""
        result = runner.invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0


class TestSyncCommands:
    """Tests for sync command group."""

    def test_sync_help(self, runner):
        """Test sync command help."""
        result = runner.invoke(cli, ["sync", "--help"])
        assert result.exit_code == 0
        assert "数据同步命令" in result.output
        assert "all" in result.output
        assert "positions" in result.output
        assert "trades" in result.output
        assert "klines" in result.output

    def test_sync_all_help(self, runner):
        """Test sync all subcommand help."""
        result = runner.invoke(cli, ["sync", "all", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--days" in result.output
        assert "--kline-days" in result.output

    def test_sync_positions_help(self, runner):
        """Test sync positions subcommand help."""
        result = runner.invoke(cli, ["sync", "positions", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output

    def test_sync_trades_help(self, runner):
        """Test sync trades subcommand help."""
        result = runner.invoke(cli, ["sync", "trades", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--days" in result.output

    def test_sync_klines_help(self, runner):
        """Test sync klines subcommand help."""
        result = runner.invoke(cli, ["sync", "klines", "--help"])
        assert result.exit_code == 0
        assert "--codes" in result.output
        assert "--days" in result.output

    def test_sync_klines_no_codes(self, runner):
        """Test sync klines requires codes."""
        result = runner.invoke(cli, ["sync", "klines"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestChartCommands:
    """Tests for chart command group."""

    def test_chart_help(self, runner):
        """Test chart command help."""
        result = runner.invoke(cli, ["chart", "--help"])
        assert result.exit_code == 0
        assert "图表生成命令" in result.output
        assert "single" in result.output
        assert "watchlist" in result.output
        assert "positions" in result.output

    def test_chart_single_help(self, runner):
        """Test chart single subcommand help."""
        result = runner.invoke(cli, ["chart", "single", "--help"])
        assert result.exit_code == 0
        assert "--code" in result.output
        assert "--days" in result.output
        assert "--style" in result.output
        assert "--indicators" in result.output
        assert "--output" in result.output

    def test_chart_watchlist_help(self, runner):
        """Test chart watchlist subcommand help."""
        result = runner.invoke(cli, ["chart", "watchlist", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--days" in result.output
        assert "--style" in result.output

    def test_chart_positions_help(self, runner):
        """Test chart positions subcommand help."""
        result = runner.invoke(cli, ["chart", "positions", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--days" in result.output
        assert "--style" in result.output

    def test_chart_single_requires_code(self, runner):
        """Test chart single requires code option."""
        result = runner.invoke(cli, ["chart", "single"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()


class TestReportCommands:
    """Tests for report command group."""

    def test_report_help(self, runner):
        """Test report command help."""
        result = runner.invoke(cli, ["report", "--help"])
        assert result.exit_code == 0
        assert "报告生成命令" in result.output
        assert "portfolio" in result.output
        assert "technical" in result.output

    def test_report_portfolio_help(self, runner):
        """Test report portfolio subcommand help."""
        result = runner.invoke(cli, ["report", "portfolio", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output
        assert "--output" in result.output

    def test_report_technical_help(self, runner):
        """Test report technical subcommand help."""
        result = runner.invoke(cli, ["report", "technical", "--help"])
        assert result.exit_code == 0
        assert "--code" in result.output
        assert "--days" in result.output


class TestAccountCommands:
    """Tests for account command group."""

    def test_account_help(self, runner):
        """Test account command help."""
        result = runner.invoke(cli, ["account", "--help"])
        assert result.exit_code == 0
        assert "账户管理命令" in result.output
        assert "list" in result.output
        assert "info" in result.output

    def test_account_list_help(self, runner):
        """Test account list subcommand help."""
        result = runner.invoke(cli, ["account", "list", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output

    def test_account_info_help(self, runner):
        """Test account info subcommand help."""
        result = runner.invoke(cli, ["account", "info", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output


class TestDBCommands:
    """Tests for db command group."""

    def test_db_help(self, runner):
        """Test db command help."""
        result = runner.invoke(cli, ["db", "--help"])
        assert result.exit_code == 0
        assert "数据库管理命令" in result.output
        assert "check" in result.output
        assert "init" in result.output
        assert "seed" in result.output
        assert "migrate" in result.output

    def test_db_check_help(self, runner):
        """Test db check subcommand help."""
        result = runner.invoke(cli, ["db", "check", "--help"])
        assert result.exit_code == 0

    def test_db_init_help(self, runner):
        """Test db init subcommand help."""
        result = runner.invoke(cli, ["db", "init", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_db_seed_help(self, runner):
        """Test db seed subcommand help."""
        result = runner.invoke(cli, ["db", "seed", "--help"])
        assert result.exit_code == 0
        assert "--user" in result.output

    def test_db_migrate_help(self, runner):
        """Test db migrate subcommand help."""
        result = runner.invoke(cli, ["db", "migrate", "--help"])
        assert result.exit_code == 0
        assert "--direction" in result.output


class TestConfigCommands:
    """Tests for config command group."""

    def test_config_help(self, runner):
        """Test config command help."""
        result = runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "配置管理命令" in result.output
        assert "show" in result.output
        assert "users" in result.output

    def test_config_show(self, runner):
        """Test config show command."""
        result = runner.invoke(cli, ["config", "show"])
        assert result.exit_code == 0
        assert "Database" in result.output
        assert "Futu OpenD" in result.output
        assert "Chart" in result.output
        assert "K-line" in result.output

    def test_config_users(self, runner):
        """Test config users command."""
        result = runner.invoke(cli, ["config", "users"])
        assert result.exit_code == 0
        # Either shows users or indicates none configured


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_parse_codes_single(self):
        """Test parsing single code."""
        codes = parse_codes("HK.00700")
        assert codes == ["HK.00700"]

    def test_parse_codes_multiple(self):
        """Test parsing multiple codes."""
        codes = parse_codes("HK.00700,US.NVDA,HK.09988")
        assert codes == ["HK.00700", "US.NVDA", "HK.09988"]

    def test_parse_codes_with_spaces(self):
        """Test parsing codes with spaces."""
        codes = parse_codes("HK.00700, US.NVDA , HK.09988")
        assert codes == ["HK.00700", "US.NVDA", "HK.09988"]

    def test_parse_codes_empty(self):
        """Test parsing empty string."""
        codes = parse_codes("")
        assert codes == []

    def test_parse_codes_none(self):
        """Test parsing None."""
        codes = parse_codes(None)
        assert codes == []

    def test_parse_codes_trailing_comma(self):
        """Test parsing with trailing comma."""
        codes = parse_codes("HK.00700,US.NVDA,")
        assert codes == ["HK.00700", "US.NVDA"]


class TestUserValidation:
    """Tests for user validation."""

    def test_invalid_user_sync(self, runner):
        """Test sync with invalid user shows error."""
        result = runner.invoke(cli, ["sync", "positions", "-u", "nonexistent_user_xyz"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "invalid" in result.output.lower()

    def test_invalid_user_chart(self, runner):
        """Test chart with invalid user shows error."""
        result = runner.invoke(cli, ["chart", "watchlist", "-u", "nonexistent_user_xyz"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "invalid" in result.output.lower()


class TestDBCheckMocked:
    """Tests for db commands with mocking."""

    @patch("main.check_connection")
    def test_db_check_success(self, mock_check, runner):
        """Test db check with successful connection."""
        mock_check.return_value = True
        result = runner.invoke(cli, ["db", "check"])
        assert result.exit_code == 0
        assert "OK" in result.output or "Success" in result.output

    @patch("main.check_connection")
    def test_db_check_failure(self, mock_check, runner):
        """Test db check with failed connection."""
        mock_check.return_value = False
        result = runner.invoke(cli, ["db", "check"])
        assert result.exit_code != 0
        assert "Error" in result.output or "failed" in result.output.lower()

    @patch("main.init_db")
    def test_db_init_success(self, mock_init, runner):
        """Test db init success."""
        mock_init.return_value = None
        result = runner.invoke(cli, ["db", "init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower() or "Success" in result.output


class TestChartStyleOptions:
    """Tests for chart style options."""

    def test_chart_style_choices(self, runner):
        """Test chart style choices are accepted."""
        for style in ["dark", "light", "chinese", "western"]:
            result = runner.invoke(
                cli,
                ["chart", "single", "--help"],
            )
            assert style in result.output.lower()

    def test_chart_invalid_style(self, runner):
        """Test chart with invalid style is rejected."""
        result = runner.invoke(
            cli,
            ["chart", "single", "-c", "HK.00700", "--style", "invalid_style"],
        )
        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()


class TestSyncKlinesIntegration:
    """Integration-like tests for sync klines."""

    @patch("fetchers.KlineFetcher")
    @patch("services.SyncService")
    def test_sync_klines_success(self, mock_service_cls, mock_fetcher_cls, runner):
        """Test sync klines with mocked service."""
        mock_service = MagicMock()
        mock_service.sync_klines.return_value = MagicMock(
            success=True,
            records_synced=100,
            records_skipped=5,
        )
        mock_service_cls.return_value = mock_service

        result = runner.invoke(
            cli,
            ["sync", "klines", "-c", "HK.00700,US.NVDA", "--days", "60"],
        )

        assert result.exit_code == 0
        assert "Success" in result.output
        mock_service.sync_klines.assert_called_once()
