"""Tests for configuration module."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from config import (
    ConfigurationError,
    OpenDConfig,
    Settings,
    UserConfig,
    UsersConfig,
    get_futu_password,
    load_users_config,
    settings,
    validate_user_config,
)


class TestSettings:
    """Tests for global settings."""

    def test_settings_instance_exists(self):
        """Test that global settings instance is available."""
        assert settings is not None
        assert isinstance(settings, Settings)

    def test_database_settings_defaults(self):
        """Test database settings have defaults."""
        assert settings.database.pool_size == 5
        assert settings.database.max_overflow == 10

    def test_futu_settings_defaults(self):
        """Test Futu settings have defaults."""
        assert settings.futu.default_host == "127.0.0.1"
        assert settings.futu.default_port == 11111

    def test_kline_settings_defaults(self):
        """Test K-line settings have defaults."""
        assert settings.kline.default_days == 250
        assert settings.kline.cache_hours == 4
        assert "HK" in settings.kline.markets

    def test_chart_settings_defaults(self):
        """Test chart settings have defaults."""
        assert settings.chart.dpi == 150
        assert settings.chart.style == "yahoo"
        assert settings.chart.volume is True

    def test_project_root_is_valid(self):
        """Test project root path is valid."""
        assert settings.project_root.exists()
        assert settings.project_root.is_dir()


class TestUserConfig:
    """Tests for user configuration."""

    def test_opend_config_defaults(self):
        """Test OpenD config defaults."""
        opend = OpenDConfig()
        assert opend.host == "127.0.0.1"
        assert opend.port == 11111

    def test_user_config_creation(self):
        """Test UserConfig creation."""
        opend = OpenDConfig(host="localhost", port=11112)
        user = UserConfig(
            username="testuser",
            display_name="Test User",
            opend=opend,
            default_markets=["HK", "US"],
            kline_days=90,
            is_active=True,
        )
        assert user.username == "testuser"
        assert user.display_name == "Test User"
        assert user.opend.port == 11112
        assert user.kline_days == 90


class TestLoadUsersConfig:
    """Tests for loading user configuration from YAML."""

    def test_load_valid_config(self):
        """Test loading a valid users.yaml config."""
        config_content = {
            "users": {
                "testuser": {
                    "display_name": "Test User",
                    "opend": {"host": "127.0.0.1", "port": 11111},
                    "default_markets": ["HK"],
                    "kline_days": 60,
                    "is_active": True,
                }
            },
            "defaults": {"kline_days": 120},
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = Path(f.name)

        try:
            users_config = load_users_config(temp_path)
            assert isinstance(users_config, UsersConfig)
            assert "testuser" in users_config.list_usernames()
            user = users_config.get_user("testuser")
            assert user.display_name == "Test User"
            assert user.kline_days == 60
        finally:
            temp_path.unlink()

    def test_load_missing_file(self):
        """Test loading non-existent config file raises error."""
        with pytest.raises(ConfigurationError) as exc_info:
            load_users_config(Path("/nonexistent/users.yaml"))
        assert "not found" in str(exc_info.value)

    def test_load_empty_config(self):
        """Test loading empty config raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_users_config(temp_path)
            assert "empty" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_load_config_no_users(self):
        """Test loading config with no users raises error."""
        config_content = {"defaults": {"kline_days": 120}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ConfigurationError) as exc_info:
                load_users_config(temp_path)
            assert "No users" in str(exc_info.value)
        finally:
            temp_path.unlink()

    def test_defaults_applied(self):
        """Test that defaults are applied to users."""
        config_content = {
            "users": {
                "testuser": {
                    "display_name": "Test",
                }
            },
            "defaults": {
                "opend": {"host": "10.0.0.1", "port": 22222},
                "kline_days": 200,
                "markets": ["A"],
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_content, f)
            temp_path = Path(f.name)

        try:
            users_config = load_users_config(temp_path)
            user = users_config.get_user("testuser")
            assert user.opend.host == "10.0.0.1"
            assert user.opend.port == 22222
            assert user.kline_days == 200
            assert "A" in user.default_markets
        finally:
            temp_path.unlink()


class TestValidateUserConfig:
    """Tests for user configuration validation."""

    def test_valid_config_no_issues(self):
        """Test valid config produces no validation issues (except password)."""
        user = UserConfig(
            username="test",
            display_name="Test",
            opend=OpenDConfig(port=11111),
            default_markets=["HK", "US"],
            kline_days=120,
        )
        issues = validate_user_config(user)
        # Only password warning expected
        assert len(issues) == 1
        assert "password" in issues[0].lower()

    def test_invalid_port_range(self):
        """Test invalid port produces error."""
        user = UserConfig(
            username="test",
            display_name="Test",
            opend=OpenDConfig(port=80),
            default_markets=["HK"],
            kline_days=120,
        )
        issues = validate_user_config(user)
        assert any("port" in issue.lower() for issue in issues)

    def test_invalid_market(self):
        """Test invalid market produces error."""
        user = UserConfig(
            username="test",
            display_name="Test",
            opend=OpenDConfig(),
            default_markets=["INVALID"],
            kline_days=120,
        )
        issues = validate_user_config(user)
        assert any("market" in issue.lower() for issue in issues)

    def test_invalid_kline_days(self):
        """Test invalid kline_days produces error."""
        user = UserConfig(
            username="test",
            display_name="Test",
            opend=OpenDConfig(),
            default_markets=["HK"],
            kline_days=500,
        )
        issues = validate_user_config(user)
        assert any("kline_days" in issue.lower() for issue in issues)


class TestGetFutuPassword:
    """Tests for Futu password retrieval."""

    def test_get_password_from_env(self):
        """Test getting password from environment variable."""
        os.environ["FUTU_PWD_TESTUSER"] = "test_password_123"
        try:
            password = get_futu_password("testuser")
            assert password == "test_password_123"
        finally:
            del os.environ["FUTU_PWD_TESTUSER"]

    def test_get_password_missing(self):
        """Test getting non-existent password returns None."""
        password = get_futu_password("nonexistent_user_xyz")
        assert password is None

    def test_password_case_insensitive_username(self):
        """Test username is converted to uppercase for env var."""
        os.environ["FUTU_PWD_MYUSER"] = "my_password"
        try:
            password = get_futu_password("myuser")
            assert password == "my_password"
            password = get_futu_password("MyUser")
            assert password == "my_password"
        finally:
            del os.environ["FUTU_PWD_MYUSER"]


class TestUsersConfigMethods:
    """Tests for UsersConfig methods."""

    def test_get_active_users(self):
        """Test getting active users."""
        users = {
            "active1": UserConfig(
                username="active1",
                display_name="Active 1",
                opend=OpenDConfig(),
                is_active=True,
            ),
            "inactive": UserConfig(
                username="inactive",
                display_name="Inactive",
                opend=OpenDConfig(),
                is_active=False,
            ),
            "active2": UserConfig(
                username="active2",
                display_name="Active 2",
                opend=OpenDConfig(),
                is_active=True,
            ),
        }
        config = UsersConfig(users=users)
        active = config.get_active_users()
        assert len(active) == 2
        assert all(u.is_active for u in active)

    def test_list_usernames(self):
        """Test listing all usernames."""
        users = {
            "user1": UserConfig(
                username="user1", display_name="User 1", opend=OpenDConfig()
            ),
            "user2": UserConfig(
                username="user2", display_name="User 2", opend=OpenDConfig()
            ),
        }
        config = UsersConfig(users=users)
        usernames = config.list_usernames()
        assert "user1" in usernames
        assert "user2" in usernames
        assert len(usernames) == 2
