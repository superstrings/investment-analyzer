"""
User configuration management.

Loads and validates user configurations from users.yaml.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from .settings import get_futu_password, settings


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""

    pass


@dataclass
class OpenDConfig:
    """Futu OpenD connection configuration."""

    host: str = "127.0.0.1"
    port: int = 11111


@dataclass
class UserConfig:
    """Single user configuration."""

    username: str
    display_name: str
    opend: OpenDConfig
    default_markets: list = field(default_factory=lambda: ["HK", "US"])
    kline_days: int = 120
    is_active: bool = True

    @property
    def trade_password(self) -> Optional[str]:
        """Get trade password from environment variable."""
        return get_futu_password(self.username)

    def has_trade_password(self) -> bool:
        """Check if trade password is configured."""
        return self.trade_password is not None


@dataclass
class UsersConfig:
    """Container for all user configurations."""

    users: dict[str, UserConfig] = field(default_factory=dict)
    defaults: dict = field(default_factory=dict)

    def get_user(self, username: str) -> Optional[UserConfig]:
        """Get user configuration by username."""
        return self.users.get(username)

    def get_active_users(self) -> list[UserConfig]:
        """Get all active user configurations."""
        return [user for user in self.users.values() if user.is_active]

    def list_usernames(self) -> list[str]:
        """List all configured usernames."""
        return list(self.users.keys())


def load_users_config(config_path: Optional[Path] = None) -> UsersConfig:
    """
    Load user configurations from YAML file.

    Args:
        config_path: Path to users.yaml. Defaults to settings.users_config_path.

    Returns:
        UsersConfig object with all user configurations.

    Raises:
        ConfigurationError: If configuration file is invalid or missing.
    """
    if config_path is None:
        config_path = settings.users_config_path

    if not config_path.exists():
        raise ConfigurationError(f"User configuration file not found: {config_path}")

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigurationError(f"Invalid YAML in configuration file: {e}")

    if raw_config is None:
        raise ConfigurationError("Configuration file is empty")

    return _parse_users_config(raw_config)


def _parse_users_config(raw_config: dict) -> UsersConfig:
    """Parse raw YAML config into UsersConfig object."""
    defaults = raw_config.get("defaults", {})
    raw_users = raw_config.get("users", {})

    if not raw_users:
        raise ConfigurationError("No users defined in configuration")

    users = {}
    for username, user_data in raw_users.items():
        users[username] = _parse_user_config(username, user_data, defaults)

    return UsersConfig(users=users, defaults=defaults)


def _parse_user_config(username: str, user_data: dict, defaults: dict) -> UserConfig:
    """Parse single user configuration with defaults."""
    if user_data is None:
        user_data = {}

    # Get OpenD config with defaults
    opend_data = user_data.get("opend", {})
    default_opend = defaults.get("opend", {})
    opend = OpenDConfig(
        host=opend_data.get("host", default_opend.get("host", "127.0.0.1")),
        port=opend_data.get("port", default_opend.get("port", 11111)),
    )

    # Get other settings with defaults
    default_markets = user_data.get(
        "default_markets", defaults.get("markets", ["HK", "US"])
    )
    kline_days = user_data.get("kline_days", defaults.get("kline_days", 120))

    return UserConfig(
        username=username,
        display_name=user_data.get("display_name", username),
        opend=opend,
        default_markets=default_markets,
        kline_days=kline_days,
        is_active=user_data.get("is_active", True),
    )


def validate_user_config(user: UserConfig) -> list[str]:
    """
    Validate user configuration and return list of warnings/errors.

    Args:
        user: UserConfig to validate

    Returns:
        List of warning/error messages (empty if valid)
    """
    issues = []

    # Check port range
    if not (1024 <= user.opend.port <= 65535):
        issues.append(
            f"OpenD port {user.opend.port} is outside valid range (1024-65535)"
        )

    # Check markets
    valid_markets = {"HK", "US", "A"}
    for market in user.default_markets:
        if market not in valid_markets:
            issues.append(f"Invalid market '{market}'. Valid markets: {valid_markets}")

    # Check kline days
    if not (1 <= user.kline_days <= 365):
        issues.append(f"kline_days {user.kline_days} should be between 1 and 365")

    # Warn if no trade password
    if not user.has_trade_password():
        issues.append(
            f"No trade password configured for user '{user.username}'. "
            f"Set FUTU_PWD_{user.username.upper()} environment variable."
        )

    return issues


def validate_all_users(users_config: UsersConfig) -> dict[str, list[str]]:
    """
    Validate all user configurations.

    Returns:
        Dict mapping username to list of issues
    """
    all_issues = {}
    for username, user in users_config.users.items():
        issues = validate_user_config(user)
        if issues:
            all_issues[username] = issues
    return all_issues


# Cached users config instance
_users_config: Optional[UsersConfig] = None


def get_users_config() -> UsersConfig:
    """
    Get cached users configuration.

    Loads configuration on first call, caches for subsequent calls.
    """
    global _users_config
    if _users_config is None:
        _users_config = load_users_config()
    return _users_config


def reload_users_config() -> UsersConfig:
    """Reload users configuration from file."""
    global _users_config
    _users_config = load_users_config()
    return _users_config
