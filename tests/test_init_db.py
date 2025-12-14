"""Tests for database initialization script."""

# Import the CLI from init_db script
import sys
from pathlib import Path

from click.testing import CliRunner

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from init_db import cli, get_db_name_from_url, get_server_url


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_db_name_from_url(self):
        """Test extracting database name from URL."""
        url = "postgresql://user:pass@localhost:5432/mydb"
        assert get_db_name_from_url(url) == "mydb"

    def test_get_db_name_from_url_with_params(self):
        """Test extracting database name from URL with query params."""
        url = "postgresql://localhost/mydb?sslmode=require"
        assert get_db_name_from_url(url) == "mydb"

    def test_get_server_url(self):
        """Test getting server URL without database name."""
        url = "postgresql://user:pass@localhost:5432/mydb"
        server_url = get_server_url(url)
        assert server_url == "postgresql://user:pass@localhost:5432/postgres"

    def test_get_server_url_simple(self):
        """Test getting server URL for simple URL."""
        url = "postgresql://localhost/mydb"
        server_url = get_server_url(url)
        assert server_url == "postgresql://localhost/postgres"


class TestCLI:
    """Tests for CLI commands."""

    def test_cli_help(self):
        """Test CLI help output."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Database management commands" in result.output

    def test_init_help(self):
        """Test init command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize database tables" in result.output
        assert "--sql" in result.output

    def test_check_help(self):
        """Test check command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0
        assert "Check database connection" in result.output

    def test_reset_help(self):
        """Test reset command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["reset", "--help"])
        assert result.exit_code == 0
        assert "Reset database" in result.output
        assert "--yes" in result.output

    def test_create_db_help(self):
        """Test create-db command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["create-db", "--help"])
        assert result.exit_code == 0
        assert "Create the database" in result.output

    def test_status_help(self):
        """Test status command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0
        assert "Show database status" in result.output

    def test_seed_help(self):
        """Test seed command help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["seed", "--help"])
        assert result.exit_code == 0
        assert "Add sample seed data" in result.output
        assert "--user" in result.output
